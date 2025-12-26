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
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import threading
import asyncio
import aiohttp
from asyncio_throttle import Throttler
warnings.filterwarnings('ignore')


class BaseExchange(ABC):
    """
    Abstract base class for all exchange data fetchers.

    All exchange modules must inherit from this class and implement
    the required methods.
    """

    # Thread-local storage for session objects (one session per thread)
    _thread_local = threading.local()

    # Circuit breaker pattern: track failures per exchange
    _failure_counts = {}
    _circuit_open_until = {}
    _failure_threshold = 5
    _circuit_timeout = 300

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

        # Initialize circuit breaker for this exchange
        if name not in BaseExchange._failure_counts:
            BaseExchange._failure_counts[name] = 0
            BaseExchange._circuit_open_until[name] = 0

        # Initialize session with connection pooling
        self._init_session()

    def _init_session(self):
        """
        Initialize a requests session with connection pooling.
        Uses thread-local storage to ensure thread safety.
        """
        # Check if this thread already has a session
        if not hasattr(self._thread_local, 'session'):
            # Create a new session with connection pooling
            session = requests.Session()

            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET", "POST"]
            )

            # Configure connection pool
            adapter = HTTPAdapter(
                pool_connections=10,    # Number of connection pools to cache
                pool_maxsize=20,        # Maximum number of connections to save in the pool
                max_retries=retry_strategy
            )

            # Mount adapter for both HTTP and HTTPS
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # Store session in thread-local storage
            self._thread_local.session = session

            print(f"[{self.name}] Initialized connection pool (10 pools, 20 max connections)")

    def _get_session(self) -> requests.Session:
        """
        Get the session for the current thread.
        Creates a new session if one doesn't exist.
        """
        if not hasattr(self._thread_local, 'session'):
            self._init_session()
        return self._thread_local.session

    def __del__(self):
        """
        Cleanup method to close the session when the exchange object is destroyed.
        """
        try:
            if hasattr(self._thread_local, 'session'):
                self._thread_local.session.close()
        except:
            pass

    def _is_circuit_open(self) -> bool:
        """
        Check if the circuit breaker is open (exchange temporarily disabled).

        Returns:
            True if circuit is open, False otherwise
        """
        current_time = time.time()
        circuit_open_until = BaseExchange._circuit_open_until.get(self.name, 0)

        if circuit_open_until > current_time:
            return True

        if circuit_open_until > 0 and circuit_open_until <= current_time:
            print(f"[{self.name}] Circuit breaker closing - attempting recovery")
            BaseExchange._failure_counts[self.name] = 0
            BaseExchange._circuit_open_until[self.name] = 0

        return False

    def _record_success(self):
        """
        Record a successful operation. Resets failure count.
        """
        if self.name in BaseExchange._failure_counts:
            if BaseExchange._failure_counts[self.name] > 0:
                print(f"[{self.name}] Operation succeeded - resetting failure count")
            BaseExchange._failure_counts[self.name] = 0

    def _record_failure(self, error: Exception):
        """
        Record a failed operation. Opens circuit breaker if threshold exceeded.

        Args:
            error: The exception that caused the failure
        """
        BaseExchange._failure_counts[self.name] = BaseExchange._failure_counts.get(self.name, 0) + 1
        failure_count = BaseExchange._failure_counts[self.name]

        print(f"[{self.name}] Operation failed ({failure_count}/{self._failure_threshold}): {error}")

        if failure_count >= self._failure_threshold:
            circuit_open_until = time.time() + self._circuit_timeout
            BaseExchange._circuit_open_until[self.name] = circuit_open_until
            print(f"[{self.name}] Circuit breaker OPEN - exchange disabled for {self._circuit_timeout}s")

    @abstractmethod
    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch raw data from the exchange API.

        REQUIRED ERROR HANDLING PATTERN:
        - Wrap entire method in try/except
        - Return pd.DataFrame() on ANY error (never return None)
        - Log errors with self.logger.error()
        - Circuit breaker will automatically track failures

        Example:
            try:
                data = self.safe_request(url)
                if not data:
                    return pd.DataFrame()
                return pd.DataFrame(data)
            except Exception as e:
                self.logger.error(f"Error: {e}")
                return pd.DataFrame()

        Returns:
            DataFrame with raw exchange data, or empty DataFrame on error
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
        if self._is_circuit_open():
            return None

        try:
            rate_limiter.acquire(self.name)

            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'User-Agent': f'ModularExchangeSystem/{self.name}'
            }

            session = self._get_session()
            response = session.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                self._record_success()
                return result
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                retry_after_seconds = float(retry_after) if retry_after else None
                rate_limiter.handle_429(self.name, retry_after_seconds)
                return None
            elif response.status_code in [400, 404] and silent_errors:
                return None
            elif response.status_code in [400, 404]:
                print(f"! Request failed for {url}: {response.status_code} {response.reason}")
                return None
            else:
                response.raise_for_status()
                result = response.json()
                self._record_success()
                return result

        except requests.exceptions.RequestException as e:
            self._record_failure(e)
            if not silent_errors:
                print(f"! Request failed for {url}: {str(e)}")
            return None
        except Exception as e:
            self._record_failure(e)
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
        if self._is_circuit_open():
            return None

        if headers is None:
            headers = {}
        if json_data is not None:
            headers['Content-Type'] = 'application/json'

        headers.update({
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'User-Agent': f'ModularExchangeSystem/{self.name}'
        })

        retry_count = 0
        backoff_delay = 2

        while retry_count <= max_retries:
            try:
                rate_limiter.acquire(self.name)

                session = self._get_session()
                response = session.post(url, json=json_data, headers=headers, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    self._record_success()
                    return result
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
                self._record_failure(e)
                if not silent_errors:
                    print(f"! POST request failed for {url}: {str(e)}")
                return None
            except Exception as e:
                self._record_failure(e)
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

    # ============================================
    # ASYNC METHODS FOR HIGH-PERFORMANCE FETCHING
    # ============================================

    def _get_async_rate_limit(self) -> int:
        """
        Get the async rate limit for this exchange.
        Override in child classes for custom limits.

        Returns:
            Requests per second allowed
        """
        # Default conservative rate limits per exchange
        rate_limits = {
            'Binance': 40,
            'ByBit': 50,
            'KuCoin': 30,
            'MEXC': 30,
            'Backpack': 20,
            'Deribit': 20,
            'Hyperliquid': 20,
            'Drift': 30,
            'Aster': 40,
            'Lighter': 20,
            'Pacifica': 20,
            'Hibachi': 20,
            'dYdX': 30
        }
        return rate_limits.get(self.name, 10)  # Default to 10 requests/sec

    def _get_async_semaphore_limit(self) -> int:
        """
        Get the maximum concurrent requests for this exchange.

        Returns:
            Maximum concurrent requests allowed
        """
        # Conservative concurrent request limits
        return min(self._get_async_rate_limit(), 50)

    async def create_async_session(self) -> aiohttp.ClientSession:
        """
        Create an aiohttp session with optimized settings for this exchange.

        Returns:
            Configured aiohttp ClientSession
        """
        connector = aiohttp.TCPConnector(
            limit=200,  # Total connection limit
            limit_per_host=100,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
            keepalive_timeout=30,  # Keep-alive timeout
            enable_cleanup_closed=True
        )

        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=10,  # Connection timeout
            sock_connect=10,
            sock_read=10
        )

        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': f'ModularExchangeSystem/{self.name}',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )

    async def async_safe_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str = 'GET',
        params: Dict = None,
        json_data: Dict = None,
        max_retries: int = 3,
        throttler: Throttler = None
    ) -> Optional[Dict]:
        """
        Make an async HTTP request with error handling and rate limiting.

        Args:
            session: aiohttp ClientSession
            url: The URL to request
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            json_data: JSON payload for POST requests
            max_retries: Maximum number of retries
            throttler: Optional Throttler for rate limiting

        Returns:
            JSON response data or None if failed
        """
        retry_count = 0
        backoff_delay = 1  # Start with 1 second

        while retry_count <= max_retries:
            try:
                # Apply rate limiting if throttler provided
                if throttler:
                    async with throttler:
                        return await self._make_async_request(
                            session, url, method, params, json_data
                        )
                else:
                    return await self._make_async_request(
                        session, url, method, params, json_data
                    )

            except aiohttp.ClientResponseError as e:
                if e.status == 429:  # Rate limited
                    if retry_count < max_retries:
                        wait_time = backoff_delay * (2 ** retry_count)
                        print(f"! Rate limited on {url}, retrying in {wait_time}s (attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        print(f"! Max retries exceeded for {url}: 429 Too Many Requests")
                        return None
                elif e.status in [400, 404]:
                    # Common for API endpoints that don't support certain symbols
                    return None
                else:
                    print(f"! Async request failed for {url}: {e.status} {e.message}")
                    return None

            except asyncio.TimeoutError:
                print(f"! Timeout for {url}")
                return None

            except Exception as e:
                print(f"! Unexpected async error for {url}: {str(e)}")
                return None

        return None

    async def _make_async_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str,
        params: Dict = None,
        json_data: Dict = None
    ) -> Optional[Dict]:
        """
        Internal method to make the actual async request.

        Args:
            session: aiohttp ClientSession
            url: The URL to request
            method: HTTP method
            params: Query parameters
            json_data: JSON payload

        Returns:
            JSON response data or None
        """
        async with session.request(
            method,
            url,
            params=params,
            json=json_data
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                response.raise_for_status()
                return None

    async def fetch_historical_async(
        self,
        symbol: str,
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Async method to fetch historical data for a symbol.
        Override in child classes for exchange-specific implementation.

        Args:
            symbol: Trading symbol
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)
            limit: Maximum records to fetch

        Returns:
            List of historical data records
        """
        # Default implementation - should be overridden
        raise NotImplementedError("Async historical fetching not implemented for this exchange")

    async def fetch_all_historical_async(
        self,
        symbols: List[str],
        days: int = 30,
        max_concurrent: int = None
    ) -> pd.DataFrame:
        """
        Fetch historical data for multiple symbols concurrently.

        Args:
            symbols: List of trading symbols
            days: Number of days of history to fetch
            max_concurrent: Maximum concurrent requests (None = use default)

        Returns:
            DataFrame with all historical data
        """
        if max_concurrent is None:
            max_concurrent = self._get_async_semaphore_limit()

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        # Create throttler for rate limiting
        rate_limit = self._get_async_rate_limit()
        throttler = Throttler(rate_limit=rate_limit, period=1.0)

        print(f"[{self.name}] Starting async historical fetch for {len(symbols)} symbols")
        print(f"  Rate limit: {rate_limit} req/s, Max concurrent: {max_concurrent}")

        async with self.create_async_session() as session:
            tasks = []
            for symbol in symbols:
                task = self._fetch_symbol_historical_with_semaphore(
                    session, semaphore, throttler, symbol, days
                )
                tasks.append(task)

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_data = []
            successful = 0
            failed = 0

            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    print(f"  Failed to fetch {symbol}: {str(result)}")
                    failed += 1
                elif result:
                    all_data.extend(result)
                    successful += 1
                else:
                    failed += 1

            print(f"[{self.name}] Async fetch complete: {successful} successful, {failed} failed")

            if all_data:
                return pd.DataFrame(all_data)
            else:
                return pd.DataFrame()

    async def _fetch_symbol_historical_with_semaphore(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        throttler: Throttler,
        symbol: str,
        days: int
    ) -> List[Dict]:
        """
        Fetch historical data for a single symbol with semaphore control.

        Args:
            session: aiohttp ClientSession
            semaphore: Semaphore for concurrency control
            throttler: Throttler for rate limiting
            symbol: Trading symbol
            days: Number of days of history

        Returns:
            List of historical records
        """
        async with semaphore:  # Limit concurrent requests
            try:
                # Calculate time range
                end_time = int(time.time() * 1000)
                start_time = end_time - (days * 24 * 60 * 60 * 1000)

                # Fetch historical data (to be implemented by child classes)
                return await self.fetch_historical_async(
                    symbol, start_time, end_time
                )
            except Exception as e:
                print(f"  Error fetching {symbol}: {str(e)}")
                return [] 