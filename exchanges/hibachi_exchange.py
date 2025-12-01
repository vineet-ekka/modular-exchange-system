"""
Hibachi Exchange Module
======================
Handles data fetching and normalization for Hibachi exchange.
Hibachi is a high-performance, privacy-focused decentralized exchange (DEX) that combines
the speed and user experience of centralized platforms with cryptographic integrity.
"""

import pandas as pd
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class HibachiExchange(BaseExchange):
    """
    Hibachi exchange data fetcher and normalizer.
    Handles perpetual contracts and funding rate data.
    """
    
    def __init__(self, enabled: bool = True):
        super().__init__("Hibachi", enabled)
        self.logger = setup_logger("HibachiExchange")
        self.base_url = "https://data-api.hibachi.xyz"
        
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from Hibachi API.
        
        Returns:
            DataFrame with raw Hibachi data
        """
        try:
            # Try to fetch market data from different possible endpoints
            markets_data = self._fetch_markets()
            if markets_data.empty:
                # If no markets data, create a basic structure for known markets
                # Based on search results, Hibachi supports BTC, ETH, and SOL with up to 5x leverage
                markets_data = self._create_basic_markets()
                if markets_data.empty:
                    return pd.DataFrame()
            
            # Fetch real funding rates from API
            funding_data = self._fetch_funding_rates(markets_data)
            if funding_data.empty:
                # Fallback to basic funding rate data if API fails
                self.logger.warning("No funding rate data from API, using fallback")
                funding_data = self._create_basic_funding_data(markets_data)
            
            # Merge market and funding data
            merged_df = markets_data.merge(funding_data, on='symbol', how='left')
            
            return merged_df
            
        except Exception as e:
            self.logger.error(f"Error fetching Hibachi data: {str(e)}")
            return pd.DataFrame()
    
    def _create_basic_markets(self) -> pd.DataFrame:
        """
        Create basic market data for known Hibachi markets.
        Based on search results, Hibachi supports BTC, ETH, and SOL with up to 5x leverage.
        
        Returns:
            DataFrame with basic market data
        """
        try:
            # Known markets from search results
            markets = [
                {'symbol': 'BTC-USDT', 'base_asset': 'BTC', 'quote_asset': 'USDT', 'leverage': 5},
                {'symbol': 'ETH-USDT', 'base_asset': 'ETH', 'quote_asset': 'USDT', 'leverage': 5},
                {'symbol': 'SOL-USDT', 'base_asset': 'SOL', 'quote_asset': 'USDT', 'leverage': 5},
            ]
            
            df = pd.DataFrame(markets)
            df['funding_interval_hours'] = 8  # Default
            df['contract_type'] = 'PERPETUAL'
            df['market_type'] = 'Hibachi'
            
            self.logger.info(f"Created basic market data for {len(df)} known Hibachi markets")
            return df
            
        except Exception as e:
            self.logger.error(f"Error creating basic markets: {str(e)}")
            return pd.DataFrame()
    
    def _create_basic_funding_data(self, markets_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create basic funding rate data for markets.
        Since Hibachi is a DEX, it might not have traditional funding rates.
        
        Args:
            markets_df: DataFrame with market symbols
            
        Returns:
            DataFrame with basic funding rate data
        """
        try:
            funding_data = []
            
            for symbol in markets_df['symbol'].tolist():
                # For DEXs, funding rates are often 0 or very low
                # This is a placeholder until we can get real data
                funding_data.append({
                    'symbol': symbol,
                    'funding_rate': 0.0,  # DEXs typically have 0 or very low funding rates
                    'index_price': None,
                    'mark_price': None,
                    'open_interest': 0
                })
            
            return pd.DataFrame(funding_data)
            
        except Exception as e:
            self.logger.error(f"Error creating basic funding data: {str(e)}")
            return pd.DataFrame()
    
    def _fetch_markets(self) -> pd.DataFrame:
        """
        Fetch market information from Hibachi API using exchange-info endpoint.
        
        Returns:
            DataFrame with market data
        """
        try:
            # Fetch exchange info endpoint
            url = f"{self.base_url}/market/exchange-info"
            data = self.safe_request(url)
            
            if not data:
                self.logger.warning("No exchange info data received from Hibachi API")
                return pd.DataFrame()
            
            # The response structure contains futureContracts
            if 'futureContracts' in data:
                markets = data['futureContracts']
            elif 'symbols' in data:
                markets = data['symbols']
            elif 'markets' in data:
                markets = data['markets']
            elif isinstance(data, list):
                markets = data
            else:
                self.logger.warning(f"Unexpected data structure from Hibachi API: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return pd.DataFrame()
            
            if not markets:
                self.logger.warning("Empty markets list from Hibachi API")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(markets)
            
            # Filter for perpetual contracts only
            # Hibachi uses symbols ending with -P for perpetuals
            perp_df = df.copy()
            
            # Filter based on symbol pattern (ending with -P) and status LIVE
            if 'symbol' in df.columns:
                perp_df = df[df['symbol'].str.endswith('-P', na=False)].copy()
            
            # Also filter by status if available
            if 'status' in perp_df.columns:
                perp_df = perp_df[perp_df['status'] == 'LIVE'].copy()
            
            if perp_df.empty:
                self.logger.warning("No perpetual contracts found in Hibachi markets")
                return pd.DataFrame()
            
            # Extract base and quote assets from symbol
            perp_df['base_asset'] = perp_df['symbol'].apply(self._extract_base_asset)
            perp_df['quote_asset'] = perp_df['symbol'].apply(self._extract_quote_asset)
            
            # Set default funding interval (Hibachi typically uses 8-hour intervals)
            perp_df['funding_interval_hours'] = 8
            
            # Set contract type
            perp_df['contract_type'] = 'PERPETUAL'
            perp_df['market_type'] = 'Hibachi'
            
            self.logger.info(f"Found {len(perp_df)} perpetual contracts from Hibachi")
            return perp_df
            
        except Exception as e:
            self.logger.error(f"Error fetching Hibachi markets: {str(e)}")
            return pd.DataFrame()
    
    def _fetch_funding_rates(self, markets_df: pd.DataFrame) -> pd.DataFrame:
        """
        Fetch funding rates for all markets using the funding-rates endpoint.
        
        Args:
            markets_df: DataFrame with market symbols
            
        Returns:
            DataFrame with funding rate data
        """
        try:
            funding_data = []
            
            # Fetch funding rates for each symbol
            for symbol in markets_df['symbol'].tolist():
                try:
                    # Rate limit between requests
                    time.sleep(0.1)
                    
                    # Fetch funding rate for this symbol using the correct endpoint
                    url = f"{self.base_url}/market/data/funding-rates"
                    params = {'symbol': symbol}
                    
                    data = self.safe_request(url, params=params, silent_errors=True)
                    
                    if data:
                        self.logger.debug(f"API response for {symbol}: {str(data)[:200]}...")
                    
                    if data and 'data' in data and data['data']:
                        # Get the most recent funding rate
                        latest_rate = data['data'][0]
                        funding_rate = float(latest_rate.get('fundingRate', 0.0))
                        index_price = float(latest_rate.get('indexPrice', 0.0)) if latest_rate.get('indexPrice') else None
                        
                        self.logger.debug(f"Fetched funding rate for {symbol}: {funding_rate}, index_price: {index_price}")
                        
                        funding_data.append({
                            'symbol': symbol,
                            'funding_rate': funding_rate,
                            'index_price': index_price,
                            'mark_price': index_price,  # Use index price as mark price for now
                            'open_interest': 0  # Will be fetched separately
                        })
                    else:
                        # If no funding rate data, use default values
                        funding_data.append({
                            'symbol': symbol,
                            'funding_rate': 0.0,
                            'index_price': None,
                            'mark_price': None,
                            'open_interest': 0
                        })
                        
                except Exception as e:
                    self.logger.debug(f"Error fetching funding rate for {symbol}: {str(e)}")
                    # Add default values for failed symbols
                    funding_data.append({
                        'symbol': symbol,
                        'funding_rate': 0.0,
                        'index_price': None,
                        'mark_price': None,
                        'open_interest': 0
                    })
            
            if not funding_data:
                self.logger.warning("No funding rate data received from Hibachi API")
                return pd.DataFrame()
            
            # Fetch open interest data separately
            funding_df = pd.DataFrame(funding_data)
            funding_df = self._add_open_interest_data(funding_df)
            
            return funding_df
            
        except Exception as e:
            self.logger.error(f"Error fetching Hibachi funding rates: {str(e)}")
            return pd.DataFrame()
    
    def _add_open_interest_data(self, funding_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add open interest data for each symbol.
        
        Args:
            funding_df: DataFrame with funding rate data
            
        Returns:
            DataFrame with open interest data added
        """
        try:
            open_interest_data = []
            
            for symbol in funding_df['symbol'].tolist():
                try:
                    # Rate limit between requests
                    time.sleep(0.05)
                    
                    # Fetch open interest for this symbol
                    url = f"{self.base_url}/market/data/open-interest"
                    params = {'symbol': symbol}
                    
                    data = self.safe_request(url, params=params, silent_errors=True)
                    
                    if data and 'totalQuantity' in data:
                        open_interest_data.append({
                            'symbol': symbol,
                            'open_interest': data['totalQuantity']
                        })
                    else:
                        open_interest_data.append({
                            'symbol': symbol,
                            'open_interest': 0
                        })
                        
                except Exception as e:
                    self.logger.debug(f"Error fetching open interest for {symbol}: {str(e)}")
                    open_interest_data.append({
                        'symbol': symbol,
                        'open_interest': 0
                    })
            
            # Merge open interest data
            oi_df = pd.DataFrame(open_interest_data)
            funding_df = funding_df.merge(oi_df, on='symbol', how='left')
            funding_df['open_interest'] = funding_df['open_interest_y'].fillna(0)
            funding_df = funding_df.drop(columns=['open_interest_y'], errors='ignore')
            
            return funding_df
            
        except Exception as e:
            self.logger.error(f"Error adding open interest data: {str(e)}")
            return funding_df
    
    def _extract_base_asset(self, symbol: str) -> str:
        """
        Extract base asset from symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT-P', 'ETH/USDT-P')
            
        Returns:
            Base asset (e.g., 'BTC', 'ETH')
        """
        try:
            # Hibachi uses format like BTC/USDT-P or ETH/USDT-P
            if '/' in symbol:
                # Remove the -P suffix first, then split by /
                clean_symbol = symbol.replace('-P', '').replace('-PERP', '')
                return clean_symbol.split('/')[0]
            elif '-' in symbol:
                return symbol.split('-')[0]
            elif '_' in symbol:
                return symbol.split('_')[0]
            else:
                # Fallback: try to remove common quote currencies and suffixes
                clean_symbol = symbol.replace('-P', '').replace('-PERP', '')
                for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
                    if clean_symbol.endswith(quote):
                        return clean_symbol[:-len(quote)]
                return clean_symbol
        except Exception:
            return symbol
    
    def _extract_quote_asset(self, symbol: str) -> str:
        """
        Extract quote asset from symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT-P', 'ETH/USDT-P')
            
        Returns:
            Quote asset (e.g., 'USDT', 'USD')
        """
        try:
            # Hibachi uses format like BTC/USDT-P or ETH/USDT-P
            if '/' in symbol:
                # Remove the -P suffix first, then split by /
                clean_symbol = symbol.replace('-P', '').replace('-PERP', '')
                return clean_symbol.split('/')[1]
            elif '-' in symbol:
                return symbol.split('-')[1]
            elif '_' in symbol:
                return symbol.split('_')[1]
            else:
                # Fallback: try to identify common quote currencies
                for quote in ['USDT', 'USDC', 'USD', 'BTC', 'ETH']:
                    if symbol.endswith(quote):
                        return quote
                return 'USDT'  # Default fallback
        except Exception:
            return 'USDT'
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform Hibachi data to unified format.
        
        Args:
            df: Raw Hibachi data
            
        Returns:
            DataFrame in unified format
        """
        if df.empty:
            return pd.DataFrame(columns=self.get_unified_columns())
        
        try:
            # Create normalized DataFrame
            normalized = pd.DataFrame({
                'exchange': 'Hibachi',
                'symbol': df['symbol'],
                'base_asset': df['base_asset'],
                'quote_asset': df['quote_asset'],
                'funding_rate': pd.to_numeric(df['funding_rate'], errors='coerce').fillna(0.0),
                'funding_interval_hours': pd.to_numeric(df['funding_interval_hours'], errors='coerce').fillna(8),
                'index_price': pd.to_numeric(df['index_price'], errors='coerce'),
                'mark_price': pd.to_numeric(df['mark_price'], errors='coerce'),
                'open_interest': pd.to_numeric(df['open_interest'], errors='coerce').fillna(0),
                'contract_type': df['contract_type'],
                'market_type': df['market_type']
            })
            
            # Calculate APR
            normalized['apr'] = self._calculate_apr(
                normalized['funding_rate'], 
                normalized['funding_interval_hours']
            )
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing Hibachi data: {str(e)}")
            return pd.DataFrame(columns=self.get_unified_columns())
    
    def _calculate_apr(self, funding_rate: pd.Series, funding_interval_hours: pd.Series) -> pd.Series:
        """
        Calculate APR from funding rate and interval.
        
        Args:
            funding_rate: Series of funding rates
            funding_interval_hours: Series of funding intervals in hours
            
        Returns:
            Series of APR values
        """
        try:
            # Calculate periods per year
            periods_per_year = (365 * 24) / funding_interval_hours
            
            # Calculate APR
            apr = funding_rate * periods_per_year * 100
            
            return apr
        except Exception as e:
            self.logger.error(f"Error calculating APR: {str(e)}")
            return pd.Series([0.0] * len(funding_rate))
    
    def fetch_historical_funding_rates(self, symbol: str, 
                                      start_time: Optional[datetime] = None, 
                                      end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            start_time: Start time for historical data (default: 30 days ago)
            end_time: End time for historical data (default: now)
            
        Returns:
            DataFrame with historical funding rates
        """
        try:
            # Set default time range if not provided
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=30)
            
            # Convert to Unix timestamps
            start_ts = int(start_time.timestamp())
            end_ts = int(end_time.timestamp())
            
            # Fetch historical funding rates using the correct endpoint
            url = f"{self.base_url}/market/data/funding-rates"
            params = {
                'symbol': symbol,
                'startTime': start_ts,
                'endTime': end_ts,
                'limit': 1000
            }
            
            data = self.safe_request(url, params=params, silent_errors=True)
            
            if not data or 'data' not in data:
                self.logger.warning(f"No historical funding rates for {symbol}")
                return pd.DataFrame()
            
            # Process records manually (matches working _fetch_funding_rates pattern)
            historical_records = []
            for record in data['data']:
                historical_records.append({
                    'funding_time': pd.to_datetime(record.get('fundingTimestamp'), unit='s'),
                    'funding_rate': float(record.get('fundingRate', 0.0)),
                    'index_price': float(record.get('indexPrice', 0.0)) if record.get('indexPrice') else None,
                    'mark_price': float(record.get('indexPrice', 0.0)) if record.get('indexPrice') else None,
                    'symbol': symbol,
                    'exchange': 'Hibachi',
                    'base_asset': self._extract_base_asset(symbol),
                    'quote_asset': self._extract_quote_asset(symbol),
                    'funding_interval_hours': 8
                })

            if not historical_records:
                return pd.DataFrame()

            df = pd.DataFrame(historical_records)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_all_perpetuals_historical(self, days: int = 30, 
                                       batch_size: int = 5,
                                       progress_callback=None,
                                       start_time: Optional[datetime] = None,
                                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical funding rates for all perpetual contracts.
        
        Args:
            days: Number of days of historical data to fetch
            batch_size: Number of symbols to fetch concurrently
            progress_callback: Callback for progress updates
            start_time: Optional start time (overrides days calculation)
            end_time: Optional end time (defaults to now)
            
        Returns:
            Combined DataFrame with all historical funding rates
        """
        try:
            # Calculate time range
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(days=days)
            
            # Get list of all perpetual contracts
            markets_df = self._fetch_markets()
            if markets_df.empty:
                self.logger.warning("No perpetual contracts found for historical data fetch")
                return pd.DataFrame()
            
            symbols = markets_df['symbol'].tolist()
            total_symbols = len(symbols)
            
            self.logger.info(f"Fetching historical data for {total_symbols} Hibachi perpetuals")
            
            all_historical_data = []
            symbols_processed = 0
            
            # Process symbols in batches
            for i in range(0, total_symbols, batch_size):
                batch = symbols[i:i+batch_size]
                
                for symbol in batch:
                    try:
                        df = self.fetch_historical_funding_rates(
                            symbol, start_time, end_time
                        )
                        if not df.empty:
                            all_historical_data.append(df)
                            
                    except Exception as e:
                        self.logger.error(f"Error fetching historical data for {symbol}: {e}")
                    
                    # Update progress
                    symbols_processed += 1
                    if progress_callback:
                        progress = (symbols_processed / total_symbols) * 100
                        progress_callback(symbols_processed, total_symbols, progress, f"Processing {symbol}")
                    
                    # Rate limiting
                    time.sleep(0.2)
            
            # Combine all data
            if all_historical_data:
                combined_df = pd.concat(all_historical_data, ignore_index=True)
                self.logger.info(f"Fetched {len(combined_df)} total historical records from Hibachi")
                return combined_df
            else:
                self.logger.warning("No historical data fetched from Hibachi")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error in fetch_all_perpetuals_historical: {str(e)}")
            return pd.DataFrame()
