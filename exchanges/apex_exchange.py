"""
ApeX Pro Exchange Module
========================
Handles data fetching and normalization for ApeX Pro (Omni) exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from .base_exchange import BaseExchange
import logging

class ApexExchange(BaseExchange):
    """
    ApeX Pro Exchange data fetcher.
    Uses the ApeX Pro Omni API v3 to fetch perpetual market data.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize ApeX Pro exchange.
        
        Args:
            enabled: Whether this exchange is enabled
        """
        super().__init__("ApeX", enabled)
        self.base_url = "https://omni.apex.exchange"
        self.logger = logging.getLogger(__name__)
        
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch perpetual market data from ApeX Pro.
        
        Returns:
            DataFrame with raw ApeX data
        """
        try:
            # Fetch all symbols first
            symbols_data = self._fetch_symbols()
            if not symbols_data:
                self.logger.warning("No symbols data received from ApeX")
                return pd.DataFrame()
            
            # Fetch ticker data (includes funding rates and open interest)
            ticker_data = self._fetch_tickers()
            if not ticker_data:
                self.logger.warning("No ticker data received from ApeX")
                return pd.DataFrame()
            
            # Combine symbol metadata with ticker data
            all_data = []
            for symbol_info in symbols_data:
                symbol = symbol_info.get('symbol', '')
                if not symbol:
                    continue
                
                # Find corresponding ticker data
                ticker_info = ticker_data.get(symbol, {})
                
                # Only include perpetual contracts
                if symbol_info.get('type') == 'PERPETUAL' or 'PERP' in symbol:
                    combined_data = {
                        'symbol': symbol,
                        'base_asset': symbol_info.get('baseAsset', ''),
                        'quote_asset': symbol_info.get('quoteAsset', ''),
                        'funding_rate': ticker_info.get('fundingRate', 0),
                        'predicted_funding_rate': ticker_info.get('predictedFundingRate', 0),
                        'index_price': ticker_info.get('indexPrice', 0),
                        'mark_price': ticker_info.get('markPrice', 0),
                        'open_interest': ticker_info.get('openInterest', 0),
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
                    all_data.append(combined_data)
            
            if not all_data:
                self.logger.warning("No perpetual contracts found on ApeX")
                return pd.DataFrame()
            
            df = pd.DataFrame(all_data)
            self.logger.info(f"Found {len(df)} perpetual contracts on ApeX")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching ApeX data: {e}")
            return pd.DataFrame()
    
    def _fetch_symbols(self) -> list:
        """
        Fetch all symbols from ApeX Pro API.
        
        Returns:
            List of symbol data
        """
        url = f"{self.base_url}/v3/symbols"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, dict) and 'data' in response:
                symbols_data = response['data']
                if isinstance(symbols_data, list):
                    return symbols_data
                else:
                    self.logger.warning("Invalid symbols data format from ApeX API")
                    return []
            else:
                self.logger.warning("Invalid response format from ApeX symbols API")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching symbols from ApeX: {e}")
            return []
    
    def _fetch_tickers(self) -> dict:
        """
        Fetch ticker data from ApeX Pro API.
        
        Returns:
            Dictionary of ticker data by symbol
        """
        url = f"{self.base_url}/v3/tickers"
        
        try:
            response = self.safe_request(url)
            if response and isinstance(response, dict) and 'data' in response:
                ticker_data = response['data']
                if isinstance(ticker_data, list):
                    # Convert list to dictionary keyed by symbol
                    ticker_dict = {}
                    for item in ticker_data:
                        symbol = item.get('symbol', '')
                        if symbol:
                            ticker_dict[symbol] = item
                    return ticker_dict
                else:
                    self.logger.warning("Invalid ticker data format from ApeX API")
                    return {}
            else:
                self.logger.warning("Invalid response format from ApeX tickers API")
                return {}
        except Exception as e:
            self.logger.error(f"Error fetching tickers from ApeX: {e}")
            return {}
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform ApeX data to unified format.
        
        Args:
            df: Raw ApeX data
            
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
            
            # Use predicted funding rate if available, otherwise use current funding rate
            funding_rate = df.get('predicted_funding_rate', df.get('funding_rate', 0))
            normalized_df['funding_rate'] = pd.to_numeric(funding_rate, errors='coerce').fillna(0)
            
            # ApeX Pro uses 8-hour funding intervals (standard for perpetuals)
            normalized_df['funding_interval_hours'] = 8
            
            # Calculate APR: funding_rate * (365 * 24 / 8) * 100
            # 8-hour intervals = 3 times per day = 1095 times per year
            periods_per_year = (365 * 24) / 8
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
            self.logger.error(f"Error normalizing ApeX data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())
