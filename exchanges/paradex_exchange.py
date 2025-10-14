"""
Paradex Exchange Module
======================
Handles data fetching and normalization for Paradex exchange.
Paradex is a decentralized perpetual exchange on Starknet.
"""

import pandas as pd
import time
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class ParadexExchange(BaseExchange):
    """
    Paradex exchange data fetcher and normalizer.
    Handles perpetual contracts with various funding intervals.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Paradex", enabled)
        self.logger = setup_logger("ParadexExchange")
        self.base_url = "https://api.prod.paradex.trade/v1"
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Paradex API.
        
        Returns:
            DataFrame with raw Paradex data
        """
        try:
            # Fetch markets data to get perpetual contracts
            markets_response = self.safe_request(f"{self.base_url}/markets")
            if not markets_response or 'results' not in markets_response:
                return pd.DataFrame()
            
            # Extract the markets list from the response
            markets_data = markets_response['results']
            
            # Convert to DataFrame
            df = pd.DataFrame(markets_data)
            
            # Filter for perpetual contracts only
            perp_df = df[df['asset_kind'] == 'PERP'].copy()
            
            if perp_df.empty:
                print("  No perpetual contracts found")
                return pd.DataFrame()
            
            print(f"  Found {len(perp_df)} perpetual contracts")
            
            # Fetch real-time data for each perpetual contract
            print("  Fetching real-time funding rates and prices...")
            realtime_data = self._fetch_realtime_data(perp_df['symbol'].tolist())
            
            # Merge real-time data with market data
            if not realtime_data.empty:
                perp_df = perp_df.merge(realtime_data, on='symbol', how='left')
            else:
                # Fallback to placeholder values if real-time fetch fails
                perp_df['funding_rate'] = 0.0
                perp_df['index_price'] = 0.0
                perp_df['mark_price'] = 0.0
                perp_df['open_interest'] = 0.0
            
            return perp_df
            
        except Exception as e:
            print(f"Error fetching Paradex data: {str(e)}")
            return pd.DataFrame()
    
    def _fetch_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch real-time funding rates and prices for all symbols.
        
        Args:
            symbols: List of market symbols
            
        Returns:
            DataFrame with real-time data
        """
        realtime_data = []
        
        # Process symbols in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            
            for symbol in batch:
                try:
                    # Fetch market summary for this symbol
                    summary_response = self.safe_request(
                        f"{self.base_url}/markets/summary",
                        params={'market': symbol}
                    )
                    
                    if summary_response and 'results' in summary_response and summary_response['results']:
                        data = summary_response['results'][0]  # First (and only) result
                        
                        realtime_data.append({
                            'symbol': symbol,
                            'funding_rate': float(data.get('funding_rate', 0)),
                            'mark_price': float(data.get('mark_price', 0)),
                            'index_price': float(data.get('underlying_price', 0)),  # Use underlying_price as index
                            'open_interest': float(data.get('open_interest', 0))
                        })
                    
                    # Small delay to respect rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"    Error fetching data for {symbol}: {str(e)}")
                    continue
        
        if realtime_data:
            print(f"    Successfully fetched real-time data for {len(realtime_data)} contracts")
            return pd.DataFrame(realtime_data)
        else:
            print("    Failed to fetch any real-time data")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Paradex data to unified format.
        
        Args:
            df: Raw Paradex data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Extract base asset from symbol (remove -USD-PERP suffix)
        def extract_base_asset(symbol):
            if symbol.endswith('-USD-PERP'):
                return symbol[:-9]  # Remove '-USD-PERP'
            return symbol
        
        # Normalize symbol format
        def normalize_symbol(symbol):
            # Convert from Paradex format (BTC-USD-PERP) to standard format (BTCUSDT)
            if symbol.endswith('-USD-PERP'):
                base = symbol[:-9]
                return f"{base}USDT"
            return symbol
        
        normalized = pd.DataFrame({
            'exchange': 'Paradex',
            'symbol': df['symbol'].apply(normalize_symbol),
            'base_asset': df['symbol'].apply(extract_base_asset),
            'quote_asset': 'USDT',  # All Paradex perps are USD-settled
            'funding_rate': pd.to_numeric(df['funding_rate'], errors='coerce'),
            'funding_interval_hours': pd.to_numeric(df['funding_period_hours'], errors='coerce'),
            'index_price': pd.to_numeric(df['index_price'], errors='coerce'),
            'mark_price': pd.to_numeric(df['mark_price'], errors='coerce'),
            'open_interest': pd.to_numeric(df['open_interest'], errors='coerce'),
            'contract_type': 'PERPETUAL',
            'market_type': 'Paradex',
        })
        
        # Calculate APR based on funding interval
        normalized['apr'] = normalized.apply(
            lambda row: self._calculate_apr(row['funding_rate'], row['funding_interval_hours']), 
            axis=1
        )
        
        return normalized
    
    def _calculate_apr(self, funding_rate: float, funding_interval_hours: float) -> float:
        """
        Calculate APR from funding rate and interval.
        
        Args:
            funding_rate: The funding rate (as decimal)
            funding_interval_hours: Funding interval in hours
            
        Returns:
            APR as percentage
        """
        if pd.isna(funding_rate) or pd.isna(funding_interval_hours) or funding_interval_hours == 0:
            return 0.0
        
        # Calculate periods per year
        periods_per_year = (365 * 24) / funding_interval_hours
        
        # Calculate APR
        apr = funding_rate * periods_per_year * 100
        
        return apr
    
    def fetch_historical_funding_rates(self, symbol: str, 
                                      start_time: Optional[datetime] = None, 
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD-PERP')
            start_time: Start time for historical data
            end_time: End time for historical data
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Convert datetime to unix milliseconds
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=30)
            
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            all_rates = []
            cursor = None
            
            # Fetch data in pages
            while True:
                params = {
                    'market': symbol,
                    'page_size': 1000,  # Maximum page size
                    'start_at': start_ms,
                    'end_at': end_ms
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                response = self.safe_request(f"{self.base_url}/funding/data", params=params)
                
                if not response or 'results' not in response:
                    break
                
                results = response['results']
                if not results:
                    break
                
                all_rates.extend(results)
                
                # Check if there are more pages
                cursor = response.get('next')
                if not cursor:
                    break
                
                # Small delay to respect rate limits
                time.sleep(0.1)
            
            if not all_rates:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(all_rates)
            
            # Convert timestamps
            df['created_at'] = pd.to_datetime(df['created_at'], unit='ms')
            df['symbol'] = symbol
            df['exchange'] = 'Paradex'
            
            # Rename columns to match our schema
            df = df.rename(columns={
                'created_at': 'funding_time',
                'funding_rate': 'funding_rate',
                'funding_period_hours': 'funding_interval_hours'
            })
            
            # Extract base asset from symbol
            df['base_asset'] = self._extract_base_asset(symbol)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def _extract_base_asset(self, symbol: str) -> str:
        """
        Extract base asset from symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD-PERP')
            
        Returns:
            Base asset (e.g., 'BTC')
        """
        if symbol.endswith('-USD-PERP'):
            return symbol[:-9]  # Remove '-USD-PERP'
        return symbol
    
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
        try:
            # Calculate time range
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)
            
            # Get list of all perpetual contracts
            markets_response = self.safe_request(f"{self.base_url}/markets")
            if not markets_response or 'results' not in markets_response:
                return pd.DataFrame()
            
            markets_data = markets_response['results']
            perp_symbols = [m['symbol'] for m in markets_data if m.get('asset_kind') == 'PERP']
            
            if not perp_symbols:
                self.logger.warning("No perpetual contracts found")
                return pd.DataFrame()
            
            self.logger.info(f"Fetching historical data for {len(perp_symbols)} perpetual contracts")
            
            all_historical_data = []
            total_symbols = len(perp_symbols)
            
            for i, symbol in enumerate(perp_symbols):
                try:
                    df = self.fetch_historical_funding_rates(symbol, start_time, end_time)
                    if not df.empty:
                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")
                    
                    # Update progress
                    if progress_callback:
                        progress = ((i + 1) / total_symbols) * 100
                        progress_callback(i + 1, total_symbols, progress, f"Processing {symbol}")
                    
                    # Small delay to respect rate limits
                    time.sleep(0.2)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
                    continue
            
            # Combine all data
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
