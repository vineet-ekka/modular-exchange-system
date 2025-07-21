"""
Backpack Exchange Module
=======================
Handles data fetching and normalization for Backpack exchange.
"""

import pandas as pd
from .base_exchange import BaseExchange


class BackpackExchange(BaseExchange):
    """
    Backpack exchange data fetcher and normalizer.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Backpack", enabled)
        self.base_url = 'https://api.backpack.exchange/api/v1/'
    
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
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Convert fundingInterval from ms to hours if present
        if 'fundingInterval' in df.columns:
            funding_interval_hours = pd.to_numeric(df['fundingInterval'], errors='coerce') / (1000 * 60 * 60)
        else:
            funding_interval_hours = None
        
        normalized = pd.DataFrame({
            'exchange': 'Backpack',
            'symbol': df['symbol'],
            'base_asset': df['baseSymbol'],
            'quote_asset': df['quoteSymbol'],
            'funding_rate': pd.to_numeric(df['fundingRate'], errors='coerce'),
            'funding_interval_hours': funding_interval_hours,
            'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
            'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
            'open_interest': pd.to_numeric(df['openInterest'], errors='coerce'),
            'contract_type': df['marketType'],
            'market_type': 'Backpack PERP',
        })
        
        return normalized 