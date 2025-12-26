"""
Lighter Exchange Module
======================
Handles data fetching and normalization for Lighter DEX.
Lighter aggregates funding rate data from multiple exchanges and provides
a unified API for accessing current and historical funding rates.
"""

import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from .base_exchange import BaseExchange
from utils.logger import setup_logger
from utils.rate_limiter import rate_limiter


class LighterExchange(BaseExchange):
    """
    Lighter DEX data fetcher and normalizer.
    Features:
    - Aggregates funding rates from multiple exchanges
    - 330+ perpetual contracts
    - Real-time and historical funding rate data
    - Public REST API access (no authentication required)
    """

    def __init__(self, enabled: bool = True):
        super().__init__("Lighter", enabled)
        self.base_url = 'https://mainnet.zklighter.elliot.ai'
        self.logger = setup_logger("LighterExchange")

        # API endpoints
        self.funding_rates_endpoint = f"{self.base_url}/api/v1/funding-rates"
        self.historical_fundings_endpoint = f"{self.base_url}/api/v1/fundings"
        self.order_book_details_endpoint = f"{self.base_url}/api/v1/orderBookDetails"

        # Cache for contract metadata
        self.contract_metadata = {}

        # Store active markets
        self.active_markets = []

        # Cache for order book details (open interest, last trade price)
        self.order_book_details = {}

        self.logger.info("Lighter exchange initialized with REST API")

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch current funding rates from Lighter API.

        Returns:
            DataFrame with raw Lighter funding rate data
        """
        try:
            # Fetch current funding rates for all markets
            response = self.safe_request(self.funding_rates_endpoint)

            if not response:
                self.logger.error("Failed to fetch funding rates from Lighter API")
                return pd.DataFrame()

            # Check response structure
            if not isinstance(response, dict) or 'funding_rates' not in response:
                self.logger.error(f"Unexpected response structure from Lighter API")
                return pd.DataFrame()

            funding_rates = response.get('funding_rates', [])

            if not funding_rates:
                self.logger.warning("No funding rates data received from Lighter")
                return pd.DataFrame()

            # Filter to only include Lighter's own funding rates
            # (API returns rates from multiple exchanges, we only want 'lighter')
            lighter_rates = [rate for rate in funding_rates if rate.get('exchange') == 'lighter']

            if not lighter_rates:
                self.logger.warning("No Lighter exchange rates found in response")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(lighter_rates)

            # Store market metadata for later use (only Lighter entries)
            self.active_markets = lighter_rates
            for market in lighter_rates:
                market_id = market.get('market_id')
                if market_id:
                    self.contract_metadata[market_id] = {
                        'symbol': market.get('symbol'),
                        'exchange': market.get('exchange'),
                        'rate': market.get('rate')
                    }

            self.logger.info(f"Fetched {len(df)} contracts from Lighter")

            # Fetch order book details for open interest data
            self.order_book_details = self._fetch_order_book_details()

            if self.order_book_details:
                self.logger.info(f"OI data available for {len(self.order_book_details)} markets")
            else:
                self.logger.warning("No OI data fetched - all contracts will have 0 OI")

            return df

        except Exception as e:
            self.logger.error(f"Error fetching Lighter data: {e}")
            return pd.DataFrame()

    def _fetch_order_book_details(self) -> Dict[int, Dict]:
        """
        Fetch open interest and price data from orderBookDetails endpoint.
        Returns a dict keyed by market_id with open_interest and last_trade_price.
        """
        try:
            response = self.safe_request(self.order_book_details_endpoint)
            if not response:
                self.logger.warning("Failed to fetch orderBookDetails from Lighter API")
                return {}

            order_book_details = response.get('order_book_details', [])
            if not order_book_details:
                self.logger.warning("No order_book_details in response")
                return {}

            result = {}
            for detail in order_book_details:
                market_id = detail.get('market_id')
                if market_id is not None:
                    try:
                        result[market_id] = {
                            'open_interest': float(detail.get('open_interest', 0) or 0),
                            'last_trade_price': float(detail.get('last_trade_price', 0) or 0)
                        }
                    except (ValueError, TypeError):
                        continue

            self.logger.info(f"Fetched order book details for {len(result)} markets")
            return result

        except Exception as e:
            self.logger.warning(f"Failed to fetch orderBookDetails: {e}")
            return {}

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Lighter data to unified format.

        Args:
            df: Raw Lighter data with columns: market_id, exchange, symbol, rate

        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())

        try:
            # Helper function to normalize symbol names
            def normalize_symbol(symbol, exchange=None):
                if pd.isna(symbol):
                    return None
                symbol = str(symbol).upper()

                # Remove numeric multiplier prefixes for all exchanges
                # This ensures consistent normalization across all data
                if symbol.startswith('1000000'):
                    symbol = symbol[7:]  # Remove 1000000 prefix
                elif symbol.startswith('100000'):
                    symbol = symbol[6:]  # Remove 100000 prefix
                elif symbol.startswith('10000'):
                    symbol = symbol[5:]  # Remove 10000 prefix
                elif symbol.startswith('1000'):
                    symbol = symbol[4:]  # Remove 1000 prefix
                elif symbol.startswith('1M'):
                    symbol = symbol[2:]  # Remove 1M prefix
                elif symbol.startswith('100X') and len(symbol) > 4:
                    symbol = symbol[3:]  # Remove 100X prefix

                # Handle 'k' prefix (e.g., kPEPE -> PEPE)
                if symbol.startswith('K') and len(symbol) > 1:
                    symbol = symbol[1:]

                return symbol

            # Calculate APR based on funding rate
            # Lighter divides the 1-hour premium by 8 to align with CEX standards
            # Even though funding is paid hourly, the rate shown is already divided by 8
            def calculate_apr(funding_rate):
                try:
                    if pd.isna(funding_rate):
                        return None
                    # We receive the raw rate from df['rate']
                    # Divide by 8 to get CEX-standard 8-hour equivalent
                    # APR = (funding_rate / 8) * 3 * 365 * 100 (3 payments per day)
                    return float(funding_rate) / 8 * 3 * 365 * 100
                except (ValueError, TypeError):
                    return None

            # Calculate USD open interest from order book details
            def calculate_usd_open_interest(row):
                try:
                    market_id = row.get('market_id')
                    if market_id is None:
                        return 0
                    # Convert numpy.int64 to Python int for dictionary lookup
                    market_id = int(market_id)
                    if market_id not in self.order_book_details:
                        return 0
                    details = self.order_book_details[market_id]
                    oi = details.get('open_interest', 0)
                    price = details.get('last_trade_price', 0)
                    return oi * price if oi and price else 0
                except (ValueError, TypeError):
                    return 0

            # Create normalized DataFrame
            normalized = pd.DataFrame({
                'exchange': 'Lighter',  # Use Lighter as the exchange name
                'symbol': df.apply(lambda row: f"{normalize_symbol(row.get('symbol'))}USDT"
                                 if pd.notna(row.get('symbol')) else None, axis=1),
                'base_asset': df.apply(lambda row: normalize_symbol(row.get('symbol')), axis=1),
                'quote_asset': 'USDT',  # Default to USDT
                'funding_rate': pd.to_numeric(df.get('rate', 0), errors='coerce') / 8,  # Divide by 8 for CEX standard alignment
                'funding_interval_hours': 8,  # Using 8-hour equivalent rate format (CEX standard)
                'apr': df['rate'].apply(calculate_apr) if 'rate' in df.columns else None,
                'index_price': None,  # Not available from REST API
                'mark_price': None,   # Not available from REST API
                'open_interest': df.apply(calculate_usd_open_interest, axis=1),
                'contract_type': 'PERPETUAL',
                'market_type': 'Lighter Aggregated',  # Lighter aggregates from multiple exchanges
            })

            # Add metadata fields
            if 'market_id' in df.columns:
                normalized['market_id'] = df['market_id']

            if 'exchange' in df.columns:
                normalized['source_exchange'] = df['exchange']  # Keep track of the original exchange

            # Filter out rows with invalid data
            normalized = normalized[
                normalized['symbol'].notna() &
                normalized['base_asset'].notna() &
                normalized['funding_rate'].notna()
            ]

            self.logger.info(f"Normalized {len(normalized)} contracts for Lighter")

            return normalized

        except Exception as e:
            self.logger.error(f"Error normalizing Lighter data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())

    def fetch_historical_funding_rates(self, market_id: int, days: int = 30,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific market from Lighter.

        Args:
            market_id: Market ID from Lighter (e.g., 1 for BTC, 50 for ARB)
            days: Number of days of history to fetch (ignored if start_time/end_time provided)
            start_time: Optional start datetime (UTC)
            end_time: Optional end datetime (UTC)

        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Calculate time range
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)

            # Convert to timestamps (Lighter uses Unix timestamps)
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())

            # Prepare parameters for the fundings endpoint
            params = {
                'market_id': market_id,
                'resolution': '1h',  # 1-hour resolution
                'start_timestamp': start_ts,
                'end_timestamp': end_ts,
                'count_back': min(days * 24, 1000)  # Limit to reasonable number of records
            }

            response = self.safe_request(
                self.historical_fundings_endpoint,
                params=params,
                silent_errors=True
            )

            if not response:
                self.logger.warning(f"No historical data fetched for market_id {market_id}")
                return pd.DataFrame()

            # Check response structure
            if not isinstance(response, dict) or 'fundings' not in response:
                self.logger.warning(f"Unexpected response format for market_id {market_id} historical data")
                return pd.DataFrame()

            fundings = response.get('fundings', [])

            if not fundings:
                return pd.DataFrame()

            # Create DataFrame
            df = pd.DataFrame(fundings)

            # Convert timestamps to datetime
            if 'timestamp' in df.columns:
                df['funding_time'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

            # Add additional fields
            df['market_id'] = market_id
            df['exchange'] = 'Lighter'

            # Get symbol from metadata if available
            symbol = None
            for market in self.active_markets:
                if market.get('market_id') == market_id:
                    symbol = market.get('symbol')
                    break

            if symbol:
                df['symbol'] = f"{symbol}USDT"
                df['base_asset'] = symbol
            else:
                df['symbol'] = f"MARKET_{market_id}"
                df['base_asset'] = f"MARKET_{market_id}"

            # Historical endpoint returns (percentage / 8), need to convert to decimal
            # The historical API returns values like 0.0012 which is already (raw_rate * 100) / 8
            # We need to divide by 100 to get the CEX-standard decimal rate
            if 'rate' in df.columns:
                df['funding_rate'] = pd.to_numeric(df['rate'], errors='coerce') / 100

            # Set funding interval to 8 hours (using CEX-standard equivalent rate)
            df['funding_interval_hours'] = 8

            # Calculate APR for historical rates (funding_rate already divided by 8)
            df['apr'] = df['funding_rate'] * 3 * 365 * 100

            # Select relevant columns
            columns = ['exchange', 'symbol', 'funding_rate', 'funding_time',
                      'funding_interval_hours', 'base_asset', 'apr', 'market_id']

            # Filter columns that exist
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]

            self.logger.info(f"Fetched {len(df)} historical records for market_id {market_id}")

            return df

        except Exception as e:
            self.logger.error(f"Error fetching historical data for market_id {market_id}: {e}")
            return pd.DataFrame()

    def fetch_all_perpetuals_historical(self, days: int = 30, batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all Lighter perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of markets to process at once (not used for rate limiting)
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

        actual_days = (end_time - start_time).days

        self.logger.info(f"Starting historical data fetch for all Lighter perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")

        # Get list of active markets if not already fetched
        if not self.active_markets:
            meta_data = self.fetch_data()
            if meta_data.empty:
                self.logger.error("Failed to fetch Lighter market metadata")
                return pd.DataFrame()

        # Get unique market IDs
        market_ids = []
        for market in self.active_markets:
            market_id = market.get('market_id')
            if market_id:
                market_ids.append(market_id)

        self.logger.info(f"Found {len(market_ids)} unique markets")

        all_historical_data = []

        # Process each market
        for i, market_id in enumerate(market_ids):
            try:
                # Fetch historical data for this market
                hist_df = self.fetch_historical_funding_rates(market_id, actual_days, start_time, end_time)

                if not hist_df.empty:
                    all_historical_data.append(hist_df)
                    self.logger.debug(f"Fetched {len(hist_df)} records for market_id {market_id}")

                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(market_ids)) * 100
                    progress_callback(i + 1, len(market_ids), progress, f"Processing market {market_id}")

                # Respect rate limits via token bucket
                rate_limiter.acquire('lighter')

            except Exception as e:
                self.logger.error(f"Error fetching historical data for market_id {market_id}: {e}")
                continue

        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            self.logger.info(f"Successfully fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            self.logger.warning("No historical data fetched for any Lighter market")
            return pd.DataFrame()

    def get_active_market_ids(self) -> List[int]:
        """
        Get list of active market IDs.

        Returns:
            List of market IDs (e.g., [1, 25, 50, ...])
        """
        try:
            # Fetch current data to get active contracts
            if not self.active_markets:
                self.fetch_data()

            if not self.active_markets:
                return []

            # Extract unique market IDs
            market_ids = []
            for market in self.active_markets:
                market_id = market.get('market_id')
                if market_id:
                    market_ids.append(market_id)

            return sorted(market_ids)

        except Exception as e:
            self.logger.error(f"Error getting active market IDs: {e}")
            return []

    def get_symbol_by_market_id(self, market_id: int) -> Optional[str]:
        """
        Get symbol name for a given market ID.

        Args:
            market_id: The market ID to lookup

        Returns:
            Symbol name or None if not found
        """
        for market in self.active_markets:
            if market.get('market_id') == market_id:
                return market.get('symbol')
        return None