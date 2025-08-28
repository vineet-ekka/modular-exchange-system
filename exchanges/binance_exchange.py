"""
Binance Exchange Module
======================
Handles data fetching and normalization for Binance exchange (USD-M and COIN-M).
Includes historical funding rate retrieval capabilities.
"""

import pandas as pd
import time
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from .base_exchange import BaseExchange
from config.settings import ENABLE_OPEN_INTEREST_FETCH
from utils.rate_limiter import rate_limiter
from utils.logger import setup_logger


class BinanceExchange(BaseExchange):
    """
    Binance exchange data fetcher and normalizer.
    Handles both USD-M and COIN-M futures markets.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Binance", enabled)
        self.logger = setup_logger("BinanceExchange")
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Binance API (both USD-M and COIN-M).
        
        Returns:
            DataFrame with raw Binance data
        """
        try:
            # Process both USD-M and COIN-M markets
            usdm_df = self._process_binance_market('USD-M')
            coinm_df = self._process_binance_market('COIN-M')
            
            # Combine datasets
            combined_df = pd.concat([usdm_df, coinm_df], ignore_index=True)
            
            return combined_df
            
        except Exception as e:
            print(f"Error fetching Binance data: {str(e)}")
            return pd.DataFrame()
    
    def _process_binance_market(self, market_type: str) -> pd.DataFrame:
        """
        Process a specific Binance market type (USD-M or COIN-M).
        
        Args:
            market_type: Either 'USD-M' or 'COIN-M'
            
        Returns:
            DataFrame for the specific market type
        """
        if market_type == 'USD-M':
            base_url = 'https://fapi.binance.com/fapi/v1/'
        else:  # COIN-M
            base_url = 'https://dapi.binance.com/dapi/v1/'
        
        # Fetch exchange info first
        markets_data = self.safe_request(base_url + 'exchangeInfo')
        if not markets_data:
            return pd.DataFrame()
        
        # Create DataFrame and filter immediately
        df = pd.DataFrame(markets_data['symbols'])
        
        # Filter for perpetuals first
        perp_df = df[df['contractType'] == 'PERPETUAL'].copy()
        
        # Filter out contracts that are not actively trading (e.g., SETTLING, PENDING_TRADING)
        # USD-M uses 'status', COIN-M uses 'contractStatus'
        status_column = 'status' if market_type == 'USD-M' else 'contractStatus'
        
        if status_column in perp_df.columns:
            total_perps = len(perp_df)
            perp_df = perp_df[perp_df[status_column] == 'TRADING'].copy()
            filtered_count = total_perps - len(perp_df)
            
            if filtered_count > 0:
                print(f"  Filtered out {filtered_count} non-trading {market_type} contracts")
        
        # Get list of trading symbols for targeted API calls
        trading_symbols = perp_df['symbol'].tolist()
        
        if not trading_symbols:
            print(f"  No trading {market_type} perpetuals found")
            return pd.DataFrame()
        
        # Fetch mark prices data only for trading symbols
        # Note: Binance premiumIndex endpoint doesn't support symbol filtering,
        # so we still fetch all but only use the ones we need
        mark_prices_data = self.safe_request(base_url + 'premiumIndex')
        if not mark_prices_data:
            return pd.DataFrame()
        
        # Filter mark prices to only trading symbols
        mark_prices_df = pd.DataFrame(mark_prices_data)
        mark_prices_df = mark_prices_df[mark_prices_df['symbol'].isin(trading_symbols)]
        
        # Merge data
        merged_df = perp_df.merge(
            mark_prices_df[['symbol', 'lastFundingRate', 'indexPrice', 'markPrice']], 
            on='symbol', how='left'
        )
        
        # Fetch open interest data only if enabled
        if ENABLE_OPEN_INTEREST_FETCH:
            print(f"  Fetching open interest for {len(merged_df)} {market_type} symbols...")
            
            # Get list of symbols to fetch
            symbols = merged_df['symbol'].tolist()
            
            # Fetch open interest data in parallel
            open_interest_data = self._fetch_open_interest_bulk(base_url, symbols)
            
            successful_oi_calls = len(open_interest_data)
            failed_oi_calls = len(symbols) - successful_oi_calls
            
            # Report results
            if successful_oi_calls > 0 or failed_oi_calls > 0:
                print(f"    Open Interest: {successful_oi_calls} successful, {failed_oi_calls} failed")
            
            # Create open interest DataFrame and merge
            if open_interest_data:
                open_interest_df = pd.DataFrame(open_interest_data)
                merged_df = merged_df.merge(open_interest_df, on='symbol', how='left')
            else:
                merged_df['openInterest'] = None
        else:
            # Skip open interest fetching if disabled
            merged_df['openInterest'] = None
            print(f"  Skipping open interest fetch for {market_type} (disabled in settings)")
        
        # Add market type
        merged_df['binance_market_type'] = market_type
        
        # Fetch and apply correct funding intervals
        merged_df = self._apply_funding_intervals(merged_df, market_type)
        
        return merged_df
    
    def _fetch_funding_intervals(self, market_type: str) -> dict:
        """
        Fetch funding interval information from Binance API.
        
        Args:
            market_type: Either 'USD-M' or 'COIN-M'
            
        Returns:
            Dictionary mapping symbol to funding_interval_hours
        """
        if market_type == 'USD-M':
            url = 'https://fapi.binance.com/fapi/v1/fundingInfo'
        else:  # COIN-M
            url = 'https://dapi.binance.com/dapi/v1/fundingInfo'
        
        # Fetch funding info
        funding_info = self.safe_request(url)
        
        # Create mapping of symbol to funding interval
        interval_map = {}
        if funding_info and isinstance(funding_info, list):
            for item in funding_info:
                if 'symbol' in item and 'fundingIntervalHours' in item:
                    interval_map[item['symbol']] = item['fundingIntervalHours']
        
        return interval_map
    
    def _apply_funding_intervals(self, df: pd.DataFrame, market_type: str) -> pd.DataFrame:
        """
        Apply correct funding intervals to the DataFrame.
        
        Args:
            df: DataFrame with exchange data
            market_type: Either 'USD-M' or 'COIN-M'
            
        Returns:
            DataFrame with correct funding intervals
        """
        # Fetch funding intervals from API
        interval_map = self._fetch_funding_intervals(market_type)
        
        # Apply intervals to DataFrame
        def get_interval(symbol):
            # Check if symbol has custom interval in the API response
            if symbol in interval_map:
                return interval_map[symbol]
            # Default: 8 hours for all contracts not in fundingInfo endpoint
            # (COIN-M contracts and some USD-M contracts use default)
            return 8
        
        df['fundingIntervalHours'] = df['symbol'].apply(get_interval)
        
        # Log the distribution
        interval_counts = df['fundingIntervalHours'].value_counts()
        for interval, count in interval_counts.items():
            print(f"  {market_type}: {count} contracts with {interval}-hour intervals")
        
        return df
    
    def _fetch_open_interest_bulk(self, base_url: str, symbols: List[str]) -> List[Dict]:
        """
        Fetch open interest data for multiple symbols in parallel.
        This replaces the terrible sequential loop with proper async requests.
        
        Args:
            base_url: Binance API base URL
            symbols: List of symbols to fetch
            
        Returns:
            List of dictionaries with symbol and openInterest data
        """
        try:
            return asyncio.run(self._async_fetch_open_interest(base_url, symbols))
        except Exception as e:
            print(f"    Error in bulk open interest fetch: {e}")
            return []
    
    async def _async_fetch_open_interest(self, base_url: str, symbols: List[str]) -> List[Dict]:
        """
        Async method to fetch open interest data with proper rate limiting.
        
        Args:
            base_url: Binance API base URL
            symbols: List of symbols to fetch
            
        Returns:
            List of successful open interest responses
        """
        # Rate limit: Binance allows 2400 requests/minute = 40 requests/second
        # We'll be conservative and do 20 requests/second with batching
        max_concurrent = 20
        results = []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
        ) as session:
            
            tasks = []
            for symbol in symbols:
                task = self._fetch_single_open_interest(session, semaphore, base_url, symbol)
                tasks.append(task)
            
            # Execute all requests concurrently with rate limiting
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful responses
            for response in responses:
                if isinstance(response, dict) and 'symbol' in response:
                    results.append(response)
        
        return results
    
    async def _fetch_single_open_interest(self, session: aiohttp.ClientSession, 
                                        semaphore: asyncio.Semaphore, 
                                        base_url: str, symbol: str) -> Optional[Dict]:
        """
        Fetch open interest for a single symbol with rate limiting.
        
        Args:
            session: aiohttp session
            semaphore: Rate limiting semaphore
            base_url: API base URL
            symbol: Symbol to fetch
            
        Returns:
            Dict with symbol and openInterest, or None if failed
        """
        async with semaphore:  # Rate limiting
            try:
                # Acquire rate limit token
                await asyncio.get_event_loop().run_in_executor(
                    None, rate_limiter.acquire, self.name
                )
                
                url = f"{base_url}openInterest"
                params = {'symbol': symbol}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'openInterest' in data:
                            return {
                                'symbol': symbol,
                                'openInterest': data['openInterest']
                            }
                    elif response.status == 429:
                        # Handle rate limit
                        retry_after = response.headers.get('Retry-After')
                        retry_after_seconds = float(retry_after) if retry_after else None
                        await asyncio.get_event_loop().run_in_executor(
                            None, rate_limiter.handle_429, self.name, retry_after_seconds
                        )
                    
                    # Silent failure for 400 errors (expected for some symbols)
                    return None
                    
            except Exception:
                # Silent failure - we expect some symbols to fail
                return None
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Binance data to unified format.
        
        Args:
            df: Raw Binance data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Add helper function before normalize_data method
        def extract_clean_base_asset(symbol, original_base_asset):
            """
            Extract the actual base asset without multiplier prefixes.
            
            Examples:
            - 1000SHIBUSDT -> SHIB
            - 1000000MOGUSDT -> MOG
            - BTCUSDT -> BTC (unchanged)
            """
            if symbol.startswith('1000000'):
                # Remove the 1000000 prefix and any quote currency suffix
                clean = symbol[7:]  # Remove '1000000'
                # Remove common quote currencies
                for suffix in ['USDT', 'USDC', 'BUSD', 'USD']:
                    if clean.endswith(suffix):
                        return clean[:-len(suffix)]
                return clean
            elif symbol.startswith('1000'):
                # Remove the 1000 prefix and any quote currency suffix
                clean = symbol[4:]  # Remove '1000'
                # Remove common quote currencies
                for suffix in ['USDT', 'USDC', 'BUSD', 'USD']:
                    if clean.endswith(suffix):
                        return clean[:-len(suffix)]
                return clean
            else:
                # Return the original base asset for normal symbols
                return original_base_asset
        
        # Update normalize_data method
        normalized = pd.DataFrame({
            'exchange': 'Binance',
            'symbol': df['symbol'],
            'base_asset': df.apply(lambda row: extract_clean_base_asset(row['symbol'], row['baseAsset']), axis=1),
            'quote_asset': df['quoteAsset'],
            'funding_rate': pd.to_numeric(df['lastFundingRate'], errors='coerce'),
            'funding_interval_hours': pd.to_numeric(df['fundingIntervalHours'], errors='coerce'),
            'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
            'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
            'open_interest': pd.to_numeric(df['openInterest'], errors='coerce') if 'openInterest' in df.columns else None,
            'contract_type': df['contractType'],
            'market_type': ['Binance ' + mt if mt else 'Binance' for mt in df['binance_market_type']] if 'binance_market_type' in df.columns else 'Binance',
        })
        
        return normalized
    
    # ==================== HISTORICAL FUNDING RATE METHODS ====================
    
    def fetch_historical_funding_rates(self, symbol: str, market_type: str = 'USD-M', 
                                      start_time: Optional[datetime] = None, 
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            market_type: Either 'USD-M' or 'COIN-M'
            start_time: Start time for historical data (default: 30 days ago)
            end_time: End time for historical data (default: now)
            
        Returns:
            DataFrame with historical funding rates
        """
        # Set default time range if not provided
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=30)
        
        # Convert to milliseconds timestamp
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        # Determine API endpoint based on market type
        if market_type == 'USD-M':
            base_url = 'https://fapi.binance.com/fapi/v1/'
        else:  # COIN-M
            base_url = 'https://dapi.binance.com/dapi/v1/'
        
        url = base_url + 'fundingRate'
        
        all_rates = []
        current_start = start_ms
        
        # Fetch in batches (max 1000 records per request)
        while current_start < end_ms:
            params = {
                'symbol': symbol,
                'startTime': current_start,
                'endTime': end_ms,
                'limit': 1000
            }
            
            # Rate limited request
            data = self.safe_request(url, params=params)
            
            if not data:
                self.logger.warning(f"Failed to fetch historical rates for {symbol}")
                break
            
            if len(data) == 0:
                # No more data available
                break
            
            all_rates.extend(data)
            
            # If we got less than 1000 records, we've reached the end
            if len(data) < 1000:
                break
            
            # Update start time for next batch (last funding time + 1ms)
            last_time = data[-1]['fundingTime']
            current_start = last_time + 1
        
        if not all_rates:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_rates)
        
        # Convert timestamps
        df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['symbol'] = symbol
        df['exchange'] = 'Binance'
        df['market_type'] = market_type
        
        # Extract base_asset from symbol
        df['base_asset'] = self._extract_base_asset(symbol, market_type)
        
        # Rename columns to match our schema
        df = df.rename(columns={
            'fundingTime': 'funding_time',
            'fundingRate': 'funding_rate',
            'markPrice': 'mark_price'
        })
        
        # Auto-detect funding interval
        if len(df) > 1:
            df['funding_interval_hours'] = self._detect_funding_interval(df['funding_time'])
        else:
            # Default to 8 hours if we can't detect
            df['funding_interval_hours'] = 8
        
        return df
    
    def _extract_base_asset(self, symbol: str, market_type: str) -> str:
        """
        Extract base asset from symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT', 'BTCUSD_PERP')
            market_type: Either 'USD-M' or 'COIN-M'
            
        Returns:
            Base asset (e.g., 'BTC')
        """
        if market_type == 'COIN-M':
            # COIN-M symbols like BTCUSD_PERP -> BTC
            if '_' in symbol:
                # Remove the _PERP or _YYMMDD suffix
                base_part = symbol.split('_')[0]
                # Remove USD from the end to get base asset
                if base_part.endswith('USD'):
                    return base_part[:-3]
            return symbol  # Fallback
        else:
            # USD-M symbols like BTCUSDT -> BTC
            # Handle 1000000 prefix first
            if symbol.startswith('1000000'):
                # Remove the 1000000 prefix and any quote currency suffix
                clean = symbol[7:]  # Remove '1000000'
                # Remove common quote currencies
                for quote in ['USDT', 'USDC', 'BUSD', 'TUSD']:
                    if clean.endswith(quote):
                        return clean[:-len(quote)]
                return clean
            elif symbol.startswith('1000'):
                # Remove the 1000 prefix and any quote currency suffix
                clean = symbol[4:]  # Remove '1000'
                # Remove common quote currencies
                for quote in ['USDT', 'USDC', 'BUSD', 'TUSD']:
                    if clean.endswith(quote):
                        return clean[:-len(quote)]
                return clean
            else:
                # Remove common quote currencies for normal symbols
                for quote in ['USDT', 'USDC', 'BUSD', 'TUSD']:
                    if symbol.endswith(quote):
                        return symbol[:-len(quote)]
            return symbol  # Fallback
    
    def _detect_funding_interval(self, funding_times: pd.Series) -> int:
        """
        Auto-detect funding interval from timestamps.
        
        Args:
            funding_times: Series of funding timestamps
            
        Returns:
            Detected interval in hours (4 or 8)
        """
        if len(funding_times) < 2:
            return 8  # Default to 8 hours
        
        # Calculate time differences
        time_diffs = funding_times.diff().dropna()
        
        # Get the most common interval in hours
        hours_diffs = time_diffs.dt.total_seconds() / 3600
        
        # Round to nearest hour and get mode
        rounded_hours = hours_diffs.round()
        most_common = rounded_hours.mode()
        
        if len(most_common) > 0:
            interval = int(most_common.iloc[0])
            # Binance uses either 4-hour or 8-hour intervals
            if interval <= 5:
                return 4
            else:
                return 8
        
        return 8  # Default to 8 hours
    
    def fetch_all_perpetuals_historical(self, days: int = 30, 
                                       batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all perpetual contracts.
        
        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to fetch concurrently
            progress_callback: Callback for progress updates
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
        
        # Log the date range being used
        actual_days = (end_time - start_time).days
        print(f"\n{'='*60}")
        print(f"BINANCE: Starting historical data fetch")
        print(f"Date range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')} ({actual_days} days)")
        print(f"{'='*60}")
        self.logger.info(f"Starting historical data fetch for all Binance perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")
        
        # Get list of all perpetual contracts
        perpetuals_usdm = self._get_perpetual_symbols('USD-M')
        perpetuals_coinm = self._get_perpetual_symbols('COIN-M')
        
        all_historical_data = []
        
        # Calculate total symbols for progress tracking
        total_symbols = len(perpetuals_usdm) + len(perpetuals_coinm)
        symbols_processed = 0
        
        # Process USD-M perpetuals
        print(f"BINANCE: Found {len(perpetuals_usdm)} USD-M perpetual contracts to process")
        self.logger.info(f"Fetching historical data for {len(perpetuals_usdm)} USD-M perpetuals")
        for i in range(0, len(perpetuals_usdm), batch_size):
            batch = perpetuals_usdm[i:i+batch_size]
            
            for symbol in batch:
                try:
                    df = self.fetch_historical_funding_rates(
                        symbol, 'USD-M', start_time, end_time
                    )
                    if not df.empty:
                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error fetching {symbol}: {e}")
                
                # Update progress
                symbols_processed += 1
                if progress_callback:
                    progress = (symbols_processed / total_symbols) * 100
                    progress_callback(symbols_processed, total_symbols, progress, f"Processing {symbol}")
                
                # Print progress every 50 symbols
                if symbols_processed % 50 == 0:
                    print(f"BINANCE: Progress - {symbols_processed}/{total_symbols} contracts ({progress:.1f}%)")
                
                # Small delay to respect rate limits
                time.sleep(0.2)
        
        # Process COIN-M perpetuals
        print(f"BINANCE: Found {len(perpetuals_coinm)} COIN-M perpetual contracts to process")
        self.logger.info(f"Fetching historical data for {len(perpetuals_coinm)} COIN-M perpetuals")
        for i in range(0, len(perpetuals_coinm), batch_size):
            batch = perpetuals_coinm[i:i+batch_size]
            
            for symbol in batch:
                try:
                    df = self.fetch_historical_funding_rates(
                        symbol, 'COIN-M', start_time, end_time
                    )
                    if not df.empty:
                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error fetching {symbol}: {e}")
                
                # Update progress
                symbols_processed += 1
                if progress_callback:
                    progress = (symbols_processed / total_symbols) * 100
                    progress_callback(symbols_processed, total_symbols, progress, f"Processing {symbol}")
                
                # Print progress every 50 symbols
                if symbols_processed % 50 == 0:
                    print(f"BINANCE: Progress - {symbols_processed}/{total_symbols} contracts ({progress:.1f}%)")
                
                # Small delay to respect rate limits
                time.sleep(0.2)
        
        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            print(f"BINANCE: Completed! Fetched {len(combined_df)} total historical records")
            print(f"BINANCE: {len(perpetuals_usdm)} USD-M + {len(perpetuals_coinm)} COIN-M = {total_symbols} total contracts")
            self.logger.info(f"Completed: fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            print(f"BINANCE: WARNING - No historical data was fetched")
            self.logger.warning("No historical data fetched")
            return pd.DataFrame()
    
    def _get_perpetual_symbols(self, market_type: str) -> List[str]:
        """
        Get list of all perpetual contract symbols.
        
        Args:
            market_type: Either 'USD-M' or 'COIN-M'
            
        Returns:
            List of perpetual contract symbols
        """
        if market_type == 'USD-M':
            base_url = 'https://fapi.binance.com/fapi/v1/'
        else:  # COIN-M
            base_url = 'https://dapi.binance.com/dapi/v1/'
        
        # Fetch exchange info
        exchange_info = self.safe_request(base_url + 'exchangeInfo')
        
        if not exchange_info or 'symbols' not in exchange_info:
            return []
        
        # Filter for perpetual contracts that are trading
        perpetuals = []
        for symbol_info in exchange_info['symbols']:
            if symbol_info.get('contractType') == 'PERPETUAL':
                # Check if actively trading
                status_field = 'status' if market_type == 'USD-M' else 'contractStatus'
                if symbol_info.get(status_field) == 'TRADING':
                    perpetuals.append(symbol_info['symbol'])
        
        self.logger.info(f"Found {len(perpetuals)} active {market_type} perpetual contracts")
        return perpetuals 