#!/usr/bin/env python3
"""
Check Database Status
=====================
Quick script to check the current state of database tables.
"""

import psycopg2
import os
from dotenv import load_dotenv

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
                else:
                    print(f"\n{table}: EMPTY")
                    
            except psycopg2.errors.UndefinedTable:
                print(f"\n{table}: Table does not exist")
                conn.rollback()
        
        print("\n" + "="*60)
        if total_records == 0:
            print("DATABASE IS EMPTY - Ready for fresh data")
        else:
            print(f"TOTAL RECORDS: {total_records:,}")
        print("="*60)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()