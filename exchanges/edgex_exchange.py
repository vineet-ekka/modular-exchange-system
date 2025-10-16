"""
EdgeX Exchange Module
====================
Handles data fetching and normalization for EdgeX exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from .base_exchange import BaseExchange
import logging

class EdgexExchange(BaseExchange):
    """
    EdgeX Exchange data fetcher.
    Uses the EdgeX API to fetch perpetual market data.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize EdgeX exchange.
        
        Args:
            enabled: Whether this exchange is enabled
        """
        super().__init__("EdgeX", enabled)
        self.base_url = "https://pro.edgex.exchange"
        self.logger = logging.getLogger(__name__)
        
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch perpetual market data from EdgeX.
        
        Returns:
            DataFrame with raw EdgeX data
        """
        try:
            # Fetch contract metadata first
            contracts_data = self._fetch_contract_metadata()
            if not contracts_data:
                self.logger.warning("No contract metadata received from EdgeX")
                return pd.DataFrame()
            
            # Fetch latest funding rates
            funding_data = self._fetch_latest_funding_rates()
            if not funding_data:
                self.logger.warning("No funding rate data received from EdgeX")
                return pd.DataFrame()
            
            # Fetch ticker data for open interest
            ticker_data = self._fetch_ticker_data()
            
            # Combine all data
            all_data = []
            for contract in contracts_data:
                symbol = contract.get('symbol', '')
                if not symbol:
                    continue
                
                # Find corresponding funding rate
                funding_info = funding_data.get(symbol, {})
                
                # Find corresponding ticker data
                ticker_info = ticker_data.get(symbol, {})
                
                combined_data = {
                    'symbol': symbol,
                    'base_asset': contract.get('baseAsset', ''),
                    'quote_asset': contract.get('quoteAsset', ''),
                    'funding_rate': funding_info.get('fundingRate', 0),
                    'funding_time': funding_info.get('timestamp', 0),
                    'next_funding_time': funding_info.get('nextFundingTime', 0),
                    'funding_interval': funding_info.get('fundingInterval', 8),
                    'index_price': ticker_info.get('indexPrice', 0),
                    'mark_price': ticker_info.get('markPrice', 0),
                    'open_interest': ticker_info.get('openInterest', 0),
                    'contract_type': 'PERPETUAL',
                    'market_type': 'PERP'
                }
                all_data.append(combined_data)
            
            if not all_data:
                self.logger.warning("No combined data available from EdgeX")
                return pd.DataFrame()
            
            df = pd.DataFrame(all_data)
            self.logger.info(f"Found {len(df)} perpetual contracts on EdgeX")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching EdgeX data: {e}")
            return pd.DataFrame()
    
    def _fetch_contract_metadata(self) -> list:
        """
        Fetch contract metadata from EdgeX API.
        
        Returns:
            List of contract metadata
        """
        url = f"{self.base_url}/api/v1/public/meta/getMetaData"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, dict) and 'data' in response:
                data = response['data']
                if 'contractList' in data:
                    return data['contractList']
                else:
                    self.logger.warning("No contractList in EdgeX metadata response")
                    return []
            else:
                self.logger.warning("Invalid response format from EdgeX metadata API")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching contract metadata from EdgeX: {e}")
            return []
    
    def _fetch_latest_funding_rates(self) -> dict:
        """
        Fetch latest funding rates from EdgeX API.
        
        Returns:
            Dictionary of funding rate data by symbol
        """
        url = f"{self.base_url}/api/v1/public/funding/getLatestFundingRate"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, list):
                # Convert list to dictionary keyed by symbol
                funding_dict = {}
                for item in response:
                    symbol = item.get('symbol', '')
                    if symbol:
                        funding_dict[symbol] = item
                return funding_dict
            else:
                self.logger.warning("Invalid response format from EdgeX funding rates API")
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching funding rates from EdgeX: {e}")
            return {}
    
    def _fetch_ticker_data(self) -> dict:
        """
        Fetch ticker data from EdgeX API.
        
        Returns:
            Dictionary of ticker data by symbol
        """
        url = f"{self.base_url}/api/v1/public/quote/getTicker"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, list):
                # Convert list to dictionary keyed by symbol
                ticker_dict = {}
                for item in response:
                    symbol = item.get('symbol', '')
                    if symbol:
                        ticker_dict[symbol] = item
                return ticker_dict
            else:
                self.logger.warning("Invalid response format from EdgeX ticker API")
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching ticker data from EdgeX: {e}")
            return {}
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform EdgeX data to unified format.
        
        Args:
            df: Raw EdgeX data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        try:
            # Create normalized DataFrame with same index as input
            normalized_df = pd.DataFrame(index=df.index)
            
            # Basic fields
            normalized_df['exchange'] = self.name
            normalized_df['symbol'] = df['symbol']
            normalized_df['base_asset'] = df['base_asset']
            normalized_df['quote_asset'] = df['quote_asset']
            
            # Convert funding rate to decimal
            normalized_df['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce').fillna(0)
            
            # EdgeX uses 8-hour funding intervals (standard for perpetuals)
            funding_interval = df.get('funding_interval', 8)
            normalized_df['funding_interval_hours'] = pd.to_numeric(funding_interval, errors='coerce').fillna(8)
            
            # Calculate APR: funding_rate * (365 * 24 / funding_interval) * 100
            periods_per_year = (365 * 24) / normalized_df['funding_interval_hours']
            normalized_df['apr'] = (normalized_df['funding_rate'] * periods_per_year * 100).round(4)
            
            # Price data
            normalized_df['index_price'] = pd.to_numeric(df['index_price'], errors='coerce').fillna(0)
            normalized_df['mark_price'] = pd.to_numeric(df['mark_price'], errors='coerce').fillna(normalized_df['index_price'])
            
            # Open interest
            normalized_df['open_interest'] = pd.to_numeric(df['open_interest'], errors='coerce').fillna(0)
            
            # Contract type and market type
            normalized_df['contract_type'] = df['contract_type']
            normalized_df['market_type'] = df['market_type']
            
            # Filter out contracts with zero open interest or invalid data
            valid_mask = (
                (normalized_df['open_interest'] > 0) &
                (normalized_df['index_price'] > 0) &
                (normalized_df['symbol'].notna())
            )
            
            filtered_df = normalized_df[valid_mask].copy()
            
            if len(filtered_df) < len(normalized_df):
                self.logger.info(f"Filtered out {len(normalized_df) - len(filtered_df)} contracts with zero open interest or invalid data")
            
            return filtered_df
            
        except Exception as e:
            self.logger.error(f"Error normalizing EdgeX data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())
