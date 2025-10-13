"""
Base Exchange Class
==================
This is the foundation class that all exchange modules must inherit from.
It defines the standard interface and common functionality.
"""

import pandas as pd
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import warnings
from utils.health_tracker import record_exchange_result
from utils.rate_limiter import rate_limiter
warnings.filterwarnings('ignore')


class BaseExchange(ABC):
    """
    Abstract base class for all exchange data fetchers.
    
    All exchange modules must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, name: str, enabled: bool = True):
        """
        Initialize the base exchange.
        
        Args:
            name: The name of the exchange
            enabled: Whether this exchange is enabled
        """
        self.name = name
        self.enabled = enabled
        self.data = pd.DataFrame()
        
    @abstractmethod
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from the exchange API.
        
        Returns:
            DataFrame with raw exchange data
        """
        pass
    
    @abstractmethod
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform exchange-specific data to unified format.
        
        Args:
            df: Raw exchange data
            
        Returns:
            DataFrame in unified format
        """
        pass
    
    def get_unified_columns(self) -> List[str]:
        """
        Get the list of unified column names.
        
        Returns:
            List of column names in unified format
        """
        return [
            'exchange',
            'symbol', 
            'base_asset',
            'quote_asset',
            'funding_rate',
            'funding_interval_hours',
            'apr',
            'index_price',
            'mark_price',
            'open_interest',
            'contract_type',
            'market_type'
        ]
    
    def process_data(self) -> pd.DataFrame:
        """
        Main method to fetch and normalize data.
        
        Returns:
            DataFrame in unified format
        """
        if not self.enabled:
            print(f"! {self.name} is disabled in settings")
            return pd.DataFrame(columns=self.get_unified_columns())
        
        try:
            print(f"Fetching {self.name} data...")
            raw_data = self.fetch_data()
            
            if raw_data.empty:
                print(f"! No data received from {self.name}")
                record_exchange_result(self.name, False)
                return pd.DataFrame(columns=self.get_unified_columns())
            
            normalized_data = self.normalize_data(raw_data)
            print(f"OK {self.name}: {len(normalized_data)} contracts")
            record_exchange_result(self.name, True)
            
            return normalized_data
            
        except Exception as e:
            print(f"X Error processing {self.name} data: {str(e)}")
            record_exchange_result(self.name, False)
            return pd.DataFrame(columns=self.get_unified_columns())
    
    def safe_request(self, url: str, params: Dict = None, delay: float = 0.1, silent_errors: bool = False) -> Optional[Dict]:
        """
        Make a safe HTTP request with error handling and rate limiting.

        Args:
            url: The URL to request
            params: Query parameters
            delay: Delay before request (for rate limiting)
            silent_errors: If True, don't print error messages for 400/404 errors

        Returns:
            JSON response data or None if failed
        """
        try:
            # Use the new rate limiter instead of simple sleep
            rate_limiter.acquire(self.name)

            # Add cache-busting headers to ensure fresh data
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'User-Agent': f'ModularExchangeSystem/{self.name}'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            # Handle different response codes
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit hit - let the rate limiter handle backoff
                retry_after = response.headers.get('Retry-After')
                retry_after_seconds = float(retry_after) if retry_after else None
                rate_limiter.handle_429(self.name, retry_after_seconds)
                return None
            elif response.status_code in [400, 404] and silent_errors:
                # Common for API endpoints that don't support certain symbols
                return None
            elif response.status_code in [400, 404]:
                print(f"! Request failed for {url}: {response.status_code} {response.reason}")
                return None
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.RequestException as e:
            if not silent_errors:
                print(f"! Request failed for {url}: {str(e)}")
            return None
        except Exception as e:
            if not silent_errors:
                print(f"! Unexpected error for {url}: {str(e)}")
            return None

    def safe_post_request(self, url: str, json_data: Dict = None, headers: Dict = None,
                         silent_errors: bool = False, max_retries: int = 3) -> Optional[Dict]:
        """
        Make a safe HTTP POST request with error handling, rate limiting, and retry logic.

        Args:
            url: The URL to request
            json_data: JSON payload for POST request
            headers: Optional headers (Content-Type will be set automatically for JSON)
            silent_errors: If True, don't print error messages for 400/404 errors
            max_retries: Maximum number of retries for 429 errors

        Returns:
            JSON response data or None if failed
        """
        if headers is None:
            headers = {}
        if json_data is not None:
            headers['Content-Type'] = 'application/json'

        # Add cache-busting headers to ensure fresh data
        headers.update({
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'User-Agent': f'ModularExchangeSystem/{self.name}'
        })

        retry_count = 0
        backoff_delay = 2  # Start with 2 second backoff

        while retry_count <= max_retries:
            try:
                # Use the rate limiter
                rate_limiter.acquire(self.name)

                response = requests.post(url, json=json_data, headers=headers, timeout=10)

                # Handle different response codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit hit - handle with retry logic
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        wait_time = backoff_delay * (2 ** retry_count)  # Exponential backoff

                    if retry_count < max_retries:
                        if not silent_errors:
                            print(f"! Rate limited on {url}, retrying in {wait_time}s (attempt {retry_count + 1}/{max_retries})")
                        time.sleep(wait_time)
                        rate_limiter.handle_429(self.name, wait_time)
                        retry_count += 1
                        continue
                    else:
                        if not silent_errors:
                            print(f"! Max retries exceeded for {url}: 429 Too Many Requests")
                        return None
                elif response.status_code in [400, 404] and silent_errors:
                    # Common for API endpoints that don't support certain symbols
                    return None
                elif response.status_code in [400, 404]:
                    if not silent_errors:
                        print(f"! POST request failed for {url}: {response.status_code} {response.reason}")
                    return None
                else:
                    response.raise_for_status()
                    return response.json()

            except requests.exceptions.RequestException as e:
                if not silent_errors:
                    print(f"! POST request failed for {url}: {str(e)}")
                return None
            except Exception as e:
                if not silent_errors:
                    print(f"! Unexpected error for {url}: {str(e)}")
                return None

        return None
    
    def convert_timestamp(self, timestamp, unit='ms'):
        """
        Convert timestamp to datetime with fallback options.
        
        Args:
            timestamp: The timestamp to convert
            unit: Expected unit ('ms', 's', or None for auto-detect)
            
        Returns:
            pandas Timestamp or None
        """
        try:
            # Handle Series/array input
            if isinstance(timestamp, pd.Series):
                return pd.to_datetime(timestamp, unit=unit, errors='coerce')
            
            # Handle scalar input
            if pd.isna(timestamp):
                return None
                
            if unit == 'auto':
                # Try milliseconds first
                dt = pd.to_datetime(timestamp, unit='ms', errors='coerce')
                if hasattr(dt, 'year') and dt.year == 1970:
                    # Try seconds
                    dt = pd.to_datetime(timestamp, unit='s', errors='coerce')
                return dt
            else:
                return pd.to_datetime(timestamp, unit=unit, errors='coerce')
                
        except Exception:
            return None 