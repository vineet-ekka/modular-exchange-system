"""
KuCoin Exchange Module
=====================
Handles data fetching and normalization for KuCoin exchange.
Includes historical funding rate retrieval capabilities.
"""

import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class KuCoinExchange(BaseExchange):
    """
    KuCoin exchange data fetcher and normalizer.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("KuCoin", enabled)
        self.base_url = 'https://api-futures.kucoin.com/api/v1/'
        self.logger = setup_logger("KuCoinExchange")
    
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from KuCoin API.
        
        Returns:
            DataFrame with raw KuCoin data
        """
        try:
            # Fetch contracts data
            contracts_data = self.safe_request(self.base_url + 'contracts/active')
            
            if not contracts_data:
                return pd.DataFrame()
            
            # Parse the response
            if 'data' in contracts_data:
                df = pd.DataFrame(contracts_data['data'])
            else:
                df = pd.DataFrame(contracts_data)
            
            if len(df) == 0:
                return df
            
            # Filter for perpetual contracts (FFWCSX type) and active status
            if 'type' in df.columns and 'status' in df.columns:
                # Only include contracts with status 'Open' (exclude 'Settled', 'Expired', etc.)
                perp_df = df[(df['type'] == 'FFWCSX') & (df['status'] == 'Open')].copy()
                self.logger.info(f"Found {len(perp_df)} active perpetual contracts (filtered {len(df) - len(perp_df)} non-active)")
            elif 'type' in df.columns:
                perp_df = df[df['type'] == 'FFWCSX'].copy()
            else:
                perp_df = df.copy()
            
            # Convert funding rate granularity from milliseconds to hours
            if 'fundingRateGranularity' in perp_df.columns:
                perp_df['fundingIntervalHours'] = perp_df['fundingRateGranularity'].apply(
                    lambda x: x / (1000 * 60 * 60) if pd.notna(x) and x > 0 else None
                )
            
            # Removed next funding time conversion
            
            # Convert numeric columns
            numeric_columns = ['openInterest', 'fundingFeeRate', 'markPrice', 'indexPrice']
            for col in numeric_columns:
                if col in perp_df.columns:
                    perp_df[col] = pd.to_numeric(perp_df[col], errors='coerce')
            
            return perp_df
            
        except Exception as e:
            print(f"Error fetching KuCoin data: {str(e)}")
            return pd.DataFrame()
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform KuCoin data to unified format.
        
        Args:
            df: Raw KuCoin data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        # Normalize base assets (XBT -> BTC and handle numeric prefixes)
        def normalize_kucoin_base_asset(symbol, base_currency):
            # First handle XBT -> BTC
            base = 'BTC' if base_currency == 'XBT' else base_currency
            
            # Special case for 1MBABYDOGE (1M = 1 Million denomination)
            if symbol.startswith('1MBABYDOGE'):
                return 'BABYDOGE'
            
            # Special case: If baseCurrency itself has numeric prefix, normalize it
            if base_currency == '1000X':
                return 'X'  # 1000X is actually X token with 1000x denomination
            
            # Handle numeric prefixes in order (longest first)
            # Check for 1000000 prefix first
            if symbol.startswith('1000000'):
                # Extract the actual base asset from symbol
                clean = symbol[7:]  # Remove '1000000' (7 chars)
                # Remove common suffixes like USDTM, USDCM
                for suffix in ['USDTM', 'USDCM', 'USDM']:
                    if clean.endswith(suffix):
                        return clean[:-len(suffix)]
                return base  # Fallback to original if pattern doesn't match
            # Check for 10000 prefix
            elif symbol.startswith('10000'):
                # Extract the actual base asset from symbol
                clean = symbol[5:]  # Remove '10000' (5 chars)
                # Remove common suffixes like USDTM, USDCM
                for suffix in ['USDTM', 'USDCM', 'USDM']:
                    if clean.endswith(suffix):
                        return clean[:-len(suffix)]
                return base  # Fallback to original if pattern doesn't match
            # Check for 1000 prefix
            elif symbol.startswith('1000'):
                # Extract the actual base asset from symbol
                clean = symbol[4:]  # Remove '1000' (4 chars)
                # Remove common suffixes like USDTM, USDCM
                for suffix in ['USDTM', 'USDCM', 'USDM']:
                    if clean.endswith(suffix):
                        return clean[:-len(suffix)]
                return base  # Fallback to original if pattern doesn't match
            return base
        
        base_assets = df.apply(lambda row: normalize_kucoin_base_asset(row['symbol'], row['baseCurrency']), axis=1)
        
        normalized = pd.DataFrame({
            'exchange': 'KuCoin',
            'symbol': df['symbol'],
            'base_asset': base_assets,
            'quote_asset': df['quoteCurrency'],
            'funding_rate': pd.to_numeric(df['fundingFeeRate'], errors='coerce'),
            'funding_interval_hours': pd.to_numeric(df['fundingIntervalHours'], errors='coerce'),
            'index_price': pd.to_numeric(df['indexPrice'], errors='coerce'),
            'mark_price': pd.to_numeric(df['markPrice'], errors='coerce'),
            'open_interest': pd.to_numeric(df['openInterest'], errors='coerce'),
            'contract_type': df['type'] if 'type' in df.columns else 'PERPETUAL',
            'market_type': 'KuCoin Futures',
        })
        
        return normalized
    
    def fetch_historical_funding_rates(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol from KuCoin.
        
        Args:
            symbol: Trading symbol (e.g., XBTUSDTM)
            days: Number of days of history to fetch
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Calculate time range (KuCoin uses milliseconds)
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            # KuCoin historical funding rate endpoint
            url = f"{self.base_url}contract/funding-rates"
            params = {
                'symbol': symbol,
                'from': start_time,
                'to': end_time
            }
            
            # Make request
            response = self.safe_request(url, params=params)
            
            if not response:
                self.logger.warning(f"No historical data for {symbol}")
                return pd.DataFrame()
            
            # Parse funding rate data
            # KuCoin returns data in 'data' field as a list
            if isinstance(response, dict) and 'data' in response:
                funding_data = response['data'] if isinstance(response['data'], list) else []
            else:
                funding_data = []
            
            if not funding_data:
                return pd.DataFrame()
            
            # Create DataFrame
            df = pd.DataFrame(funding_data)
            
            # Convert timestamps from milliseconds to datetime (field is 'timepoint' not 'timePoint')
            df['funding_time'] = pd.to_datetime(df['timepoint'], unit='ms', utc=True)
            
            # Add symbol and exchange info
            df['symbol'] = symbol
            df['exchange'] = 'KuCoin'
            df['funding_interval_hours'] = 8  # KuCoin uses 8-hour intervals
            
            # Extract base asset from symbol (e.g., XBTUSDTM -> XBT)
            df['base_asset'] = self._extract_base_asset(symbol)
            
            # Rename columns to match our schema
            df = df.rename(columns={
                'fundingRate': 'funding_rate',
                'markPrice': 'mark_price'
            })
            
            # Select relevant columns
            columns = ['exchange', 'symbol', 'funding_rate', 'funding_time', 
                      'mark_price', 'funding_interval_hours', 'base_asset']
            
            # Filter columns that exist
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _extract_base_asset(self, symbol: str) -> str:
        """
        Extract base asset from KuCoin symbol.
        
        Args:
            symbol: KuCoin symbol (e.g., XBTUSDTM, ETHUSDTM, 1000BONKUSDTM, 10000CATUSDTM, 1000000MOGUSDTM, 1000XUSDTM, 1MBABYDOGEUSDTM)
            
        Returns:
            Base asset (e.g., BTC, ETH, BONK, CAT, MOG, X, BABYDOGE)
        """
        # Special case for 1MBABYDOGE (1M = 1 Million denomination)
        if symbol.startswith('1MBABYDOGE'):
            return 'BABYDOGE'
        # Special case for 1000XUSDTM - should return 'X' not '1000X'
        elif symbol in ['1000XUSDTM', '1000XUSDCM', '1000XUSDM']:
            return 'X'
        
        # Handle numeric prefixes in order (longest first)
        # Check for 1000000 prefix first
        if symbol.startswith('1000000'):
            # Remove the 1000000 prefix (7 chars)
            clean = symbol[7:]
            # Remove common suffixes
            for suffix in ['USDTM', 'USDCM', 'USDM']:
                if clean.endswith(suffix):
                    return clean[:-len(suffix)]
            return clean
        # Check for 10000 prefix
        elif symbol.startswith('10000'):
            # Remove the 10000 prefix (5 chars)
            clean = symbol[5:]
            # Remove common suffixes
            for suffix in ['USDTM', 'USDCM', 'USDM']:
                if clean.endswith(suffix):
                    return clean[:-len(suffix)]
            return clean
        # Check for 1000 prefix
        elif symbol.startswith('1000'):
            # Remove the 1000 prefix (4 chars)
            clean = symbol[4:]
            # Remove common suffixes
            for suffix in ['USDTM', 'USDCM', 'USDM']:
                if clean.endswith(suffix):
                    return clean[:-len(suffix)]
            return clean
        
        # KuCoin symbol format: BASEUSDTM or BASEUSDCM
        # Special case: XBT is Bitcoin on KuCoin
        if symbol.startswith('XBT'):
            return 'BTC'  # Normalize XBT to BTC for consistency
        
        # Remove common suffixes
        for suffix in ['USDTM', 'USDCM', 'USDM']:
            if symbol.endswith(suffix):
                base = symbol[:-len(suffix)]
                return base
        
        # Fallback: return first 3-4 characters
        if len(symbol) >= 6:
            return symbol[:3]
        return symbol
    
    def fetch_all_perpetuals_historical(self, days: int = 30, batch_size: int = 10, 
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all KuCoin perpetual contracts.
        
        Args:
            days: Number of days of history to fetch
            batch_size: Number of symbols to process in each batch
            progress_callback: Optional callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)
            
        Returns:
            DataFrame with all historical funding rates
        """
        try:
            # Calculate time range - use provided times or calculate from days
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)
            
            # Calculate actual days for the fetch_historical_funding_rates method
            actual_days = (end_time - start_time).days
            
            self.logger.info(f"Starting KuCoin historical data fetch")
            self.logger.info(f"  Date range: {start_time.isoformat()} to {end_time.isoformat()} ({actual_days} days)")
            
            # First get list of all active perpetual contracts
            contracts_data = self.safe_request(self.base_url + 'contracts/active')
            
            if not contracts_data or 'data' not in contracts_data:
                self.logger.error("Failed to fetch KuCoin contracts")
                return pd.DataFrame()
            
            # Filter for active perpetual contracts only
            contracts = contracts_data['data']
            perpetuals = [c for c in contracts if c.get('type') == 'FFWCSX' and c.get('status') == 'Open']
            
            self.logger.info(f"Found {len(perpetuals)} active KuCoin perpetual contracts")
            
            # Collect historical data for each contract
            all_historical_data = []
            symbols_processed = 0
            total_symbols = len(perpetuals)
            
            for i in range(0, len(perpetuals), batch_size):
                batch = perpetuals[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(perpetuals) + batch_size - 1) // batch_size
                
                self.logger.info(f"Processing batch {batch_num}/{total_batches}")
                
                for contract in batch:
                    symbol = contract['symbol']
                    
                    # Fetch historical data for this symbol with actual days
                    hist_df = self.fetch_historical_funding_rates(symbol, actual_days)
                    
                    if not hist_df.empty:
                        all_historical_data.append(hist_df)
                        self.logger.info(f"  {symbol}: {len(hist_df)} historical records")
                    else:
                        self.logger.warning(f"  {symbol}: No historical data")
                    
                    symbols_processed += 1
                    
                    # Update progress if callback provided
                    if progress_callback:
                        progress = int((symbols_processed / total_symbols) * 100)
                        message = f"Processing KuCoin: {symbols_processed}/{total_symbols} symbols"
                        progress_callback(symbols_processed, total_symbols, progress, message)
                    
                    # Small delay to respect rate limits
                    time.sleep(0.1)
                
                # Batch delay
                if i + batch_size < len(perpetuals):
                    self.logger.info(f"Batch {batch_num} complete. Waiting before next batch...")
                    time.sleep(2)
            
            # Combine all historical data
            if all_historical_data:
                combined_df = pd.concat(all_historical_data, ignore_index=True)
                self.logger.info(f"Successfully fetched {len(combined_df)} total historical records")
                return combined_df
            else:
                self.logger.warning("No historical data collected")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error in fetch_all_perpetuals_historical: {e}")
            return pd.DataFrame() 