"""
Fix incorrect funding intervals in the database.
Corrects the hardcoded 8-hour intervals for contracts that actually have 4-hour intervals.

This script:
1. Fetches correct funding intervals from Binance API
2. Updates the exchange_data table with correct intervals
3. Recalculates APR values using the correct formula
4. Updates historical data table if it exists
"""

import psycopg2
import requests
from datetime import datetime, timezone
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def fix_funding_intervals():
    """Main function to fix funding intervals in the database."""
    
    # Database configuration
    db_config = {
        'host': os.getenv("POSTGRES_HOST", "localhost"),
        'port': os.getenv("POSTGRES_PORT", "5432"),
        'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
        'user': os.getenv("POSTGRES_USER", "postgres"),
        'password': os.getenv("POSTGRES_PASSWORD", "postgres123")
    }
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Fetch funding info from Binance USD-M API
        print("\nFetching funding interval information from Binance...")
        response = requests.get('https://fapi.binance.com/fapi/v1/fundingInfo')
        response.raise_for_status()
        funding_info = response.json()
        
        # Create mapping of symbol to funding interval
        interval_map = {}
        for item in funding_info:
            interval_map[item['symbol']] = item['fundingIntervalHours']
        
        # Count distribution
        four_hour_symbols = [s for s, h in interval_map.items() if h == 4]
        eight_hour_symbols = [s for s, h in interval_map.items() if h == 8]
        
        print(f"\nFound {len(funding_info)} symbols with custom funding settings:")
        print(f"  - {len(four_hour_symbols)} symbols with 4-hour intervals")
        print(f"  - {len(eight_hour_symbols)} symbols with 8-hour intervals")
        
        # Check current state in database
        print("\nChecking current database state...")
        cur.execute("""
            SELECT funding_interval_hours, COUNT(DISTINCT symbol) 
            FROM exchange_data 
            WHERE exchange = 'Binance' 
            GROUP BY funding_interval_hours
            ORDER BY funding_interval_hours
        """)
        
        print("Current funding interval distribution:")
        for row in cur.fetchall():
            print(f"  {row[0]}-hour intervals: {row[1]} symbols")
        
        # Update exchange_data table
        print("\nUpdating exchange_data table...")
        update_count = 0
        
        for symbol, hours in interval_map.items():
            # Update funding_interval_hours and recalculate APR
            cur.execute("""
                UPDATE exchange_data 
                SET funding_interval_hours = %s,
                    apr = CASE 
                        WHEN funding_rate IS NOT NULL THEN 
                            funding_rate * (365.0 * 24 / %s) * 100
                        ELSE NULL
                    END,
                    last_updated = %s
                WHERE exchange = 'Binance' 
                    AND symbol = %s
                    AND (funding_interval_hours != %s OR funding_interval_hours IS NULL)
            """, (hours, hours, datetime.now(timezone.utc), symbol, hours))
            
            if cur.rowcount > 0:
                update_count += 1
        
        print(f"  Updated {update_count} records in exchange_data")
        
        # Check if funding_rates_historical table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'funding_rates_historical'
            )
        """)
        
        has_historical = cur.fetchone()[0]
        
        if has_historical:
            print("\nUpdating funding_rates_historical table...")
            historical_update_count = 0
            
            for symbol, hours in interval_map.items():
                cur.execute("""
                    UPDATE funding_rates_historical 
                    SET funding_interval_hours = %s
                    WHERE exchange = 'Binance' 
                        AND symbol = %s
                        AND (funding_interval_hours != %s OR funding_interval_hours IS NULL)
                """, (hours, symbol, hours))
                
                historical_update_count += cur.rowcount
            
            print(f"  Updated {historical_update_count} records in funding_rates_historical")
        
        # Also need to update base_asset field for any missing values
        print("\nUpdating base_asset for COIN-M contracts...")
        cur.execute("""
            UPDATE exchange_data
            SET base_asset = 
                CASE 
                    WHEN symbol LIKE '%USD_PERP' THEN 
                        SUBSTRING(symbol FROM 1 FOR LENGTH(symbol) - 8)
                    WHEN symbol LIKE '%USDT' THEN 
                        SUBSTRING(symbol FROM 1 FOR LENGTH(symbol) - 4)
                    WHEN symbol LIKE '%USDC' THEN 
                        SUBSTRING(symbol FROM 1 FOR LENGTH(symbol) - 4)
                    ELSE base_asset
                END
            WHERE exchange = 'Binance' 
                AND (base_asset IS NULL OR base_asset = '')
        """)
        print(f"  Updated {cur.rowcount} base_asset fields")
        
        # Commit all changes
        print("\nCommitting changes...")
        conn.commit()
        
        # Verify the fix
        print("\nVerifying the fix...")
        cur.execute("""
            SELECT funding_interval_hours, COUNT(DISTINCT symbol) 
            FROM exchange_data 
            WHERE exchange = 'Binance' 
            GROUP BY funding_interval_hours
            ORDER BY funding_interval_hours
        """)
        
        print("Updated funding interval distribution:")
        for row in cur.fetchall():
            print(f"  {row[0]}-hour intervals: {row[1]} symbols")
        
        # Sample verification - check a known 4-hour symbol
        print("\nSample verification (LPTUSDT - should be 4-hour):")
        cur.execute("""
            SELECT symbol, funding_rate, funding_interval_hours, apr
            FROM exchange_data
            WHERE exchange = 'Binance' AND symbol = 'LPTUSDT'
        """)
        
        result = cur.fetchone()
        if result:
            symbol, rate, hours, apr = result
            if rate:
                calculated_apr = float(rate) * (365 * 24 / hours) * 100
                print(f"  Symbol: {symbol}")
                print(f"  Funding Rate: {rate}")
                print(f"  Interval: {hours} hours")
                print(f"  Stored APR: {apr:.2f}%")
                print(f"  Calculated APR: {calculated_apr:.2f}%")
                print(f"  Match: {'✓ Correct!' if abs(float(apr) - calculated_apr) < 0.01 else '✗ Mismatch!'}")
        
        # Close connection
        cur.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✓ Funding intervals fixed successfully!")
        print("  - Database records updated with correct intervals")
        print("  - APR values recalculated with proper formula")
        print("  - Please restart data collection to use the updated code")
        print("="*60)
        
        return True
        
    except requests.RequestException as e:
        print(f"\n✗ Error fetching data from Binance API: {e}")
        return False
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    print("="*60)
    print("FUNDING INTERVAL FIX SCRIPT")
    print("="*60)
    print("This script will:")
    print("1. Fetch correct funding intervals from Binance")
    print("2. Update the database with correct intervals")
    print("3. Recalculate APR values")
    print("="*60)
    
    # Run the fix
    success = fix_funding_intervals()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)