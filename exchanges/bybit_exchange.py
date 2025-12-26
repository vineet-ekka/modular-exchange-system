"""
ByBit Exchange Module
=====================
Handles data fetching and normalization for ByBit exchange.
Supports both Linear (USDT/USDC) and Inverse perpetual markets.
"""

import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger
from utils.rate_limiter import rate_limiter


class ByBitExchange(BaseExchange):
    """
    ByBit exchange data fetcher and normalizer.
    Features:
    - 668+ Linear (USDT) perpetual contracts
    - 28+ Inverse (USD) perpetual contracts
    - Mixed funding intervals: 1, 2, 4, and 8 hours
    - Dynamic APR calculation based on funding interval
    """

    def __init__(self, enabled: bool = True):
        super().__init__("ByBit", enabled)
        self.base_url = 'https://api.bybit.com'
        self.logger = setup_logger("ByBitExchange")

        # Cache for instrument data
        self.instrument_cache = {}

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from ByBit API (both Linear and Inverse markets).

        Returns:
            DataFrame with raw ByBit data
        """
        try:
            all_data = []

            # Process Linear (USDT) perpetuals
            linear_data = self._fetch_market_data('linear')
            if not linear_data.empty:
                all_data.append(linear_data)
                self.logger.info(f"Fetched {len(linear_data)} linear perpetual contracts")

            # Process Inverse (USD) perpetuals
            inverse_data = self._fetch_market_data('inverse')
            if not inverse_data.empty:
                all_data.append(inverse_data)
                self.logger.info(f"Fetched {len(inverse_data)} inverse perpetual contracts")

            if not all_data:
                self.logger.warning("No data fetched from ByBit")
                return pd.DataFrame()

            # Combine all market data
            combined_df = pd.concat(all_data, ignore_index=True)

            return combined_df

        except Exception as e:
            self.logger.error(f"Error fetching ByBit data: {e}")
            return pd.DataFrame()

    def _fetch_market_data(self, category: str) -> pd.DataFrame:
        """
        Fetch data for a specific market category.

        Args:
            category: 'linear' or 'inverse'

        Returns:
            DataFrame with market data
        """
        try:
            # First fetch all instruments info (with pagination)
            instruments = self._fetch_all_instruments(category)
            if not instruments:
                return pd.DataFrame()

            # Create DataFrame from instruments
            instruments_df = pd.DataFrame(instruments)

            # Filter for trading status only
            instruments_df = instruments_df[instruments_df['status'] == 'Trading'].copy()

            # Cache instrument data for quick lookup
            for _, row in instruments_df.iterrows():
                self.instrument_cache[row['symbol']] = {
                    'fundingInterval': row['fundingInterval'],
                    'contractType': row['contractType'],
                    'baseCoin': row['baseCoin'],
                    'quoteCoin': row['quoteCoin']
                }

            # Fetch current tickers with funding rates
            tickers_url = f"{self.base_url}/v5/market/tickers"
            tickers_params = {'category': category}

            tickers_data = self.safe_request(tickers_url, params=tickers_params)
            if not tickers_data or 'result' not in tickers_data:
                self.logger.warning(f"Failed to fetch tickers for {category}")
                return pd.DataFrame()

            tickers_df = pd.DataFrame(tickers_data['result']['list'])

            # Merge instruments with tickers on symbol
            merged_df = pd.merge(
                instruments_df[['symbol', 'baseCoin', 'quoteCoin', 'fundingInterval', 'contractType']],
                tickers_df[['symbol', 'fundingRate', 'markPrice', 'indexPrice', 'openInterest', 'openInterestValue', 'nextFundingTime']],
                on='symbol',
                how='inner'
            )

            # Add category info
            merged_df['category'] = category

            return merged_df

        except Exception as e:
            self.logger.error(f"Error fetching {category} market data: {e}")
            return pd.DataFrame()

    def _fetch_all_instruments(self, category: str) -> List[Dict]:
        """
        Fetch all instruments for a category, handling pagination.

        Args:
            category: 'linear' or 'inverse'

        Returns:
            List of instrument dictionaries
        """
        all_instruments = []
        cursor = None
        max_iterations = 10  # Safety limit

        for _ in range(max_iterations):
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {
                'category': category,
                'limit': 1000
            }

            if cursor:
                params['cursor'] = cursor

            response = self.safe_request(url, params=params)

            if not response or 'result' not in response:
                break

            instruments = response['result'].get('list', [])
            if not instruments:
                break

            # Filter for perpetual contracts only
            perpetuals = [i for i in instruments if i.get('contractType') in ['LinearPerpetual', 'InversePerpetual']]
            all_instruments.extend(perpetuals)

            # Check for next page
            cursor = response['result'].get('nextPageCursor')
            if not cursor:
                break

            # Respect rate limits via token bucket
            rate_limiter.acquire('bybit')

        return all_instruments

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform ByBit data to unified format.

        Args:
            df: Raw ByBit data

        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())

        try:
            # Normalize base asset names
            def normalize_bybit_asset(symbol, base_coin):
                """Remove numeric prefixes from asset names."""
                if pd.isna(base_coin):
                    return None

                base_coin = str(base_coin)

                # Handle numeric prefixes in baseCoin
                if base_coin.startswith('10000000'):
                    return base_coin[8:]  # e.g., 10000000SHIB -> SHIB
                elif base_coin.startswith('1000000'):
                    return base_coin[7:]  # e.g., 1000000BABYDOGE -> BABYDOGE
                elif base_coin.startswith('100000'):
                    return base_coin[6:]  # e.g., 100000MOG -> MOG
                elif base_coin.startswith('10000'):
                    return base_coin[5:]  # e.g., 10000LADYS -> LADYS
                elif base_coin.startswith('1000'):
                    return base_coin[4:]  # e.g., 1000FLOKI -> FLOKI

                return base_coin

            # Calculate APR based on funding interval
            def calculate_apr(row):
                try:
                    funding_rate = float(row.get('fundingRate', 0) or 0)
                    interval_mins = float(row.get('fundingInterval', 480) or 480)  # Default 8 hours
                    interval_hours = interval_mins / 60

                    if interval_hours <= 0:
                        return None

                    # Calculate periods per year
                    periods_per_day = 24 / interval_hours
                    periods_per_year = periods_per_day * 365

                    return funding_rate * periods_per_year * 100

                except (ValueError, TypeError, ZeroDivisionError):
                    return None

            # Convert funding interval from minutes to hours
            df['funding_interval_hours'] = pd.to_numeric(df['fundingInterval'], errors='coerce') / 60

            # Create normalized DataFrame
            normalized = pd.DataFrame({
                'exchange': 'ByBit',
                'symbol': df['symbol'],
                'base_asset': df.apply(lambda row: normalize_bybit_asset(row.get('symbol'), row.get('baseCoin')), axis=1),
                'quote_asset': df['quoteCoin'],
                'funding_rate': pd.to_numeric(df['fundingRate'], errors='coerce'),
                'funding_interval_hours': df['funding_interval_hours'],
                'apr': df.apply(calculate_apr, axis=1),
                'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
                'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
                'open_interest': pd.to_numeric(df['openInterestValue'], errors='coerce'),  # Already in USD
                'contract_type': df['contractType'].apply(lambda x: 'PERPETUAL' if 'Perpetual' in str(x) else str(x)),
                'market_type': df['category'].apply(lambda x: f"ByBit {str(x).title()}"),
            })

            # Add next funding time if available
            if 'nextFundingTime' in df.columns:
                normalized['next_funding_time'] = pd.to_datetime(
                    pd.to_numeric(df['nextFundingTime'], errors='coerce'),
                    unit='ms',
                    utc=True
                )

            # Filter out rows with invalid data
            normalized = normalized[
                normalized['symbol'].notna() &
                normalized['funding_rate'].notna() &
                normalized['mark_price'].notna() &
                (normalized['mark_price'] > 0)
            ]

            self.logger.info(f"Normalized {len(normalized)} contracts for ByBit")

            return normalized

        except Exception as e:
            self.logger.error(f"Error normalizing ByBit data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())

    def fetch_historical_funding_rates(self, symbol: str, days: int = 30,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol from ByBit.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            days: Number of days of history to fetch
            start_time: Optional start datetime (UTC)
            end_time: Optional end datetime (UTC)

        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Determine category based on symbol
            category = 'inverse' if symbol.endswith('USD') and not symbol.endswith('USDT') else 'linear'

            # Calculate time range
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)

            # ByBit limits to 200 records per request
            # We need to paginate through the data
            all_data = []
            current_end = int(end_time.timestamp() * 1000)
            target_start = int(start_time.timestamp() * 1000)

            max_iterations = 50  # Safety limit
            for _ in range(max_iterations):
                url = f"{self.base_url}/v5/market/funding/history"
                params = {
                    'category': category,
                    'symbol': symbol,
                    'endTime': current_end,
                    'limit': 200
                }

                response = self.safe_request(url, params=params, silent_errors=True)

                if not response or 'result' not in response:
                    break

                data_list = response['result'].get('list', [])
                if not data_list:
                    break

                # Add data to collection
                all_data.extend(data_list)

                # Check if we've reached our target start time
                last_timestamp = int(data_list[-1]['fundingRateTimestamp'])
                if last_timestamp <= target_start:
                    break

                # Set new end time for next iteration
                current_end = last_timestamp - 1

                # Respect rate limits via token bucket
                rate_limiter.acquire('bybit')

            if not all_data:
                self.logger.warning(f"No historical data fetched for {symbol}")
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(all_data)

            # Convert timestamps to datetime
            df['funding_time'] = pd.to_datetime(
                pd.to_numeric(df['fundingRateTimestamp'], errors='coerce'),
                unit='ms',
                utc=True
            )

            # Filter to requested time range
            df = df[(df['funding_time'] >= start_time) & (df['funding_time'] <= end_time)]

            # Get funding interval from cache or default
            funding_interval = 8  # Default 8 hours
            if symbol in self.instrument_cache:
                interval_mins = self.instrument_cache[symbol].get('fundingInterval', 480)
                funding_interval = interval_mins / 60

            # Add additional fields
            df['exchange'] = 'ByBit'
            df['funding_interval_hours'] = funding_interval

            # Normalize base asset
            base_asset = symbol
            for suffix in ['USDT', 'USDC', 'USD', 'PERP']:
                if symbol.endswith(suffix):
                    base_asset = symbol[:-len(suffix)]
                    break

            # Apply numeric prefix normalization
            if base_asset.startswith('10000000'):
                base_asset = base_asset[8:]
            elif base_asset.startswith('1000000'):
                base_asset = base_asset[7:]
            elif base_asset.startswith('100000'):
                base_asset = base_asset[6:]
            elif base_asset.startswith('10000'):
                base_asset = base_asset[5:]
            elif base_asset.startswith('1000'):
                base_asset = base_asset[4:]

            df['base_asset'] = base_asset

            # Rename columns to match our schema
            df = df.rename(columns={
                'fundingRate': 'funding_rate'
            })

            # Ensure funding_rate is numeric
            df['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')

            # Calculate APR
            periods_per_year = (365 * 24) / funding_interval
            df['apr'] = df['funding_rate'] * periods_per_year * 100

            # Select relevant columns
            columns = ['exchange', 'symbol', 'funding_rate', 'funding_time',
                      'funding_interval_hours', 'base_asset', 'apr']

            # Filter columns that exist
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]

            # Remove duplicates
            df = df.drop_duplicates(subset=['funding_time'], keep='first')

            # Sort by time
            df = df.sort_values('funding_time')

            self.logger.info(f"Fetched {len(df)} historical records for {symbol}")

            return df

        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_all_perpetuals_historical(self, days: int = 30, batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all ByBit perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to process at once
            progress_callback: Optional callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)

        Returns:
            Combined DataFrame with all historical funding rates
        """
        # Calculate time range
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=days)

        self.logger.info(f"Starting historical data fetch for all ByBit perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()}")

        # Get list of all active symbols
        current_data = self.fetch_data()
        if current_data.empty:
            self.logger.error("Failed to fetch current ByBit data")
            return pd.DataFrame()

        symbols = current_data['symbol'].unique().tolist()
        self.logger.info(f"Found {len(symbols)} unique symbols to fetch")

        all_historical_data = []

        # Process each symbol
        for i, symbol in enumerate(symbols):
            try:
                # Fetch historical data for this symbol
                hist_df = self.fetch_historical_funding_rates(symbol, days, start_time, end_time)

                if not hist_df.empty:
                    all_historical_data.append(hist_df)
                    self.logger.debug(f"Fetched {len(hist_df)} records for {symbol}")

                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(symbols)) * 100
                    progress_callback(i + 1, len(symbols), progress, f"Processing {symbol}")

                # Respect rate limits via token bucket
                rate_limiter.acquire('bybit')

            except Exception as e:
                self.logger.error(f"Error fetching historical data for {symbol}: {e}")
                continue

        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            self.logger.info(f"Successfully fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            self.logger.warning("No historical data fetched for any ByBit symbol")
            return pd.DataFrame()

    def get_active_symbols(self) -> List[str]:
        """
        Get list of active symbol names for historical backfill.

        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        try:
            # Fetch current data to get active contracts
            df = self.fetch_data()

            if df.empty:
                return []

            # Extract unique symbols
            symbols = df['symbol'].unique().tolist()

            return sorted(symbols)

        except Exception as e:
            self.logger.error(f"Error getting active symbols: {e}")
            return []