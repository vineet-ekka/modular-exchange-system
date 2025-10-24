"""
Create database indexes for arbitrage filter system optimization.
These indexes are critical for the batch Z-score calculation performance.
"""

import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DATABASE', 'exchange_data'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres123')
}

def create_indexes():
    """Create optimized indexes for arbitrage filter batch queries."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    indexes = [
        # Critical for batch Z-score calculation - self-join optimization
        {
            'name': 'idx_historical_pair_lookup',
            'table': 'funding_rates_historical',
            'columns': '(base_asset, exchange, symbol, funding_time DESC)',
            'where': 'WHERE funding_rate IS NOT NULL',
            'description': 'Optimize contract pair lookups in batch query'
        },
        # Speed up time-based filtering in CTE
        {
            'name': 'idx_historical_time_exchange',
            'table': 'funding_rates_historical',
            'columns': '(funding_time DESC, exchange, symbol)',
            'where': 'WHERE funding_rate IS NOT NULL',
            'description': 'Optimize time range filtering'
        },
        # Additional index for funding_time + base_asset filtering
        {
            'name': 'idx_historical_funding_time_asset',
            'table': 'funding_rates_historical',
            'columns': '(funding_time, base_asset)',
            'where': 'WHERE funding_rate IS NOT NULL',
            'description': 'Speed up 30-day window filtering'
        },
        # For SQL-level filtering in main query
        {
            'name': 'idx_exchange_data_arbitrage',
            'table': 'exchange_data',
            'columns': '(base_asset, exchange, funding_rate)',
            'where': 'WHERE funding_rate IS NOT NULL',
            'description': 'Optimize asset and exchange filtering'
        },
        # Existing indexes to verify
        {
            'name': 'idx_exchange_data_base_asset',
            'table': 'exchange_data',
            'columns': '(base_asset)',
            'where': '',
            'description': 'Base asset filtering',
            'check_only': True
        },
        {
            'name': 'idx_exchange_data_updated',
            'table': 'exchange_data',
            'columns': '(last_updated DESC)',
            'where': '',
            'description': 'Recent data filtering',
            'check_only': True
        },
        {
            'name': 'idx_funding_stats_lookup',
            'table': 'funding_statistics',
            'columns': '(exchange, symbol)',
            'where': '',
            'description': 'Statistics lookup',
            'check_only': True
        }
    ]

    print("=" * 60)
    print("Creating/Verifying Arbitrage Filter Indexes")
    print("=" * 60)

    created_count = 0
    existing_count = 0

    for index in indexes:
        # Check if index exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = %s
            )
        """, (index['name'],))

        exists = cur.fetchone()[0]

        if exists:
            print(f"[EXISTS] Index {index['name']} already exists")
            existing_count += 1
        elif index.get('check_only'):
            print(f"[WARNING] Index {index['name']} does not exist (optional)")
        else:
            # Create the index
            print(f"Creating index {index['name']}...")
            print(f"  Description: {index['description']}")

            sql = f"""
                CREATE INDEX IF NOT EXISTS {index['name']}
                ON {index['table']} {index['columns']}
                {index['where']}
            """

            start_time = time.time()
            try:
                cur.execute(sql)
                conn.commit()
                elapsed = time.time() - start_time
                print(f"  [SUCCESS] Created in {elapsed:.2f} seconds")
                created_count += 1
            except Exception as e:
                print(f"  [ERROR] Error creating index: {e}")
                conn.rollback()

    # Analyze tables to update statistics for query planner
    print("\nUpdating table statistics for query planner...")
    tables = ['funding_rates_historical', 'exchange_data', 'funding_statistics']
    for table in tables:
        try:
            cur.execute(f"ANALYZE {table}")
            conn.commit()
            print(f"  [SUCCESS] Analyzed {table}")
        except Exception as e:
            print(f"  [ERROR] Error analyzing {table}: {e}")

    # Get table sizes for context
    print("\nTable Statistics:")
    for table in ['funding_rates_historical', 'exchange_data']:
        cur.execute(f"""
            SELECT
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('{table}')) as total_size
            FROM {table}
        """)
        row_count, size = cur.fetchone()
        print(f"  {table}: {row_count:,} rows, {size}")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print(f"Index Creation Complete")
    print(f"  Created: {created_count} new indexes")
    print(f"  Existing: {existing_count} indexes")
    print("=" * 60)

if __name__ == "__main__":
    create_indexes()