"""
Pacifica Exchange Module
=======================
Handles data fetching and normalization for Pacifica Finance exchange.
Includes historical funding rate retrieval capabilities.
"""

import pandas as pd
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from .base_exchange import BaseExchange
from utils.logger import setup_logger
from utils.rate_limiter import rate_limiter


class PacificaExchange(BaseExchange):
    """
    Pacifica Finance exchange data fetcher and normalizer.
    Handles perpetual contracts with funding rate data.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Pacifica", enabled)
        self.logger = setup_logger("PacificaExchange")
        self.base_url = "https://api.pacifica.fi"
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Pacifica API using the prices endpoint for richer data.
        
        Returns:
            DataFrame with raw Pacifica data
        """
        try:
            # Fetch market prices from Pacifica API (includes open interest, mark prices, etc.)
            url = f"{self.base_url}/api/v1/info/prices"
            data = self.safe_request(url)
            
            if not data or not data.get('success'):
                print(f"! Pacifica API returned unsuccessful response: {data}")
                return pd.DataFrame()
            
            markets = data.get('data', [])
            if not markets:
                print("! No market data received from Pacifica")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(markets)
            
            # Add exchange-specific metadata
            df['exchange'] = 'Pacifica'
            df['contract_type'] = 'PERPETUAL'
            df['market_type'] = 'Pacifica'
            
            # Pacifica uses 1-hour funding intervals (based on API docs)
            df['funding_interval_hours'] = 1
            
            # Map Pacifica API fields to our expected field names
            # Pacifica uses 'funding' for current funding rate, 'next_funding' for next funding rate
            if 'funding' in df.columns:
                df['funding_rate'] = df['funding']
            if 'next_funding' in df.columns:
                df['next_funding_rate'] = df['next_funding']
            
            print(f"  Fetched {len(df)} contracts from Pacifica")
            return df
            
        except Exception as e:
            print(f"Error fetching Pacifica data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Pacifica data to unified format.
        
        Args:
            df: Raw Pacifica data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Extract base and quote assets from symbol
        def extract_assets(symbol):
            """Extract base and quote assets from Pacifica symbol format."""
            # Pacifica symbols are simple like "ETH", "BTC", etc.
            # They don't have quote currency suffixes like other exchanges
            return symbol, 'USD'  # Pacifica uses USD as quote currency
        
        # Apply asset extraction
        assets = df['symbol'].apply(extract_assets)
        df['base_asset'] = [asset[0] for asset in assets]
        df['quote_asset'] = [asset[1] for asset in assets]
        
        # Convert open interest from token units to USD by multiplying by mark price
        open_interest_tokens = pd.to_numeric(df.get('open_interest', 0), errors='coerce')
        mark_price = pd.to_numeric(df.get('mark', 0), errors='coerce')
        open_interest_usd = open_interest_tokens * mark_price
        
        # Normalize to unified format
        normalized = pd.DataFrame({
            'exchange': 'Pacifica',
            'symbol': df['symbol'],
            'base_asset': df['base_asset'],
            'quote_asset': df['quote_asset'],
            'funding_rate': pd.to_numeric(df.get('funding_rate', df.get('funding', 0)), errors='coerce'),
            'funding_interval_hours': pd.to_numeric(df['funding_interval_hours'], errors='coerce'),
            'index_price': pd.to_numeric(df.get('oracle', 0), errors='coerce'),  # Oracle price from Pacifica
            'mark_price': pd.to_numeric(df.get('mark', 0), errors='coerce'),     # Mark price from Pacifica
            'open_interest': open_interest_usd,  # Open interest converted to USD
            'contract_type': df['contract_type'],
            'market_type': df['market_type'],
        })
        
        return normalized
    
    def fetch_historical_funding_rates(self, symbol: str, 
                                      start_time: Optional[datetime] = None, 
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'ETH')
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
        
        # Convert to milliseconds timestamp for Pacifica API
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        url = f"{self.base_url}/api/v1/funding_rate/history"

        all_rates = []
        cursor = None
        limit = 200
        max_iterations = 500
        iteration = 0

        # Fetch in batches using cursor pagination
        while iteration < max_iterations:
            iteration += 1
            params = {
                'symbol': symbol,
                'limit': limit
            }

            # Add cursor if we have one from previous page
            if cursor:
                params['cursor'] = cursor

            # Rate limited request
            data = self.safe_request(url, params=params)

            if not data or not data.get('success'):
                self.logger.warning(f"Failed to fetch historical rates for {symbol}")
                break

            rates = data.get('data', [])
            if not rates:
                break

            # Filter by time range and check if we can stop early
            filtered_rates = []
            all_out_of_range = True

            for rate in rates:
                created_at = rate.get('created_at', 0)
                if start_ms <= created_at <= end_ms:
                    filtered_rates.append(rate)
                    all_out_of_range = False
                elif created_at < start_ms:
                    all_out_of_range = True
                    break

            all_rates.extend(filtered_rates)

            # Stop if we've gone past our time range (timestamps are descending)
            if all_out_of_range and len(all_rates) > 0:
                self.logger.info(f"Reached end of time range for {symbol}")
                break

            # Check API pagination fields
            has_more = data.get('has_more', False)
            if not has_more:
                break

            # Get cursor for next page
            cursor = data.get('next_cursor')
            if not cursor:
                break

            # Respect rate limits via token bucket
            rate_limiter.acquire('pacifica')

        if iteration >= max_iterations:
            self.logger.warning(f"Reached maximum iterations ({max_iterations}) for {symbol}")
        
        if not all_rates:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_rates)
        
        # Convert timestamps
        df['created_at'] = pd.to_datetime(df['created_at'], unit='ms')
        df['symbol'] = symbol
        df['exchange'] = 'Pacifica'
        df['market_type'] = 'Pacifica'
        
        # Extract base_asset from symbol
        df['base_asset'] = symbol
        df['quote_asset'] = 'USD'
        
        # Rename columns to match our schema
        df = df.rename(columns={
            'created_at': 'funding_time',
            'funding_rate': 'funding_rate'
        })
        
        # Pacifica uses 1-hour funding intervals
        df['funding_interval_hours'] = 1
        
        return df
    
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
        print(f"PACIFICA: Starting historical data fetch")
        print(f"Date range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')} ({actual_days} days)")
        print(f"{'='*60}")
        self.logger.info(f"Starting historical data fetch for all Pacifica perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")
        
        # Get list of all perpetual contracts
        perpetuals = self._get_perpetual_symbols()
        
        all_historical_data = []
        
        # Calculate total symbols for progress tracking
        total_symbols = len(perpetuals)
        symbols_processed = 0
        
        # Process all perpetuals
        print(f"PACIFICA: Found {len(perpetuals)} perpetual contracts to process")
        self.logger.info(f"Fetching historical data for {len(perpetuals)} perpetuals")
        
        for i in range(0, len(perpetuals), batch_size):
            batch = perpetuals[i:i+batch_size]
            
            for symbol in batch:
                try:
                    df = self.fetch_historical_funding_rates(
                        symbol, start_time, end_time
                    )
                    if not df.empty:
                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")
                except Exception as e:
                    self.logger.error(f"Error fetching {symbol}: {e}")
                
                # Update progress
                symbols_processed += 1
                progress = (symbols_processed / total_symbols) * 100
                if progress_callback:
                    progress_callback(symbols_processed, total_symbols, progress, f"Processing {symbol}")
                
                # Print progress every 10 symbols
                if symbols_processed % 10 == 0:
                    print(f"PACIFICA: Progress - {symbols_processed}/{total_symbols} contracts ({progress:.1f}%)")
                
                # Respect rate limits via token bucket
                rate_limiter.acquire('pacifica')
        
        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            print(f"PACIFICA: Completed! Fetched {len(combined_df)} total historical records")
            print(f"PACIFICA: {len(perpetuals)} total contracts processed")
            self.logger.info(f"Completed: fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            print(f"PACIFICA: WARNING - No historical data was fetched")
            self.logger.warning("No historical data fetched")
            return pd.DataFrame()
    
    def _get_perpetual_symbols(self) -> List[str]:
        """
        Get list of all perpetual contract symbols.
        
        Returns:
            List of perpetual contract symbols
        """
        # Fetch current market info to get all available symbols
        url = f"{self.base_url}/api/v1/info"
        data = self.safe_request(url)
        
        if not data or not data.get('success'):
            return []
        
        markets = data.get('data', [])
        symbols = [market['symbol'] for market in markets if 'symbol' in market]
        
        self.logger.info(f"Found {len(symbols)} active Pacifica perpetual contracts")
        return symbols
