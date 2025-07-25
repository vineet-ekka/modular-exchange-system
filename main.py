"""
Main Exchange Data System
========================
This is the main entry point for the modular exchange data system.
Non-coders can easily modify settings in config/settings.py without touching this code.
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
from database.supabase_manager import SupabaseManager
from utils.logger import setup_logger, log_execution_time
from utils.health_tracker import get_health_report
from utils.health_check import print_health_status


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
        self.supabase_manager = SupabaseManager()
        self.data_processor = None
        self.unified_data = None
        
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
            
            # Step 4: Export data
            self._export_data()
            
            # Step 5: Upload to database
            self._upload_to_database()
            
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
        if not self.supabase_manager.test_connection():
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
    
    def _export_data(self):
        """Export data to CSV."""
        print("\n4. Exporting data...")
        
        if self.data_processor:
            exported_file = self.data_processor.export_to_csv()
            if exported_file:
                print(f"OK Data exported to: {exported_file}")
    
    def _upload_to_database(self):
        """Upload data to Supabase."""
        print("\n5. Uploading to database...")
        
        if self.unified_data is not None and not self.unified_data.empty:
            success = self.supabase_manager.upload_data(self.unified_data)
            if success:
                print("OK Data uploaded to database successfully")
            else:
                print("! Database upload failed")
    
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