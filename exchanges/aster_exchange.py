"""
Aster DEX Exchange Module
=========================
Handles data fetching and normalization for Aster DEX.
"""

import pandas as pd
import requests
import time
import hashlib
import hmac
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class AsterExchange(BaseExchange):
    """
    Aster DEX data fetcher and normalizer.
    Features:
    - Perpetual futures contracts
    - API rate limit: 2400 request weight per minute
    - Supports public and authenticated endpoints
    """

    def __init__(self, enabled: bool = True):
        super().__init__("Aster", enabled)
        self.base_url = 'https://fapi.asterdex.com'
        self.logger = setup_logger("AsterExchange")

        # API credentials (optional for public endpoints)
        self.api_key = None
        self.api_secret = None

        # Cache for contract metadata
        self.contract_metadata = {}
        self.funding_intervals = {}  # Cache funding intervals per symbol

        # Rate limiting for Aster: 2400 requests per minute = 40 per second
        # Conservative: use 20 per second for safety
        self.max_concurrent_requests = 20

    def _generate_signature(self, params: Dict[str, Any], timestamp: int) -> str:
        """
        Generate HMAC SHA256 signature for authenticated requests.

        Args:
            params: Query parameters
            timestamp: Current timestamp in milliseconds

        Returns:
            Signature string
        """
        if not self.api_secret:
            return ""

        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        query_string += f"&timestamp={timestamp}"

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Aster DEX API using async/parallel requests.

        Returns:
            DataFrame with raw Aster data
        """
        try:
            # First, get exchange info to get all available symbols and their metadata
            exchange_info_url = f"{self.base_url}/fapi/v1/exchangeInfo"
            exchange_info = self.safe_request(exchange_info_url)

            if not exchange_info or 'symbols' not in exchange_info:
                self.logger.error("Failed to fetch exchange info from Aster")
                return pd.DataFrame()

            # Filter for perpetual contracts only
            perp_symbols = []
            for symbol_info in exchange_info['symbols']:
                if symbol_info.get('contractType') == 'PERPETUAL' and symbol_info.get('status') == 'TRADING':
                    perp_symbols.append(symbol_info['symbol'])
                    # Store metadata for later use
                    self.contract_metadata[symbol_info['symbol']] = {
                        'baseAsset': symbol_info.get('baseAsset'),
                        'quoteAsset': symbol_info.get('quoteAsset'),
                        'pricePrecision': symbol_info.get('pricePrecision'),
                        'quantityPrecision': symbol_info.get('quantityPrecision')
                    }

            if not perp_symbols:
                self.logger.warning("No perpetual contracts found on Aster")
                return pd.DataFrame()

            self.logger.info(f"Found {len(perp_symbols)} perpetual contracts on Aster")

            # Fetch all data in parallel using asyncio
            all_contracts = asyncio.run(self._fetch_all_symbols_async(perp_symbols))

            if not all_contracts:
                self.logger.warning("No contract data collected from Aster")
                return pd.DataFrame()

            df = pd.DataFrame(all_contracts)
            self.logger.info(f"Fetched {len(df)} contracts from Aster")

            # Determine funding intervals from funding times
            df = self._determine_funding_intervals(df)

            return df

        except Exception as e:
            self.logger.error(f"Error fetching Aster data: {e}")
            return pd.DataFrame()

    async def _fetch_all_symbols_async(self, symbols: List[str]) -> List[Dict]:
        """
        Fetch data for all symbols in parallel using asyncio.

        Args:
            symbols: List of symbols to fetch

        Returns:
            List of contract data dictionaries
        """
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Create aiohttp session with connection pooling
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            ttl_dns_cache=300,
            keepalive_timeout=30
        )

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            # Create tasks for all symbols
            tasks = [
                self._fetch_symbol_data_async(session, semaphore, symbol)
                for symbol in symbols
            ]

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out errors and None results
            valid_results = []
            for result in results:
                if isinstance(result, dict) and 'symbol' in result:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    self.logger.debug(f"Error in async fetch: {result}")

            return valid_results

    async def _fetch_symbol_data_async(self, session: aiohttp.ClientSession,
                                       semaphore: asyncio.Semaphore,
                                       symbol: str) -> Optional[Dict]:
        """
        Fetch all data for a single symbol in parallel.

        Args:
            session: aiohttp session
            semaphore: Rate limiting semaphore
            symbol: Symbol to fetch

        Returns:
            Contract data dictionary or None
        """
        async with semaphore:
            try:
                # Fetch all 3 endpoints in parallel for this symbol
                tasks = [
                    self._fetch_endpoint_async(session, f"{self.base_url}/fapi/v1/premiumIndex", {'symbol': symbol}),
                    self._fetch_endpoint_async(session, f"{self.base_url}/fapi/v1/ticker/24hr", {'symbol': symbol}),
                    self._fetch_endpoint_async(session, f"{self.base_url}/fapi/v1/openInterest", {'symbol': symbol})
                ]

                # Wait for all 3 endpoints to complete
                premium_data, ticker_data, oi_data = await asyncio.gather(*tasks, return_exceptions=True)

                # Check if we got valid premium data (required)
                if isinstance(premium_data, Exception) or not premium_data:
                    return None

                # Build contract data
                contract_data = {
                    'symbol': symbol,
                    'fundingRate': premium_data.get('lastFundingRate'),
                    'fundingTime': premium_data.get('nextFundingTime'),
                    'markPrice': premium_data.get('markPrice'),
                    'volume24h': ticker_data.get('volume') if isinstance(ticker_data, dict) else None,
                    'openInterest': oi_data.get('openInterest') if isinstance(oi_data, dict) else None,
                    **self.contract_metadata.get(symbol, {})
                }

                return contract_data

            except Exception as e:
                self.logger.debug(f"Error fetching data for {symbol}: {e}")
                return None

    async def _fetch_endpoint_async(self, session: aiohttp.ClientSession,
                                   url: str,
                                   params: Dict) -> Optional[Dict]:
        """
        Fetch a single endpoint asynchronously.

        Args:
            session: aiohttp session
            url: Endpoint URL
            params: Query parameters

        Returns:
            Response data or None
        """
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited - log but don't retry here
                    self.logger.warning(f"Rate limited on {url}")
                    return None
                else:
                    return None
        except asyncio.TimeoutError:
            self.logger.debug(f"Timeout on {url}")
            return None
        except Exception as e:
            self.logger.debug(f"Error on {url}: {e}")
            return None

    def _determine_funding_intervals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Determine funding intervals based on funding times.
        OPTIMIZED: Using default intervals instead of making 100+ API calls.

        Args:
            df: DataFrame with funding data

        Returns:
            DataFrame with funding_interval_hours column added
        """
        # OPTIMIZATION: Default to 4 hours for Aster (most common interval)
        # This avoids making 100+ extra API calls that slow down collection
        # Can be overridden per symbol if needed in the future
        df['funding_interval_hours'] = 4

        # Optional: If specific symbols need different intervals, set them here
        # Example: df.loc[df['symbol'] == 'BTCUSDT', 'funding_interval_hours'] = 8

        return df

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Aster data to unified format.

        Args:
            df: Raw Aster data

        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())

        try:
            # Convert funding rate to numeric (should already be in decimal format from premiumIndex)
            funding_rate = pd.to_numeric(df['fundingRate'], errors='coerce')

            # Get funding interval hours (default to 8 if not present)
            if 'funding_interval_hours' in df.columns:
                funding_interval_hours = df['funding_interval_hours']
            else:
                funding_interval_hours = 8

            # Calculate APR based on funding interval
            # APR = funding_rate * periods_per_year * 100
            periods_per_year = (365 * 24) / funding_interval_hours
            apr = funding_rate * periods_per_year * 100

            # Normalize asset names (remove prefixes if present)
            def normalize_asset_name(asset):
                if pd.isna(asset):
                    return asset
                asset = str(asset)
                # Remove 'k' prefix for thousands (e.g., kPEPE -> PEPE)
                if asset.startswith('k'):
                    return asset[1:]
                # Remove numerical prefixes (e.g., 1000SHIB -> SHIB)
                if asset.startswith('1000'):
                    return asset[4:]
                return asset

            # Create normalized DataFrame
            normalized = pd.DataFrame({
                'exchange': 'Aster',
                'symbol': df['symbol'],
                'base_asset': df['baseAsset'].apply(normalize_asset_name) if 'baseAsset' in df.columns else df['symbol'].str.replace('USDT', '').str.replace('USDC', ''),
                'quote_asset': df['quoteAsset'] if 'quoteAsset' in df.columns else 'USDT',
                'funding_rate': funding_rate,
                'funding_interval_hours': funding_interval_hours,
                'apr': apr,
                'index_price': pd.to_numeric(df.get('markPrice'), errors='coerce'),  # Using mark price as proxy
                'mark_price': pd.to_numeric(df.get('markPrice'), errors='coerce'),
                'open_interest': pd.to_numeric(df.get('openInterest'), errors='coerce'),
                'contract_type': 'PERPETUAL',
                'market_type': 'Aster DEX',
            })

            # Add volume if available
            if 'volume24h' in df.columns:
                normalized['volume_24h'] = pd.to_numeric(df['volume24h'], errors='coerce')

            # Filter out rows with invalid data
            normalized = normalized[
                normalized['symbol'].notna() &
                normalized['funding_rate'].notna() &
                normalized['mark_price'].notna() &
                (normalized['mark_price'] > 0)
            ]

            self.logger.info(f"Normalized {len(normalized)} contracts for Aster")

            return normalized

        except Exception as e:
            self.logger.error(f"Error normalizing Aster data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())

    def fetch_historical_funding_rates(self, symbol: str, days: int = 30,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol from Aster.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            days: Number of days of history to fetch (ignored if start_time/end_time provided)
            start_time: Optional start datetime (UTC)
            end_time: Optional end datetime (UTC)

        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Calculate time range
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)

            # Convert to milliseconds for API
            start_time_ms = int(start_time.timestamp() * 1000)
            end_time_ms = int(end_time.timestamp() * 1000)

            all_rates = []

            # Fetch funding rate history in batches (API limit is usually 1000 per request)
            url = f"{self.base_url}/fapi/v1/fundingRate"

            current_end = end_time_ms
            while current_end > start_time_ms:
                params = {
                    'symbol': symbol,
                    'endTime': current_end,
                    'limit': 1000  # Maximum allowed by API
                }

                if start_time_ms:
                    params['startTime'] = start_time_ms

                data = self.safe_request(url, params=params)

                if not data:
                    break

                all_rates.extend(data)

                # If we got less than limit, we've reached the end
                if len(data) < 1000:
                    break

                # Update current_end to the earliest timestamp we got
                current_end = min(item['fundingTime'] for item in data) - 1

                # Small delay to respect rate limits
                time.sleep(0.1)

            if not all_rates:
                self.logger.warning(f"No historical data for {symbol}")
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(all_rates)

            # Convert timestamps to datetime
            df['funding_time'] = pd.to_datetime(df['fundingTime'], unit='ms', utc=True)

            # Add additional fields
            df['symbol'] = symbol
            df['exchange'] = 'Aster'

            # Get funding interval for this symbol
            df['funding_interval_hours'] = self.funding_intervals.get(symbol, 8)

            # Normalize base asset
            metadata = self.contract_metadata.get(symbol, {})
            base_asset = metadata.get('baseAsset', symbol.replace('USDT', '').replace('USDC', ''))
            if base_asset.startswith('k'):
                base_asset = base_asset[1:]
            elif base_asset.startswith('1000'):
                base_asset = base_asset[4:]
            df['base_asset'] = base_asset

            # Ensure fundingRate is numeric
            df['fundingRate'] = pd.to_numeric(df['fundingRate'], errors='coerce')

            # Calculate APR for historical rates
            periods_per_year = (365 * 24) / df['funding_interval_hours'].iloc[0]
            df['apr'] = df['fundingRate'] * periods_per_year * 100

            # Rename columns to match our schema
            df = df.rename(columns={
                'fundingRate': 'funding_rate'
            })

            # Select relevant columns
            columns = ['exchange', 'symbol', 'funding_rate', 'funding_time',
                      'funding_interval_hours', 'base_asset', 'apr']

            # Filter columns that exist
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]

            self.logger.info(f"Fetched {len(df)} historical records for {symbol}")

            return df

        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_all_perpetuals_historical(self, days: int = 30, batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all Aster perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to process at once (not used for sequential processing)
            progress_callback: Optional callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)

        Returns:
            Combined DataFrame with all historical funding rates
        """
        # Calculate time range - use provided times or calculate from days
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=days)

        # Calculate actual days for the fetch_historical_funding_rates method
        actual_days = (end_time - start_time).days

        self.logger.info(f"Starting historical data fetch for all Aster perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")

        # Get list of all active symbols
        symbols = self.get_active_symbols()

        if not symbols:
            self.logger.error("No active symbols found on Aster")
            return pd.DataFrame()

        self.logger.info(f"Found {len(symbols)} perpetual contracts")

        all_historical_data = []
        failed_symbols = []

        # Process each symbol
        for i, symbol in enumerate(symbols):
            try:
                # Fetch historical data for this symbol using specified time range
                hist_df = self.fetch_historical_funding_rates(symbol, actual_days, start_time, end_time)

                if not hist_df.empty:
                    all_historical_data.append(hist_df)
                    self.logger.debug(f"Fetched {len(hist_df)} records for {symbol}")
                else:
                    self.logger.debug(f"No historical data for {symbol}")

                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(symbols)) * 100
                    progress_callback(i + 1, len(symbols), progress, f"Processing {symbol}")

                # Small delay to respect rate limits (2400 requests per minute = 40 per second max)
                time.sleep(0.1)  # Conservative delay

            except Exception as e:
                self.logger.error(f"Error fetching historical data for {symbol}: {e}")
                failed_symbols.append(symbol)
                continue

        # Log any failures
        if failed_symbols:
            self.logger.warning(f"Failed to fetch data for {len(failed_symbols)} symbols: {failed_symbols[:10]}")

        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            self.logger.info(f"Successfully fetched {len(combined_df)} total historical records")

            # Sort by funding_time for consistency
            if 'funding_time' in combined_df.columns:
                combined_df = combined_df.sort_values('funding_time', ascending=False)

            return combined_df
        else:
            self.logger.warning("No historical data fetched for any Aster symbol")
            return pd.DataFrame()

    def get_active_symbols(self) -> List[str]:
        """
        Get list of active perpetual contract symbols.

        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        try:
            # Get exchange info
            exchange_info_url = f"{self.base_url}/fapi/v1/exchangeInfo"
            exchange_info = self.safe_request(exchange_info_url)

            if not exchange_info or 'symbols' not in exchange_info:
                return []

            # Filter for active perpetual contracts
            symbols = []
            for symbol_info in exchange_info['symbols']:
                if (symbol_info.get('contractType') == 'PERPETUAL' and
                    symbol_info.get('status') == 'TRADING'):
                    symbols.append(symbol_info['symbol'])

            return sorted(symbols)

        except Exception as e:
            self.logger.error(f"Error getting active symbols: {e}")
            return []