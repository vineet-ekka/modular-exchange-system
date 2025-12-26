"""
MEXC Exchange Module
===================
Handles data fetching and normalization for MEXC exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger
from utils.rate_limiter import rate_limiter
import asyncio
import aiohttp
from asyncio_throttle import Throttler


class MexcExchange(BaseExchange):
    """
    MEXC exchange data fetcher and normalizer.
    Features:
    - Perpetual contracts with funding rates
    - Historical funding rate data
    - Open interest data (holdVol field)
    - 8-hour funding intervals (standard)
    """

    def __init__(self, enabled: bool = True):
        super().__init__("MEXC", enabled)
        self.base_url = 'https://contract.mexc.com/api/v1'
        self.logger = setup_logger("MexcExchange")

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from MEXC API with optimized bulk fetching.
        
        Returns:
            DataFrame with raw MEXC data
        """
        try:
            # Get all contract details
            contracts_data = self._fetch_contract_details()
            if not contracts_data:
                return pd.DataFrame()

            self.logger.info(f"Found {len(contracts_data)} contracts")

            # Try to fetch all funding rates and tickers in bulk first
            all_funding_rates = self._fetch_all_funding_rates()
            all_tickers = self._fetch_all_tickers()
            
            # If bulk fetch failed, fall back to optimized batch processing
            if not all_funding_rates or not all_tickers:
                self.logger.info("Bulk fetch failed, falling back to batch processing")
                return self._fetch_data_batch_optimized(contracts_data)

            # Process data using bulk results
            all_data = []
            for contract in contracts_data:
                symbol = contract['symbol']
                
                # Get funding rate from bulk data
                funding_data = all_funding_rates.get(symbol, {})
                ticker_data = all_tickers.get(symbol, {})
                
                if funding_data:  # Only include contracts with funding data
                    combined_data = {
                        'symbol': symbol,
                        'base_asset': contract.get('baseCoin', ''),
                        'quote_asset': contract.get('quoteCoin', ''),
                        'funding_rate': funding_data.get('fundingRate', 0),
                        'funding_time': funding_data.get('timestamp', 0),
                        'next_funding_time': funding_data.get('nextSettleTime', 0),
                        'funding_interval': funding_data.get('collectCycle', 8),
                        'index_price': ticker_data.get('indexPrice', 0),
                        'mark_price': ticker_data.get('markPrice', 0),
                        'open_interest': ticker_data.get('holdVol', 0),
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
                    all_data.append(combined_data)

            if not all_data:
                self.logger.warning("No funding rate data retrieved from MEXC")
                return pd.DataFrame()

            self.logger.info(f"Successfully processed {len(all_data)} contracts using bulk fetch")
            return pd.DataFrame(all_data)

        except Exception as e:
            self.logger.error(f"Error fetching MEXC data: {e}")
            return pd.DataFrame()

    def _fetch_contract_details(self) -> List[Dict]:
        """
        Fetch all contract details from MEXC.
        
        Returns:
            List of contract data
        """
        try:
            url = f"{self.base_url}/contract/detail"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                return data.get('data', [])
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching contract details: {e}")
            return []

    def _fetch_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current funding rate for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Funding rate data or None
        """
        try:
            url = f"{self.base_url}/contract/funding_rate/{symbol}"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                return data.get('data', {})
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    def _fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data or None
        """
        try:
            url = f"{self.base_url}/contract/ticker"
            params = {'symbol': symbol}
            data = self.safe_request(url, params=params)
            
            if data and data.get('success'):
                return data.get('data', {})
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    def _fetch_all_funding_rates(self) -> Dict[str, Dict]:
        """
        Fetch all funding rates in bulk if possible.
        
        Returns:
            Dictionary of funding rate data by symbol
        """
        try:
            # Try to fetch all funding rates at once
            url = f"{self.base_url}/contract/funding_rate"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                funding_list = data.get('data', [])
                funding_dict = {}
                for item in funding_list:
                    symbol = item.get('symbol')
                    if symbol:
                        funding_dict[symbol] = item
                self.logger.info(f"Fetched {len(funding_dict)} funding rates in bulk")
                return funding_dict
            return {}
            
        except Exception as e:
            self.logger.warning(f"Bulk funding rate fetch failed: {e}")
            return {}

    def _fetch_all_tickers(self) -> Dict[str, Dict]:
        """
        Fetch all tickers in bulk if possible.
        
        Returns:
            Dictionary of ticker data by symbol
        """
        try:
            # Try to fetch all tickers at once
            url = f"{self.base_url}/contract/ticker"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                ticker_list = data.get('data', [])
                ticker_dict = {}
                for item in ticker_list:
                    symbol = item.get('symbol')
                    if symbol:
                        ticker_dict[symbol] = item
                self.logger.info(f"Fetched {len(ticker_dict)} tickers in bulk")
                return ticker_dict
            return {}
            
        except Exception as e:
            self.logger.warning(f"Bulk ticker fetch failed: {e}")
            return {}

    def _fetch_data_batch_optimized(self, contracts_data: List[Dict]) -> pd.DataFrame:
        """
        Optimized batch processing with larger batches and parallel processing.
        Now with connection pooling optimization - each thread reuses connections.

        Args:
            contracts_data: List of contract data

        Returns:
            DataFrame with processed data
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_data = []
        batch_size = 50  # Increased batch size
        total_contracts = len(contracts_data)

        # Pre-initialize sessions for all threads to ensure connection pooling is ready
        # This prevents the overhead of creating sessions on first request in each thread
        self.logger.info("Pre-initializing connection pools for MEXC fallback mode...")

        def process_contract(contract):
            """Process a single contract - now with connection pooling via BaseExchange."""
            symbol = contract['symbol']
            try:
                # Get current funding rate - uses session pooling from BaseExchange
                funding_data = self._fetch_funding_rate(symbol)
                if funding_data:
                    # Get ticker data for open interest and prices - also uses pooling
                    ticker_data = self._fetch_ticker(symbol)
                    
                    # Combine data
                    return {
                        'symbol': symbol,
                        'base_asset': contract.get('baseCoin', ''),
                        'quote_asset': contract.get('quoteCoin', ''),
                        'funding_rate': funding_data.get('fundingRate', 0),
                        'funding_time': funding_data.get('timestamp', 0),
                        'next_funding_time': funding_data.get('nextSettleTime', 0),
                        'funding_interval': funding_data.get('collectCycle', 8),
                        'index_price': ticker_data.get('indexPrice', 0) if ticker_data else 0,
                        'mark_price': ticker_data.get('markPrice', 0) if ticker_data else 0,
                        'open_interest': ticker_data.get('holdVol', 0) if ticker_data else 0,
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
            except Exception as e:
                self.logger.warning(f"Failed to fetch data for {symbol}: {e}")
                return None
            return None
        
        # Process in batches with parallel execution
        for i in range(0, total_contracts, batch_size):
            batch = contracts_data[i:i + batch_size]
            self.logger.info(f"Processing MEXC batch {i//batch_size + 1}/{(total_contracts + batch_size - 1)//batch_size} ({len(batch)} contracts)")
            
            # Use ThreadPoolExecutor for parallel processing within each batch
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_contract = {executor.submit(process_contract, contract): contract for contract in batch}
                
                for future in as_completed(future_to_contract, timeout=30):
                    result = future.result()
                    if result:
                        all_data.append(result)
            
            # Respect rate limits via token bucket between batches
            if i + batch_size < total_contracts:
                rate_limiter.acquire('mexc')

        if not all_data:
            self.logger.warning("No funding rate data retrieved from MEXC")
            return pd.DataFrame()

        self.logger.info(f"Successfully processed {len(all_data)} contracts using optimized batch processing")
        return pd.DataFrame(all_data)

    def normalize_mexc_symbol(self, symbol):
        """Remove numerical prefixes from MEXC symbols like 1000000BABYDOGE -> BABYDOGE"""
        if pd.isna(symbol):
            return symbol

        symbol_str = str(symbol)
        # Remove common numerical prefixes
        prefixes_to_remove = [
            '1000000',  # 1M
            '100000',   # 100K
            '10000',    # 10K
            '1000',     # 1K
            '100',      # 100
            '10',       # 10
        ]

        for prefix in prefixes_to_remove:
            if symbol_str.startswith(prefix):
                return symbol_str[len(prefix):]

        return symbol_str

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform MEXC data to unified format.

        Args:
            df: Raw MEXC data

        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())

        try:
            # Create normalized DataFrame with proper length
            normalized_df = pd.DataFrame(index=df.index)
            
            # Basic mapping
            normalized_df['exchange'] = self.name
            normalized_df['symbol'] = df['symbol'].apply(self.normalize_mexc_symbol)
            normalized_df['base_asset'] = df['base_asset'].apply(self.normalize_mexc_symbol)
            normalized_df['quote_asset'] = df['quote_asset']
            normalized_df['funding_rate'] = df['funding_rate']
            
            # Use actual funding interval from API, default to 8 if not available
            funding_interval = df.get('funding_interval', 8)
            normalized_df['funding_interval_hours'] = funding_interval
            
            normalized_df['contract_type'] = df['contract_type']
            normalized_df['market_type'] = df['market_type']
            
            # Calculate APR based on actual funding interval
            periods_per_year = (365 * 24) / funding_interval
            normalized_df['apr'] = df['funding_rate'] * periods_per_year * 100
            
            # Prices
            normalized_df['index_price'] = df['index_price']
            normalized_df['mark_price'] = df['mark_price']
            
            # Open interest
            normalized_df['open_interest'] = df['open_interest']
            
            # Add timestamps
            if 'funding_time' in df.columns:
                normalized_df['funding_time'] = pd.to_datetime(df['funding_time'], unit='ms', errors='coerce')
            if 'next_funding_time' in df.columns:
                normalized_df['next_funding_time'] = pd.to_datetime(df['next_funding_time'], unit='ms', errors='coerce')
            
            return normalized_df

        except Exception as e:
            self.logger.error(f"Error normalizing MEXC data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())

    def fetch_historical_funding_rates(self, symbol: str, days: int = 30,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a symbol.

        Args:
            symbol: Trading symbol
            days: Number of days to fetch
            start_time: Optional start time for historical data
            end_time: Optional end time for historical data

        Returns:
            DataFrame with historical funding rates
        """
        try:
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)

            url = f"{self.base_url}/contract/funding_rate/history"

            all_records = []
            page_num = 1

            while True:
                params = {
                    'symbol': symbol,
                    'page_num': page_num,
                    'page_size': 1000
                }

                data = self.safe_request(url, params=params)

                if not (data and data.get('success')):
                    break

                page_data = data.get('data', {})
                result_list = page_data.get('resultList', [])
                total_page = page_data.get('totalPage', 0)

                if not result_list:
                    break

                all_records.extend(result_list)

                if page_num >= total_page:
                    break

                page_num += 1
                rate_limiter.acquire('mexc')

            if all_records:
                df = pd.DataFrame(all_records)

                if 'settleTime' in df.columns:
                    df['funding_time'] = pd.to_datetime(df['settleTime'], unit='ms', errors='coerce', utc=True)
                elif 'fundingTime' in df.columns:
                    df['funding_time'] = pd.to_datetime(df['fundingTime'], unit='ms', errors='coerce', utc=True)
                else:
                    return pd.DataFrame()

                if 'fundingRate' in df.columns:
                    df['funding_rate'] = df['fundingRate'].astype(float)
                elif 'rate' in df.columns:
                    df['funding_rate'] = df['rate'].astype(float)
                else:
                    return pd.DataFrame()

                df['symbol'] = symbol

                df = df[df['funding_time'].notna()]
                if not df.empty:
                    df = df[(df['funding_time'] >= start_time) & (df['funding_time'] <= end_time)]

                return df[['symbol', 'funding_rate', 'funding_time']]

            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()

    def _extract_base_asset(self, symbol: str) -> str:
        """
        Extract base asset from MEXC symbol by removing numerical prefixes and quote currency.

        Args:
            symbol: Trading symbol (e.g., '1000SHIBUSDT' or 'BTCUSDT')

        Returns:
            Base asset (e.g., 'SHIB' or 'BTC')
        """
        if not symbol:
            return symbol

        symbol_str = str(symbol)

        prefixes_to_remove = [
            '1000000',
            '100000',
            '10000',
            '1000',
            '100',
            '10',
        ]

        for prefix in prefixes_to_remove:
            if symbol_str.startswith(prefix):
                symbol_str = symbol_str[len(prefix):]
                break

        for quote in ['USDT', 'USDC', 'BUSD']:
            if symbol_str.endswith(quote):
                return symbol_str[:-len(quote)]

        return symbol_str

    def fetch_all_perpetuals_historical(self, days: int = 30,
                                       batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to fetch concurrently (unused, kept for compatibility)
            progress_callback: Callback for progress updates
            start_time: Optional start time (unused, MEXC API uses days/limit)
            end_time: Optional end time (unused, MEXC API uses days/limit)

        Returns:
            Combined DataFrame with all historical funding rates
        """
        try:
            contracts = self._fetch_contract_details()
            if not contracts:
                self.logger.warning("No perpetual contracts found")
                return pd.DataFrame()

            perp_symbols = [c['symbol'] for c in contracts if c.get('symbol')]

            if not perp_symbols:
                self.logger.warning("No perpetual contract symbols found")
                return pd.DataFrame()

            self.logger.info(f"Fetching historical data for {len(perp_symbols)} perpetual contracts")

            all_historical_data = []
            total_symbols = len(perp_symbols)

            for i, symbol in enumerate(perp_symbols):
                try:
                    df = self.fetch_historical_funding_rates(symbol, days, start_time, end_time)
                    if not df.empty:
                        df['exchange'] = 'MEXC'
                        df['funding_interval_hours'] = 8

                        base_asset = self._extract_base_asset(symbol)
                        df['base_asset'] = base_asset
                        df['quote_asset'] = 'USDT'

                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")

                    if progress_callback:
                        progress = ((i + 1) / total_symbols) * 100
                        progress_callback(i + 1, total_symbols, progress, f"Processing {symbol}")

                    rate_limiter.acquire('mexc')

                except Exception as e:
                    self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
                    continue

            if all_historical_data:
                combined_df = pd.concat(all_historical_data, ignore_index=True)
                self.logger.info(f"Completed: fetched {len(combined_df)} total historical records")
                return combined_df
            else:
                self.logger.warning("No historical data fetched")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error in fetch_all_perpetuals_historical: {str(e)}")
            return pd.DataFrame()

    # ============================================
    # ASYNC METHODS FOR HIGH-PERFORMANCE FETCHING
    # ============================================

    async def fetch_historical_async(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        start_time: int = None,
        end_time: int = None,
        throttler: Throttler = None
    ) -> List[Dict]:
        """
        Async method to fetch historical funding rates for a single symbol.

        Args:
            session: aiohttp ClientSession
            symbol: Trading symbol
            start_time: Start timestamp (milliseconds) - unused by MEXC API
            end_time: End timestamp (milliseconds) - unused by MEXC API
            throttler: Optional throttler for rate limiting

        Returns:
            List of historical funding rate records
        """
        try:
            url = f"{self.base_url}/contract/funding_rate/history"
            all_records = []
            page_num = 1
            max_pages = 10  # Safety limit

            while page_num <= max_pages:
                params = {
                    'symbol': symbol,
                    'page_num': page_num,
                    'page_size': 1000  # Maximum page size
                }

                # Make async request with rate limiting
                data = await self.async_safe_request(
                    session, url, 'GET', params=params, throttler=throttler
                )

                if not data or not data.get('success'):
                    break

                records = data.get('data', {}).get('resultList', [])
                if not records:
                    break

                # Process records
                for record in records:
                    processed_record = {
                        'exchange': self.name,
                        'symbol': self.normalize_mexc_symbol(symbol),
                        'funding_rate': float(record.get('fundingRate', 0)),
                        'funding_time': int(record.get('settleTime', 0)),
                        'timestamp': int(record.get('settleTime', 0))
                    }
                    all_records.append(processed_record)

                # Check if there are more pages
                total_pages = data.get('data', {}).get('totalPage', 1)
                if page_num >= total_pages:
                    break

                page_num += 1

            return all_records

        except Exception as e:
            self.logger.error(f"Error in async fetch for {symbol}: {str(e)}")
            return []

    async def fetch_all_perpetuals_historical_async(
        self,
        days: int = 30,
        max_concurrent: int = 30
    ) -> pd.DataFrame:
        """
        Async method to fetch historical data for all MEXC perpetuals.

        Args:
            days: Number of days of history (used for progress, not API)
            max_concurrent: Maximum concurrent requests

        Returns:
            DataFrame with all historical funding rates
        """
        try:
            # Fetch contract list first
            contracts = self._fetch_contract_details()
            if not contracts:
                self.logger.warning("No perpetual contracts found")
                return pd.DataFrame()

            # Get perpetual symbols
            perp_symbols = [c['symbol'] for c in contracts if c.get('symbol')]
            if not perp_symbols:
                self.logger.warning("No perpetual contract symbols found")
                return pd.DataFrame()

            self.logger.info(f"[ASYNC] Fetching historical data for {len(perp_symbols)} MEXC perpetuals")

            # Create rate limiter
            rate_limit = 30  # 30 requests per second for MEXC
            throttler = Throttler(rate_limit=rate_limit, period=1.0)

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)

            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    limit=200,
                    limit_per_host=100,
                    ttl_dns_cache=300,
                    keepalive_timeout=30
                ),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:

                # Create tasks for all symbols
                tasks = []
                for symbol in perp_symbols:
                    task = self._fetch_symbol_with_semaphore_mexc(
                        session, semaphore, throttler, symbol
                    )
                    tasks.append(task)

                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                all_data = []
                successful = 0
                failed = 0

                for symbol, result in zip(perp_symbols, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Failed to fetch {symbol}: {str(result)}")
                        failed += 1
                    elif result:
                        all_data.extend(result)
                        successful += 1
                    else:
                        failed += 1

                self.logger.info(f"[ASYNC] Complete: {successful} successful, {failed} failed, {len(all_data)} total records")

                if all_data:
                    df = pd.DataFrame(all_data)

                    # Add additional columns for compatibility
                    df['exchange'] = self.name
                    df['base_asset'] = df['symbol'].apply(self.normalize_mexc_symbol)
                    df['quote_asset'] = 'USDT'
                    df['funding_interval_hours'] = 8

                    # Convert timestamps
                    df['funding_time'] = pd.to_datetime(df['funding_time'], unit='ms')

                    return df
                else:
                    return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error in async fetch_all_perpetuals: {str(e)}")
            return pd.DataFrame()

    async def _fetch_symbol_with_semaphore_mexc(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        throttler: Throttler,
        symbol: str
    ) -> List[Dict]:
        """
        Fetch historical data for a single symbol with semaphore control.

        Args:
            session: aiohttp ClientSession
            semaphore: Semaphore for concurrency control
            throttler: Throttler for rate limiting
            symbol: Trading symbol

        Returns:
            List of historical records for the symbol
        """
        async with semaphore:  # Limit concurrent requests
            try:
                return await self.fetch_historical_async(
                    session, symbol, throttler=throttler
                )
            except Exception as e:
                self.logger.error(f"Error fetching {symbol}: {str(e)}")
                return []

    def run_async_backfill(self, days: int = 30) -> pd.DataFrame:
        """
        Convenience method to run async backfill from sync context.

        Args:
            days: Number of days of history to fetch

        Returns:
            DataFrame with historical data
        """
        return asyncio.run(self.fetch_all_perpetuals_historical_async(days))
