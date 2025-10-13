#!/usr/bin/env python3
"""
Arbitrage Spread Historical Backfill V2
========================================
Improved version that directly calculates spreads from funding_rates_historical.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Tuple
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD
from utils.logger import setup_logger

logger = setup_logger("SpreadBackfillV2")

def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def calculate_and_insert_spreads(conn, days: int = 30):
    """
    Calculate spreads directly from funding_rates_historical table.

    Args:
        conn: Database connection
        days: Number of days to backfill
    """
    cursor = conn.cursor()

    # Get all unique assets that exist in current exchange_data
    logger.info("Finding assets with data from multiple exchanges...")
    cursor.execute("""
        SELECT DISTINCT base_asset
        FROM exchange_data
        WHERE base_asset IS NOT NULL
        ORDER BY base_asset
    """)
    assets = [row[0] for row in cursor.fetchall()]

    logger.info(f"Found {len(assets)} unique assets to process")

    exchange_pairs = [
        ('binance', 'kucoin'),
        ('binance', 'backpack'),
        ('binance', 'hyperliquid'),
        ('kucoin', 'backpack'),
        ('kucoin', 'hyperliquid'),
        ('backpack', 'hyperliquid')
    ]

    total_inserted = 0
    processed_assets = 0

    for asset in assets:
        asset_inserted = 0

        for ex1, ex2 in exchange_pairs:
            try:
                # Build the query to calculate daily spreads
                # This handles symbol matching across exchanges
                query = """
                    WITH ex1_data AS (
                        SELECT
                            DATE(funding_time) as funding_date,
                            AVG(funding_rate) as avg_rate,
                            AVG(funding_interval_hours) as avg_interval,
                            COUNT(*) as data_points
                        FROM funding_rates_historical
                        WHERE exchange = %s
                            AND funding_time >= NOW() - INTERVAL '%s days'
                            AND (
                                -- Match various symbol formats
                                UPPER(symbol) LIKE UPPER(%s) || '%%'
                                OR UPPER(symbol) LIKE '1000' || UPPER(%s) || '%%'
                                OR UPPER(symbol) LIKE 'K' || UPPER(%s) || '%%'
                                OR (UPPER(%s) = 'BABYDOGE' AND UPPER(symbol) LIKE '1MBABYDOGE%%')
                                OR (UPPER(%s) = 'LADYS' AND UPPER(symbol) LIKE '10000LADYS%%')
                            )
                            AND funding_rate IS NOT NULL
                        GROUP BY DATE(funding_time)
                    ),
                    ex2_data AS (
                        SELECT
                            DATE(funding_time) as funding_date,
                            AVG(funding_rate) as avg_rate,
                            AVG(funding_interval_hours) as avg_interval,
                            COUNT(*) as data_points
                        FROM funding_rates_historical
                        WHERE exchange = %s
                            AND funding_time >= NOW() - INTERVAL '%s days'
                            AND (
                                UPPER(symbol) LIKE UPPER(%s) || '%%'
                                OR UPPER(symbol) LIKE '1000' || UPPER(%s) || '%%'
                                OR UPPER(symbol) LIKE 'K' || UPPER(%s) || '%%'
                                OR (UPPER(%s) = 'BABYDOGE' AND UPPER(symbol) LIKE '1MBABYDOGE%%')
                                OR (UPPER(%s) = 'LADYS' AND UPPER(symbol) LIKE '10000LADYS%%')
                            )
                            AND funding_rate IS NOT NULL
                        GROUP BY DATE(funding_time)
                    ),
                    spreads AS (
                        SELECT
                            %s as asset,
                            %s as exchange_long,
                            %s as exchange_short,
                            e1.funding_date,
                            e1.avg_rate as long_rate,
                            e2.avg_rate as short_rate,
                            (e1.avg_rate * (24.0 / e1.avg_interval) -
                             e2.avg_rate * (24.0 / e2.avg_interval)) as daily_spread
                        FROM ex1_data e1
                        INNER JOIN ex2_data e2 ON e1.funding_date = e2.funding_date
                        WHERE e1.avg_rate IS NOT NULL AND e2.avg_rate IS NOT NULL
                    )
                    INSERT INTO arbitrage_spreads_historical
                    (asset, exchange_long, exchange_short, funding_rate_long,
                     funding_rate_short, funding_rate_spread, recorded_at)
                    SELECT
                        asset,
                        exchange_long,
                        exchange_short,
                        long_rate,
                        short_rate,
                        daily_spread,
                        funding_date + INTERVAL '12 hours'  -- Use noon of the day
                    FROM spreads
                    ON CONFLICT (asset, exchange_long, exchange_short, recorded_at)
                    DO UPDATE SET
                        funding_rate_long = EXCLUDED.funding_rate_long,
                        funding_rate_short = EXCLUDED.funding_rate_short,
                        funding_rate_spread = EXCLUDED.funding_rate_spread
                """

                # Execute for ex1 -> ex2 direction
                cursor.execute(query, (
                    ex1, days, asset, asset, asset, asset, asset,  # ex1 parameters
                    ex2, days, asset, asset, asset, asset, asset,  # ex2 parameters
                    asset, ex1, ex2  # spread parameters
                ))
                count1 = cursor.rowcount

                # Execute for ex2 -> ex1 direction (reverse spread)
                cursor.execute(query, (
                    ex2, days, asset, asset, asset, asset, asset,  # ex1 parameters (now ex2)
                    ex1, days, asset, asset, asset, asset, asset,  # ex2 parameters (now ex1)
                    asset, ex2, ex1  # spread parameters (reversed)
                ))
                count2 = cursor.rowcount

                if count1 > 0 or count2 > 0:
                    asset_inserted += count1 + count2

            except Exception as e:
                logger.debug(f"Error processing {asset} for {ex1}-{ex2}: {e}")

        if asset_inserted > 0:
            total_inserted += asset_inserted
            processed_assets += 1

            if processed_assets % 50 == 0:
                conn.commit()
                logger.info(f"Processed {processed_assets}/{len(assets)} assets, inserted {total_inserted} spreads...")

    # Final commit
    conn.commit()
    cursor.close()

    logger.info(f"Completed: Processed {processed_assets} assets, inserted {total_inserted} spread records")
    return total_inserted

def verify_backfill(conn):
    """Verify the backfill results."""
    cursor = conn.cursor()

    # Check overall statistics
    cursor.execute("""
        SELECT
            COUNT(DISTINCT asset) as unique_assets,
            COUNT(DISTINCT DATE(recorded_at)) as days_with_data,
            COUNT(*) as total_records,
            MIN(recorded_at) as oldest_record,
            MAX(recorded_at) as newest_record
        FROM arbitrage_spreads_historical
    """)

    stats = cursor.fetchone()
    logger.info("=" * 60)
    logger.info("BACKFILL VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Unique assets: {stats[0]}")
    logger.info(f"Days with data: {stats[1]}")
    logger.info(f"Total records: {stats[2]}")
    logger.info(f"Date range: {stats[3]} to {stats[4]}")

    # Check specific important assets
    logger.info("\nKey Asset Coverage:")
    for asset in ['BTC', 'ETH', 'XMR', 'SOL', 'DOGE', 'SHIB', 'PEPE']:
        cursor.execute("""
            SELECT
                COUNT(DISTINCT DATE(recorded_at)) as days,
                COUNT(DISTINCT exchange_long || '-' || exchange_short) as pairs,
                COUNT(*) as records
            FROM arbitrage_spreads_historical
            WHERE asset = %s
                AND recorded_at >= NOW() - INTERVAL '30 days'
        """, (asset,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            logger.info(f"  {asset:6}: {result[0]:2} days, {result[1]:2} exchange pairs, {result[2]:5} records")
        else:
            logger.info(f"  {asset:6}: No recent data found")

    cursor.close()

def main(days: int = 30, force: bool = False):
    """
    Main backfill process.

    Args:
        days: Number of days to backfill
        force: Force re-backfill even if data exists
    """
    logger.info("=" * 60)
    logger.info("ARBITRAGE SPREAD HISTORICAL BACKFILL V2")
    logger.info("=" * 60)
    logger.info(f"Backfilling {days} days of spread data from funding rates")

    conn = get_db_connection()

    try:
        # Check if we already have sufficient data (unless forced)
        if not force:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT DATE(recorded_at))
                FROM arbitrage_spreads_historical
                WHERE recorded_at >= NOW() - INTERVAL '%s days'
            """, (days,))
            existing_days = cursor.fetchone()[0]
            cursor.close()

            if existing_days >= days - 5:  # Allow some tolerance
                logger.info(f"Already have {existing_days} days of spread data.")
                logger.info("Use --force to re-run backfill anyway.")
                verify_backfill(conn)
                return

        # Perform the backfill
        logger.info("Starting spread calculation and insertion...")
        start_time = time.time()

        inserted = calculate_and_insert_spreads(conn, days)

        duration = time.time() - start_time
        logger.info(f"Backfill completed in {duration:.2f} seconds")

        # Verify results
        verify_backfill(conn)

        logger.info("\n" + "=" * 60)
        logger.info("BACKFILL COMPLETE!")
        logger.info("Sharpe ratios can now be calculated for all assets with 7+ days of data.")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error during backfill: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backfill historical arbitrage spreads')
    parser.add_argument('--days', type=int, default=30, help='Number of days to backfill (default: 30)')
    parser.add_argument('--force', action='store_true', help='Force re-backfill even if data exists')

    args = parser.parse_args()
    main(days=args.days, force=args.force)