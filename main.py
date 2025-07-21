"""
Main Exchange Data System
========================
This is the main entry point for the modular exchange data system.
Non-coders can easily modify settings in config/settings.py without touching this code.
"""

import time
import sys
import os

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


def main():
    """
    Main function to run the exchange data system.
    """
    # Create and run the system
    system = ExchangeDataSystem()
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