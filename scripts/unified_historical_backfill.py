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
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger
from config.settings import (
    EXCHANGES, 
    HISTORICAL_SYNC_ENABLED,
    HISTORICAL_ALIGN_TO_MIDNIGHT,
    HISTORICAL_WINDOW_DAYS
)

logger = setup_logger("UnifiedBackfill")

# Exchange mapping
EXCHANGE_CLASSES = {
    'binance': BinanceExchange,
    'kucoin': KuCoinExchange,
    'backpack': BackpackExchange,
    'hyperliquid': HyperliquidExchange,
    # Add more exchanges here as they get historical support
}


class UnifiedBackfill:
    """Unified backfill coordinator for multiple exchanges."""
    
    def __init__(self, days: int = 30, batch_size: int = 10, dry_run: bool = False, 
                 align_to_midnight: bool = None, sync_enabled: bool = None):
        """
        Initialize unified backfill.
        
        Args:
            days: Number of days to backfill
            batch_size: Number of symbols to process per batch
            dry_run: If True, fetch data but don't upload to database
            align_to_midnight: If True, align dates to midnight UTC (uses config if None)
            sync_enabled: If True, use synchronized dates (uses config if None)
        """
        self.days = days
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.db_manager = None
        
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
        # Calculate end time
        self.unified_end_time = datetime.now(timezone.utc)
        
        # Align to midnight if configured
        if self.align_to_midnight:
            self.unified_end_time = self.unified_end_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        
        # Calculate start time
        self.unified_start_time = self.unified_end_time - timedelta(days=self.days)
        
        logger.info(f"Unified date range calculated:")
        logger.info(f"  Start: {self.unified_start_time.isoformat()}")
        logger.info(f"  End: {self.unified_end_time.isoformat()}")
        logger.info(f"  Aligned to midnight: {self.align_to_midnight}")
        
    def initialize(self) -> bool:
        """Initialize database connection and check prerequisites."""
        try:
            # Check for existing lock
            if self.lock_file.exists() or self.dashboard_lock_file.exists():
                lock_age = time.time() - self.lock_file.stat().st_mtime if self.lock_file.exists() else 0
                dash_lock_age = time.time() - self.dashboard_lock_file.stat().st_mtime if self.dashboard_lock_file.exists() else 0
                if lock_age < 600 or dash_lock_age < 600:  # Less than 10 minutes old
                    logger.warning("Another backfill is already running!")
                    logger.warning("If this is incorrect, delete .unified_backfill.lock and .backfill.lock")
                    return False
            
            # Create lock files
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
                       records_fetched: int, status: str = "processing", completeness_data: dict = None):
        """Update progress for an exchange with optional completeness data."""
        with self.lock:
            self.progress_data[exchange] = {
                'symbols_processed': symbols_processed,
                'total_symbols': total_symbols,
                'records_fetched': records_fetched,
                'status': status,
                'progress': int((symbols_processed / total_symbols * 100)) if total_symbols > 0 else 0
            }
            
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
            
            # Write status files
            status_data = {
                'running': True,
                'overall_progress': overall_progress,
                'total_records': total_records,
                'exchanges': self.progress_data,
                'completeness': completeness_summary,
                'message': f"Processing {active_exchanges} exchange(s)..."
            }
            self.status_file.write_text(json.dumps(status_data, indent=2))
            
            # Also write dashboard-compatible status file
            dashboard_status = {
                'running': True,
                'progress': overall_progress,
                'message': f"Unified backfill: {overall_progress}% complete ({total_records:,} records)",
                'completed': False
            }
            self.dashboard_status_file.write_text(json.dumps(dashboard_status, indent=2))
    
    def backfill_exchange(self, exchange_name: str) -> Tuple[str, int, bool]:
        """
        Backfill historical data for a single exchange.
        
        Returns:
            Tuple of (exchange_name, records_count, success)
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
            
            # Create progress callback for this exchange
            def progress_callback(symbols_processed, total_symbols, progress, message):
                # Track records fetched (estimate based on progress)
                records_estimate = int(symbols_processed * 24 * self.days / 8)  # Rough estimate
                self.update_progress(exchange_name, symbols_processed, total_symbols, 
                                   records_estimate, "processing")
            
            # Fetch historical data with unified dates if sync is enabled
            start_time = time.time()
            
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
                return (exchange_name, 0, False)
            
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
            
            # Log completeness summary
            if completeness_data:
                complete_symbols = sum(1 for s in completeness_data.values() if s['completeness'] >= 95)
                logger.info(f"{exchange_name.upper()}: {complete_symbols}/{len(completeness_data)} symbols have ≥95% completeness")
            
            logger.info(f"="*60)
            
            # Upload to database
            if not self.dry_run and self.db_manager:
                logger.info(f"Uploading {exchange_name} data to database...")
                upload_start = time.time()
                
                success = self.db_manager.upload_historical_funding_rates(historical_df)
                
                if success:
                    upload_time = time.time() - upload_start
                    logger.info(f"{exchange_name}: Uploaded in {upload_time:.2f}s")
                    self.update_progress(exchange_name, 
                                       historical_df['symbol'].nunique(),
                                       historical_df['symbol'].nunique(),
                                       len(historical_df), "completed",
                                       completeness_data=completeness_data)
                    return (exchange_name, len(historical_df), True)
                else:
                    logger.error(f"Failed to upload {exchange_name} data")
                    self.update_progress(exchange_name, 0, 0, 0, "upload_failed")
                    return (exchange_name, 0, False)
            else:
                # Dry run - just return stats
                self.update_progress(exchange_name,
                                   historical_df['symbol'].nunique(),
                                   historical_df['symbol'].nunique(),
                                   len(historical_df), "completed_dry_run",
                                   completeness_data=completeness_data)
                return (exchange_name, len(historical_df), True)
                
        except Exception as e:
            logger.error(f"Error backfilling {exchange_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.update_progress(exchange_name, 0, 0, 0, "error")
            return (exchange_name, 0, False)
    
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
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.backfill_exchange, exchange): exchange 
                for exchange in exchanges
            }
            
            # Process results as they complete
            for future in as_completed(futures):
                exchange_name, records, success = future.result()
                results.append({
                    'exchange': exchange_name,
                    'records': records,
                    'success': success
                })
                
                if not success:
                    all_success = False
                total_records += records
        
        # Final summary
        logger.info("="*60)
        logger.info("BACKFILL SUMMARY")
        logger.info("="*60)
        for result in results:
            status = "✓" if result['success'] else "✗"
            logger.info(f"{status} {result['exchange']}: {result['records']} records")
        logger.info(f"Total records: {total_records}")
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
        results = []
        
        for exchange in exchanges:
            exchange_name, records, success = self.backfill_exchange(exchange)
            results.append({
                'exchange': exchange_name,
                'records': records,
                'success': success
            })
            
            if not success:
                all_success = False
            total_records += records
        
        # Final summary
        logger.info("="*60)
        logger.info("BACKFILL SUMMARY")
        logger.info("="*60)
        for result in results:
            status = "✓" if result['success'] else "✗"
            logger.info(f"{status} {result['exchange']}: {result['records']} records")
        logger.info(f"Total records: {total_records}")
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
        default=2,
        help='Maximum parallel workers (default: 2)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not upload to database'
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
    logger.info("="*60)
    
    # Create backfill coordinator
    backfill = UnifiedBackfill(
        days=args.days,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    # Initialize
    if not backfill.initialize():
        logger.error("Failed to initialize backfill")
        sys.exit(1)
    
    try:
        # Run backfill
        start_time = time.time()
        
        if args.parallel:
            success = backfill.run_parallel(exchanges, args.max_workers)
        else:
            success = backfill.run_sequential(exchanges)
        
        total_time = time.time() - start_time
        
        # Final status
        logger.info(f"Total backfill time: {total_time:.2f} seconds")
        
        if success:
            logger.info("="*60)
            logger.info("UNIFIED BACKFILL COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            
            # Write final status
            final_status = {
                'running': False,
                'overall_progress': 100,
                'exchanges': backfill.progress_data,
                'message': "Backfill completed successfully",
                'completed': True,
                'total_time': total_time
            }
            backfill.status_file.write_text(json.dumps(final_status, indent=2))
        else:
            logger.error("="*60)
            logger.error("UNIFIED BACKFILL COMPLETED WITH ERRORS")
            logger.error("="*60)
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        backfill.cleanup()


if __name__ == "__main__":
    main()