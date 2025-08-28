#!/usr/bin/env python3
"""
Database Management Tools
=========================
Consolidated utility for database operations.
Usage: python database_tools.py [check|clear|status]
"""

import psycopg2
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

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


def check_database():
    """Check the status of all database tables."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("="*60)
        print("DATABASE STATUS CHECK")
        print("="*60)
        
        tables = ['exchange_data', 'exchange_data_historical', 'funding_rates_historical']
        total_records = 0
        
        for table in tables:
            try:
                # Get count
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                total_records += count
                
                # Get sample if has data
                if count > 0:
                    cur.execute(f"SELECT COUNT(DISTINCT exchange) FROM {table}")
                    exchanges = cur.fetchone()[0]
                    print(f"\n{table}:")
                    print(f"  Records: {count:,}")
                    print(f"  Exchanges: {exchanges}")
                    
                    # Get date range for historical tables
                    if 'historical' in table:
                        try:
                            if table == 'funding_rates_historical':
                                cur.execute(f"SELECT MIN(funding_time), MAX(funding_time) FROM {table}")
                            else:
                                cur.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
                            min_date, max_date = cur.fetchone()
                            if min_date and max_date:
                                print(f"  Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
                        except:
                            pass
                else:
                    print(f"\n{table}: EMPTY")
                    
            except Exception as e:
                print(f"\n{table}: ERROR - {e}")
        
        print(f"\nTotal records across all tables: {total_records:,}")
        
        # Check database size
        cur.execute("""
            SELECT pg_database_size(%s) as db_size
        """, (DB_CONFIG['database'],))
        db_size = cur.fetchone()[0]
        print(f"Database size: {db_size / 1024 / 1024:.2f} MB")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False


def clear_database(quick=False):
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
    
    # Ask for confirmation unless quick mode
    if not quick:
        confirmation = input("Type 'DELETE ALL' to confirm: ")
        if confirmation != "DELETE ALL":
            print("\nOperation cancelled.")
            return False
    else:
        print("Quick mode: Skipping confirmation")
    
    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get counts before deletion
        tables = ['exchange_data', 'exchange_data_historical', 'funding_rates_historical']
        counts_before = {}
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts_before[table] = cur.fetchone()[0]
            except:
                counts_before[table] = 0
        
        # Clear each table
        for table in tables:
            try:
                print(f"\nClearing {table}...")
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                print(f"  ✓ Cleared {counts_before[table]:,} records from {table}")
            except Exception as e:
                print(f"  ✗ Error clearing {table}: {e}")
        
        # Commit changes
        conn.commit()
        print("\n✓ All tables cleared successfully!")
        
        # Show summary
        total_deleted = sum(counts_before.values())
        print(f"\nTotal records deleted: {total_deleted:,}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Database operation failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def main():
    """Main entry point for database tools."""
    parser = argparse.ArgumentParser(description='Database management tools')
    parser.add_argument('command', choices=['check', 'clear', 'status'], 
                       help='Command to execute')
    parser.add_argument('--quick', action='store_true',
                       help='Skip confirmations (for clear command)')
    
    args = parser.parse_args()
    
    if args.command in ['check', 'status']:
        success = check_database()
    elif args.command == 'clear':
        success = clear_database(quick=args.quick)
    else:
        print(f"Unknown command: {args.command}")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()