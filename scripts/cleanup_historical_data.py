#!/usr/bin/env python3
"""
Historical Data Cleanup Script
===============================
Manually clean up old historical funding rate data from the database.

Usage:
    python cleanup_historical_data.py --days 30
    python cleanup_historical_data.py --days 60 --dry-run
    python cleanup_historical_data.py --days 30 --exchange binance
"""

import sys
import os
import argparse
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.postgres_manager import PostgresManager
from config.settings import HISTORICAL_WINDOW_DAYS


def count_old_records(conn, days: int, exchange: str = None) -> int:
    """Count how many records would be deleted."""
    cursor = conn.cursor()

    query = """
        SELECT COUNT(*)
        FROM funding_rates_historical
        WHERE funding_time < NOW() - INTERVAL %s
    """
    params = [f'{days} days']

    if exchange:
        query += " AND LOWER(exchange) = LOWER(%s)"
        params.append(exchange)

    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    cursor.close()

    return count


def get_date_range(conn, exchange: str = None) -> tuple:
    """Get the current date range of historical data."""
    cursor = conn.cursor()

    query = """
        SELECT MIN(funding_time), MAX(funding_time), COUNT(*)
        FROM funding_rates_historical
    """

    if exchange:
        query += " WHERE LOWER(exchange) = LOWER(%s)"
        cursor.execute(query, (exchange,))
    else:
        cursor.execute(query)

    result = cursor.fetchone()
    cursor.close()

    return result


def cleanup_historical_data(days: int, dry_run: bool = False, exchange: str = None, verbose: bool = False):
    """
    Clean up historical funding rate data older than specified days.

    Args:
        days: Number of days to keep
        dry_run: If True, only show what would be deleted without actually deleting
        exchange: Optional exchange filter
        verbose: Show detailed information
    """
    print("="*60)
    print("HISTORICAL DATA CLEANUP UTILITY")
    print("="*60)

    # Connect to database
    db = PostgresManager()
    conn = db.connection

    try:
        # Get current data statistics
        min_date, max_date, total_records = get_date_range(conn, exchange)

        if not min_date:
            print("\nNo historical data found in database.")
            return

        print(f"\nCurrent Historical Data:")
        print(f"  Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        print(f"  Total records: {total_records:,}")

        if exchange:
            print(f"  Exchange filter: {exchange}")

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        print(f"\nCleanup Parameters:")
        print(f"  Retention period: {days} days")
        print(f"  Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")

        # Count records to be deleted
        delete_count = count_old_records(conn, days, exchange)

        if delete_count == 0:
            print(f"\n✓ No records older than {days} days to delete.")
            return

        print(f"\n{'Would delete' if dry_run else 'Will delete'}: {delete_count:,} records")
        percentage = (delete_count / total_records) * 100
        print(f"  This is {percentage:.1f}% of total records")

        # Calculate what would remain
        remaining = total_records - delete_count
        print(f"  Records remaining after cleanup: {remaining:,}")

        if verbose and delete_count > 0:
            # Show sample of records to be deleted
            cursor = conn.cursor()
            sample_query = """
                SELECT exchange, symbol, funding_time
                FROM funding_rates_historical
                WHERE funding_time < NOW() - INTERVAL %s
            """
            params = [f'{days} days']

            if exchange:
                sample_query += " AND LOWER(exchange) = LOWER(%s)"
                params.append(exchange)

            sample_query += " ORDER BY funding_time DESC LIMIT 10"

            cursor.execute(sample_query, params)
            samples = cursor.fetchall()

            if samples:
                print("\n  Sample of records to be deleted (newest 10):")
                for exc, sym, time in samples:
                    print(f"    {exc:12} {sym:20} {time.strftime('%Y-%m-%d %H:%M')}")

            cursor.close()

        if not dry_run:
            # Ask for confirmation
            print("\n" + "!"*60)
            print("WARNING: This operation cannot be undone!")
            print("!"*60)

            confirmation = input("\nType 'DELETE' to confirm deletion: ")
            if confirmation != 'DELETE':
                print("\nOperation cancelled.")
                return

            print("\nDeleting old records...")

            # Perform the deletion
            if exchange:
                deleted_count = db.cleanup_historical_funding_rates(days)
            else:
                # Use custom query for exchange filter
                cursor = conn.cursor()
                delete_query = """
                    DELETE FROM funding_rates_historical
                    WHERE funding_time < NOW() - INTERVAL %s
                """
                params = [f'{days} days']

                if exchange:
                    delete_query += " AND LOWER(exchange) = LOWER(%s)"
                    params.append(exchange)

                cursor.execute(delete_query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()

            if deleted_count > 0:
                print(f"\n✓ Successfully deleted {deleted_count:,} records")

                # Show new statistics
                min_date, max_date, total_records = get_date_range(conn, exchange)
                print(f"\nNew Historical Data Statistics:")
                print(f"  Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
                print(f"  Total records: {total_records:,}")
            else:
                print("\n✓ No records were deleted")

    except Exception as e:
        print(f"\n✗ Error during cleanup: {e}")
        if not dry_run:
            conn.rollback()

    finally:
        conn.close()

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Clean up old historical funding rate data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete data older than 30 days
  python cleanup_historical_data.py --days 30

  # Dry run - see what would be deleted
  python cleanup_historical_data.py --days 60 --dry-run

  # Delete only Binance data older than 30 days
  python cleanup_historical_data.py --days 30 --exchange binance

  # Use default retention period from settings
  python cleanup_historical_data.py
        """
    )

    parser.add_argument(
        '--days', '-d',
        type=int,
        default=HISTORICAL_WINDOW_DAYS,
        help=f'Number of days to keep (default: {HISTORICAL_WINDOW_DAYS} from settings)'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--exchange', '-e',
        type=str,
        help='Clean up data for specific exchange only'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed information'
    )

    args = parser.parse_args()

    # Validate days parameter
    if args.days < 1:
        print("Error: Days must be at least 1")
        sys.exit(1)

    if args.days > 365:
        print(f"Warning: Keeping {args.days} days of data is a lot!")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)

    # Run cleanup
    cleanup_historical_data(
        days=args.days,
        dry_run=args.dry_run,
        exchange=args.exchange,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()