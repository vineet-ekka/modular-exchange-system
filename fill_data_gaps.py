#!/usr/bin/env python3
"""
Targeted Gap Filler for Historical Data
Fills specific gaps in Hyperliquid and Backpack data
"""

import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
from exchanges.hyperliquid_exchange import HyperliquidExchange
from exchanges.backpack_exchange import BackpackExchange
from database.postgres_manager import PostgresManager
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger("GapFiller")

def fill_hyperliquid_gap():
    """Fill the Aug 12-18 gap in Hyperliquid data."""
    print("="*60)
    print("FILLING HYPERLIQUID GAP (Aug 12-18, 2025)")
    print("="*60)
    
    exchange = HyperliquidExchange()
    db_manager = PostgresManager()
    
    # The gap is from Aug 12 to Aug 18
    # We need to fetch from Aug 11 to Aug 19 to ensure complete coverage
    start_date = datetime(2025, 8, 11, 0, 0)
    end_date = datetime(2025, 8, 19, 23, 59)
    
    print(f"Target period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Use the existing backfill method
    try:
        print("Fetching historical data for gap period...")
        
        # Calculate days for the gap
        days = (end_date - start_date).days + 1
        
        # Create a custom progress callback
        def progress_callback(symbols_processed, total_symbols, progress, message):
            if symbols_processed % 10 == 0:
                print(f"  Progress: {symbols_processed}/{total_symbols} symbols ({progress:.1f}%)")
        
        # Fetch historical data for the gap period
        historical_df = exchange.fetch_all_perpetuals_historical(
            days=days,
            batch_size=5,
            progress_callback=progress_callback,
            end_time=end_date
        )
        
        if not historical_df.empty:
            print(f"\nFetched {len(historical_df)} records for gap period")
            
            # Filter to only the gap period
            historical_df['funding_time'] = pd.to_datetime(historical_df['funding_time'])
            gap_df = historical_df[
                (historical_df['funding_time'] >= datetime(2025, 8, 12, 0, 0)) &
                (historical_df['funding_time'] <= datetime(2025, 8, 18, 23, 59))
            ]
            
            print(f"Filtered to {len(gap_df)} records within gap")
            
            # Upload to database
            print("Uploading to database...")
            success = db_manager.upload_historical_funding_rates(gap_df)
            
            if success:
                print(f"OK: Successfully filled Hyperliquid gap with {len(gap_df)} records")
                return len(gap_df)
            else:
                print("ERROR: Failed to upload gap data")
                return 0
        else:
            print("No data fetched for gap period")
            return 0
            
    except Exception as e:
        print(f"Error filling Hyperliquid gap: {e}")
        import traceback
        traceback.print_exc()
        return 0

def fill_backpack_gaps():
    """Fill missing 1-hour interval data for Backpack."""
    print("\n" + "="*60)
    print("FILLING BACKPACK DATA GAPS")
    print("="*60)
    
    exchange = BackpackExchange()
    db_manager = PostgresManager()
    
    # Fetch last 30 days with more aggressive retry
    print("Fetching complete 30-day history for Backpack...")
    
    try:
        historical_df = exchange.fetch_all_perpetuals_historical(
            days=30,
            batch_size=3  # Smaller batches for better success rate
        )
        
        if not historical_df.empty:
            print(f"Fetched {len(historical_df)} total records")
            
            # Upload all data (will use UPSERT to avoid duplicates)
            success = db_manager.upload_historical_funding_rates(historical_df)
            
            if success:
                print(f"OK: Successfully updated Backpack data with {len(historical_df)} records")
                return len(historical_df)
            else:
                print("ERROR: Failed to upload Backpack data")
                return 0
        else:
            print("No data fetched for Backpack")
            return 0
            
    except Exception as e:
        print(f"Error filling Backpack gaps: {e}")
        return 0

if __name__ == "__main__":
    print("Starting targeted gap filling...")
    print()
    
    # Fill Hyperliquid gap
    hl_records = fill_hyperliquid_gap()
    
    # Fill Backpack gaps
    bp_records = fill_backpack_gaps()
    
    print("\n" + "="*60)
    print("GAP FILLING COMPLETE")
    print("="*60)
    print(f"Hyperliquid: {hl_records:,} records added")
    print(f"Backpack: {bp_records:,} records updated")
    print(f"Total: {hl_records + bp_records:,} records")
