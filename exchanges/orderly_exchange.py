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

            # Fetch ALL open interests in a single batch call
            oi_map = self._fetch_all_open_interests()
            self.logger.info(f"Fetched open interest data for {len(oi_map)} contracts")

            # Fetch funding rates for each perpetual
            all_data = []
            for instrument in perp_instruments:
                symbol = instrument['symbol']

                # Get current funding rate
                funding_data = self._fetch_funding_rate(symbol)
                if funding_data:
                    # Get open interest from pre-fetched batch data
                    open_interest = oi_map.get(symbol, 0.0)
                    
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

    def _fetch_all_open_interests(self) -> Dict[str, float]:
        """
        Fetch open interest for ALL symbols in a single API call.

        Returns:
            Dictionary mapping symbol to open interest value
        """
        try:
            url = f"{self.base_url}/v1/public/market_info/traders_open_interests"
            data = self.safe_request(url)

            if data and data.get('success') and 'data' in data:
                rows = data['data'].get('rows', [])
                oi_map = {}
                for row in rows:
                    symbol = row.get('symbol')
                    long_oi = row.get('long_oi', 0)
                    short_oi = row.get('short_oi', 0)
                    if symbol:
                        oi_map[symbol] = abs(long_oi)
                return oi_map
            return {}

        except Exception as e:
            self.logger.error(f"Error fetching open interests: {e}")
            return {}

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
                    df['symbol'] = symbol
                    return df[['symbol', 'funding_rate', 'funding_time']]

            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()

    def _extract_base_asset(self, symbol: str) -> str:
        """
        Extract base asset from Orderly symbol.

        Args:
            symbol: Trading symbol (e.g., 'PERP_BTC_USDC' or 'PERP_1000SHIB_USDC')

        Returns:
            Base asset with numerical prefixes removed (e.g., 'BTC' or 'SHIB')
        """
        if not symbol:
            return symbol

        symbol_str = str(symbol)

        if symbol_str.startswith('PERP_'):
            parts = symbol_str[5:].split('_')
            if len(parts) >= 2:
                base_asset = parts[0]

                prefixes_to_remove = [
                    '1000000',
                    '100000',
                    '10000',
                    '1000',
                    '100',
                    '10',
                ]

                for prefix in prefixes_to_remove:
                    if base_asset.startswith(prefix):
                        return base_asset[len(prefix):]

                return base_asset

        return symbol_str

    def _extract_quote_asset(self, symbol: str) -> str:
        """
        Extract quote asset from Orderly symbol.

        Args:
            symbol: Trading symbol (e.g., 'PERP_BTC_USDC')

        Returns:
            Quote asset (e.g., 'USDC')
        """
        if not symbol:
            return ''

        symbol_str = str(symbol)

        if symbol_str.startswith('PERP_'):
            parts = symbol_str[5:].split('_')
            if len(parts) >= 2:
                return parts[-1]

        return ''

    def fetch_all_perpetuals_historical(self, days: int = 30,
                                       batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to fetch concurrently (unused, kept for compatibility)
            progress_callback: Callback for progress updates
            start_time: Optional start time (unused, Orderly API uses limit parameter)
            end_time: Optional end time (unused, Orderly API uses limit parameter)

        Returns:
            Combined DataFrame with all historical funding rates
        """
        try:
            instruments_data = self._fetch_instruments()
            if not instruments_data:
                self.logger.warning("No instruments found")
                return pd.DataFrame()

            perp_symbols = [inst['symbol'] for inst in instruments_data
                          if inst.get('symbol_type') == 'PERP' or 'PERP' in inst.get('symbol', '')]

            if not perp_symbols:
                self.logger.warning("No perpetual symbols found")
                return pd.DataFrame()

            self.logger.info(f"Fetching historical data for {len(perp_symbols)} perpetual contracts")

            all_historical_data = []
            total_symbols = len(perp_symbols)

            for i, symbol in enumerate(perp_symbols):
                try:
                    df = self.fetch_historical_funding_rates(symbol, days)
                    if not df.empty:
                        df['exchange'] = 'Orderly'
                        df['funding_interval_hours'] = 8

                        base_asset = self._extract_base_asset(symbol)
                        quote_asset = self._extract_quote_asset(symbol)

                        df['base_asset'] = base_asset
                        df['quote_asset'] = quote_asset

                        all_historical_data.append(df)
                        self.logger.debug(f"Fetched {len(df)} records for {symbol}")

                    if progress_callback:
                        progress = ((i + 1) / total_symbols) * 100
                        progress_callback(i + 1, total_symbols, progress, f"Processing {symbol}")

                    time.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
                    continue

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
