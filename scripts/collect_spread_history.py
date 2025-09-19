#!/usr/bin/env python3
"""
Arbitrage Spread History Collector
===================================
Continuously collects and records arbitrage spreads for statistical analysis.
Runs every 30 seconds to build historical data for z-score calculations.
"""

import time
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.postgres_manager import PostgresManager
from utils.arbitrage_scanner import calculate_arbitrage_opportunities
from utils.arbitrage_spread_statistics import ArbitrageSpreadStatistics
from utils.logger import setup_logger
import requests
import psycopg2
from config.settings import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD


logger = setup_logger("SpreadHistoryCollector")


def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def collect_spreads():
    """Collect and record current spreads."""
    try:
        # Fetch current funding data from API
        response = requests.get('http://localhost:8000/api/funding-rates-grid', timeout=30)
        response.raise_for_status()

        data = response.json()
        funding_data = data.get('data', [])

        if not funding_data:
            logger.warning("No funding data received from API")
            return 0

        # Calculate all opportunities (including those below typical threshold)
        # We want to record ALL spreads for complete statistics
        opportunities = calculate_arbitrage_opportunities(
            funding_data,
            min_spread=0,  # Record all spreads, even zero
            include_statistics=False  # Don't need z-scores for recording
        )

        # Get database connection
        conn = get_db_connection()
        spread_stats = ArbitrageSpreadStatistics(conn)

        # Batch record all spreads
        spreads_to_record = []
        for opp in opportunities:
            spreads_to_record.append({
                'asset': opp['asset'],
                'exchange_long': opp['long_exchange'],
                'exchange_short': opp['short_exchange'],
                'long_rate': opp['long_rate'],
                'short_rate': opp['short_rate'],
                'apr_spread': opp['apr_spread']
            })

        # Record spreads
        count = spread_stats.batch_record_spreads(spreads_to_record)

        logger.info(f"Recorded {count} spreads at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Close connection
        conn.close()

        return count

    except requests.RequestException as e:
        logger.error(f"Error fetching funding data from API: {e}")
        return 0
    except Exception as e:
        logger.error(f"Error collecting spreads: {e}")
        return 0


def refresh_materialized_view():
    """Refresh the materialized view for statistics."""
    try:
        conn = get_db_connection()
        spread_stats = ArbitrageSpreadStatistics(conn)

        success = spread_stats.refresh_statistics_view()

        if success:
            logger.info("Successfully refreshed materialized view")
        else:
            logger.warning("Failed to refresh materialized view")

        conn.close()
        return success

    except Exception as e:
        logger.error(f"Error refreshing materialized view: {e}")
        return False


def clean_old_data():
    """Clean old spread history data (older than 60 days)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Call the cleanup function
        cursor.execute("SELECT clean_old_spread_history()")
        conn.commit()

        logger.info("Cleaned old spread history data")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error cleaning old data: {e}")


def main():
    """Main loop for spread collection."""
    logger.info("Starting arbitrage spread history collector...")
    logger.info("This will collect spread data every 30 seconds for z-score calculations")

    # Track time for periodic tasks
    last_refresh_time = time.time()
    last_cleanup_time = time.time()

    # Refresh interval for materialized view (5 minutes)
    REFRESH_INTERVAL = 300

    # Cleanup interval (1 day)
    CLEANUP_INTERVAL = 86400

    collection_count = 0
    error_count = 0

    while True:
        try:
            # Collect spreads
            start_time = time.time()
            count = collect_spreads()
            duration = time.time() - start_time

            if count > 0:
                collection_count += 1
                logger.debug(f"Collection #{collection_count}: {count} spreads in {duration:.2f}s")
            else:
                error_count += 1
                logger.warning(f"Collection failed (error #{error_count})")

            # Refresh materialized view every 5 minutes
            if time.time() - last_refresh_time >= REFRESH_INTERVAL:
                logger.info("Refreshing materialized view...")
                if refresh_materialized_view():
                    last_refresh_time = time.time()

            # Clean old data once per day
            if time.time() - last_cleanup_time >= CLEANUP_INTERVAL:
                logger.info("Cleaning old data...")
                clean_old_data()
                last_cleanup_time = time.time()

            # Print status every 10 collections
            if collection_count % 10 == 0 and collection_count > 0:
                logger.info(f"Status: {collection_count} successful collections, {error_count} errors")

            # Wait 30 seconds before next collection
            time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            error_count += 1
            time.sleep(30)  # Wait before retrying

    logger.info(f"Collector stopped. Total collections: {collection_count}, Errors: {error_count}")


if __name__ == "__main__":
    main()