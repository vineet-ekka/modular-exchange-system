"""
Orderly Network Exchange Module
==============================
Handles data fetching and normalization for Orderly Network exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class OrderlyExchange(BaseExchange):
    """
    Orderly Network exchange data fetcher and normalizer.
    Features:
    - Perpetual contracts with funding rates
    - Historical funding rate data
    - Open interest data
    - 8-hour funding intervals (standard)
    """

    def __init__(self, enabled: bool = True):
        super().__init__("Orderly", enabled)
        self.base_url = 'https://api.orderly.org'
        self.logger = setup_logger("OrderlyExchange")

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Orderly Network API.
        
        Returns:
            DataFrame with raw Orderly Network data
        """
        try:
            # First get all instruments
            instruments_data = self._fetch_instruments()
            if not instruments_data:
                return pd.DataFrame()

            # Filter for perpetual contracts
            perp_instruments = [inst for inst in instruments_data 
                              if inst.get('symbol_type') == 'PERP' or 'PERP' in inst.get('symbol', '')]
            
            if not perp_instruments:
                self.logger.warning("No perpetual contracts found in Orderly Network")
                return pd.DataFrame()

            self.logger.info(f"Found {len(perp_instruments)} perpetual contracts")

            # Fetch funding rates for each perpetual
            all_data = []
            for instrument in perp_instruments:
                symbol = instrument['symbol']
                
                # Get current funding rate
                funding_data = self._fetch_funding_rate(symbol)
                if funding_data:
                    # Get open interest
                    open_interest = self._fetch_open_interest(symbol)
                    
                    # Combine data
                    combined_data = {
                        'symbol': symbol,
                        'base_asset': instrument.get('base', ''),
                        'quote_asset': instrument.get('quote', ''),
                        'funding_rate': funding_data.get('funding_rate', 0),
                        'funding_time': funding_data.get('funding_rate_timestamp', 0),
                        'next_funding_time': funding_data.get('next_funding_time', 0),
                        'open_interest': open_interest,
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
                    all_data.append(combined_data)

            if not all_data:
                self.logger.warning("No funding rate data retrieved from Orderly Network")
                return pd.DataFrame()

            return pd.DataFrame(all_data)

        except Exception as e:
            self.logger.error(f"Error fetching Orderly Network data: {e}")
            return pd.DataFrame()

    def _fetch_instruments(self) -> List[Dict]:
        """
        Fetch all instruments from Orderly Network.
        
        Returns:
            List of instrument data
        """
        try:
            url = f"{self.base_url}/v1/public/info"
            data = self.safe_request(url)
            
            if data and data.get('success') and 'data' in data:
                return data['data'].get('rows', [])
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching instruments: {e}")
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
            url = f"{self.base_url}/v1/public/funding_rate_history"
            params = {'symbol': symbol, 'limit': 1}
            
            data = self.safe_request(url, params=params)
            
            if data and data.get('success') and 'data' in data:
                rows = data['data'].get('rows', [])
                if rows:
                    return rows[0]  # Most recent funding rate
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    def _fetch_open_interest(self, symbol: str) -> Optional[float]:
        """
        Fetch open interest for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Open interest value or None
        """
        try:
            url = f"{self.base_url}/v1/public/market_info/traders_open_interests"
            params = {'symbol': symbol}
            
            data = self.safe_request(url, params=params)
            
            if data and data.get('success') and 'data' in data:
                return data['data'].get('open_interest', 0)
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching open interest for {symbol}: {e}")
            return None

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Orderly Network data to unified format.
        
        Args:
            df: Raw Orderly Network data
            
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
            
            # Extract base_asset and quote_asset from symbol names
            # Orderly symbols follow pattern: PERP_BASEASSET_QUOTEASSET
            def parse_orderly_symbol(symbol):
                if pd.isna(symbol):
                    return '', ''
                
                symbol_str = str(symbol)
                if symbol_str.startswith('PERP_'):
                    # Remove PERP_ prefix and split by _
                    parts = symbol_str[5:].split('_')
                    if len(parts) >= 2:
                        base_asset = parts[0]
                        quote_asset = parts[-1]  # Last part is quote asset
                        return base_asset, quote_asset
                
                return '', ''
            
            def normalize_orderly_asset(asset):
                """Remove numerical prefixes from Orderly assets like 1000000BABYDOGE -> BABYDOGE"""
                if pd.isna(asset) or asset == '':
                    return asset
                
                asset_str = str(asset)
                # Remove common numerical prefixes
                prefixes_to_remove = [
                    '1000000',  # 1M
                    '100000',   # 100K
                    '10000',    # 10K
                    '1000',     # 1K
                    '100',      # 100
                    '10',       # 10
                ]
                
                for prefix in prefixes_to_remove:
                    if asset_str.startswith(prefix):
                        return asset_str[len(prefix):]
                
                return asset_str
            
            # Parse symbols to extract base and quote assets
            parsed_assets = df['symbol'].apply(parse_orderly_symbol)
            base_assets = [assets[0] for assets in parsed_assets]
            quote_assets = [assets[1] for assets in parsed_assets]
            
            # Normalize base assets to remove k-token prefixes
            normalized_df['base_asset'] = [normalize_orderly_asset(asset) for asset in base_assets]
            normalized_df['quote_asset'] = quote_assets
            normalized_df['funding_rate'] = df['funding_rate']
            normalized_df['funding_interval_hours'] = 8  # Orderly uses 8-hour funding
            normalized_df['contract_type'] = df['contract_type']
            normalized_df['market_type'] = df['market_type']
            
            # Calculate APR (8-hour funding = 3 times per day)
            periods_per_year = (365 * 24) / 8  # 1,095 periods per year
            normalized_df['apr'] = df['funding_rate'] * periods_per_year * 100
            
            # Set prices to None (not available from this API)
            normalized_df['index_price'] = None
            normalized_df['mark_price'] = None
            
            # Open interest
            normalized_df['open_interest'] = df['open_interest']
            
            # Add timestamps
            if 'funding_time' in df.columns:
                normalized_df['funding_time'] = pd.to_datetime(df['funding_time'], unit='ms', errors='coerce')
            if 'next_funding_time' in df.columns:
                normalized_df['next_funding_time'] = pd.to_datetime(df['next_funding_time'], unit='ms', errors='coerce')
            
            return normalized_df

        except Exception as e:
            self.logger.error(f"Error normalizing Orderly Network data: {e}")
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
            url = f"{self.base_url}/v1/public/funding_rate_history"
            params = {
                'symbol': symbol,
                'limit': min(days * 3, 1000)  # 3 funding periods per day, max 1000
            }
            
            data = self.safe_request(url, params=params)
            
            if data and data.get('success') and 'data' in data:
                rows = data['data'].get('rows', [])
                if rows:
                    df = pd.DataFrame(rows)
                    df['funding_time'] = pd.to_datetime(df['funding_rate_timestamp'], unit='ms', errors='coerce')
                    df['funding_rate'] = df['funding_rate'].astype(float)
                    return df[['symbol', 'funding_rate', 'funding_time']]
            
            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()
