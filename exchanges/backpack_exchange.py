"""
Backpack Exchange Module
=======================
Handles data fetching and normalization for Backpack exchange.
Includes historical funding rate retrieval capabilities.
"""

import pandas as pd
import time
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class BackpackExchange(BaseExchange):
    """
    Backpack exchange data fetcher and normalizer.
    Supports both real-time and historical funding rate data.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Backpack", enabled)
        self.base_url = 'https://api.backpack.exchange/api/v1/'
        self.logger = setup_logger("BackpackExchange")
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Backpack API.
        
        Returns:
            DataFrame with raw Backpack data
        """
        try:
            # Fetch data from all endpoints
            markets_data = self.safe_request(self.base_url + 'markets')
            mark_prices_data = self.safe_request(self.base_url + 'markPrices')
            open_interest_data = self.safe_request(self.base_url + 'openInterest')
            
            if not all([markets_data, mark_prices_data, open_interest_data]):
                return pd.DataFrame()
            
            # Create DataFrames
            df = pd.DataFrame(markets_data)
            mark_prices_df = pd.DataFrame(mark_prices_data)
            open_interest_df = pd.DataFrame(open_interest_data)
            
            # Filter for only PERP marketType
            perp_df = df[df['marketType'] == 'PERP'].copy()

            # Filter out invisible/delisted markets
            if 'visible' in perp_df.columns:
                perp_df = perp_df[perp_df['visible'] == True].copy()

            # Merge the DataFrames
            merged_df = perp_df.merge(
                mark_prices_df[['symbol', 'fundingRate', 'indexPrice', 'markPrice']], 
                on='symbol', how='left'
            )
            merged_df = merged_df.merge(
                open_interest_df[['symbol', 'openInterest']], 
                on='symbol', how='left'
            )
            
            return merged_df
            
        except Exception as e:
            print(f"Error fetching Backpack data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Backpack data to unified format.
        
        Args:
            df: Raw Backpack data
            
        Returns:
            DataFrame in unified format with APR calculated
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Convert fundingInterval from ms to hours if present
        if 'fundingInterval' in df.columns:
            funding_interval_hours = pd.to_numeric(df['fundingInterval'], errors='coerce') / (1000 * 60 * 60)
        else:
            funding_interval_hours = None
        
        # Convert funding rate to numeric
        funding_rate = pd.to_numeric(df['fundingRate'], errors='coerce')
        
        # Calculate APR: funding_rate * (8760 hours_per_year / funding_interval_hours) * 100
        apr = None
        if funding_interval_hours is not None:
            apr = funding_rate * (8760 / funding_interval_hours) * 100
        
        # Normalize base assets (remove k prefix if present)
        def normalize_backpack_base_asset(base_symbol):
            if base_symbol.startswith('k'):
                return base_symbol[1:]  # e.g., kBONK -> BONK
            return base_symbol
        
        base_assets = df['baseSymbol'].apply(normalize_backpack_base_asset)
        
        normalized = pd.DataFrame({
            'exchange': 'Backpack',
            'symbol': df['symbol'],
            'base_asset': base_assets,
            'quote_asset': df['quoteSymbol'],
            'funding_rate': funding_rate,
            'funding_interval_hours': funding_interval_hours,
            'apr': apr,
            'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
            'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
            'open_interest': pd.to_numeric(df['openInterest'], errors='coerce'),
            'contract_type': df['marketType'],
            'market_type': 'Backpack PERP',
        })
        
        return normalized
    
    # ==================== HISTORICAL FUNDING RATE METHODS ====================
    
    def fetch_historical_funding_rates(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'SOL_USDC_PERP')
            days: Number of days of historical data to fetch (default: 30)
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Calculate how many records we need (considering funding intervals)
            # Backpack uses 1-hour funding intervals = 24 per day
            estimated_records = days * 24
            limit = min(10000, estimated_records * 2)  # Use API's maximum limit of 10000
            
            all_rates = []
            offset = 0
            
            while len(all_rates) < estimated_records:
                # Fetch a batch of historical funding rates
                url = self.base_url + 'fundingRates'
                params = {
                    'symbol': symbol,
                    'limit': limit,
                    'offset': offset
                }
                
                data = self.safe_request(url, params=params)
                
                if not data or len(data) == 0:
                    break
                
                all_rates.extend(data)
                
                # Check if we have enough data
                if len(data) < limit:
                    break  # No more data available
                
                offset += limit
            
            if not all_rates:
                self.logger.warning(f"No historical funding rates found for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(all_rates)
            
            # Parse timestamps and make timezone-aware
            df['funding_time'] = pd.to_datetime(df['intervalEndTimestamp'], utc=True)
            
            # Add exchange and symbol info
            df['exchange'] = 'Backpack'
            df['symbol'] = symbol
            
            # Extract base asset from symbol (e.g., 'SOL_USDC_PERP' -> 'SOL', 'kBONK_USDC_PERP' -> 'BONK')
            base = symbol.split('_')[0] if '_' in symbol else symbol
            # Normalize k prefix
            if base.startswith('k'):
                df['base_asset'] = base[1:]  # e.g., kBONK -> BONK
            else:
                df['base_asset'] = base
            
            # Rename columns to match our schema
            df = df.rename(columns={
                'fundingRate': 'funding_rate'
            })
            
            # Convert funding rate to numeric
            df['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')
            
            # Detect funding interval from the data
            if len(df) > 1:
                df = df.sort_values('funding_time')
                time_diffs = df['funding_time'].diff().dropna()
                hours_diff = time_diffs.dt.total_seconds() / 3600
                # Get the most common interval
                most_common_interval = int(hours_diff.mode().iloc[0]) if len(hours_diff.mode()) > 0 else 8
                df['funding_interval_hours'] = most_common_interval
            else:
                df['funding_interval_hours'] = 8  # Default to 8 hours
            
            # Filter to requested time range
            end_time = pd.Timestamp.now(tz='UTC')
            start_time = end_time - pd.Timedelta(days=days)
            df = df[(df['funding_time'] >= start_time) & (df['funding_time'] <= end_time)]
            
            # Sort by time descending (newest first)
            df = df.sort_values('funding_time', ascending=False)
            
            self.logger.info(f"Fetched {len(df)} historical funding rates for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_all_perpetuals_historical(self, days: int = 30, 
                                       batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all Backpack perpetual contracts.
        
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
        
        # Calculate actual days for logging
        actual_days = (end_time - start_time).days
        
        self.logger.info(f"Starting historical data fetch for all Backpack perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")
        
        # Get list of all perpetual contracts
        markets_data = self.safe_request(self.base_url + 'markets')
        if not markets_data:
            self.logger.error("Failed to fetch Backpack markets")
            return pd.DataFrame()
        
        # Filter for perpetual contracts
        perpetuals = [m for m in markets_data if m.get('marketType') == 'PERP']
        symbols = [p['symbol'] for p in perpetuals]
        
        self.logger.info(f"Found {len(symbols)} perpetual contracts")
        
        all_historical_data = []
        
        # Process each symbol
        for i, symbol in enumerate(symbols):
            try:
                # Fetch historical data for this symbol using actual days
                df = self.fetch_historical_funding_rates(symbol, days=actual_days)
                
                if not df.empty:
                    # Add funding interval from market data
                    market_info = next((p for p in perpetuals if p['symbol'] == symbol), None)
                    if market_info and 'fundingInterval' in market_info:
                        interval_hours = market_info['fundingInterval'] / (1000 * 60 * 60)
                        df['funding_interval_hours'] = interval_hours
                    
                    all_historical_data.append(df)
                    self.logger.debug(f"Fetched {len(df)} records for {symbol}")
                
                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(symbols)) * 100
                    progress_callback(i + 1, len(symbols), progress, f"Processing {symbol}")
                
                # Small delay to respect rate limits
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error fetching historical data for {symbol}: {e}")
        
        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            self.logger.info(f"Completed: fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            self.logger.warning("No historical data fetched for Backpack")
            return pd.DataFrame() 