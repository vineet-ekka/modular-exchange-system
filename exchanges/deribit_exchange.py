"""
Deribit Exchange Module
======================
Handles data fetching and normalization for Deribit exchange.
Supports perpetual contracts with funding rate data using JSON-RPC API.
"""

import pandas as pd
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class DeribitExchange(BaseExchange):
    """
    Deribit exchange data fetcher and normalizer.
    Features:
    - Perpetual contracts with funding rates
    - Historical funding rate data
    - Open interest data
    - 8-hour funding intervals (standard)
    - JSON-RPC API integration
    """

    def __init__(self, enabled: bool = True):
        super().__init__("Deribit", enabled)
        self.base_url = 'https://www.deribit.com/api/v2'
        self.logger = setup_logger("DeribitExchange")
        self.request_id = 1

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Deribit API.
        
        Returns:
            DataFrame with raw Deribit data
        """
        try:
            # Get all perpetual instruments
            instruments = self._fetch_perpetual_instruments()
            if not instruments:
                return pd.DataFrame()

            self.logger.info(f"Found {len(instruments)} perpetual contracts")

            # Fetch funding rates and other data for each perpetual
            all_data = []
            for instrument in instruments:
                symbol = instrument['instrument_name']
                
                # Get current funding rate
                funding_data = self._fetch_funding_rate(symbol)
                if funding_data:
                    # Get ticker data for open interest and prices
                    ticker_data = self._fetch_ticker(symbol)
                    
                    # Combine data
                    combined_data = {
                        'symbol': symbol,
                        'base_asset': instrument.get('base_currency', ''),
                        'quote_asset': instrument.get('quote_currency', ''),
                        'funding_rate': funding_data.get('interest_8h', 0),
                        'funding_time': funding_data.get('timestamp', 0),
                        'index_price': ticker_data.get('index_price', 0) if ticker_data else 0,
                        'mark_price': ticker_data.get('mark_price', 0) if ticker_data else 0,
                        'open_interest': ticker_data.get('open_interest', 0) if ticker_data else 0,
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
                    all_data.append(combined_data)

            if not all_data:
                self.logger.warning("No funding rate data retrieved from Deribit")
                return pd.DataFrame()

            return pd.DataFrame(all_data)

        except Exception as e:
            self.logger.error(f"Error fetching Deribit data: {e}")
            return pd.DataFrame()

    def _fetch_perpetual_instruments(self) -> List[Dict]:
        """
        Fetch all perpetual instruments from Deribit.
        
        Returns:
            List of perpetual instrument data
        """
        try:
            # Get BTC perpetuals
            btc_instruments = self._fetch_instruments_by_currency('BTC')
            
            # Get ETH perpetuals
            eth_instruments = self._fetch_instruments_by_currency('ETH')
            
            # Get USDC perpetuals (Deribit has many USDC perpetuals)
            usdc_instruments = self._fetch_instruments_by_currency('USDC')
            
            # Combine and filter for perpetuals
            all_instruments = btc_instruments + eth_instruments + usdc_instruments
            perpetuals = [inst for inst in all_instruments 
                         if inst.get('kind') == 'future' and 
                         'PERPETUAL' in inst.get('instrument_name', '')]
            
            return perpetuals
            
        except Exception as e:
            self.logger.error(f"Error fetching perpetual instruments: {e}")
            return []

    def _fetch_instruments_by_currency(self, currency: str) -> List[Dict]:
        """
        Fetch instruments for a specific currency.
        
        Args:
            currency: Currency code (BTC, ETH, etc.)
            
        Returns:
            List of instrument data
        """
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': 'public/get_instruments',
                'params': {'currency': currency, 'kind': 'future'},
                'id': self._get_next_request_id()
            }
            
            data = self.safe_post_request(self.base_url, json_data=payload)
            
            if data and 'result' in data:
                return data['result']
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching instruments for {currency}: {e}")
            return []

    def _fetch_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current funding rate for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Funding rate data or None
        """
        try:
            # Get funding rate history for the last 8 hours
            end_time = int(time.time() * 1000)
            start_time = end_time - (8 * 60 * 60 * 1000)  # 8 hours ago
            
            payload = {
                'jsonrpc': '2.0',
                'method': 'public/get_funding_rate_history',
                'params': {
                    'instrument_name': symbol,
                    'start_timestamp': start_time,
                    'end_timestamp': end_time
                },
                'id': self._get_next_request_id()
            }
            
            data = self.safe_post_request(self.base_url, json_data=payload)
            
            if data and 'result' in data and data['result']:
                # Return the most recent funding rate
                return data['result'][-1]
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    def _fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data or None
        """
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': 'public/ticker',
                'params': {'instrument_name': symbol},
                'id': self._get_next_request_id()
            }
            
            data = self.safe_post_request(self.base_url, json_data=payload)
            
            if data and 'result' in data:
                return data['result']
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    def _get_next_request_id(self) -> int:
        """
        Get the next request ID for JSON-RPC calls.
        
        Returns:
            Next request ID
        """
        self.request_id += 1
        return self.request_id

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

        try:
            # Create normalized DataFrame with proper length
            normalized_df = pd.DataFrame(index=df.index)
            
            # Basic mapping
            normalized_df['exchange'] = self.name
            normalized_df['symbol'] = df['symbol']
            normalized_df['base_asset'] = df['base_asset']
            normalized_df['quote_asset'] = df['quote_asset']
            normalized_df['funding_rate'] = df['funding_rate']
            normalized_df['funding_interval_hours'] = 8  # Deribit uses 8-hour funding
            normalized_df['contract_type'] = df['contract_type']
            normalized_df['market_type'] = df['market_type']
            
            # Calculate APR (8-hour funding = 3 times per day)
            periods_per_year = (365 * 24) / 8  # 1,095 periods per year
            normalized_df['apr'] = df['funding_rate'] * periods_per_year * 100
            
            # Prices
            normalized_df['index_price'] = df['index_price']
            normalized_df['mark_price'] = df['mark_price']
            
            # Open interest
            normalized_df['open_interest'] = df['open_interest']
            
            # Add timestamps
            if 'funding_time' in df.columns:
                normalized_df['funding_time'] = pd.to_datetime(df['funding_time'], unit='ms', errors='coerce')
            
            return normalized_df

        except Exception as e:
            self.logger.error(f"Error normalizing Deribit data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())

    def fetch_historical_funding_rates(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Fetch historical funding rates for a symbol.
        
        Args:
            symbol: Trading symbol
            days: Number of days to fetch
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            payload = {
                'jsonrpc': '2.0',
                'method': 'public/get_funding_rate_history',
                'params': {
                    'instrument_name': symbol,
                    'start_timestamp': start_time,
                    'end_timestamp': end_time
                },
                'id': self._get_next_request_id()
            }
            
            data = self.safe_post_request(self.base_url, json_data=payload)
            
            if data and 'result' in data:
                rows = data['result']
                if rows:
                    df = pd.DataFrame(rows)
                    df['funding_time'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
                    df['funding_rate'] = df['interest_8h'].astype(float)
                    return df[['symbol', 'funding_rate', 'funding_time']]
            
            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()
