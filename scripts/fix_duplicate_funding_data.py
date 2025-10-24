#!/usr/bin/env python3
"""
Fix duplicate funding rate entries in the database.
This script:
1. Identifies duplicate entries in funding_rates_historical
2. Removes duplicates keeping the most recent
3. Adds a UNIQUE constraint to prevent future duplicates
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': os.getenv("POSTGRES_PORT", "5432"),
    'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
    'user': os.getenv("POSTGRES_USER", "postgres"),
    'password': os.getenv("POSTGRES_PASSWORD", "postgres123")
}

def get_connection():
    """Create database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

def check_duplicates(conn):
    """Check for duplicate entries in funding_rates_historical."""
    logger.info("Checking for duplicate funding rate entries...")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Find duplicates
    query = """
        SELECT exchange, symbol, funding_time, COUNT(*) as count
        FROM funding_rates_historical
        GROUP BY exchange, symbol, funding_time
        HAVING COUNT(*) > 1
        ORDER BY count DESC, exchange, symbol, funding_time DESC
        LIMIT 100
    """

    cur.execute(query)
    duplicates = cur.fetchall()

    if not duplicates:
        logger.info("No duplicate entries found!")
        return 0

    logger.warning(f"Found {len(duplicates)} duplicate timestamp combinations")

    # Get total duplicate records count
    total_query = """
        SELECT COUNT(*) - COUNT(DISTINCT (exchange, symbol, funding_time))
        FROM funding_rates_historical
    """
    cur.execute(total_query)
    total_duplicates = cur.fetchone()[0]

    logger.warning(f"Total duplicate records to remove: {total_duplicates}")

    # Show sample duplicates
    logger.info("\nSample duplicate entries (showing first 5):")
    for i, dup in enumerate(duplicates[:5]):
        logger.info(f"  {dup['exchange']}:{dup['symbol']} at {dup['funding_time']} - {dup['count']} copies")

    cur.close()
    return total_duplicates

def remove_duplicates(conn):
    """Remove duplicate entries, keeping the most recent."""
    logger.info("Removing duplicate entries...")

    cur = conn.cursor()

    # Create a temporary table with deduplicated data
    # Using ctid to identify and keep only one row per unique combination
    dedupe_query = """
        -- First, check if we have an id column
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'funding_rates_historical'
        AND column_name = 'id';
    """

    cur.execute(dedupe_query)
    has_id = cur.fetchone() is not None

    if has_id:
        # Use id column for ordering (prefer higher id = more recent)
        delete_query = """
            DELETE FROM funding_rates_historical a
            USING funding_rates_historical b
            WHERE a.exchange = b.exchange
                AND a.symbol = b.symbol
                AND a.funding_time = b.funding_time
                AND a.id < b.id;
        """
    else:
        # Use ctid for deduplication (PostgreSQL internal row identifier)
        delete_query = """
            DELETE FROM funding_rates_historical
            WHERE ctid NOT IN (
                SELECT MIN(ctid)
                FROM funding_rates_historical
                GROUP BY exchange, symbol, funding_time
            );
        """

    logger.info("Executing deduplication query...")
    cur.execute(delete_query)
    deleted_count = cur.rowcount

    logger.info(f"Removed {deleted_count} duplicate records")

    cur.close()
    return deleted_count

def add_unique_constraint(conn):
    """Add UNIQUE constraint to prevent future duplicates."""
    logger.info("Adding UNIQUE constraint...")

    cur = conn.cursor()

    # Check if constraint already exists
    check_query = """
        SELECT conname
        FROM pg_constraint
        WHERE conname = 'unique_exchange_symbol_funding_time';
    """

    cur.execute(check_query)
    exists = cur.fetchone() is not None

    if exists:
        logger.info("UNIQUE constraint already exists")
        cur.close()
        return False

    # Add the constraint
    try:
        constraint_query = """
            ALTER TABLE funding_rates_historical
            ADD CONSTRAINT unique_exchange_symbol_funding_time
            UNIQUE (exchange, symbol, funding_time);
        """

        cur.execute(constraint_query)
        logger.info("Successfully added UNIQUE constraint")

        # Also create an index for better query performance
        index_query = """
            CREATE INDEX IF NOT EXISTS idx_funding_historical_lookup
            ON funding_rates_historical(exchange, symbol, funding_time DESC);
        """

        cur.execute(index_query)
        logger.info("Created performance index")

        cur.close()
        return True

    except psycopg2.errors.DuplicateTable:
        logger.warning("Constraint already exists (different name)")
        cur.close()
        return False
    except Exception as e:
        logger.error(f"Failed to add constraint: {e}")
        cur.close()
        return False

def verify_fix(conn):
    """Verify that duplicates have been removed."""
    logger.info("\nVerifying fix...")

    cur = conn.cursor()

    # Check for any remaining duplicates
    verify_query = """
        SELECT COUNT(*) as dup_count
        FROM (
            SELECT exchange, symbol, funding_time
            FROM funding_rates_historical
            GROUP BY exchange, symbol, funding_time
            HAVING COUNT(*) > 1
        ) as dups
    """

    cur.execute(verify_query)
    remaining = cur.fetchone()[0]

    if remaining == 0:
        logger.info("✅ All duplicates have been removed!")
    else:
        logger.warning(f"❌ Still have {remaining} duplicate combinations")

    # Get table statistics
    stats_query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT (exchange, symbol)) as unique_contracts,
            MIN(funding_time) as earliest_data,
            MAX(funding_time) as latest_data
        FROM funding_rates_historical
    """

    cur.execute(stats_query)
    stats = cur.fetchone()

    logger.info("\nTable Statistics:")
    logger.info(f"  Total records: {stats[0]:,}")
    logger.info(f"  Unique contracts: {stats[1]:,}")
    logger.info(f"  Data range: {stats[2]} to {stats[3]}")

    cur.close()

def main():
    """Main execution function."""
    logger.info("Starting duplicate funding data fix...")
    logger.info("=" * 60)

    # Connect to database
    conn = get_connection()

    try:
        # Check for duplicates
        duplicate_count = check_duplicates(conn)

        if duplicate_count > 0:
            # Ask for confirmation
            response = input(f"\nDo you want to remove {duplicate_count} duplicate records? (yes/no): ")

            if response.lower() in ['yes', 'y']:
                # Remove duplicates
                removed = remove_duplicates(conn)

                # Commit the changes
                conn.commit()
                logger.info("Changes committed to database")
            else:
                logger.info("Operation cancelled by user")
                return

        # Always try to add constraint to prevent future duplicates
        constraint_added = add_unique_constraint(conn)
        if constraint_added:
            conn.commit()
            logger.info("Constraint committed to database")

        # Verify the fix
        verify_fix(conn)

        logger.info("\n" + "=" * 60)
        logger.info("Fix completed successfully!")

    except Exception as e:
        logger.error(f"Error during fix: {e}")
        conn.rollback()
        logger.error("Changes rolled back")
        raise

    finally:
        conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    main()