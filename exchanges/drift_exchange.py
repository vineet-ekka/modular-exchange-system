import requests
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from exchanges.base_exchange import BaseExchange
from config.settings import DRIFT_MIN_VOLUME_THRESHOLD
from utils.rate_limiter import rate_limiter
import logging

logger = logging.getLogger(__name__)

class DriftExchange(BaseExchange):
    """
    Drift Exchange implementation for fetching perpetual contract funding rates.

    Drift is a decentralized perpetual futures exchange built on Solana.
    API Documentation: https://drift-labs.github.io/v2-teacher/
    Data API Base URL: https://data.api.drift.trade/
    """

    def __init__(self, enabled: bool = True):
        super().__init__("Drift", enabled)
        self.base_url = "https://data.api.drift.trade"
        self.funding_interval_hours = 1  # Drift uses hourly funding rates

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch current funding rates from Drift's /contracts endpoint.
        Filters for active PERP contracts only (excluding betting markets and 0 open interest).

        Returns:
            DataFrame of contract data
        """
        try:
            url = f"{self.base_url}/contracts"

            # Add cache-busting headers to ensure fresh data
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }

            logger.info(f"Fetching Drift funding rates from {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            contracts = data.get('contracts', [])

            # Filter for active PERP contracts only (excluding betting markets and zero-volume contracts)
            active_perps = []
            for contract in contracts:
                if (contract.get('product_type') == 'PERP' and
                    'BET' not in contract.get('ticker_id', '') and
                    float(contract.get('open_interest', 0)) > 0 and
                    float(contract.get('base_volume', 0)) > DRIFT_MIN_VOLUME_THRESHOLD):
                    active_perps.append(contract)

            logger.info(f"Drift: Fetched {len(active_perps)} active PERP contracts")

            # Convert to DataFrame
            if active_perps:
                return pd.DataFrame(active_perps)
            else:
                return pd.DataFrame()

        except requests.RequestException as e:
            logger.error(f"Error fetching Drift data: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error in Drift fetch_data: {e}")
            return pd.DataFrame()

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize Drift data to common format.

        Drift specifics:
        - Funding rates are already in decimal format (no conversion needed)
        - Symbol format: XXX-PERP needs to remove -PERP suffix
        - Special prefixes: 1MBONK → BONK, 1MPEPE → PEPE, 1KMEW → MEW, 1KWEN → WEN
        - APR calculation: funding_rate * 24 * 365 * 100 (hourly funding)

        Args:
            df: Raw contract DataFrame from Drift API

        Returns:
            DataFrame of normalized contract data
        """
        if df.empty:
            return pd.DataFrame()

        normalized = []

        for _, contract in df.iterrows():
            try:
                # Extract and normalize symbol
                ticker = contract.get('ticker_id', '')
                symbol = ticker.replace('-PERP', '')

                # Handle special prefixes
                if symbol.startswith('1M'):
                    symbol = symbol[2:]  # Remove '1M' prefix
                elif symbol.startswith('1K'):
                    symbol = symbol[2:]  # Remove '1K' prefix

                # Extract funding rate (API returns as percentage, convert to decimal)
                # e.g., 0.001713968 means 0.001713968%, divide by 100 to get decimal
                funding_rate = float(contract.get('funding_rate', 0)) / 100

                # Calculate APR (hourly funding, so 24 * 365 periods per year)
                periods_per_year = 24 * 365  # 8,760 hours per year
                apr = funding_rate * periods_per_year * 100

                # Extract next funding time
                next_funding_timestamp = contract.get('next_funding_rate_timestamp')
                next_funding_time = None
                if next_funding_timestamp and next_funding_timestamp != 'N/A':
                    try:
                        # Convert milliseconds to datetime
                        next_funding_time = datetime.fromtimestamp(int(next_funding_timestamp) / 1000)
                    except (ValueError, TypeError):
                        next_funding_time = None

                normalized_contract = {
                    'exchange': self.name,
                    'symbol': symbol,
                    'funding_rate': funding_rate,
                    'apr': apr,
                    'next_funding_time': next_funding_time,
                    'funding_interval_hours': self.funding_interval_hours,
                    'timestamp': datetime.now(timezone.utc),
                    'open_interest': float(contract.get('open_interest', 0)),
                    'index_price': float(contract.get('index_price', 0)),
                    'mark_price': float(contract.get('last_price', 0)),
                    'base_asset': symbol,
                    'quote_asset': 'USDC',
                    'contract_type': 'perpetual',
                    'market_type': 'perp'
                }

                normalized.append(normalized_contract)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Error normalizing Drift contract {contract.get('ticker_id', 'unknown')}: {e}")
                continue

        logger.info(f"Drift: Normalized {len(normalized)} contracts")

        # Convert to DataFrame
        if normalized:
            return pd.DataFrame(normalized)
        else:
            return pd.DataFrame()

    def fetch_historical_funding_rates(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        Fetch historical funding rates for a specific symbol from Drift.
        Uses the /fundingRates endpoint which returns up to 30 days of hourly data.

        Args:
            symbol: The trading symbol (e.g., 'SOL', 'BTC')
            days: Number of days of historical data (max 30)

        Returns:
            List of historical funding rate records
        """
        try:
            # Convert symbol to Drift format (add -PERP suffix)
            market_name = f"{symbol}-PERP"

            # Handle special cases where we need prefixes
            special_symbols = {
                'BONK': '1MBONK-PERP',
                'PEPE': '1MPEPE-PERP',
                'MEW': '1KMEW-PERP',
                'WEN': '1KWEN-PERP'
            }

            if symbol in special_symbols:
                market_name = special_symbols[symbol]

            url = f"{self.base_url}/fundingRates"
            params = {'marketName': market_name}

            logger.info(f"Fetching Drift historical rates for {market_name}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            funding_rates = data.get('fundingRates', [])

            historical = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            for rate_data in funding_rates:
                try:
                    # Parse timestamp (ts is in seconds, not milliseconds)
                    timestamp = int(rate_data.get('ts', 0))
                    if timestamp == 0:
                        continue

                    funding_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

                    # Skip if outside requested range
                    if funding_time < cutoff_time:
                        continue

                    # Calculate funding rate percentage
                    # Formula: (fundingRate / 1e9) / (oraclePriceTwap / 1e6)
                    funding_rate_raw = float(rate_data.get('fundingRate', 0))
                    oracle_twap = float(rate_data.get('oraclePriceTwap', 1))

                    if oracle_twap == 0:
                        continue

                    funding_rate_pct = (funding_rate_raw / 1e9) / (oracle_twap / 1e6)

                    # Calculate APR
                    apr = funding_rate_pct * 24 * 365 * 100

                    historical.append({
                        'exchange': self.name,
                        'symbol': symbol,
                        'funding_rate': funding_rate_pct,
                        'apr': apr,
                        'funding_time': funding_time,
                        'funding_interval_hours': self.funding_interval_hours
                    })

                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Error parsing Drift historical rate: {e}")
                    continue

            # Sort by funding time (newest first)
            historical.sort(key=lambda x: x['funding_time'], reverse=True)

            logger.info(f"Drift: Fetched {len(historical)} historical rates for {symbol}")
            return historical

        except requests.RequestException as e:
            logger.error(f"Error fetching Drift historical data for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Drift fetch_historical: {e}")
            return []

    def fetch_all_perpetuals_historical(self, days: int = 30,
                                       batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all Drift perpetual contracts.

        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to process at once (not used for sequential processing)
            progress_callback: Optional callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)

        Returns:
            Combined DataFrame with all historical funding rates
        """
        import time

        # Calculate time range - use provided times or calculate from days
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=days)

        # Calculate actual days for logging
        actual_days = (end_time - start_time).days

        logger.info(f"Starting historical data fetch for all Drift perpetuals")
        logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")

        # Get list of all perpetual contracts using fetch_data
        contracts_df = self.fetch_data()
        if contracts_df.empty:
            logger.error("Failed to fetch Drift contracts")
            return pd.DataFrame()

        # Normalize the data to get the symbols
        normalized_df = self.normalize_data(contracts_df)
        if normalized_df.empty:
            logger.error("Failed to normalize Drift contracts")
            return pd.DataFrame()

        # Get unique symbols
        symbols = normalized_df['symbol'].unique().tolist()

        logger.info(f"Found {len(symbols)} perpetual contracts")

        all_historical_data = []

        # Process each symbol
        for i, symbol in enumerate(symbols):
            try:
                # Fetch historical data for this symbol using actual days
                historical_list = self.fetch_historical_funding_rates(symbol, days=actual_days)

                if historical_list:
                    # Convert list of dicts to DataFrame
                    df = pd.DataFrame(historical_list)

                    # Filter by date range if needed
                    if 'funding_time' in df.columns:
                        df['funding_time'] = pd.to_datetime(df['funding_time'])

                        # If start_time or end_time have timezone info, localize the funding_time column
                        if start_time and start_time.tzinfo is not None:
                            # Assume UTC for funding times if not already timezone-aware
                            if df['funding_time'].dt.tz is None:
                                df['funding_time'] = df['funding_time'].dt.tz_localize('UTC')

                        # Convert start_time and end_time to pandas Timestamps for comparison
                        start_ts = pd.Timestamp(start_time) if start_time else None
                        end_ts = pd.Timestamp(end_time) if end_time else None

                        if start_ts and end_ts:
                            df = df[(df['funding_time'] >= start_ts) & (df['funding_time'] <= end_ts)]

                    if not df.empty:
                        all_historical_data.append(df)
                        logger.debug(f"Fetched {len(df)} records for {symbol}")

                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(symbols)) * 100
                    progress_callback(i + 1, len(symbols), progress, f"Processing {symbol}")

                # Respect rate limits via token bucket
                rate_limiter.acquire('drift')

            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}")

        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            logger.info(f"Completed: fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            logger.warning("No historical data fetched for Drift")
            return pd.DataFrame()