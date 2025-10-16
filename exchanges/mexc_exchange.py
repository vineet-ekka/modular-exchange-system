"""
MEXC Exchange Module
===================
Handles data fetching and normalization for MEXC exchange.
Supports perpetual contracts with funding rate data.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
from .base_exchange import BaseExchange
from utils.logger import setup_logger


class MexcExchange(BaseExchange):
    """
    MEXC exchange data fetcher and normalizer.
    Features:
    - Perpetual contracts with funding rates
    - Historical funding rate data
    - Open interest data (holdVol field)
    - 8-hour funding intervals (standard)
    """

    def __init__(self, enabled: bool = True):
        super().__init__("MEXC", enabled)
        self.base_url = 'https://contract.mexc.com/api/v1'
        self.logger = setup_logger("MexcExchange")

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from MEXC API with optimized bulk fetching.
        
        Returns:
            DataFrame with raw MEXC data
        """
        try:
            # Get all contract details
            contracts_data = self._fetch_contract_details()
            if not contracts_data:
                return pd.DataFrame()

            self.logger.info(f"Found {len(contracts_data)} contracts")

            # Try to fetch all funding rates and tickers in bulk first
            all_funding_rates = self._fetch_all_funding_rates()
            all_tickers = self._fetch_all_tickers()
            
            # If bulk fetch failed, fall back to optimized batch processing
            if not all_funding_rates or not all_tickers:
                self.logger.info("Bulk fetch failed, falling back to batch processing")
                return self._fetch_data_batch_optimized(contracts_data)

            # Process data using bulk results
            all_data = []
            for contract in contracts_data:
                symbol = contract['symbol']
                
                # Get funding rate from bulk data
                funding_data = all_funding_rates.get(symbol, {})
                ticker_data = all_tickers.get(symbol, {})
                
                if funding_data:  # Only include contracts with funding data
                    combined_data = {
                        'symbol': symbol,
                        'base_asset': contract.get('baseCoin', ''),
                        'quote_asset': contract.get('quoteCoin', ''),
                        'funding_rate': funding_data.get('fundingRate', 0),
                        'funding_time': funding_data.get('timestamp', 0),
                        'next_funding_time': funding_data.get('nextSettleTime', 0),
                        'funding_interval': funding_data.get('collectCycle', 8),
                        'index_price': ticker_data.get('indexPrice', 0),
                        'mark_price': ticker_data.get('markPrice', 0),
                        'open_interest': ticker_data.get('holdVol', 0),
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
                    all_data.append(combined_data)

            if not all_data:
                self.logger.warning("No funding rate data retrieved from MEXC")
                return pd.DataFrame()

            self.logger.info(f"Successfully processed {len(all_data)} contracts using bulk fetch")
            return pd.DataFrame(all_data)

        except Exception as e:
            self.logger.error(f"Error fetching MEXC data: {e}")
            return pd.DataFrame()

    def _fetch_contract_details(self) -> List[Dict]:
        """
        Fetch all contract details from MEXC.
        
        Returns:
            List of contract data
        """
        try:
            url = f"{self.base_url}/contract/detail"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                return data.get('data', [])
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching contract details: {e}")
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
            url = f"{self.base_url}/contract/funding_rate/{symbol}"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                return data.get('data', {})
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
            url = f"{self.base_url}/contract/ticker"
            params = {'symbol': symbol}
            data = self.safe_request(url, params=params)
            
            if data and data.get('success'):
                return data.get('data', {})
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    def _fetch_all_funding_rates(self) -> Dict[str, Dict]:
        """
        Fetch all funding rates in bulk if possible.
        
        Returns:
            Dictionary of funding rate data by symbol
        """
        try:
            # Try to fetch all funding rates at once
            url = f"{self.base_url}/contract/funding_rate"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                funding_list = data.get('data', [])
                funding_dict = {}
                for item in funding_list:
                    symbol = item.get('symbol')
                    if symbol:
                        funding_dict[symbol] = item
                self.logger.info(f"Fetched {len(funding_dict)} funding rates in bulk")
                return funding_dict
            return {}
            
        except Exception as e:
            self.logger.warning(f"Bulk funding rate fetch failed: {e}")
            return {}

    def _fetch_all_tickers(self) -> Dict[str, Dict]:
        """
        Fetch all tickers in bulk if possible.
        
        Returns:
            Dictionary of ticker data by symbol
        """
        try:
            # Try to fetch all tickers at once
            url = f"{self.base_url}/contract/ticker"
            data = self.safe_request(url)
            
            if data and data.get('success'):
                ticker_list = data.get('data', [])
                ticker_dict = {}
                for item in ticker_list:
                    symbol = item.get('symbol')
                    if symbol:
                        ticker_dict[symbol] = item
                self.logger.info(f"Fetched {len(ticker_dict)} tickers in bulk")
                return ticker_dict
            return {}
            
        except Exception as e:
            self.logger.warning(f"Bulk ticker fetch failed: {e}")
            return {}

    def _fetch_data_batch_optimized(self, contracts_data: List[Dict]) -> pd.DataFrame:
        """
        Optimized batch processing with larger batches and parallel processing.
        
        Args:
            contracts_data: List of contract data
            
        Returns:
            DataFrame with processed data
        """
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_data = []
        batch_size = 50  # Increased batch size
        total_contracts = len(contracts_data)
        
        def process_contract(contract):
            """Process a single contract."""
            symbol = contract['symbol']
            try:
                # Get current funding rate
                funding_data = self._fetch_funding_rate(symbol)
                if funding_data:
                    # Get ticker data for open interest and prices
                    ticker_data = self._fetch_ticker(symbol)
                    
                    # Combine data
                    return {
                        'symbol': symbol,
                        'base_asset': contract.get('baseCoin', ''),
                        'quote_asset': contract.get('quoteCoin', ''),
                        'funding_rate': funding_data.get('fundingRate', 0),
                        'funding_time': funding_data.get('timestamp', 0),
                        'next_funding_time': funding_data.get('nextSettleTime', 0),
                        'funding_interval': funding_data.get('collectCycle', 8),
                        'index_price': ticker_data.get('indexPrice', 0) if ticker_data else 0,
                        'mark_price': ticker_data.get('markPrice', 0) if ticker_data else 0,
                        'open_interest': ticker_data.get('holdVol', 0) if ticker_data else 0,
                        'contract_type': 'PERPETUAL',
                        'market_type': 'PERP'
                    }
            except Exception as e:
                self.logger.warning(f"Failed to fetch data for {symbol}: {e}")
                return None
            return None
        
        # Process in batches with parallel execution
        for i in range(0, total_contracts, batch_size):
            batch = contracts_data[i:i + batch_size]
            self.logger.info(f"Processing MEXC batch {i//batch_size + 1}/{(total_contracts + batch_size - 1)//batch_size} ({len(batch)} contracts)")
            
            # Use ThreadPoolExecutor for parallel processing within each batch
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_contract = {executor.submit(process_contract, contract): contract for contract in batch}
                
                for future in as_completed(future_to_contract, timeout=30):
                    result = future.result()
                    if result:
                        all_data.append(result)
            
            # Reduced delay between batches
            if i + batch_size < total_contracts:
                time.sleep(0.1)  # Reduced from 0.5s to 0.1s

        if not all_data:
            self.logger.warning("No funding rate data retrieved from MEXC")
            return pd.DataFrame()

        self.logger.info(f"Successfully processed {len(all_data)} contracts using optimized batch processing")
        return pd.DataFrame(all_data)

    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform MEXC data to unified format.
        
        Args:
            df: Raw MEXC data
            
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
            
            # Use actual funding interval from API, default to 8 if not available
            funding_interval = df.get('funding_interval', 8)
            normalized_df['funding_interval_hours'] = funding_interval
            
            normalized_df['contract_type'] = df['contract_type']
            normalized_df['market_type'] = df['market_type']
            
            # Calculate APR based on actual funding interval
            periods_per_year = (365 * 24) / funding_interval
            normalized_df['apr'] = df['funding_rate'] * periods_per_year * 100
            
            # Prices
            normalized_df['index_price'] = df['index_price']
            normalized_df['mark_price'] = df['mark_price']
            
            # Open interest
            normalized_df['open_interest'] = df['open_interest']
            
            # Add timestamps
            if 'funding_time' in df.columns:
                normalized_df['funding_time'] = pd.to_datetime(df['funding_time'], unit='ms', errors='coerce')
            if 'next_funding_time' in df.columns:
                normalized_df['next_funding_time'] = pd.to_datetime(df['next_funding_time'], unit='ms', errors='coerce')
            
            return normalized_df

        except Exception as e:
            self.logger.error(f"Error normalizing MEXC data: {e}")
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
            url = f"{self.base_url}/contract/funding_rate/history"
            params = {
                'symbol': symbol,
                'limit': min(days * 3, 1000)  # 3 funding periods per day, max 1000
            }
            
            data = self.safe_request(url, params=params)
            
            if data and data.get('success'):
                rows = data.get('data', [])
                if rows:
                    df = pd.DataFrame(rows)
                    df['funding_time'] = pd.to_datetime(df['fundingTime'], unit='ms', errors='coerce')
                    df['funding_rate'] = df['fundingRate'].astype(float)
                    return df[['symbol', 'funding_rate', 'funding_time']]
            
            return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical funding rates for {symbol}: {e}")
            return pd.DataFrame()
