#!/usr/bin/env python3
"""
Historical Data Collection Entry Point
======================================
Continuously collects exchange data at configured intervals
and stores it in the historical database table for time-series analysis.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Optional
import pandas as pd

from config.validator import validate_configuration
from config import settings
from utils.continuous_fetcher import ContinuousFetcher
from utils.health_check import print_health_status
from database.supabase_manager import SupabaseManager


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Continuously collect exchange data for historical analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (5 minute intervals)
  python main_historical.py
  
  # Run with custom interval (60 seconds)
  python main_historical.py --interval 60
  
  # Run for a specific duration (2 hours)
  python main_historical.py --duration 7200
  
  # Run with verbose output
  python main_historical.py --verbose
  
  # Check historical data summary
  python main_historical.py --summary
        """
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=settings.HISTORICAL_FETCH_INTERVAL,
        help=f'Fetch interval in seconds (default: {settings.HISTORICAL_FETCH_INTERVAL})'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        help='Run duration in seconds (runs indefinitely if not specified)'
    )
    
    parser.add_argument(
        '--summary', '-s',
        action='store_true',
        help='Show historical data summary and exit'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Disable database upload (dry run)'
    )
    
    return parser.parse_args()


def show_historical_summary():
    """Display summary of historical data in database."""
    print("\n============================================================")
    print("HISTORICAL DATA SUMMARY")
    print("============================================================")
    
    try:
        supabase = SupabaseManager()
        summary = supabase.get_historical_summary()
        
        if summary:
            print(f"Table: {summary.get('table_name', 'N/A')}")
            print(f"Total records: {summary.get('total_records', 0):,}")
            print(f"Oldest record: {summary.get('oldest_record', 'N/A')}")
            print(f"Newest record: {summary.get('newest_record', 'N/A')}")
            print(f"Unique exchanges: {summary.get('unique_exchanges', 0)}")
            print(f"Unique symbols: {summary.get('unique_symbols', 0)}")
        else:
            print("! No historical data found or unable to fetch summary")
            
    except Exception as e:
        print(f"X Error fetching historical summary: {e}")
    
    print("============================================================")


def data_collection_callback(data: pd.DataFrame, stats: dict):
    """
    Callback function called after each successful data collection.
    
    Args:
        data: Collected data DataFrame
        stats: Collection statistics
    """
    # Display top APR contracts
    if not data.empty and 'apr' in data.columns:
        top_apr = data.nlargest(5, 'apr')[['exchange', 'symbol', 'funding_rate', 'apr']]
        if not top_apr.empty:
            print("\nTop 5 APR contracts:")
            for _, row in top_apr.iterrows():
                print(f"  {row['exchange']:10} {row['symbol']:15} "
                      f"Rate: {row['funding_rate']:8.6f} APR: {row['apr']:6.2f}%")


def main():
    """Main entry point for historical data collection."""
    args = parse_arguments()
    
    # Show summary and exit if requested
    if args.summary:
        show_historical_summary()
        return 0
    
    # Configuration validation
    print("Validating configuration...")
    try:
        validate_configuration(settings)
        print("OK Configuration validation passed")
    except Exception as e:
        print(f"X Configuration error: {e}")
        return 1
    
    # Check if historical collection is enabled
    if not settings.ENABLE_HISTORICAL_COLLECTION:
        print("! Historical data collection is disabled in settings")
        print("  Set ENABLE_HISTORICAL_COLLECTION = True to enable")
        return 1
    
    # Override database upload if --no-upload specified
    if args.no_upload:
        settings.ENABLE_DATABASE_UPLOAD = False
        print("! Database upload disabled (dry run mode)")
    
    # Show initial configuration
    print("\n============================================================")
    print("HISTORICAL DATA COLLECTION SYSTEM")
    print("============================================================")
    print(f"Fetch interval: {args.interval} seconds")
    print(f"Max duration: {'Indefinite' if not args.duration else f'{args.duration} seconds'}")
    print(f"Database upload: {'Enabled' if settings.ENABLE_DATABASE_UPLOAD else 'Disabled'}")
    print(f"CSV export: {'Enabled' if settings.ENABLE_CSV_EXPORT else 'Disabled'}")
    print(f"Historical table: {settings.HISTORICAL_TABLE_NAME}")
    print(f"CSV filename prefix: {settings.HISTORICAL_CSV_FILENAME}")
    print(f"Enabled exchanges: {[k for k, v in settings.EXCHANGES.items() if v]}")
    print("============================================================\n")
    
    # Test database connection
    if settings.ENABLE_DATABASE_UPLOAD:
        print("Testing database connection...")
        supabase = SupabaseManager()
        if not supabase.test_connection():
            print("X Failed to connect to database. Please check your credentials.")
            return 1
    
    # Show initial health status
    print("\nInitial system health:")
    print_health_status()
    
    # Create continuous fetcher
    fetcher = ContinuousFetcher(
        fetch_interval=args.interval,
        max_retries=settings.HISTORICAL_MAX_RETRIES,
        base_backoff=settings.HISTORICAL_BASE_BACKOFF
    )
    
    # Set up duration limit if specified
    start_time = time.time()
    
    try:
        # Start continuous collection with duration limit
        if args.verbose:
            # Use callback for verbose output
            fetcher.start(callback=data_collection_callback, duration=args.duration)
        else:
            fetcher.start(duration=args.duration)
    
    except KeyboardInterrupt:
        # Handled by signal handler in ContinuousFetcher
        pass
    
    except Exception as e:
        print(f"\nX Unexpected error: {e}")
        fetcher.stop()
        return 1
    
    # Show final health status
    print("\nFinal system health:")
    print_health_status()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())