#!/usr/bin/env python3
"""
Simulate unified backfill date synchronization for different day ranges.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta, timezone
from scripts.unified_historical_backfill import UnifiedBackfill

def simulate_backfill_dates(days_list=[1, 7, 30]):
    """Simulate the date calculation for different day ranges."""
    
    print("="*60)
    print("UNIFIED BACKFILL DATE SIMULATION")
    print("="*60)
    
    for days in days_list:
        print(f"\n{'='*60}")
        print(f"Simulating backfill with {days} day(s)")
        print(f"{'='*60}")
        
        # Create UnifiedBackfill instance with dry_run to avoid DB operations
        backfill = UnifiedBackfill(
            days=days,
            batch_size=10,
            dry_run=True
        )
        
        # Check if dates were calculated
        if backfill.sync_enabled:
            print(f"\nSynchronized dates ENABLED")
            print(f"Align to midnight: {backfill.align_to_midnight}")
            
            if backfill.unified_start_time and backfill.unified_end_time:
                print(f"\nUnified Date Range:")
                print(f"  Start: {backfill.unified_start_time.isoformat()}")
                print(f"  End:   {backfill.unified_end_time.isoformat()}")
                
                # Calculate actual duration
                duration = backfill.unified_end_time - backfill.unified_start_time
                print(f"\nDuration:")
                print(f"  Days: {duration.days}")
                print(f"  Hours: {duration.total_seconds() / 3600:.0f}")
                
                # Show what each exchange would receive
                print(f"\nAll exchanges will receive these exact parameters:")
                print(f"  start_time = {backfill.unified_start_time.isoformat()}")
                print(f"  end_time = {backfill.unified_end_time.isoformat()}")
            else:
                print("ERROR: Unified dates were not calculated!")
        else:
            print("Synchronized dates DISABLED - each exchange calculates independently")

def compare_with_without_sync():
    """Compare behavior with and without synchronization."""
    print("\n" + "="*60)
    print("COMPARING WITH AND WITHOUT SYNCHRONIZATION")
    print("="*60)
    
    # Test with sync enabled
    print("\n1. WITH SYNCHRONIZATION (Default)")
    print("-" * 40)
    backfill_sync = UnifiedBackfill(days=7, dry_run=True, sync_enabled=True, align_to_midnight=True)
    
    if backfill_sync.unified_start_time:
        print(f"All exchanges use: {backfill_sync.unified_start_time.isoformat()} to {backfill_sync.unified_end_time.isoformat()}")
    
    # Test without sync
    print("\n2. WITHOUT SYNCHRONIZATION")
    print("-" * 40)
    backfill_no_sync = UnifiedBackfill(days=7, dry_run=True, sync_enabled=False)
    
    if not backfill_no_sync.unified_start_time:
        print("Each exchange calculates its own dates based on when it runs")
        print("Example: If exchanges run 1 minute apart:")
        
        now = datetime.now(timezone.utc)
        for i, exchange in enumerate(['Binance', 'KuCoin', 'Backpack', 'Hyperliquid']):
            exchange_time = now + timedelta(seconds=i*15)  # Simulate 15 seconds between each
            exchange_start = exchange_time - timedelta(days=7)
            print(f"  {exchange}: {exchange_start.isoformat()[:19]} to {exchange_time.isoformat()[:19]}")

if __name__ == "__main__":
    # Run simulations
    simulate_backfill_dates([1, 7, 30])
    compare_with_without_sync()
    
    print("\n" + "="*60)
    print("SIMULATION COMPLETE")
    print("="*60)