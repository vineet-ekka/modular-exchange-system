"""
Kraken Exchange Module
======================
Handles data fetching and normalization for Kraken Futures exchange.
"""

import pandas as pd
import numpy as np
from .base_exchange import BaseExchange
from typing import Dict, List, Optional


class KrakenExchange(BaseExchange):
    """
    Kraken Futures exchange data fetcher and normalizer.
    
    Kraken Futures API provides perpetual contracts with funding rates.
    Documentation: https://docs.futures.kraken.com/
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Kraken", enabled)
        self.base_url = 'https://futures.kraken.com/derivatives/api/v3/'
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Kraken Futures API.
        
        Returns:
            DataFrame with raw Kraken data
        """
        try:
            # Step 1: Fetch instruments to get base/quote assets
            instruments_data = self.safe_request(self.base_url + 'instruments')
            
            if not instruments_data or 'instruments' not in instruments_data:
                print(f"! No instruments data received from Kraken")
                return pd.DataFrame()
            
            # Create instruments DataFrame with base/quote info
            instruments_df = pd.DataFrame(instruments_data['instruments'])
            
            # Step 2: Fetch all tickers data (includes most fields we need)
            tickers_data = self.safe_request(self.base_url + 'tickers')
            
            if not tickers_data or 'tickers' not in tickers_data:
                print(f"! No tickers data received from Kraken")
                return pd.DataFrame()
            
            # Create tickers DataFrame
            tickers_df = pd.DataFrame(tickers_data['tickers'])
            
            # Filter for perpetual contracts (check tag field)
            # Perpetuals typically have 'perpetual' in their tag
            if 'tag' in tickers_df.columns:
                perp_df = tickers_df[tickers_df['tag'].str.contains('perpetual', case=False, na=False)].copy()
            else:
                # Fallback: filter by symbol prefix if tag is not available
                perp_df = tickers_df[tickers_df['symbol'].str.startswith('PF_')].copy()
            
            if perp_df.empty:
                print(f"! No perpetual contracts found on Kraken")
                return pd.DataFrame()
            
            # Merge with instruments data to get base/quote assets
            merged_df = perp_df.merge(
                instruments_df[['symbol', 'base', 'quote']], 
                on='symbol', 
                how='left'
            )
            
            print(f"  Retrieved {len(merged_df)} Kraken perpetual contracts")
            
            return merged_df
            
        except Exception as e:
            print(f"Error fetching Kraken data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Kraken data to unified format.
        
        Args:
            df: Raw Kraken data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Parse numeric fields first
        raw_funding_rate = pd.to_numeric(df.get('fundingRate', 0), errors='coerce')
        mark_price = pd.to_numeric(df.get('markPrice', 0), errors='coerce')
        index_price = pd.to_numeric(df.get('indexPrice', 0), errors='coerce')
        open_interest = pd.to_numeric(df.get('openInterest', 0), errors='coerce')
        
        # Calculate adjusted funding rate for Kraken
        # Kraken provides funding rate that needs to be divided by mark price
        funding_rate = raw_funding_rate / mark_price
        
        # Set to NaN where mark_price is invalid (0, negative, or NaN)
        invalid_mask = (mark_price <= 0) | pd.isna(mark_price)
        funding_rate[invalid_mask] = np.nan
        
        # Count and log invalid entries
        invalid_count = invalid_mask.sum()
        if invalid_count > 0:
            print(f"  Warning: {invalid_count} Kraken contracts have invalid mark prices (funding rate set to NaN)")
        
        # Create normalized DataFrame
        normalized = pd.DataFrame({
            'exchange': 'Kraken',
            'symbol': df['symbol'],
            'base_asset': df['base'],  # Using 'base' field from instruments
            'quote_asset': df['quote'],  # Using 'quote' field from instruments
            'funding_rate': funding_rate,
            'funding_interval_hours': 1,  # Kraken uses 1-hour funding intervals as per Endpoint.md
            'index_price': index_price,
            'mark_price': mark_price,
            'open_interest': open_interest,
            'contract_type': 'PERPETUAL',
            'market_type': 'Kraken Futures',
        })
        
        # Calculate APR (will be done by DataProcessor, but ensure column exists)
        normalized['apr'] = None
        
        # Remove rows with invalid base/quote assets
        normalized = normalized.dropna(subset=['base_asset', 'quote_asset'])
        
        return normalized