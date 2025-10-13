"""
Hyperliquid Exchange Module
===========================
Handles data fetching and normalization for Hyperliquid DEX.
Supports 170+ perpetual contracts with 1-hour funding intervals.
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class HyperliquidExchange(BaseExchange):
    """
    Hyperliquid DEX data fetcher and normalizer.
    Features:
    - 170+ active perpetual contracts
    - 1-hour funding intervals (24 payments/day)
    - No authentication required for public data
    - Special handling for 'k' prefix (thousands) and '@' prefix (indices)
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Hyperliquid", enabled)
        self.base_url = 'https://api.hyperliquid.xyz/info'
        self.logger = setup_logger("HyperliquidExchange")
        
        # Cache for contract metadata
        self.contract_metadata = {}
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Hyperliquid API.
        Uses metaAndAssetCtxs endpoint to get all contract data in one call.
        
        Returns:
            DataFrame with raw Hyperliquid data
        """
        try:
            # Prepare request body for metaAndAssetCtxs
            payload = {"type": "metaAndAssetCtxs"}
            
            # Make POST request to get all contract data
            data = self.safe_post_request(
                self.base_url,
                json_data=payload
            )

            if not data:
                self.logger.error("Failed to fetch contract data from Hyperliquid API")
                return pd.DataFrame()
            
            if not data or len(data) < 2:
                self.logger.error("Invalid response structure from Hyperliquid API")
                return pd.DataFrame()
            
            # Extract universe (contract metadata) and asset contexts (current data)
            metadata = data[0]
            asset_contexts = data[1]
            
            if 'universe' not in metadata:
                self.logger.error("No universe data in response")
                return pd.DataFrame()
            
            universe = metadata['universe']
            
            # Filter out delisted contracts if the field exists
            active_contracts = []
            for i, contract in enumerate(universe):
                # Check if contract is not delisted (default to active if field doesn't exist)
                if not contract.get('isDelisted', False):
                    if i < len(asset_contexts):
                        # Combine metadata with current data
                        contract_data = {
                            **contract,
                            **asset_contexts[i]
                        }
                        active_contracts.append(contract_data)
            
            if not active_contracts:
                self.logger.warning("No active contracts found")
                return pd.DataFrame()
            
            # Create DataFrame from active contracts
            df = pd.DataFrame(active_contracts)
            
            # Store metadata for later use
            for contract in active_contracts:
                if 'name' in contract:
                    self.contract_metadata[contract['name']] = {
                        'szDecimals': contract.get('szDecimals', 8),
                        'maxLeverage': contract.get('maxLeverage', 1)
                    }
            
            self.logger.info(f"Fetched {len(df)} active contracts from Hyperliquid")
            
            return df
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching Hyperliquid data: {e}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Hyperliquid data to unified format.
        
        Args:
            df: Raw Hyperliquid data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        try:
            # Handle special prefixes in asset names
            def normalize_asset_name(name):
                if pd.isna(name):
                    return name
                name = str(name)
                # Handle 'k' prefix (thousands) - remove prefix for base asset
                if name.startswith('k'):
                    return name[1:]  # e.g., kPEPE -> PEPE
                # Handle '@' prefix (indices) - keep for identification
                if name.startswith('@'):
                    return 'INDEX' + name[1:]  # e.g., @1 -> INDEX1
                return name
            
            # Convert open interest from base asset to USD
            def calculate_usd_open_interest(row):
                try:
                    oi = float(row.get('openInterest', 0) or 0)
                    mark_price = float(row.get('markPx', 0) or 0)
                    return oi * mark_price
                except (ValueError, TypeError):
                    return 0
            
            # Calculate APR for 1-hour funding intervals
            def calculate_apr(funding_rate):
                try:
                    if pd.isna(funding_rate):
                        return None
                    # 1-hour intervals = 24 payments per day = 8,760 per year
                    return float(funding_rate) * 24 * 365 * 100
                except (ValueError, TypeError):
                    return None
            
            # Create normalized DataFrame
            normalized = pd.DataFrame({
                'exchange': 'Hyperliquid',
                'symbol': df['name'].apply(lambda x: f"{x}USDC" if pd.notna(x) else None),
                'base_asset': df['name'].apply(normalize_asset_name),
                'quote_asset': 'USDC',  # All Hyperliquid contracts are USDC-quoted
                'funding_rate': pd.to_numeric(df['funding'], errors='coerce'),
                'funding_interval_hours': 1,  # Hyperliquid uses 1-hour intervals
                'apr': df['funding'].apply(lambda x: calculate_apr(pd.to_numeric(x, errors='coerce'))),
                'index_price': pd.to_numeric(df.get('oraclePx', df.get('markPx')), errors='coerce'),
                'mark_price': pd.to_numeric(df['markPx'], errors='coerce'),
                'open_interest': df.apply(calculate_usd_open_interest, axis=1),
                'contract_type': 'PERPETUAL',
                'market_type': 'Hyperliquid DEX',
            })
            
            # Add additional useful fields if needed
            if 'dayNtlVlm' in df.columns:
                normalized['volume_24h'] = pd.to_numeric(df['dayNtlVlm'], errors='coerce')
            
            if 'premium' in df.columns:
                normalized['premium'] = pd.to_numeric(df['premium'], errors='coerce')
            
            # Filter out rows with invalid data
            normalized = normalized[
                normalized['symbol'].notna() & 
                normalized['funding_rate'].notna() &
                normalized['mark_price'].notna() &
                (normalized['mark_price'] > 0)
            ]
            
            self.logger.info(f"Normalized {len(normalized)} contracts for Hyperliquid")
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing Hyperliquid data: {e}")
            return pd.DataFrame(columns=self.get_unified_columns())
    
    def fetch_historical_funding_rates(self, coin: str, days: int = 30,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific coin from Hyperliquid.

        Args:
            coin: Asset name (e.g., 'BTC', 'ETH')
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

            # Split into 15-day chunks to avoid 500-record limit
            # Hyperliquid API returns max 500 records per request
            # 15 days * 24 hours = 360 records, safely under the limit
            chunk_days = 15
            all_data = []
            current_start = start_time

            while current_start < end_time:
                # Calculate chunk end time
                chunk_end = min(current_start + timedelta(days=chunk_days), end_time)

                # Convert to milliseconds for API
                chunk_start_ms = int(current_start.timestamp() * 1000)
                chunk_end_ms = int(chunk_end.timestamp() * 1000)

                # Prepare request for funding history
                payload = {
                    "type": "fundingHistory",
                    "coin": coin,
                    "startTime": chunk_start_ms,
                    "endTime": chunk_end_ms
                }

                # Make POST request with rate limiting and retry logic
                chunk_data = self.safe_post_request(
                    self.base_url,
                    json_data=payload,
                    silent_errors=True  # Don't spam errors for individual coins
                )

                if chunk_data:
                    all_data.extend(chunk_data)
                    self.logger.debug(f"Fetched {len(chunk_data)} records for {coin} "
                                    f"({current_start.date()} to {chunk_end.date()})")

                # Move to next chunk
                current_start = chunk_end

            if not all_data:
                self.logger.warning(f"No historical data fetched for {coin}")
                return pd.DataFrame()

            # Create DataFrame from combined data
            df = pd.DataFrame(all_data)

            # Remove duplicates based on time (in case of overlapping chunks)
            df = df.drop_duplicates(subset=['time'], keep='first')
            
            # Convert timestamps from milliseconds to datetime
            df['funding_time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
            
            # Add additional fields
            df['symbol'] = f"{coin}USDC"
            df['exchange'] = 'Hyperliquid'
            df['funding_interval_hours'] = 1
            # Normalize base asset (remove 'k' prefix if present)
            if coin.startswith('k'):
                df['base_asset'] = coin[1:]  # e.g., kPEPE -> PEPE
            elif coin.startswith('@'):
                df['base_asset'] = 'INDEX' + coin[1:]  # e.g., @1 -> INDEX1
            else:
                df['base_asset'] = coin
            
            # Ensure fundingRate is properly parsed as numeric
            df['fundingRate'] = pd.to_numeric(df['fundingRate'], errors='coerce')
            
            # Calculate APR for historical rates
            df['apr'] = df['fundingRate'] * 24 * 365 * 100
            
            # Rename columns to match our schema
            df = df.rename(columns={
                'fundingRate': 'funding_rate'
            })
            
            # Select relevant columns
            columns = ['exchange', 'symbol', 'funding_rate', 'funding_time', 
                      'funding_interval_hours', 'base_asset', 'apr', 'premium']
            
            # Filter columns that exist
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]
            
            self.logger.info(f"Fetched {len(df)} historical records for {coin}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {coin}: {e}")
            return pd.DataFrame()
    
    def fetch_all_perpetuals_historical(self, days: int = 30, batch_size: int = 10,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all Hyperliquid perpetual contracts.
        
        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to process at once
            progress_callback: Optional callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)
            
        Returns:
            Combined DataFrame with all historical funding rates
        """
        # Calculate time range - use provided times or calculate from days
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=days)
        
        # Calculate actual days for the fetch_historical_funding_rates method
        actual_days = (end_time - start_time).days
        
        self.logger.info(f"Starting historical data fetch for all Hyperliquid perpetuals")
        self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")
        
        # First get list of all active assets
        meta_data = self.fetch_data()
        if meta_data.empty:
            self.logger.error("Failed to fetch Hyperliquid asset metadata")
            return pd.DataFrame()
        
        # Get unique base assets (using 'name' column from Hyperliquid API)
        assets = meta_data['name'].unique().tolist()
        self.logger.info(f"Found {len(assets)} unique assets")
        
        all_historical_data = []
        
        # Process each asset
        for i, asset in enumerate(assets):
            try:
                # Fetch historical data for this asset using specified time range
                hist_df = self.fetch_historical_funding_rates(asset, actual_days, start_time, end_time)
                
                if not hist_df.empty:
                    all_historical_data.append(hist_df)
                    self.logger.debug(f"Fetched {len(hist_df)} records for {asset}")
                
                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(assets)) * 100
                    progress_callback(i + 1, len(assets), progress, f"Processing {asset}")
                
                # Delay to respect rate limits (increased to avoid 429 errors)
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error fetching historical data for {asset}: {e}")
                continue
        
        # Combine all data
        if all_historical_data:
            combined_df = pd.concat(all_historical_data, ignore_index=True)
            self.logger.info(f"Successfully fetched {len(combined_df)} total historical records")
            return combined_df
        else:
            self.logger.warning("No historical data fetched for any Hyperliquid asset")
            return pd.DataFrame()
    
    def fetch_all_mid_prices(self) -> Dict[str, float]:
        """
        Fetch current mid prices for all assets.
        Useful for quick price checks and calculations.
        
        Returns:
            Dictionary mapping asset names to mid prices
        """
        try:
            payload = {"type": "allMids"}
            
            data = self.safe_post_request(
                self.base_url,
                json_data=payload
            )

            if not data:
                self.logger.warning("Failed to fetch mid prices")
                return {}
            
            # Convert string prices to float
            prices = {}
            for asset, price in data.items():
                try:
                    prices[asset] = float(price)
                except (ValueError, TypeError):
                    continue
            
            return prices
            
        except Exception as e:
            self.logger.error(f"Error fetching mid prices: {e}")
            return {}
    
    def get_active_coins(self) -> List[str]:
        """
        Get list of active coin names for historical backfill.
        
        Returns:
            List of coin names (e.g., ['BTC', 'ETH', 'SOL'])
        """
        try:
            # Fetch current data to get active contracts
            df = self.fetch_data()
            
            if df.empty:
                return []
            
            # Extract unique coin names
            coins = []
            for name in df['name'].unique():
                if pd.notna(name):
                    name = str(name)
                    # Skip special prefixes for historical data
                    if not name.startswith('@'):
                        coins.append(name)
            
            return sorted(coins)
            
        except Exception as e:
            self.logger.error(f"Error getting active coins: {e}")
            return []