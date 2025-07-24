"""
Deribit Exchange Module
=======================
Handles data fetching and normalization for Deribit exchange.
"""

import pandas as pd
from .base_exchange import BaseExchange


class DeribitExchange(BaseExchange):
    """
    Deribit exchange data fetcher and normalizer.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Deribit", enabled)
        self.base_url = 'https://www.deribit.com/api/v2/public/'
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Deribit API.
        
        Returns:
            DataFrame with raw Deribit data
        """
        try:
            # First, get all perpetual instruments
            instruments_url = self.base_url + 'get_instruments'
            
            all_instruments = []
            
            # Fetch instruments for each currency type
            for currency in ['BTC', 'ETH', 'SOL', 'MATIC', 'USDC']:
                params = {
                    'currency': currency,
                    'kind': 'future'
                }
                
                instruments_data = self.safe_request(instruments_url, params=params)
                
                if instruments_data and 'result' in instruments_data:
                    instruments = instruments_data['result']
                    # Filter for perpetual contracts only
                    perp_instruments = [inst for inst in instruments if inst.get('settlement_period') == 'perpetual']
                    all_instruments.extend(perp_instruments)
            
            if not all_instruments:
                print("No perpetual instruments found on Deribit")
                return pd.DataFrame()
            
            # Create instruments DataFrame
            instruments_df = pd.DataFrame(all_instruments)
            
            # Now fetch ticker data for each instrument
            ticker_data = []
            ticker_url = self.base_url + 'ticker'
            
            print(f"Fetching ticker data for {len(instruments_df)} Deribit perpetual contracts...")
            
            for idx, instrument in instruments_df.iterrows():
                instrument_name = instrument['instrument_name']
                params = {'instrument_name': instrument_name}
                
                ticker_response = self.safe_request(ticker_url, params=params, silent_errors=True)
                
                if ticker_response and 'result' in ticker_response:
                    ticker = ticker_response['result']
                    # Combine instrument and ticker data
                    combined_data = {
                        'instrument_name': instrument_name,
                        'base_currency': instrument['base_currency'],
                        'quote_currency': instrument.get('quote_currency', 'USD'),
                        'settlement_period': instrument['settlement_period'],
                        'funding_8h': ticker.get('funding_8h', 0),
                        'index_price': ticker.get('index_price'),
                        'mark_price': ticker.get('mark_price'),
                        'open_interest': ticker.get('open_interest'),
                        'contract_size': instrument.get('contract_size', 1)
                    }
                    ticker_data.append(combined_data)
            
            if not ticker_data:
                return pd.DataFrame()
            
            return pd.DataFrame(ticker_data)
            
        except Exception as e:
            print(f"Error fetching Deribit data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Deribit data to unified format.
        
        Args:
            df: Raw Deribit data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Deribit uses 8-hour funding intervals
        funding_interval_hours = 8
        
        # Use funding_8h directly as it's the primary funding rate field for Deribit
        funding_rate = pd.to_numeric(df['funding_8h'], errors='coerce')
        
        # Calculate open interest in USD
        # For Deribit, open_interest is in contracts, multiply by contract_size
        open_interest_usd = pd.to_numeric(df['open_interest'], errors='coerce') * pd.to_numeric(df['contract_size'], errors='coerce')
        
        normalized = pd.DataFrame({
            'exchange': 'Deribit',
            'symbol': df['instrument_name'],
            'base_asset': df['base_currency'],
            'quote_asset': df['quote_currency'],
            'funding_rate': funding_rate,
            'funding_interval_hours': funding_interval_hours,
            'index_price': pd.to_numeric(df['index_price'], errors='coerce'),
            'mark_price': pd.to_numeric(df['mark_price'], errors='coerce'),
            'open_interest': open_interest_usd,
            'contract_type': 'PERP',
            'market_type': 'Deribit PERP',
        })
        
        return normalized