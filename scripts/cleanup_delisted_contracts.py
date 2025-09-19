#!/usr/bin/env python3
"""
Cleanup Delisted Contracts
=========================
Maintenance script to identify and clean up delisted contracts from the system.

This script:
1. Identifies contracts with stale data
2. Marks them as inactive in contract_metadata
3. Removes stale data from exchange_data
4. Provides a detailed report of all actions
"""

import psycopg2
import argparse
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='exchange_data',
        user='postgres',
        password='postgres123'
    )


def identify_stale_contracts(conn, threshold_hours: int = 24) -> List[Tuple[str, str, datetime]]:
    """
    Identify contracts with stale data.

    Args:
        conn: Database connection
        threshold_hours: Hours since last update to consider stale

    Returns:
        List of (exchange, symbol, last_updated) tuples
    """
    cur = conn.cursor()

    query = """
    SELECT ed.exchange, ed.symbol, ed.last_updated
    FROM exchange_data ed
    LEFT JOIN contract_metadata cm
        ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
    WHERE ed.last_updated < NOW() - INTERVAL '%s hours'
    AND (cm.is_active = true OR cm.is_active IS NULL)
    ORDER BY ed.last_updated, ed.exchange, ed.symbol
    """

    cur.execute(query, (threshold_hours,))
    stale_contracts = cur.fetchall()
    cur.close()

    return stale_contracts


def mark_contracts_inactive(conn, contracts: List[Tuple[str, str]], dry_run: bool = False) -> int:
    """
    Mark contracts as inactive in contract_metadata.

    Args:
        conn: Database connection
        contracts: List of (exchange, symbol) tuples
        dry_run: If True, don't actually update

    Returns:
        Number of contracts marked inactive
    """
    if not contracts:
        return 0

    cur = conn.cursor()

    # Build the update query
    placeholders = ','.join(['(%s, %s)'] * len(contracts))
    flat_params = [item for contract in contracts[:2] for item in contract[:2]]  # Only exchange and symbol

    query = f"""
    UPDATE contract_metadata
    SET
        is_active = false,
        notes = COALESCE(notes || E'\\n', '') ||
               'Marked as delisted on ' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
    WHERE (exchange, symbol) IN ({placeholders})
    AND is_active = true
    RETURNING exchange, symbol
    """

    if dry_run:
        logger.info(f"[DRY RUN] Would mark {len(contracts)} contracts as inactive")
        return 0

    cur.execute(query, flat_params)
    updated = cur.fetchall()
    conn.commit()
    cur.close()

    return len(updated)


def remove_stale_data(conn, threshold_hours: int = 48, dry_run: bool = False) -> Dict[str, int]:
    """
    Remove stale data from exchange_data.

    Args:
        conn: Database connection
        threshold_hours: Hours since last update before removal
        dry_run: If True, don't actually delete

    Returns:
        Dictionary with counts of removed entries
    """
    cur = conn.cursor()
    stats = {'inactive_contracts': 0, 'orphaned_entries': 0}

    # Remove stale data for inactive contracts
    query1 = """
    DELETE FROM exchange_data ed
    USING contract_metadata cm
    WHERE ed.exchange = cm.exchange
    AND ed.symbol = cm.symbol
    AND cm.is_active = false
    AND ed.last_updated < NOW() - INTERVAL '%s hours'
    RETURNING ed.exchange, ed.symbol
    """

    if dry_run:
        # Count what would be deleted - need different query structure for SELECT
        count_query1 = """
        SELECT COUNT(*) FROM exchange_data ed
        JOIN contract_metadata cm
            ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
        WHERE cm.is_active = false
        AND ed.last_updated < NOW() - INTERVAL '%s hours'
        """
        cur.execute(count_query1, (threshold_hours,))
        count = cur.fetchone()[0]
        logger.info(f"[DRY RUN] Would remove {count} stale entries from inactive contracts")
        stats['inactive_contracts'] = count
    else:
        cur.execute(query1, (threshold_hours,))
        removed = cur.fetchall()
        stats['inactive_contracts'] = len(removed)
        conn.commit()

    # Remove orphaned entries (not in metadata at all)
    query2 = """
    DELETE FROM exchange_data ed
    WHERE NOT EXISTS (
        SELECT 1 FROM contract_metadata cm
        WHERE cm.exchange = ed.exchange AND cm.symbol = ed.symbol
    )
    AND ed.last_updated < NOW() - INTERVAL '%s hours'
    RETURNING ed.exchange, ed.symbol
    """

    if dry_run:
        # Count what would be deleted - use proper SELECT query
        count_query2 = """
        SELECT COUNT(*) FROM exchange_data ed
        WHERE NOT EXISTS (
            SELECT 1 FROM contract_metadata cm
            WHERE cm.exchange = ed.exchange AND cm.symbol = ed.symbol
        )
        AND ed.last_updated < NOW() - INTERVAL '%s hours'
        """
        cur.execute(count_query2, (threshold_hours,))
        count = cur.fetchone()[0]
        logger.info(f"[DRY RUN] Would remove {count} orphaned entries")
        stats['orphaned_entries'] = count
    else:
        cur.execute(query2, (threshold_hours,))
        orphans = cur.fetchall()
        stats['orphaned_entries'] = len(orphans)
        conn.commit()

    cur.close()
    return stats


def generate_report(stale_contracts: List[Tuple], marked_inactive: int, removal_stats: Dict) -> None:
    """
    Generate a detailed report of the cleanup operation.

    Args:
        stale_contracts: List of stale contracts found
        marked_inactive: Number of contracts marked inactive
        removal_stats: Statistics from data removal
    """
    print("\n" + "="*70)
    print("DELISTED CONTRACT CLEANUP REPORT")
    print("="*70)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    print(f"Stale Contracts Found: {len(stale_contracts)}")
    if stale_contracts:
        print("\nMost Stale Contracts (up to 10):")
        print("-"*50)
        print(f"{'Exchange':<15} {'Symbol':<20} {'Last Updated'}")
        print("-"*50)
        for exchange, symbol, last_updated in stale_contracts[:10]:
            days_old = (datetime.now(timezone.utc) - last_updated.replace(tzinfo=timezone.utc)).days
            print(f"{exchange:<15} {symbol:<20} {last_updated} ({days_old} days old)")
        if len(stale_contracts) > 10:
            print(f"... and {len(stale_contracts) - 10} more")

    print("\nActions Taken:")
    print("-"*50)
    print(f"Contracts marked as inactive: {marked_inactive}")
    print(f"Stale entries removed (inactive contracts): {removal_stats['inactive_contracts']}")
    print(f"Orphaned entries removed: {removal_stats['orphaned_entries']}")
    print(f"Total entries cleaned: {removal_stats['inactive_contracts'] + removal_stats['orphaned_entries']}")

    print("\n" + "="*70)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Clean up delisted contracts from the exchange data system'
    )
    parser.add_argument(
        '--stale-threshold',
        type=int,
        default=24,
        help='Hours since last update to consider a contract stale (default: 24)'
    )
    parser.add_argument(
        '--removal-threshold',
        type=int,
        default=48,
        help='Hours before removing stale data from database (default: 48)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = get_db_connection()

        # Step 1: Identify stale contracts
        logger.info(f"Identifying contracts with data older than {args.stale_threshold} hours...")
        stale_contracts = identify_stale_contracts(conn, args.stale_threshold)
        logger.info(f"Found {len(stale_contracts)} stale contracts")

        # Step 2: Mark contracts as inactive
        contracts_to_mark = [(c[0], c[1]) for c in stale_contracts]
        marked_inactive = mark_contracts_inactive(conn, contracts_to_mark, args.dry_run)
        if not args.dry_run:
            logger.info(f"Marked {marked_inactive} contracts as inactive")

        # Step 3: Remove stale data
        logger.info(f"Removing data older than {args.removal_threshold} hours...")
        removal_stats = remove_stale_data(conn, args.removal_threshold, args.dry_run)
        if not args.dry_run:
            logger.info(f"Removed {removal_stats['inactive_contracts'] + removal_stats['orphaned_entries']} total entries")

        # Step 4: Generate report
        generate_report(stale_contracts, marked_inactive, removal_stats)

        # Close connection
        conn.close()
        logger.info("Cleanup complete!")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())