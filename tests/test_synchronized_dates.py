#!/usr/bin/env python3
"""
Test script to verify synchronized historical date ranges.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta, timezone
from config.settings import HISTORICAL_SYNC_ENABLED, HISTORICAL_ALIGN_TO_MIDNIGHT

def test_date_calculation():
    """Test the date calculation logic."""
    print("Testing Synchronized Date Calculation")
    print("=" * 50)
    
    # Settings check
    print(f"HISTORICAL_SYNC_ENABLED: {HISTORICAL_SYNC_ENABLED}")
    print(f"HISTORICAL_ALIGN_TO_MIDNIGHT: {HISTORICAL_ALIGN_TO_MIDNIGHT}")
    print()
    
    # Test multiple day ranges
    test_days = [1, 7, 30]
    
    for days in test_days:
        print(f"\nTesting {days} day(s) window:")
        print("-" * 40)
        
        end_time = datetime.now(timezone.utc)
        print(f"Current time: {end_time.isoformat()}")
        
        if HISTORICAL_ALIGN_TO_MIDNIGHT:
            aligned_end = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"Aligned to midnight: {aligned_end.isoformat()}")
        else:
            aligned_end = end_time
            print(f"Not aligned (using current time): {aligned_end.isoformat()}")
        
        start_time = aligned_end - timedelta(days=days)
        print(f"Start time ({days} days ago): {start_time.isoformat()}")
        
        # Show the date range that all exchanges would use
        print(f"\nDate range for {days}-day window:")
        print(f"  Start: {start_time.isoformat()}")
        print(f"  End: {aligned_end.isoformat()}")
        print(f"  Duration: {(aligned_end - start_time).days} days")
        print(f"  Total hours: {(aligned_end - start_time).total_seconds() / 3600:.0f} hours")
    
    return start_time, aligned_end

def verify_exchange_compatibility():
    """Verify that all exchanges can accept the date parameters."""
    print("\nVerifying Exchange Compatibility")
    print("=" * 50)
    
    from exchanges.binance_exchange import BinanceExchange
    from exchanges.kucoin_exchange import KuCoinExchange
    from exchanges.backpack_exchange import BackpackExchange
    from exchanges.hyperliquid_exchange import HyperliquidExchange
    
    exchanges = [
        ('Binance', BinanceExchange),
        ('KuCoin', KuCoinExchange),
        ('Backpack', BackpackExchange),
        ('Hyperliquid', HyperliquidExchange)
    ]
    
    for name, ExchangeClass in exchanges:
        try:
            exchange = ExchangeClass()
            method = getattr(exchange, 'fetch_all_perpetuals_historical', None)
            if method:
                # Check if method accepts start_time and end_time
                import inspect
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                
                has_start = 'start_time' in params
                has_end = 'end_time' in params
                
                if has_start and has_end:
                    print(f"[OK] {name}: Supports synchronized dates (start_time, end_time)")
                else:
                    print(f"[X] {name}: Missing parameters - start_time:{has_start}, end_time:{has_end}")
            else:
                print(f"[X] {name}: No fetch_all_perpetuals_historical method")
        except Exception as e:
            print(f"[X] {name}: Error - {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SYNCHRONIZED HISTORICAL DATE RANGE TEST")
    print("="*60 + "\n")
    
    # Test date calculation
    start_time, end_time = test_date_calculation()
    
    # Verify exchange compatibility
    verify_exchange_compatibility()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)