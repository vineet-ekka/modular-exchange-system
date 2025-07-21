"""
Binance Exchange Module
======================
Handles data fetching and normalization for Binance exchange (USD-M and COIN-M).
"""

import pandas as pd
import time
import asyncio
import aiohttp
from typing import List, Dict, Optional
from .base_exchange import BaseExchange
from config.settings import ENABLE_OPEN_INTEREST_FETCH
from utils.rate_limiter import rate_limiter


class BinanceExchange(BaseExchange):
    """
    Binance exchange data fetcher and normalizer.
    Handles both USD-M and COIN-M futures markets.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Binance", enabled)
    
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
        
        # Set funding interval (8 hours is standard for Binance)
        merged_df['fundingIntervalHours'] = 8
        
        return merged_df
    
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
        
        normalized = pd.DataFrame({
            'exchange': 'Binance',
            'symbol': df['symbol'],
            'base_asset': df['baseAsset'],
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