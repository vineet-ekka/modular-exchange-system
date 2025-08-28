#!/usr/bin/env python3
"""
Custom Hyperliquid Gap Filler
Specifically designed to fill the Aug 12-18 data gap
"""

import sys
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.postgres_manager import PostgresManager
from exchanges.hyperliquid_exchange import HyperliquidExchange
from utils.logger import setup_logger

logger = setup_logger("HyperliquidGapFiller")

def fetch_funding_history_direct(coin, start_time_ms, end_time_ms):
    """Fetch funding history directly from API."""
    url = 'https://api.hyperliquid.xyz/info'
    payload = {
        'type': 'fundingHistory',
        'coin': coin,
        'startTime': start_time_ms,
        'endTime': end_time_ms
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching {coin}: {e}")
    
    return []

def main():
    print("="*60)
    print("HYPERLIQUID GAP FILLER - CUSTOM IMPLEMENTATION")
    print("="*60)
    print(f"Target: Aug 12-18, 2025 data gap")
    print()
    
    # Initialize
    db_manager = PostgresManager()
    exchange = HyperliquidExchange()
    
    # Get list of all Hyperliquid coins
    print("Fetching list of active coins...")
    coins = exchange.get_active_coins()
    print(f"Found {len(coins)} active coins")
    
    # Define gap period
    start_time = datetime(2025, 8, 12, 0, 0)
    end_time = datetime(2025, 8, 19, 0, 0)  # Include one extra day
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    print(f"Fetching data from {start_time} to {end_time}")
    print()
    
    # Collect all data
    all_records = []
    successful_coins = 0
    failed_coins = []
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(coins), batch_size):
        batch = coins[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(coins)-1)//batch_size + 1}")
        
        for coin in batch:
            try:
                # Fetch funding history
                data = fetch_funding_history_direct(coin, start_ms, end_ms)
                
                if data:
                    # Convert to DataFrame format
                    for record in data:
                        all_records.append({
                            'exchange': 'Hyperliquid',
                            'symbol': f'{coin}USDC',
                            'base_asset': coin,
                            'quote_asset': 'USDC',
                            'funding_rate': float(record.get('fundingRate', 0)),
                            'funding_time': datetime.fromtimestamp(record['time'] / 1000),
                            'funding_interval_hours': 1,
                            'mark_price': None,  # Not provided in this endpoint
                        })
                    
                    successful_coins += 1
                    print(f"  {coin}: {len(data)} records fetched")
                else:
                    failed_coins.append(coin)
                    print(f"  {coin}: No data")
                
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                failed_coins.append(coin)
                print(f"  {coin}: Error - {e}")
        
        # Pause between batches
        if i + batch_size < len(coins):
            print("  Pausing between batches...")
            time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"Collection complete!")
    print(f"Successful: {successful_coins} coins")
    print(f"Failed: {len(failed_coins)} coins")
    print(f"Total records collected: {len(all_records)}")
    
    if all_records:
        # Create DataFrame
        df = pd.DataFrame(all_records)
        
        # Filter to only the gap period (Aug 12-18)
        df['funding_time'] = pd.to_datetime(df['funding_time'])
        gap_df = df[
            (df['funding_time'] >= datetime(2025, 8, 12, 0, 0)) &
            (df['funding_time'] <= datetime(2025, 8, 18, 23, 59))
        ]
        
        print(f"\nFiltered to gap period: {len(gap_df)} records")
        
        # Upload to database
        print("Uploading to database...")
        success = db_manager.upload_historical_funding_rates(gap_df)
        
        if success:
            print(f"\nSUCCESS! Filled Hyperliquid gap with {len(gap_df)} records")
            
            # Show summary statistics
            print("\nSummary:")
            print(f"  Date range: {gap_df['funding_time'].min()} to {gap_df['funding_time'].max()}")
            print(f"  Unique symbols: {gap_df['symbol'].nunique()}")
            print(f"  Average funding rate: {gap_df['funding_rate'].mean():.8f}")
        else:
            print("\nERROR: Failed to upload to database")
    else:
        print("\nNo data collected - unable to fill gap")
    
    if failed_coins:
        print(f"\nFailed coins ({len(failed_coins)}):")
        print(", ".join(failed_coins[:20]))

if __name__ == "__main__":
    main()