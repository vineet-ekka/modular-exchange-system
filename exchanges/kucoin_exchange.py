"""
KuCoin Exchange Module
=====================
Handles data fetching and normalization for KuCoin exchange.
"""

import pandas as pd
from .base_exchange import BaseExchange


class KuCoinExchange(BaseExchange):
    """
    KuCoin exchange data fetcher and normalizer.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("KuCoin", enabled)
        self.base_url = 'https://api-futures.kucoin.com/api/v1/'
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from KuCoin API.
        
        Returns:
            DataFrame with raw KuCoin data
        """
        try:
            # Fetch contracts data
            contracts_data = self.safe_request(self.base_url + 'contracts/active')
            
            if not contracts_data:
                return pd.DataFrame()
            
            # Parse the response
            if 'data' in contracts_data:
                df = pd.DataFrame(contracts_data['data'])
            else:
                df = pd.DataFrame(contracts_data)
            
            if len(df) == 0:
                return df
            
            # Filter for perpetual contracts (FFWCSX type)
            if 'type' in df.columns:
                perp_df = df[df['type'] == 'FFWCSX'].copy()
            else:
                perp_df = df.copy()
            
            # Convert funding rate granularity from milliseconds to hours
            if 'fundingRateGranularity' in perp_df.columns:
                perp_df['fundingIntervalHours'] = perp_df['fundingRateGranularity'].apply(
                    lambda x: x / (1000 * 60 * 60) if pd.notna(x) and x > 0 else None
                )
            
            # Removed next funding time conversion
            
            # Convert numeric columns
            numeric_columns = ['openInterest', 'fundingFeeRate', 'markPrice', 'indexPrice']
            for col in numeric_columns:
                if col in perp_df.columns:
                    perp_df[col] = pd.to_numeric(perp_df[col], errors='coerce')
            
            return perp_df
            
        except Exception as e:
            print(f"Error fetching KuCoin data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform KuCoin data to unified format.
        
        Args:
            df: Raw KuCoin data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        normalized = pd.DataFrame({
            'exchange': 'KuCoin',
            'symbol': df['symbol'],
            'base_asset': df['baseCurrency'],
            'quote_asset': df['quoteCurrency'],
            'funding_rate': pd.to_numeric(df['fundingFeeRate'], errors='coerce'),
            'funding_interval_hours': pd.to_numeric(df['fundingIntervalHours'], errors='coerce'),
            'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
            'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
            'open_interest': pd.to_numeric(df['openInterest'], errors='coerce'),
            'contract_type': df['type'] if 'type' in df.columns else 'PERPETUAL',
            'market_type': 'KuCoin Futures',
        })
        
        return normalized 