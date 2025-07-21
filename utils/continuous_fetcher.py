"""
Continuous Data Fetcher
=======================
Implements continuous data collection with configurable intervals,
graceful shutdown, and error recovery.
"""

import time
import signal
import threading
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, List, Callable
from utils.logger import setup_logger
from utils.rate_limiter import rate_limiter
from exchanges.exchange_factory import ExchangeFactory
from data_processing.data_processor import DataProcessor
from database.supabase_manager import SupabaseManager
from config.settings import DEBUG_MODE, EXCHANGES


class ContinuousFetcher:
    """
    Continuously fetches data from exchanges at specified intervals.
    
    Features:
    - Configurable fetch intervals
    - Graceful shutdown handling
    - Error recovery with exponential backoff
    - Integration with rate limiter
    - Progress reporting
    """
    
    def __init__(self, 
                 fetch_interval: int = 300,
                 max_retries: int = 3,
                 base_backoff: int = 60):
        """
        Initialize the continuous fetcher.
        
        Args:
            fetch_interval: Seconds between fetch cycles (default: 300 = 5 minutes)
            max_retries: Maximum retry attempts on failure (default: 3)
            base_backoff: Base backoff time in seconds (default: 60)
        """
        self.fetch_interval = fetch_interval
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        
        # Components
        self.exchange_factory = ExchangeFactory(EXCHANGES)
        self.data_processor = None  # Will be created when data is available
        self.supabase_manager = SupabaseManager()
        self.logger = setup_logger(__name__)
        
        # State
        self.running = False
        self.shutdown_event = threading.Event()
        self.stats = {
            'total_fetches': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'total_records': 0,
            'start_time': None,
            'last_fetch_time': None,
            'consecutive_failures': 0
        }
        
        # Setup signal handlers for graceful shutdown
        # Note: SIGTERM is not available on Windows
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n! Shutdown signal received. Stopping continuous fetcher...")
        self.stop()
    
    def start(self, callback: Optional[Callable] = None, duration: Optional[float] = None):
        """
        Start continuous data fetching.
        
        Args:
            callback: Optional callback function to call after each fetch
                     Signature: callback(data: pd.DataFrame, stats: Dict)
            duration: Optional duration in seconds to run the fetcher
        """
        if self.running:
            print("! Continuous fetcher is already running")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.now(timezone.utc)
        start_timestamp = time.time()
        
        print(f"OK Starting continuous data fetcher (interval: {self.fetch_interval}s)")
        if duration:
            print(f"   Duration limit: {duration} seconds")
        print("Press Ctrl+C to stop gracefully\n")
        
        while self.running and not self.shutdown_event.is_set():
            # Check duration limit
            if duration and (time.time() - start_timestamp) >= duration:
                print(f"\n! Duration limit reached ({duration}s)")
                self.running = False
                break
            fetch_start = time.time()
            
            try:
                # Perform data fetch
                data = self._fetch_cycle()
                
                if data is not None and not data.empty:
                    # Update statistics
                    self.stats['successful_fetches'] += 1
                    self.stats['total_records'] += len(data)
                    self.stats['consecutive_failures'] = 0
                    
                    # Call callback if provided
                    if callback:
                        callback(data, self.stats.copy())
                    
                    print(f"OK Fetch cycle completed: {len(data)} records")
                else:
                    self._handle_fetch_failure()
                
            except Exception as e:
                self.logger.error(f"Unexpected error in fetch cycle: {e}")
                self._handle_fetch_failure()
            
            finally:
                self.stats['total_fetches'] += 1
                self.stats['last_fetch_time'] = datetime.now(timezone.utc)
            
            # Wait for next cycle or shutdown
            fetch_duration = time.time() - fetch_start
            wait_time = max(0, self.fetch_interval - fetch_duration)
            
            if wait_time > 0 and self.running:
                self._print_progress()
                print(f"  Next fetch in {wait_time:.0f} seconds...")
                self.shutdown_event.wait(wait_time)
    
    def _fetch_cycle(self) -> Optional[pd.DataFrame]:
        """
        Perform a single fetch cycle with retry logic.
        
        Returns:
            DataFrame with fetched data or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                print(f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Fetching data...")
                
                # Get rate limiter status
                rate_status = rate_limiter.get_status()
                for exchange, status in rate_status.items():
                    if status['in_backoff']:
                        print(f"  ! {exchange} in backoff for {status['backoff_remaining']:.1f}s")
                
                # Fetch data from all exchanges
                all_data = self.exchange_factory.process_all_exchanges()
                
                if all_data.empty:
                    print("! No data fetched from any exchange")
                    if attempt < self.max_retries - 1:
                        backoff = self.base_backoff * (2 ** attempt)
                        print(f"  Retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(backoff)
                        continue
                    return None
                
                # Add timestamp for historical tracking
                all_data['timestamp'] = datetime.now(timezone.utc)
                
                # Process data (calculate APR, validate, etc.)
                self.data_processor = DataProcessor(all_data)
                
                # Upload to historical table
                if self._upload_historical_data(all_data):
                    return all_data
                else:
                    print("! Failed to upload data to database")
                    if attempt < self.max_retries - 1:
                        backoff = self.base_backoff * (2 ** attempt)
                        print(f"  Retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(backoff)
                        continue
                    return None
                
            except Exception as e:
                self.logger.error(f"Error in fetch cycle attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    backoff = self.base_backoff * (2 ** attempt)
                    print(f"  Retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(backoff)
                else:
                    return None
        
        return None
    
    def _upload_historical_data(self, data: pd.DataFrame) -> bool:
        """
        Upload data to historical table.
        
        Args:
            data: DataFrame with timestamp column
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the historical upload method (will be added to SupabaseManager)
            return self.supabase_manager.upload_historical_data(data)
        except AttributeError:
            # Fallback to regular upload if historical method not yet implemented
            print("! Historical upload method not found, using regular upload")
            return self.supabase_manager.upload_data(data)
    
    def _handle_fetch_failure(self):
        """Handle fetch failures with exponential backoff."""
        self.stats['failed_fetches'] += 1
        self.stats['consecutive_failures'] += 1
        
        if self.stats['consecutive_failures'] >= self.max_retries:
            print(f"! WARNING: {self.stats['consecutive_failures']} consecutive failures")
            
            # Extended backoff after multiple failures
            extended_backoff = self.base_backoff * (2 ** self.stats['consecutive_failures'])
            max_backoff = min(extended_backoff, 3600)  # Cap at 1 hour
            
            print(f"  Entering extended backoff: {max_backoff}s")
            self.shutdown_event.wait(max_backoff)
    
    def _print_progress(self):
        """Print progress statistics."""
        if not self.stats['start_time']:
            return
        
        runtime = datetime.now(timezone.utc) - self.stats['start_time']
        runtime_hours = runtime.total_seconds() / 3600
        
        print("\n--- Progress Report ---")
        print(f"  Runtime: {runtime_hours:.1f} hours")
        print(f"  Total fetches: {self.stats['total_fetches']}")
        print(f"  Successful: {self.stats['successful_fetches']}")
        print(f"  Failed: {self.stats['failed_fetches']}")
        print(f"  Total records: {self.stats['total_records']:,}")
        
        if self.stats['successful_fetches'] > 0:
            avg_records = self.stats['total_records'] / self.stats['successful_fetches']
            print(f"  Avg records/fetch: {avg_records:.0f}")
        
        if self.stats['total_fetches'] > 0:
            success_rate = (self.stats['successful_fetches'] / self.stats['total_fetches']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
    
    def stop(self):
        """Stop the continuous fetcher gracefully."""
        if not self.running:
            return
        
        self.running = False
        self.shutdown_event.set()
        
        print("\nOK Continuous fetcher stopped")
        self._print_final_report()
    
    def _print_final_report(self):
        """Print final statistics report."""
        print("\n============================================================")
        print("FINAL REPORT - Continuous Data Collection")
        print("============================================================")
        
        if self.stats['start_time']:
            runtime = datetime.now(timezone.utc) - self.stats['start_time']
            print(f"Total runtime: {runtime}")
        
        print(f"Total fetch cycles: {self.stats['total_fetches']}")
        print(f"Successful fetches: {self.stats['successful_fetches']}")
        print(f"Failed fetches: {self.stats['failed_fetches']}")
        print(f"Total records collected: {self.stats['total_records']:,}")
        
        if self.stats['successful_fetches'] > 0:
            avg_records = self.stats['total_records'] / self.stats['successful_fetches']
            print(f"Average records per fetch: {avg_records:.0f}")
        
        if self.stats['total_fetches'] > 0:
            success_rate = (self.stats['successful_fetches'] / self.stats['total_fetches']) * 100
            print(f"Overall success rate: {success_rate:.1f}%")
        
        print("============================================================")
    
    def get_stats(self) -> Dict:
        """
        Get current statistics.
        
        Returns:
            Dictionary with current stats
        """
        return self.stats.copy()