#!/usr/bin/env python3
"""Quick data update script - fetch once and exit"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import EXCHANGES
from exchanges.exchange_factory import ExchangeFactory
from database.postgres_manager import PostgresManager
from data_processing.data_processor import DataProcessor

def quick_update():
    """Perform a single data collection cycle."""
    print("Starting quick data update...")
    
    # Initialize components
    exchange_factory = ExchangeFactory(EXCHANGES)
    db_manager = PostgresManager()
    
    # Fetch data from all exchanges
    print("Fetching from exchanges...")
    unified_data = exchange_factory.process_all_exchanges()
    
    if unified_data.empty:
        print("No data retrieved")
        return False
    
    print(f"Retrieved {len(unified_data)} contracts")
    
    # Process data
    data_processor = DataProcessor(unified_data)
    data_processor.display_summary()
    
    # Upload to database
    print("Uploading to database...")
    success = db_manager.upload_data(unified_data)
    
    if success:
        print("Data update successful!")
        return True
    else:
        print("Upload failed")
        return False

if __name__ == "__main__":
    try:
        success = quick_update()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)