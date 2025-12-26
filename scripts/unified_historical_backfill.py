#!/usr/bin/env python3
"""
Unified Historical Funding Rate Backfill
=========================================
Backfill historical funding rates for multiple exchanges in one command.
Supports parallel or sequential execution with combined progress tracking.
"""

import sys
import time
import argparse
import json
import threading
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from exchanges.binance_exchange import BinanceExchange
from exchanges.kucoin_exchange import KuCoinExchange
from exchanges.backpack_exchange import BackpackExchange
from exchanges.hyperliquid_exchange import HyperliquidExchange
from exchanges.drift_exchange import DriftExchange
from exchanges.aster_exchange import AsterExchange
from exchanges.lighter_exchange import LighterExchange
from exchanges.bybit_exchange import ByBitExchange
from exchanges.pacifica_exchange import PacificaExchange
from exchanges.hibachi_exchange import HibachiExchange
from exchanges.mexc_exchange import MexcExchange
from exchanges.deribit_exchange import DeribitExchange
from exchanges.dydx_exchange import DydxExchange
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger
from config.settings import (
    EXCHANGES,
    HISTORICAL_SYNC_ENABLED,
    HISTORICAL_ALIGN_TO_MIDNIGHT,
    HISTORICAL_WINDOW_DAYS
)

logger = setup_logger("UnifiedBackfill")

# Configuration constants
STALE_LOCK_TIMEOUT_SECONDS = 600  # 10 minutes
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1  # Exponential backoff base
COMPLETENESS_THRESHOLD_PERCENT = 95.0
PROGRESS_LOG_INTERVAL_ASSETS = 50  # Log progress every N assets

# Exchange mapping
EXCHANGE_CLASSES = {
    'binance': BinanceExchange,
    'kucoin': KuCoinExchange,
    'backpack': BackpackExchange,
    'hyperliquid': HyperliquidExchange,
    'drift': DriftExchange,
    'aster': AsterExchange,
    'lighter': LighterExchange,
    'bybit': ByBitExchange,
    'pacifica': PacificaExchange,
    'hibachi': HibachiExchange,
    'mexc': MexcExchange,
    'deribit': DeribitExchange,
    'dydx': DydxExchange,
    # Add more exchanges here as they get historical support
}


class UnifiedBackfill:
    """Unified backfill coordinator for multiple exchanges."""
    
    def __init__(self, days: int = 30, batch_size: int = 10, dry_run: bool = False,
                 align_to_midnight: bool = None, sync_enabled: bool = None,
                 is_loop_mode: bool = False):
        """
        Initialize unified backfill.

        Args:
            days: Number of days to backfill
            batch_size: Number of symbols to process per batch
            dry_run: If True, fetch data but don't upload to database
            align_to_midnight: If True, align dates to midnight UTC (uses config if None)
            sync_enabled: If True, use synchronized dates (uses config if None)
            is_loop_mode: If True, running in loop mode (disables lock conflicts)
        """
        self.days = days
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.db_manager = None
        self.is_loop_mode = is_loop_mode
        
        # Use config values if not explicitly provided
        self.sync_enabled = sync_enabled if sync_enabled is not None else HISTORICAL_SYNC_ENABLED
        self.align_to_midnight = align_to_midnight if align_to_midnight is not None else HISTORICAL_ALIGN_TO_MIDNIGHT
        
        # Calculate synchronized date range if enabled
        self.unified_start_time = None
        self.unified_end_time = None
        if self.sync_enabled:
            self._calculate_unified_dates()
        
        # Progress tracking
        self.progress_data = {}
        self.symbol_completeness = {}  # Track per-symbol completeness
        self.lock = threading.Lock()
        
        # Status file for overall progress
        self.status_file = Path(".unified_backfill.status")
        self.lock_file = Path(".unified_backfill.lock")
        
        # Also update the main backfill status file for dashboard compatibility
        self.dashboard_status_file = Path(".backfill.status")
        self.dashboard_lock_file = Path(".backfill.lock")
    
    def _calculate_unified_dates(self):
        """Calculate unified start and end dates for all exchanges."""
        # Calculate end time - always use current time to get latest data
        self.unified_end_time = datetime.now(timezone.utc)

        # Calculate start time
        self.unified_start_time = self.unified_end_time - timedelta(days=self.days)

        # Align start time to midnight if configured (for clean historical window)
        # But keep end time as current time to include today's recent hours
        if self.align_to_midnight:
            self.unified_start_time = self.unified_start_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        logger.info(f"Unified date range calculated:")
        logger.info(f"  Start: {self.unified_start_time.isoformat()}")
        logger.info(f"  End: {self.unified_end_time.isoformat()}")
        logger.info(f"  Start aligned to midnight: {self.align_to_midnight}")
        
    def _write_status_atomic(self, file_path: Path, data: dict):
        """Atomically write JSON status file to prevent corruption on crash."""
        temp_path = file_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            for attempt in range(3):
                try:
                    temp_path.replace(file_path)
                    return
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.1 * (attempt + 1))
                    else:
                        with open(file_path, 'w') as f:
                            json.dump(data, f, indent=2, default=str)
                        if temp_path.exists():
                            temp_path.unlink()
                        return
        except Exception as e:
            logger.error(f"Failed to write status file {file_path}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def _acquire_lock(self, lock_path: Path) -> bool:
        """Atomically acquire a lock file. Returns True if successful, False if lock already exists."""
        try:
            # Use O_CREAT | O_EXCL for atomic create-if-not-exists
            # This will raise FileExistsError if the lock already exists
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, f"pid:{os.getpid()}\ntime:{time.time()}".encode())
            os.close(fd)
            return True
        except FileExistsError:
            # Lock already exists - check if it's stale
            if lock_path.exists():
                lock_age = time.time() - lock_path.stat().st_mtime
                if lock_age >= STALE_LOCK_TIMEOUT_SECONDS:
                    logger.warning(f"Stale lock detected ({lock_age/60:.1f} minutes old). Removing...")
                    try:
                        lock_path.unlink()
                        # Try acquiring again after removing stale lock
                        return self._acquire_lock(lock_path)
                    except Exception as e:
                        logger.error(f"Failed to remove stale lock: {e}")
                        return False
                else:
                    return False
            return False
        except Exception as e:
            logger.error(f"Unexpected error acquiring lock {lock_path}: {e}")
            return False

    def initialize(self) -> bool:
        """Initialize database connection and check prerequisites."""
        try:
            # In loop mode, force cleanup of any existing locks first
            if self.is_loop_mode:
                if self.lock_file.exists():
                    logger.info("Loop mode: Removing existing unified backfill lock")
                    self.lock_file.unlink()
                if self.dashboard_lock_file.exists():
                    logger.info("Loop mode: Removing existing dashboard lock")
                    self.dashboard_lock_file.unlink()

            # Atomically acquire locks (skipped in loop mode since we force-cleaned above)
            if not self.is_loop_mode:
                if not self._acquire_lock(self.lock_file):
                    logger.warning("Another backfill is already running!")
                    logger.warning("If this is incorrect, delete .unified_backfill.lock and .backfill.lock")
                    return False

                if not self._acquire_lock(self.dashboard_lock_file):
                    logger.warning("Another backfill is already running (dashboard lock)!")
                    # Clean up the first lock we just created
                    if self.lock_file.exists():
                        self.lock_file.unlink()
                    return False
            else:
                # In loop mode, create locks normally after force cleanup
                self.lock_file.touch()
                self.dashboard_lock_file.touch()
            
            # Initialize database if not dry run
            if not self.dry_run:
                self.db_manager = PostgresManager()
                if not self.db_manager.test_connection():
                    logger.error("Database connection failed!")
                    return False
                logger.info("Database connection successful")
            else:
                logger.info("Dry run mode - database operations disabled")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        if self.lock_file.exists():
            self.lock_file.unlink()
        if self.dashboard_lock_file.exists():
            self.dashboard_lock_file.unlink()
    
    def update_progress(self, exchange: str, symbols_processed: int, total_symbols: int,
                       records_fetched: int, status: str = "processing", completeness_data: dict = None,
                       price_assets: int = 0, start_time: float = None, elapsed_time: float = None):
        """Update progress for an exchange with optional completeness data and timing."""
        with self.lock:
            progress_entry = {
                'symbols_processed': symbols_processed,
                'total_symbols': total_symbols,
                'records_fetched': records_fetched,
                'status': status,
                'progress': int((symbols_processed / total_symbols * 100)) if total_symbols > 0 else 0,
                'price_assets': price_assets
            }

            # Add timing data if provided
            if start_time is not None:
                progress_entry['start_time'] = start_time
            if elapsed_time is not None:
                progress_entry['elapsed_time'] = elapsed_time
                # Calculate estimated remaining time for in-progress exchanges
                if status == "processing" and symbols_processed > 0 and total_symbols > 0:
                    avg_time_per_symbol = elapsed_time / symbols_processed
                    remaining_symbols = total_symbols - symbols_processed
                    progress_entry['estimated_remaining'] = avg_time_per_symbol * remaining_symbols

            self.progress_data[exchange] = progress_entry
            
            # Store completeness data if provided
            if completeness_data:
                if exchange not in self.symbol_completeness:
                    self.symbol_completeness[exchange] = {}
                self.symbol_completeness[exchange].update(completeness_data)
            
            # Calculate overall progress
            total_progress = 0
            active_exchanges = 0
            total_records = 0
            
            for ex_data in self.progress_data.values():
                if ex_data['total_symbols'] > 0:
                    total_progress += ex_data['progress']
                    active_exchanges += 1
                    total_records += ex_data['records_fetched']
            
            overall_progress = int(total_progress / active_exchanges) if active_exchanges > 0 else 0
            
            # Calculate completeness metrics
            completeness_summary = {}
            if self.symbol_completeness:
                for ex, symbols in self.symbol_completeness.items():
                    complete_count = sum(1 for s in symbols.values() if s.get('completeness', 0) >= 95)
                    total = len(symbols)
                    completeness_summary[ex] = {
                        'complete': complete_count,
                        'total': total,
                        'percentage': round(complete_count / total * 100, 2) if total > 0 else 0
                    }
            
            # Write status files atomically
            status_data = {
                'running': True,
                'overall_progress': overall_progress,
                'total_records': total_records,
                'exchanges': self.progress_data,
                'completeness': completeness_summary,
                'message': f"Processing {active_exchanges} exchange(s)..."
            }
            self._write_status_atomic(self.status_file, status_data)

            # Also write dashboard-compatible status file atomically
            dashboard_status = {
                'running': True,
                'progress': overall_progress,
                'message': f"Unified backfill: {overall_progress}% complete ({total_records:,} records)",
                'completed': False
            }
            self._write_status_atomic(self.dashboard_status_file, dashboard_status)
    
    def backfill_exchange(self, exchange_name: str, max_retries: int = RETRY_MAX_ATTEMPTS) -> Tuple[str, int, bool, int]:
        """
        Backfill historical data for a single exchange with retry logic.

        Args:
            exchange_name: Name of the exchange to backfill
            max_retries: Maximum number of retry attempts for transient failures

        Returns:
            Tuple of (exchange_name, records_count, success, price_assets_count)
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return self._backfill_exchange_impl(exchange_name)
            except Exception as e:
                last_exception = e
                # Check if this is a transient error worth retrying
                error_msg = str(e).lower()
                is_transient = any(keyword in error_msg for keyword in [
                    'timeout', 'connection', 'network', 'rate limit',
                    'temporarily', 'unavailable', 'try again'
                ])

                if is_transient and attempt < max_retries - 1:
                    wait_time = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"{exchange_name}: Transient error on attempt {attempt + 1}/{max_retries}: {e}")
                    logger.info(f"{exchange_name}: Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Non-transient error or final attempt - give up
                    logger.error(f"{exchange_name}: Failed after {attempt + 1} attempts: {e}")
                    raise

        # Should not reach here, but handle it anyway
        raise last_exception if last_exception else Exception("Unknown error in retry logic")

    def _backfill_exchange_impl(self, exchange_name: str) -> Tuple[str, int, bool, int]:
        """
        Internal implementation of exchange backfill (called by retry wrapper).

        Returns:
            Tuple of (exchange_name, records_count, success, price_assets_count)
        """
        try:
            logger.info(f"="*60)
            logger.info(f"Starting backfill for {exchange_name.upper()}")
            logger.info(f"="*60)
            
            # Get exchange class
            exchange_class = EXCHANGE_CLASSES.get(exchange_name.lower())
            if not exchange_class:
                logger.error(f"Exchange {exchange_name} not supported for historical backfill")
                return (exchange_name, 0, False)
            
            # Initialize exchange
            exchange = exchange_class()
            
            # Fetch historical data with unified dates if sync is enabled
            start_time = time.time()

            # Create progress callback for this exchange
            def progress_callback(symbols_processed, total_symbols, progress, message):
                # Track records fetched (estimate based on progress)
                records_estimate = int(symbols_processed * 24 * self.days / 8)  # Rough estimate
                current_elapsed = time.time() - start_time
                self.update_progress(exchange_name, symbols_processed, total_symbols,
                                   records_estimate, "processing",
                                   start_time=start_time,
                                   elapsed_time=current_elapsed)
            
            # Prepare kwargs for the fetch method
            fetch_kwargs = {
                'days': self.days,
                'batch_size': self.batch_size,
                'progress_callback': progress_callback
            }
            
            # Add unified dates if sync is enabled
            if self.sync_enabled and self.unified_start_time and self.unified_end_time:
                fetch_kwargs['start_time'] = self.unified_start_time
                fetch_kwargs['end_time'] = self.unified_end_time
                logger.info(f"{exchange_name}: Using unified date range")
            
            historical_df = exchange.fetch_all_perpetuals_historical(**fetch_kwargs)
            
            if historical_df.empty:
                logger.warning(f"No historical data fetched for {exchange_name}")
                self.update_progress(exchange_name, 0, 0, 0, "no_data")
                return (exchange_name, 0, False, 0)
            
            elapsed_time = time.time() - start_time
            logger.info(f"="*60)
            logger.info(f"{exchange_name.upper()}: Successfully fetched {len(historical_df)} records in {elapsed_time:.2f}s")
            unique_symbols = historical_df['symbol'].nunique() if 'symbol' in historical_df.columns else 0
            logger.info(f"{exchange_name.upper()}: {unique_symbols} unique contracts processed")
            
            # Calculate per-symbol completeness
            completeness_data = {}
            if 'symbol' in historical_df.columns and 'funding_interval_hours' in historical_df.columns:
                for symbol in historical_df['symbol'].unique():
                    symbol_data = historical_df[historical_df['symbol'] == symbol]
                    actual_points = len(symbol_data)
                    
                    # Get funding interval (use most common if varies)
                    funding_interval = symbol_data['funding_interval_hours'].mode()[0] if not symbol_data['funding_interval_hours'].empty else 8
                    
                    # Calculate expected points for 30-day window
                    expected_points = (self.days * 24) / funding_interval
                    completeness_pct = (actual_points / expected_points * 100) if expected_points > 0 else 0
                    
                    completeness_data[symbol] = {
                        'actual': actual_points,
                        'expected': int(expected_points),
                        'completeness': round(completeness_pct, 2),
                        'interval': funding_interval
                    }
                    
                    # Log warnings for low completeness
                    if completeness_pct < 95:
                        logger.warning(f"{exchange_name}:{symbol} - Low completeness: {completeness_pct:.1f}% ({actual_points}/{int(expected_points)} points)")
            
            # Log completeness summary and validate against threshold
            completeness_acceptable = True
            if completeness_data:
                complete_symbols = sum(1 for s in completeness_data.values() if s['completeness'] >= 95)
                overall_completeness_pct = (complete_symbols / len(completeness_data) * 100) if len(completeness_data) > 0 else 0
                logger.info(f"{exchange_name.upper()}: {complete_symbols}/{len(completeness_data)} symbols have ≥95% completeness ({overall_completeness_pct:.1f}%)")

                # Check if overall completeness meets threshold
                if overall_completeness_pct < COMPLETENESS_THRESHOLD_PERCENT:
                    logger.warning(f"{exchange_name.upper()}: Overall completeness {overall_completeness_pct:.1f}% is below threshold {COMPLETENESS_THRESHOLD_PERCENT}%")
                    logger.warning(f"{exchange_name.upper()}: This may indicate missing data or API issues - consider re-running backfill")
                    completeness_acceptable = False

            logger.info(f"="*60)
            
            # Upload to database
            if not self.dry_run and self.db_manager:
                logger.info(f"Uploading {exchange_name} data to database...")
                upload_start = time.time()
                
                success = self.db_manager.upload_historical_funding_rates(historical_df)
                
                if success:
                    upload_time = time.time() - upload_start
                    logger.info(f"{exchange_name}: Uploaded funding rates in {upload_time:.2f}s")

                    # Price collection feature not yet implemented
                    price_assets_collected = 0

                    self.update_progress(exchange_name,
                                       historical_df['symbol'].nunique(),
                                       historical_df['symbol'].nunique(),
                                       len(historical_df), "completed",
                                       completeness_data=completeness_data,
                                       price_assets=price_assets_collected,
                                       start_time=start_time,
                                       elapsed_time=elapsed_time)
                    return (exchange_name, len(historical_df), True, price_assets_collected)
                else:
                    logger.error(f"Failed to upload {exchange_name} data")
                    self.update_progress(exchange_name, 0, 0, 0, "upload_failed")
                    return (exchange_name, 0, False, 0)
            else:
                # Dry run - just return stats
                self.update_progress(exchange_name,
                                   historical_df['symbol'].nunique(),
                                   historical_df['symbol'].nunique(),
                                   len(historical_df), "completed_dry_run",
                                   completeness_data=completeness_data)
                return (exchange_name, len(historical_df), True, 0)

        except Exception as e:
            logger.error(f"Error backfilling {exchange_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.update_progress(exchange_name, 0, 0, 0, "error")
            return (exchange_name, 0, False, 0)
    
    def run_parallel(self, exchanges: List[str], max_workers: int = 2) -> bool:
        """
        Run backfill for multiple exchanges in parallel.
        
        Args:
            exchanges: List of exchange names
            max_workers: Maximum number of parallel workers
            
        Returns:
            True if all successful, False otherwise
        """
        logger.info(f"Running parallel backfill for {exchanges} with {max_workers} workers")

        all_success = True
        total_records = 0
        successful_exchanges = 0
        failed_exchanges = 0

        logger.info("="*60)
        logger.info("BACKFILL SUMMARY (processing as completed)")
        logger.info("="*60)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.backfill_exchange, exchange): exchange
                for exchange in exchanges
            }

            # Process and log results immediately as they complete (no accumulation)
            for future in as_completed(futures):
                exchange_name, records, success, price_assets = future.result()

                # Log immediately (no accumulation in memory)
                status = "✓" if success else "✗"
                price_info = f", {price_assets} assets with prices" if price_assets > 0 else ""
                logger.info(f"{status} {exchange_name}: {records:,} funding records{price_info}")

                # Update running totals only
                if not success:
                    all_success = False
                    failed_exchanges += 1
                else:
                    successful_exchanges += 1
                total_records += records

        # Final summary
        logger.info("="*60)
        logger.info(f"Total records: {total_records:,}")
        logger.info(f"Successful: {successful_exchanges}/{len(exchanges)} exchanges")
        if failed_exchanges > 0:
            logger.info(f"Failed: {failed_exchanges} exchanges")
        logger.info("="*60)
        
        return all_success
    
    def run_sequential(self, exchanges: List[str]) -> bool:
        """
        Run backfill for multiple exchanges sequentially.

        Args:
            exchanges: List of exchange names

        Returns:
            True if all successful, False otherwise
        """
        logger.info(f"Running sequential backfill for {exchanges}")

        all_success = True
        total_records = 0
        successful_exchanges = 0
        failed_exchanges = 0

        logger.info("="*60)
        logger.info("BACKFILL SUMMARY (processing sequentially)")
        logger.info("="*60)

        for exchange in exchanges:
            exchange_name, records, success, price_assets = self.backfill_exchange(exchange)

            # Log immediately (no accumulation in memory)
            status = "✓" if success else "✗"
            price_info = f", {price_assets} assets with prices" if price_assets > 0 else ""
            logger.info(f"{status} {exchange_name}: {records:,} funding records{price_info}")

            # Update running totals only
            if not success:
                all_success = False
                failed_exchanges += 1
            else:
                successful_exchanges += 1
            total_records += records

        # Final summary
        logger.info("="*60)
        logger.info(f"Total records: {total_records:,}")
        logger.info(f"Successful: {successful_exchanges}/{len(exchanges)} exchanges")
        if failed_exchanges > 0:
            logger.info(f"Failed: {failed_exchanges} exchanges")
        logger.info("="*60)

        return all_success


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Unified historical funding rate backfill for multiple exchanges'
    )
    parser.add_argument(
        '--exchanges',
        type=str,
        help='Comma-separated list of exchanges (e.g., binance,kucoin). Default: all enabled'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to backfill (default: 30)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of symbols to process per batch (default: 10)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run exchanges in parallel (default: sequential)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=13,
        help='Maximum parallel workers (default: 13, one per exchange)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not upload to database'
    )
    parser.add_argument(
        '--loop-hourly',
        action='store_true',
        help='Run continuously at the start of every UTC hour (XX:00)'
    )

    args = parser.parse_args()
    
    # Determine which exchanges to backfill
    if args.exchanges:
        exchanges = [e.strip().lower() for e in args.exchanges.split(',')]
    else:
        # Use all enabled exchanges that support historical data
        exchanges = [name for name, enabled in EXCHANGES.items() 
                    if enabled and name in EXCHANGE_CLASSES]
    
    if not exchanges:
        logger.error("No exchanges specified or enabled for backfill")
        sys.exit(1)
    
    # Validate exchanges
    invalid_exchanges = [e for e in exchanges if e not in EXCHANGE_CLASSES]
    if invalid_exchanges:
        logger.error(f"Unsupported exchanges for historical backfill: {invalid_exchanges}")
        logger.info(f"Supported exchanges: {list(EXCHANGE_CLASSES.keys())}")
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("UNIFIED HISTORICAL FUNDING RATE BACKFILL")
    logger.info("="*60)
    logger.info(f"Exchanges: {exchanges}")
    logger.info(f"Days to backfill: {args.days}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Mode: {'PARALLEL' if args.parallel else 'SEQUENTIAL'}")
    if args.parallel:
        logger.info(f"Max workers: {args.max_workers}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Loop mode: {'HOURLY UTC' if args.loop_hourly else 'SINGLE RUN'}")
    logger.info("="*60)
    
    # Function to calculate seconds until next UTC hour
    def seconds_until_next_hour():
        """Calculate seconds until the next UTC hour (XX:00:00)."""
        now = datetime.now(timezone.utc)
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return (next_hour - now).total_seconds()

    # Function to run a single backfill iteration
    def run_backfill_iteration(run_number=None, is_loop_mode=False):
        """Run a single backfill iteration."""
        # Create backfill coordinator
        backfill = UnifiedBackfill(
            days=args.days,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            is_loop_mode=is_loop_mode
        )

        # Initialize
        if not backfill.initialize():
            logger.error("Failed to initialize backfill")
            return False

        try:
            # Run backfill
            start_time = time.time()

            if args.parallel:
                success = backfill.run_parallel(exchanges, args.max_workers)
            else:
                success = backfill.run_sequential(exchanges)

            total_time = time.time() - start_time

            # Calculate total records from progress data
            total_records = sum(ex_data.get('records_fetched', 0) for ex_data in backfill.progress_data.values())

            # Final status
            logger.info(f"Total backfill time: {total_time:.2f} seconds")
            logger.info(f"Total records collected: {total_records:,}")

            if success:
                logger.info("="*60)
                if run_number:
                    logger.info(f"BACKFILL RUN #{run_number} COMPLETED SUCCESSFULLY")
                else:
                    logger.info("UNIFIED BACKFILL COMPLETED SUCCESSFULLY")
                logger.info("="*60)

                # Write final status atomically
                final_status = {
                    'running': False,
                    'overall_progress': 100,
                    'exchanges': backfill.progress_data,
                    'message': "Backfill completed successfully",
                    'completed': True,
                    'total_time': total_time,
                    'run_number': run_number
                }
                backfill._write_status_atomic(backfill.status_file, final_status)

                # Also update dashboard-compatible status file atomically
                dashboard_final_status = {
                    'running': False,
                    'progress': 100,
                    'message': f"Backfill completed: {total_records:,} records in {int(total_time)}s",
                    'completed': True,
                    'total_records': total_records,
                    'total_time': total_time,
                    'timestamp': datetime.now().isoformat()
                }
                backfill._write_status_atomic(backfill.dashboard_status_file, dashboard_final_status)
            else:
                logger.error("="*60)
                if run_number:
                    logger.error(f"BACKFILL RUN #{run_number} COMPLETED WITH ERRORS")
                else:
                    logger.error("UNIFIED BACKFILL COMPLETED WITH ERRORS")
                logger.error("="*60)

            return success

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            backfill.cleanup()

    # Main execution logic
    if args.loop_hourly:
        # Hourly loop mode
        logger.info("Starting hourly backfill loop. Press Ctrl+C to stop.")

        # Loop statistics
        loop_stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'start_time': datetime.now(timezone.utc)
        }

        try:
            while True:
                # Calculate time until next hour
                wait_seconds = seconds_until_next_hour()
                next_run_time = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)

                # If we're very close to the hour (within 5 seconds), run immediately
                if wait_seconds > 5:
                    logger.info(f"Next backfill scheduled for: {next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    logger.info(f"Waiting {int(wait_seconds)} seconds ({wait_seconds/60:.1f} minutes)...")

                    # Sleep with periodic updates
                    while wait_seconds > 60:
                        time.sleep(60)
                        wait_seconds = seconds_until_next_hour()
                        if wait_seconds > 60:
                            logger.info(f"Time remaining: {int(wait_seconds)} seconds ({wait_seconds/60:.1f} minutes)")

                    # Sleep for remaining seconds
                    if wait_seconds > 0:
                        time.sleep(wait_seconds)

                # Run backfill
                loop_stats['total_runs'] += 1
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

                # Force cleanup any stale locks before starting (extra safety for loop mode)
                lock_files_to_clean = [Path(".unified_backfill.lock"), Path(".backfill.lock")]
                for lock_file in lock_files_to_clean:
                    if lock_file.exists():
                        try:
                            lock_file.unlink()
                            logger.debug(f"Cleaned up stale lock file: {lock_file}")
                        except Exception as e:
                            logger.warning(f"Could not remove lock file {lock_file}: {e}")

                logger.info("="*60)
                logger.info(f"[{current_time}] STARTING HOURLY BACKFILL RUN #{loop_stats['total_runs']}")
                logger.info("="*60)

                success = run_backfill_iteration(loop_stats['total_runs'], is_loop_mode=True)

                if success:
                    loop_stats['successful_runs'] += 1
                else:
                    loop_stats['failed_runs'] += 1

                # Print loop statistics
                uptime = datetime.now(timezone.utc) - loop_stats['start_time']
                logger.info("="*60)
                logger.info("HOURLY LOOP STATISTICS")
                logger.info(f"Total runs: {loop_stats['total_runs']}")
                logger.info(f"Successful: {loop_stats['successful_runs']}")
                logger.info(f"Failed: {loop_stats['failed_runs']}")
                logger.info(f"Success rate: {loop_stats['successful_runs']/loop_stats['total_runs']*100:.1f}%")
                logger.info(f"Uptime: {str(uptime).split('.')[0]}")
                logger.info("="*60)

        except KeyboardInterrupt:
            logger.warning("\nHourly backfill loop interrupted by user")
            logger.info(f"Completed {loop_stats['total_runs']} runs ({loop_stats['successful_runs']} successful)")
            sys.exit(0)

    else:
        # Single run mode (original behavior)
        try:
            success = run_backfill_iteration()
            sys.exit(0 if success else 1)
        except KeyboardInterrupt:
            logger.warning("Backfill interrupted by user")
            sys.exit(1)


if __name__ == "__main__":
    main()