"""
Exchange Data Collector
=======================
Real-time funding rate collection from cryptocurrency exchanges.
Configuration can be modified in config/settings.py without touching this code.
"""

import time
import sys
import os
import argparse
import signal
import threading
from datetime import datetime, timezone

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    EXCHANGES, API_DELAY, ENABLE_CONSOLE_DISPLAY, DEBUG_MODE
)
from config.validator import validate_and_exit_on_error
from exchanges.exchange_factory import ExchangeFactory
from data_processing.data_processor import DataProcessor
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger, log_execution_time
from utils.health_tracker import get_health_report
from utils.health_check import print_health_status
from utils.contract_metadata_manager import ContractMetadataManager
from utils.backfill_completeness import BackfillCompletenessValidator
from utils.zscore_calculator import ZScoreCalculator
from utils.redis_cache import RedisCache


class ExchangeDataSystem:
    """
    Main orchestrator for the exchange data system.
    Coordinates all modules and provides a simple interface.
    """
    
    def __init__(self):
        """
        Initialize the exchange data system.
        """
        # Validate configuration first
        import config.settings as settings
        validate_and_exit_on_error(settings)
        
        self.logger = setup_logger("main")
        self.exchange_factory = ExchangeFactory(EXCHANGES)
        self.db_manager = PostgresManager()
        self.metadata_manager = ContractMetadataManager(self.db_manager.connection)
        self.completeness_validator = BackfillCompletenessValidator()
        self.last_completeness_check = None
        self.data_processor = None
        self.unified_data = None

        # Initialize Redis cache for invalidation
        self.cache = RedisCache()
        self.cache_invalidation_enabled = True  # Can be disabled if needed
        
        # Loop control
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Statistics for loop mode
        self.loop_stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'start_time': None,
            'last_run_time': None
        }
    
    @log_execution_time
    def run(self):
        """
        Main method to run the entire system.
        """
        print("="*60)
        print("MODULAR EXCHANGE DATA SYSTEM")
        print("="*60)
        
        try:
            # Step 1: Test database connection
            self._test_database_connection()
            
            # Step 2: Fetch data from all exchanges
            self._fetch_exchange_data()
            
            # Step 3: Process and display data
            self._process_and_display_data()
            
            # Step 4: Upload to database
            self._upload_to_database()

            # Step 5: Calculate and update Z-scores
            self._update_zscore_statistics()

            # Step 6: Invalidate cache after database updates
            self._invalidate_cache()

            # Step 7: Sync contract metadata (NEW)
            self._sync_contract_metadata()

            # Step 8: Cleanup stale data from inactive contracts
            self._cleanup_stale_data()

            # Step 9: Cleanup old historical funding rate data
            self._cleanup_historical_data()

            # Step 10: Check data completeness (hourly)
            self._check_data_completeness()
            
            print("\n" + "="*60)
            print("OK SYSTEM COMPLETED SUCCESSFULLY")
            print("="*60)
            
            # Show system health status
            print_health_status()
            
        except Exception as e:
            self.logger.error(f"System failed: {e}")
            print(f"\nX SYSTEM FAILED: {e}")
            return False
        
        return True
    
    def _test_database_connection(self):
        """Test the database connection."""
        print("\n1. Testing database connection...")
        if not self.db_manager.test_connection():
            print("! Database connection failed, but continuing...")
        else:
            print("OK Database connection successful")
    
    def _fetch_exchange_data(self):
        """Fetch data from all enabled exchanges."""
        print("\n2. Fetching exchange data...")
        
        # Show which exchanges are enabled
        enabled_exchanges = self.exchange_factory.get_enabled_exchanges()
        print(f"Enabled exchanges: {[ex.name for ex in enabled_exchanges]}")
        
        # Process all exchanges
        self.unified_data = self.exchange_factory.process_all_exchanges()
        
        if self.unified_data.empty:
            print("! No data retrieved from any exchange")
        else:
            print(f"OK Retrieved {len(self.unified_data)} total contracts")
    
    def _process_and_display_data(self):
        """Process and display the unified data."""
        print("\n3. Processing and displaying data...")
        
        if self.unified_data is None or self.unified_data.empty:
            print("! No data to process")
            return
        
        # Create data processor
        self.data_processor = DataProcessor(self.unified_data)
        
        # Display summary
        self.data_processor.display_summary()
        
        # Display table if enabled
        if ENABLE_CONSOLE_DISPLAY:
            self.data_processor.display_table()
    
    def _upload_to_database(self):
        """Upload data to Supabase."""
        print("\n4. Uploading to database...")
        
        if self.unified_data is not None and not self.unified_data.empty:
            success = self.db_manager.upload_data(self.unified_data)
            if success:
                print("OK Data uploaded to database successfully")
            else:
                print("! Database upload failed")
    
    def _update_zscore_statistics(self):
        """Calculate and update Z-scores and percentiles for all contracts."""
        print("\n5. Calculating Z-scores and percentiles...")
        
        try:
            # Create Z-score calculator instance with database connection
            zscore_calc = ZScoreCalculator(self.db_manager.connection)
            
            # Update statistics
            result = zscore_calc.process_all_contracts()
            
            if result:
                print(f"[OK] Z-scores updated for {result.get('contracts_updated', 0)} contracts")
                if result.get('extreme_values', 0) > 0:
                    print(f"  ! {result.get('extreme_values', 0)} contracts with |Z| > 2.0")
            else:
                print("[OK] Z-scores calculation completed")
                
        except Exception as e:
            self.logger.error(f"Z-score calculation failed: {e}")
            print(f"! Z-score calculation failed: {e}")
    
    def _sync_contract_metadata(self):
        """Synchronize contract metadata table with current data."""
        print("\n7. Syncing contract metadata...")
        
        try:
            sync_stats = self.metadata_manager.sync_with_exchange_data()
            
            if 'error' in sync_stats:
                print(f"! Metadata sync failed: {sync_stats['error']}")
            else:
                if sync_stats['new_listings'] > 0:
                    print(f"+ Added {sync_stats['new_listings']} new contract(s)")
                if sync_stats['delistings'] > 0:
                    print(f"- Marked {sync_stats['delistings']} contract(s) as delisted")
                if sync_stats['updates'] > 0:
                    print(f"~ Updated {sync_stats['updates']} contract(s)")
                
                if sync_stats['new_listings'] == 0 and sync_stats['delistings'] == 0 and sync_stats['updates'] == 0:
                    print("OK Metadata is up to date")
                else:
                    print(f"OK Metadata sync completed")
                    
        except Exception as e:
            self.logger.error(f"Metadata sync error: {e}")
            print(f"! Metadata sync error: {e}")
    
    def _cleanup_stale_data(self):
        """Remove stale data for inactive contracts from exchange_data table."""
        from config.settings import AUTO_CLEANUP_DELISTED, STALE_DATA_REMOVAL_HOURS

        if not AUTO_CLEANUP_DELISTED:
            return  # Skip if cleanup is disabled

        print("\n8. Cleaning up stale data...")

        try:
            # Get configuration from settings
            stale_threshold_hours = STALE_DATA_REMOVAL_HOURS

            # Query to remove stale data for inactive contracts
            query = """
            DELETE FROM exchange_data ed
            USING contract_metadata cm
            WHERE ed.exchange = cm.exchange
            AND ed.symbol = cm.symbol
            AND cm.is_active = false
            AND ed.last_updated < NOW() - INTERVAL '%s hours'
            RETURNING ed.exchange, ed.symbol
            """

            cursor = self.db_manager.cursor
            cursor.execute(query, (stale_threshold_hours,))
            removed = cursor.fetchall()
            self.db_manager.connection.commit()

            if removed:
                print(f"- Removed {len(removed)} stale entries from inactive contracts")
                for exchange, symbol in removed[:5]:  # Show first 5
                    print(f"  Removed: {exchange} - {symbol}")
                if len(removed) > 5:
                    print(f"  ... and {len(removed) - 5} more")

            # Also remove orphaned entries (not in metadata at all)
            orphan_query = """
            DELETE FROM exchange_data ed
            WHERE NOT EXISTS (
                SELECT 1 FROM contract_metadata cm
                WHERE cm.exchange = ed.exchange AND cm.symbol = ed.symbol
            )
            AND ed.last_updated < NOW() - INTERVAL '%s hours'
            RETURNING ed.exchange, ed.symbol
            """

            cursor.execute(orphan_query, (stale_threshold_hours,))
            orphans = cursor.fetchall()
            self.db_manager.connection.commit()

            if orphans:
                print(f"- Removed {len(orphans)} orphaned entries")

            if not removed and not orphans:
                print("OK No stale data to clean up")
            else:
                total_cleaned = len(removed) + len(orphans)
                print(f"OK Cleaned up {total_cleaned} stale entries")

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            print(f"! Cleanup error: {e}")

    def _cleanup_historical_data(self):
        """Remove old historical funding rate data based on retention policy."""
        from config.settings import HISTORICAL_WINDOW_DAYS

        # Only run cleanup once per hour to avoid excessive deletions
        current_time = datetime.now(timezone.utc)
        if hasattr(self, 'last_historical_cleanup'):
            time_since_last = (current_time - self.last_historical_cleanup).total_seconds()
            if time_since_last < 3600:  # Less than 1 hour
                return

        print("\n9. Cleaning up old historical funding rate data...")

        try:
            # Use the configured retention period (default: 30 days)
            retention_days = HISTORICAL_WINDOW_DAYS

            # Call the new cleanup function
            deleted_count = self.db_manager.cleanup_historical_funding_rates(retention_days)

            if deleted_count == -1:
                print("! Historical data cleanup failed")
            elif deleted_count == 0:
                print(f"OK No historical data older than {retention_days} days to remove")
            else:
                print(f"OK Removed {deleted_count:,} historical records older than {retention_days} days")

            self.last_historical_cleanup = current_time

        except Exception as e:
            self.logger.error(f"Historical cleanup error: {e}")
            print(f"! Historical cleanup error: {e}")

    def _check_data_completeness(self, force: bool = False):
        """
        Check data completeness periodically and log warnings.

        DISABLED BY DEFAULT - This check is optional and can be enabled by setting
        ENABLE_COMPLETENESS_CHECK=True in settings. The default sample of 4 contracts
        is not statistically significant for a system tracking 2,275+ contracts.

        For comprehensive validation, use: python scripts/retry_incomplete_contracts.py
        """
        enable_check = getattr(self, 'enable_completeness_check', False)

        if not enable_check:
            return

        current_time = datetime.now(timezone.utc)

        if not force and self.last_completeness_check:
            time_since_last_check = (current_time - self.last_completeness_check).total_seconds()
            if time_since_last_check < 3600:
                return

        print("\n10. Checking data completeness...")

        try:
            incomplete_count = 0
            low_completeness = []

            sample_contracts = [
                ('binance', 'BTCUSDT'),
                ('binance', 'ETHUSDT'),
                ('kucoin', 'XBTUSDTM'),
                ('hyperliquid', 'BTC'),
            ]

            for exchange, symbol in sample_contracts:
                result = self.completeness_validator.validate_contract(exchange, symbol, days=30)
                completeness = result.get('completeness_percentage', 0)

                if completeness < 95:
                    incomplete_count += 1
                    low_completeness.append(f"{exchange}:{symbol} ({completeness:.1f}%)")

            if incomplete_count > 0:
                self.logger.warning(f"Data completeness warning: {incomplete_count} contracts below 95% threshold")
                print(f"! Data completeness warning: {', '.join(low_completeness)}")
                print(f"  Run 'python scripts/retry_incomplete_contracts.py' to fix gaps")
            else:
                print("OK Data completeness check passed")

            self.last_completeness_check = current_time

        except Exception as e:
            self.logger.error(f"Completeness check error: {e}")
            print(f"! Completeness check error: {e}")
    
    def get_statistics(self) -> dict:
        """
        Get comprehensive statistics about the system.
        
        Returns:
            Dictionary with system statistics
        """
        stats = {
            'enabled_exchanges': self.exchange_factory.get_exchange_status(),
            'total_contracts': len(self.unified_data) if self.unified_data is not None else 0,
        }
        
        if self.data_processor:
            stats.update(self.data_processor.get_statistics())
            stats['data_quality_score'] = self.data_processor.quality_score
        
        return stats
    
    def get_exchange_data(self, exchange_name: str):
        """
        Get data for a specific exchange.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            DataFrame for the specified exchange
        """
        if self.data_processor:
            return self.data_processor.get_exchange_data(exchange_name)
        return None
    
    def get_top_funding_rates(self, limit: int = 10):
        """
        Get top funding rates.
        
        Args:
            limit: Number of results to return
            
        Returns:
            DataFrame with top funding rates
        """
        if self.data_processor:
            return self.data_processor.get_top_funding_rates(limit)
        return None

    def _invalidate_cache(self):
        """
        Invalidate Redis cache after database updates to ensure fresh data.
        This forces API endpoints to fetch new data on the next request.
        """
        if not self.cache_invalidation_enabled:
            return

        try:
            # Check if Redis is available
            if self.cache.is_available():
                # Clear all cached data
                self.cache.clear()
                self.logger.info("Cache invalidated after database update")
                print("OK Cache invalidated to ensure fresh data")
            else:
                self.logger.debug("Redis not available, using in-memory cache")
        except Exception as e:
            self.logger.warning(f"Cache invalidation failed: {e}")
            # Non-critical error, continue execution

    def run_loop(self, interval: int = 300, duration: int = None, quiet: bool = False):
        """
        Run the system in a continuous loop.
        
        Args:
            interval: Seconds between runs (default: 300 = 5 minutes)
            duration: Total duration in seconds (None = run indefinitely)
            quiet: If True, suppress console display during loops
        """
        self.running = True
        self.loop_stats['start_time'] = datetime.now(timezone.utc)
        start_timestamp = time.time()
        
        print(f"\n{'='*60}")
        print("STARTING CONTINUOUS DATA COLLECTION")
        print(f"{'='*60}")
        print(f"Interval: {interval} seconds")
        print(f"Duration: {'Indefinite' if duration is None else f'{duration} seconds'}")
        print(f"Display mode: {'Quiet' if quiet else 'Full'}")
        print("Press Ctrl+C to stop gracefully")
        print(f"{'='*60}\n")
        
        # Temporarily disable console display if quiet mode
        original_display_setting = ENABLE_CONSOLE_DISPLAY
        if quiet:
            import config.settings
            config.settings.ENABLE_CONSOLE_DISPLAY = False
        
        try:
            while self.running and not self.shutdown_event.is_set():
                # Check duration limit
                if duration and (time.time() - start_timestamp) >= duration:
                    print(f"\n! Duration limit reached ({duration}s)")
                    break
                
                run_start = time.time()
                self.loop_stats['total_runs'] += 1
                
                # Show timestamp for this run
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                print(f"\n[{current_time}] Starting run #{self.loop_stats['total_runs']}")
                
                # Run the system
                success = self.run()
                
                if success:
                    self.loop_stats['successful_runs'] += 1
                else:
                    self.loop_stats['failed_runs'] += 1
                
                self.loop_stats['last_run_time'] = datetime.now(timezone.utc)
                
                # Show brief stats
                self._print_loop_progress()
                
                # Calculate wait time
                run_duration = time.time() - run_start
                wait_time = max(0, interval - run_duration)
                
                if wait_time > 0 and self.running:
                    print(f"\n  Next run in {wait_time:.0f} seconds...")
                    self.shutdown_event.wait(wait_time)
                    
        except KeyboardInterrupt:
            print("\n! Shutdown signal received...")
        finally:
            # Restore original display setting
            if quiet:
                config.settings.ENABLE_CONSOLE_DISPLAY = original_display_setting
            
            self.running = False
            self._print_loop_summary()
    
    def stop_loop(self):
        """Stop the continuous loop gracefully."""
        self.running = False
        self.shutdown_event.set()
    
    def _print_loop_progress(self):
        """Print progress statistics for loop mode."""
        if not self.loop_stats['start_time']:
            return
        
        runtime = datetime.now(timezone.utc) - self.loop_stats['start_time']
        runtime_minutes = runtime.total_seconds() / 60
        
        print(f"\n--- Loop Progress ---")
        print(f"  Runtime: {runtime_minutes:.1f} minutes")
        print(f"  Total runs: {self.loop_stats['total_runs']}")
        print(f"  Successful: {self.loop_stats['successful_runs']}")
        print(f"  Failed: {self.loop_stats['failed_runs']}")
        
        if self.loop_stats['total_runs'] > 0:
            success_rate = (self.loop_stats['successful_runs'] / self.loop_stats['total_runs']) * 100
            print(f"  Success rate: {success_rate:.1f}%")
    
    def _print_loop_summary(self):
        """Print final summary for loop mode."""
        print(f"\n{'='*60}")
        print("LOOP SUMMARY")
        print(f"{'='*60}")
        
        if self.loop_stats['start_time']:
            runtime = datetime.now(timezone.utc) - self.loop_stats['start_time']
            print(f"Total runtime: {runtime}")
        
        print(f"Total runs: {self.loop_stats['total_runs']}")
        print(f"Successful runs: {self.loop_stats['successful_runs']}")
        print(f"Failed runs: {self.loop_stats['failed_runs']}")
        
        if self.loop_stats['total_runs'] > 0:
            success_rate = (self.loop_stats['successful_runs'] / self.loop_stats['total_runs']) * 100
            print(f"Overall success rate: {success_rate:.1f}%")
        
        print(f"{'='*60}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Exchange Data System - Fetch and process cryptocurrency exchange data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run (default)
  python main.py
  
  # Continuous mode with 5-minute intervals
  python main.py --loop
  
  # Loop with custom interval (60 seconds)
  python main.py --loop --interval 60
  
  # Loop for specific duration (2 hours)
  python main.py --loop --duration 7200
  
  # Quiet mode (suppress detailed output)
  python main.py --loop --quiet
        """
    )
    
    parser.add_argument(
        '--loop', '-l',
        action='store_true',
        help='Run in continuous loop mode'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=300,
        help='Interval between runs in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        help='Total duration in seconds (runs indefinitely if not specified)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode - suppress console display during loops'
    )
    
    return parser.parse_args()


def setup_signal_handlers(system):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print("\n! Shutdown signal received. Stopping...")
        system.stop_loop()
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)


def main():
    """
    Main function to run the exchange data system.
    """
    args = parse_arguments()
    
    # Create the system
    system = ExchangeDataSystem()
    
    if args.loop:
        # Setup signal handlers for loop mode
        setup_signal_handlers(system)
        
        # Run in loop mode
        system.run_loop(
            interval=args.interval,
            duration=args.duration,
            quiet=args.quiet
        )
    else:
        # Single run mode
        success = system.run()
        
        if success:
            # Show final statistics
            stats = system.get_statistics()
            print(f"\nFinal Statistics:")
            print(f"  Total contracts: {stats.get('total_contracts', 0)}")
            print(f"  Data quality score: {stats.get('data_quality_score', 0):.1f}/100")
            print(f"  Enabled exchanges: {list(stats.get('enabled_exchanges', {}).keys())}")
        
        return success


if __name__ == "__main__":
    # Add delay between API calls
    if API_DELAY > 0:
        time.sleep(API_DELAY)
    
    # Run the system
    main() 