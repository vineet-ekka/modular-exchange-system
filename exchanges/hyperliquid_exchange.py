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
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                self.logger.error(f"API request failed with status {response.status_code}")
                return pd.DataFrame()
            
            data = response.json()
            
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
    
    def fetch_historical_funding_rates(self, coin: str, days: int = 30) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific coin from Hyperliquid.
        
        Args:
            coin: Asset name (e.g., 'BTC', 'ETH')
            days: Number of days of history to fetch
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Calculate start time in milliseconds
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            # Prepare request for funding history
            payload = {
                "type": "fundingHistory",
                "coin": coin,
                "startTime": start_time
            }
            
            # Make POST request
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch history for {coin}: {response.status_code}")
                return pd.DataFrame()
            
            data = response.json()
            
            if not data:
                self.logger.warning(f"No historical data for {coin}")
                return pd.DataFrame()
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
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
                # Fetch historical data for this asset using actual days
                hist_df = self.fetch_historical_funding_rates(asset, actual_days)
                
                if not hist_df.empty:
                    all_historical_data.append(hist_df)
                    self.logger.debug(f"Fetched {len(hist_df)} records for {asset}")
                
                # Update progress
                if progress_callback:
                    progress = ((i + 1) / len(assets)) * 100
                    progress_callback(i + 1, len(assets), progress, f"Processing {asset}")
                
                # Small delay to respect rate limits
                time.sleep(0.5)
                
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
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch mid prices: {response.status_code}")
                return {}
            
            data = response.json()
            
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