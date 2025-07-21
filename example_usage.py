"""
Example Usage
============
This file shows how easy it is to use the modular exchange data system.
Perfect for non-coders who want to customize the behavior.
"""

from main import ExchangeDataSystem
from config.settings import EXCHANGES, DISPLAY_LIMIT


def example_basic_usage():
    """
    Basic usage example - just run the system as configured.
    """
    print("=== BASIC USAGE EXAMPLE ===")
    
    # Create and run the system
    system = ExchangeDataSystem()
    success = system.run()
    
    if success:
        print("✓ System completed successfully!")
    else:
        print("❌ System failed")


def example_custom_analysis():
    """
    Example of custom analysis using the system components.
    """
    print("\n=== CUSTOM ANALYSIS EXAMPLE ===")
    
    # Create system
    system = ExchangeDataSystem()
    
    # Run the system
    success = system.run()
    
    if not success:
        print("❌ System failed, cannot perform analysis")
        return
    
    # Get statistics
    stats = system.get_statistics()
    print(f"📊 Total contracts: {stats.get('total_contracts', 0)}")
    
    # Get data for specific exchange
    binance_data = system.get_exchange_data("Binance")
    if not binance_data.empty:
        print(f"📈 Binance contracts: {len(binance_data)}")
        
        # Show top funding rates for Binance
        top_rates = binance_data.nlargest(5, 'funding_rate')
        print("\n🔥 Top 5 Binance Funding Rates:")
        for _, row in top_rates.iterrows():
            print(f"  {row['symbol']}: {row['funding_rate']:.6f}")
    
    # Get top funding rates across all exchanges
    top_rates = system.get_top_funding_rates(limit=10)
    if not top_rates.empty:
        print(f"\n🏆 Top 10 Funding Rates Across All Exchanges:")
        for _, row in top_rates.iterrows():
            print(f"  {row['exchange']} {row['symbol']}: {row['funding_rate']:.6f}")


def example_show_settings():
    """
    Example showing current settings.
    """
    print("\n=== CURRENT SETTINGS ===")
    print(f"Enabled exchanges: {list(EXCHANGES.keys())}")
    print(f"Display limit: {DISPLAY_LIMIT}")
    
    # Show which exchanges are enabled
    enabled = [name for name, enabled in EXCHANGES.items() if enabled]
    disabled = [name for name, enabled in EXCHANGES.items() if not enabled]
    
    print(f"✅ Enabled: {enabled}")
    if disabled:
        print(f"❌ Disabled: {disabled}")


def example_historical_collection():
    """
    Example commands for historical data collection.
    """
    print("\n=== HISTORICAL DATA COLLECTION EXAMPLES ===")
    print("# IMPORTANT: Always use --duration to avoid indefinite runs!")
    print()
    print("1. Quick test (3 minutes, 1-minute intervals):")
    print("   python main_historical.py --interval 60 --duration 180")
    print()
    print("2. Production run (24 hours, 5-minute intervals):")
    print("   python main_historical.py --interval 300 --duration 86400")
    print()
    print("3. High-frequency monitoring (1 hour, 30-second intervals):")
    print("   python main_historical.py --interval 30 --duration 3600")
    print()
    print("4. View historical data summary:")
    print("   python main_historical.py --summary")
    print()
    print("5. Dry run without database upload:")
    print("   python main_historical.py --no-upload --duration 300")


def example_quick_tips():
    """
    Quick tips for non-coders.
    """
    print("\n=== QUICK TIPS FOR NON-CODERS ===")
    print("1. To disable an exchange: Edit config/settings.py")
    print("   Change 'backpack': True to 'backpack': False")
    print()
    print("2. To change display limit: Edit config/settings.py")
    print("   Change DISPLAY_LIMIT = 30 to DISPLAY_LIMIT = 50")
    print()
    print("3. To disable database upload: Edit config/settings.py")
    print("   Change ENABLE_DATABASE_UPLOAD = True to False")
    print()
    print("4. To enable debug mode: Edit config/settings.py")
    print("   Change DEBUG_MODE = False to DEBUG_MODE = True")
    print()
    print("5. To add a new exchange: Follow the README.md guide")
    print()
    print("6. For historical data collection: ALWAYS use --duration flag!")


if __name__ == "__main__":
    print("🎯 MODULAR EXCHANGE DATA SYSTEM - EXAMPLES")
    print("=" * 50)
    
    # Show current settings
    example_show_settings()
    
    # Run basic example
    example_basic_usage()
    
    # Run custom analysis example
    example_custom_analysis()
    
    # Show historical collection examples
    example_historical_collection()
    
    # Show quick tips
    example_quick_tips()
    
    print("\n" + "=" * 50)
    print("✅ All examples completed!")
    print("💡 Check config/settings.py to customize the system") 