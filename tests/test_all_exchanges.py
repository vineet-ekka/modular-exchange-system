#!/usr/bin/env python3
"""
Test all exchanges including Hyperliquid
=========================================
Tests data collection from all 4 active exchanges.
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

from exchanges.exchange_factory import ExchangeFactory
from config.settings import EXCHANGES
import pandas as pd
import time


def test_all_exchanges():
    """Test all active exchanges."""
    print("="*60)
    print("TESTING ALL EXCHANGES (4-EXCHANGE SYSTEM)")
    print("="*60)
    
    # Initialize exchange factory
    print("\n1. Initializing Exchange Factory...")
    factory = ExchangeFactory(EXCHANGES)
    enabled = factory.get_enabled_exchanges()
    print(f"   Found {len(enabled)} enabled exchanges:")
    for ex in enabled:
        print(f"   • {ex.name}")
    
    # Test sequential collection
    print("\n2. Testing Sequential Collection Mode...")
    print(f"   Sequential mode enabled: {factory.sequential_mode}")
    print(f"   Exchange delay: {factory.exchange_delay} seconds")
    
    # Collect data from all exchanges
    print("\n3. Collecting data from all exchanges...")
    start_time = time.time()
    
    all_data = factory.process_all_exchanges()
    
    end_time = time.time()
    duration = end_time - start_time
    
    if all_data.empty:
        print("   ✗ No data collected!")
        return False
    
    print(f"\n   ✓ Collection completed in {duration:.1f} seconds")
    print(f"   ✓ Total contracts collected: {len(all_data)}")
    
    # Break down by exchange
    print("\n4. Contracts by Exchange:")
    exchange_counts = all_data['exchange'].value_counts()
    for exchange, count in exchange_counts.items():
        print(f"   • {exchange}: {count} contracts")
    
    # Check funding intervals
    print("\n5. Funding Intervals by Exchange:")
    for exchange in all_data['exchange'].unique():
        exchange_data = all_data[all_data['exchange'] == exchange]
        intervals = exchange_data['funding_interval_hours'].value_counts()
        print(f"\n   {exchange}:")
        for interval, count in intervals.items():
            percentage = (count / len(exchange_data)) * 100
            print(f"     • {interval}h: {count} contracts ({percentage:.1f}%)")
    
    # Check unique assets
    print("\n6. Asset Coverage:")
    unique_assets = all_data['base_asset'].nunique()
    print(f"   • Total unique assets: {unique_assets}")
    
    # Find assets that exist on multiple exchanges
    asset_exchanges = all_data.groupby('base_asset')['exchange'].nunique()
    multi_exchange_assets = asset_exchanges[asset_exchanges > 1]
    print(f"   • Assets on multiple exchanges: {len(multi_exchange_assets)}")
    
    if len(multi_exchange_assets) > 0:
        print("\n   Examples of multi-exchange assets:")
        for asset in multi_exchange_assets.head(5).index:
            exchanges = all_data[all_data['base_asset'] == asset]['exchange'].unique()
            print(f"     • {asset}: {', '.join(exchanges)}")
    
    # Check APR statistics
    print("\n7. APR Statistics:")
    print(f"   • Average APR: {all_data['apr'].mean():.2f}%")
    print(f"   • Median APR: {all_data['apr'].median():.2f}%")
    print(f"   • Min APR: {all_data['apr'].min():.2f}%")
    print(f"   • Max APR: {all_data['apr'].max():.2f}%")
    
    # Find top APR contracts
    print("\n8. Top 5 APR Contracts:")
    top_apr = all_data.nlargest(5, 'apr')[['exchange', 'symbol', 'funding_rate', 'apr', 'funding_interval_hours']]
    for _, row in top_apr.iterrows():
        print(f"   • {row['exchange']} {row['symbol']}: {row['apr']:.2f}% "
              f"(rate: {row['funding_rate']:.8f}, interval: {row['funding_interval_hours']}h)")
    
    # Hyperliquid specific checks
    hyperliquid_data = all_data[all_data['exchange'] == 'Hyperliquid']
    if not hyperliquid_data.empty:
        print("\n9. Hyperliquid Specific Stats:")
        print(f"   • Contracts: {len(hyperliquid_data)}")
        print(f"   • All using 1-hour funding intervals: {(hyperliquid_data['funding_interval_hours'] == 1).all()}")
        print(f"   • Average APR: {hyperliquid_data['apr'].mean():.2f}%")
        
        # Check for special contracts
        k_contracts = hyperliquid_data[hyperliquid_data['base_asset'].str.endswith('K', na=False)]
        if not k_contracts.empty:
            print(f"   • 'k' prefix contracts: {len(k_contracts)}")
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✓ Successfully collected data from {len(enabled)} exchanges")
    print(f"✓ Total contracts: {len(all_data)}")
    print(f"✓ Unique assets: {unique_assets}")
    print(f"✓ Multi-exchange assets: {len(multi_exchange_assets)}")
    
    # Final breakdown
    print("\nFinal System Statistics:")
    print(f"• Binance: {len(all_data[all_data['exchange'] == 'Binance'])} contracts")
    print(f"• KuCoin: {len(all_data[all_data['exchange'] == 'KuCoin'])} contracts")
    print(f"• Backpack: {len(all_data[all_data['exchange'] == 'Backpack'])} contracts")
    print(f"• Hyperliquid: {len(all_data[all_data['exchange'] == 'Hyperliquid'])} contracts")
    print(f"• TOTAL: {len(all_data)} contracts across {unique_assets} unique assets")
    
    return True


if __name__ == "__main__":
    success = test_all_exchanges()
    sys.exit(0 if success else 1)