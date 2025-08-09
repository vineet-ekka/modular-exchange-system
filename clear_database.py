#!/usr/bin/env python3
"""
Clear All Data from Database
============================
This script removes all data from the exchange database tables.
WARNING: This will permanently delete all data!
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': os.getenv("POSTGRES_PORT", "5432"),
    'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
    'user': os.getenv("POSTGRES_USER", "postgres"),
    'password': os.getenv("POSTGRES_PASSWORD", "postgres123")
}

def clear_all_tables():
    """Clear all data from database tables."""
    
    print("="*60)
    print("DATABASE CLEANUP UTILITY")
    print("="*60)
    print("\nWARNING: This will DELETE ALL DATA from the database!")
    print("Tables to be cleared:")
    print("  - exchange_data (real-time data)")
    print("  - exchange_data_historical (historical data)")
    print("  - funding_rates_historical (funding rate history)")
    print("")
    
    # Ask for confirmation
    confirmation = input("Type 'DELETE ALL' to confirm: ")
    if confirmation != "DELETE ALL":
        print("\nOperation cancelled.")
        return
    
    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✓ Connected to PostgreSQL")
        
        # Get table counts before deletion
        tables = ['exchange_data', 'exchange_data_historical', 'funding_rates_historical']
        counts_before = {}
        
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                counts_before[table] = count
                print(f"\n{table}: {count:,} records found")
            except psycopg2.errors.UndefinedTable:
                counts_before[table] = 0
                print(f"\n{table}: Table does not exist")
                conn.rollback()
        
        print("\n" + "-"*40)
        print("Starting deletion process...")
        print("-"*40)
        
        # Clear each table
        for table in tables:
            if counts_before[table] > 0:
                try:
                    print(f"\nClearing {table}...")
                    cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                    conn.commit()
                    print(f"✓ Cleared {counts_before[table]:,} records from {table}")
                except Exception as e:
                    print(f"✗ Error clearing {table}: {e}")
                    conn.rollback()
        
        # Verify all tables are empty
        print("\n" + "-"*40)
        print("Verification:")
        print("-"*40)
        
        all_clear = True
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                if count == 0:
                    print(f"✓ {table}: EMPTY")
                else:
                    print(f"✗ {table}: Still has {count} records")
                    all_clear = False
            except:
                conn.rollback()
        
        # Summary
        print("\n" + "="*60)
        if all_clear:
            print("SUCCESS: All data has been cleared!")
            total_deleted = sum(counts_before.values())
            print(f"Total records deleted: {total_deleted:,}")
        else:
            print("WARNING: Some tables may still contain data")
        print("="*60)
        
        # Close connection
        cur.close()
        conn.close()
        print("\n✓ Database connection closed")
        
    except psycopg2.OperationalError as e:
        print(f"\n✗ Database connection error: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running (docker-compose up -d)")
        print("2. Database credentials are correct in .env file")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)

def quick_clear():
    """Quick clear without confirmation - use with caution!"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        tables = ['exchange_data', 'exchange_data_historical', 'funding_rates_historical']
        
        for table in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                conn.commit()
                print(f"[OK] Cleared {table}")
            except:
                conn.rollback()
        
        cur.close()
        conn.close()
        print("\n[OK] All tables cleared successfully")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Check for quick mode
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("Quick clearing all tables...")
        quick_clear()
    else:
        clear_all_tables()