#!/usr/bin/env python3
"""
Contract Monitor Utility
========================
Monitors contracts for staleness and automatically marks delisted/inactive contracts.
Should be run periodically (e.g., every hour) to maintain data quality.
"""

import os
import psycopg2
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import setup_logger
from config.settings import API_MAX_DATA_AGE_DAYS

logger = setup_logger("contract_monitor")

def get_db_connection():
    """Create database connection."""
    from dotenv import load_dotenv
    load_dotenv()

    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DATABASE', 'exchange_data'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres123')
    )

def monitor_stale_contracts(conn, threshold_hours: int = 24) -> List[Tuple]:
    """
    Monitor for contracts that haven't been updated recently.

    Args:
        conn: Database connection
        threshold_hours: Hours before considering a contract stale

    Returns:
        List of contracts that are potentially delisted
    """
    cur = conn.cursor()

    # Find contracts that are stale but marked as active
    query = """
        SELECT
            ed.exchange,
            ed.symbol,
            ed.base_asset,
            ed.apr,
            ed.last_updated,
            EXTRACT(epoch FROM (NOW() - ed.last_updated))/3600 as hours_old,
            cm.is_active
        FROM exchange_data ed
        LEFT JOIN contract_metadata cm
            ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
        WHERE ed.last_updated < NOW() - INTERVAL %s
            AND (cm.is_active = true OR cm.is_active IS NULL)
        ORDER BY ed.last_updated ASC
    """

    cur.execute(query, (f"{threshold_hours} hours",))
    stale_contracts = cur.fetchall()

    if stale_contracts:
        logger.warning(f"Found {len(stale_contracts)} potentially delisted contracts")
        for contract in stale_contracts[:5]:  # Log first 5
            exchange, symbol, asset, apr, last_update, hours, is_active = contract
            logger.warning(f"  {exchange} {symbol} ({asset}): {hours:.1f} hours old, APR: {apr:.2f}%")

    return stale_contracts

def auto_mark_inactive(conn, stale_contracts: List[Tuple], threshold_hours: int = 48) -> int:
    """
    Automatically mark very stale contracts as inactive.

    Args:
        conn: Database connection
        stale_contracts: List of stale contracts
        threshold_hours: Hours threshold for auto-marking as inactive

    Returns:
        Number of contracts marked as inactive
    """
    cur = conn.cursor()
    marked_inactive = 0

    for contract in stale_contracts:
        exchange, symbol, asset, apr, last_update, hours_old, is_active = contract

        # Only auto-mark if older than threshold
        if hours_old > threshold_hours:
            # Update or insert contract_metadata
            cur.execute("""
                INSERT INTO contract_metadata (exchange, symbol, is_active, last_seen_at, notes)
                VALUES (%s, %s, false, %s, %s)
                ON CONFLICT (exchange, symbol)
                DO UPDATE SET
                    is_active = false,
                    last_seen_at = EXCLUDED.last_seen_at,
                    notes = COALESCE(contract_metadata.notes || '; ', '') || EXCLUDED.notes
            """, (
                exchange,
                symbol,
                last_update,
                f"Auto-marked inactive at {datetime.now(timezone.utc).isoformat()} (stale for {hours_old:.1f} hours)"
            ))

            logger.info(f"Auto-marked inactive: {exchange} {symbol} (stale for {hours_old:.1f} hours)")
            marked_inactive += 1

    if marked_inactive > 0:
        conn.commit()
        logger.info(f"Automatically marked {marked_inactive} contracts as inactive")

    return marked_inactive

def check_reactivations(conn) -> int:
    """
    Check if any previously inactive contracts have started updating again.

    Args:
        conn: Database connection

    Returns:
        Number of reactivated contracts
    """
    cur = conn.cursor()

    # Find inactive contracts that have been updated recently
    query = """
        SELECT
            cm.exchange,
            cm.symbol,
            ed.last_updated,
            EXTRACT(epoch FROM (NOW() - ed.last_updated))/3600 as hours_since_update
        FROM contract_metadata cm
        INNER JOIN exchange_data ed
            ON cm.exchange = ed.exchange AND cm.symbol = ed.symbol
        WHERE cm.is_active = false
            AND ed.last_updated > NOW() - INTERVAL '2 hours'
    """

    cur.execute(query)
    reactivate_candidates = cur.fetchall()

    reactivated = 0
    for exchange, symbol, last_update, hours in reactivate_candidates:
        # Mark as active again
        cur.execute("""
            UPDATE contract_metadata
            SET is_active = true,
                notes = COALESCE(notes || '; ', '') || %s
            WHERE exchange = %s AND symbol = %s
        """, (
            f"Reactivated at {datetime.now(timezone.utc).isoformat()} (updated {hours:.1f} hours ago)",
            exchange,
            symbol
        ))

        logger.info(f"Reactivated: {exchange} {symbol} (updated {hours:.1f} hours ago)")
        reactivated += 1

    if reactivated > 0:
        conn.commit()
        logger.info(f"Reactivated {reactivated} contracts")

    return reactivated

def generate_status_report(conn) -> Dict:
    """
    Generate a status report of contract health.

    Args:
        conn: Database connection

    Returns:
        Dictionary with contract health statistics
    """
    cur = conn.cursor()

    # Get total contracts
    cur.execute("SELECT COUNT(*) FROM exchange_data")
    total_contracts = cur.fetchone()[0]

    # Get active contracts
    cur.execute("""
        SELECT COUNT(*)
        FROM exchange_data ed
        LEFT JOIN contract_metadata cm
            ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
        WHERE cm.is_active = true OR cm.is_active IS NULL
    """)
    active_contracts = cur.fetchone()[0]

    # Get inactive contracts
    cur.execute("""
        SELECT COUNT(*)
        FROM contract_metadata
        WHERE is_active = false
    """)
    inactive_contracts = cur.fetchone()[0]

    # Get stale contracts (not updated in last 24 hours)
    cur.execute("""
        SELECT COUNT(*)
        FROM exchange_data
        WHERE last_updated < NOW() - INTERVAL '24 hours'
    """)
    stale_24h = cur.fetchone()[0]

    # Get very stale contracts (not updated in last 48 hours)
    cur.execute("""
        SELECT COUNT(*)
        FROM exchange_data
        WHERE last_updated < NOW() - INTERVAL '48 hours'
    """)
    stale_48h = cur.fetchone()[0]

    # Get contracts by exchange
    cur.execute("""
        SELECT exchange, COUNT(*) as count
        FROM exchange_data
        GROUP BY exchange
        ORDER BY count DESC
    """)
    by_exchange = dict(cur.fetchall())

    return {
        'total_contracts': total_contracts,
        'active_contracts': active_contracts,
        'inactive_contracts': inactive_contracts,
        'stale_24h': stale_24h,
        'stale_48h': stale_48h,
        'by_exchange': by_exchange,
        'health_percentage': (active_contracts / total_contracts * 100) if total_contracts > 0 else 0
    }

def run_monitoring_cycle(
    threshold_warn_hours: int = 24,
    threshold_inactive_hours: int = 48,
    dry_run: bool = False
) -> Dict:
    """
    Run a complete monitoring cycle.

    Args:
        threshold_warn_hours: Hours before warning about stale contracts
        threshold_inactive_hours: Hours before auto-marking as inactive
        dry_run: If True, don't make any changes

    Returns:
        Dictionary with monitoring results
    """
    logger.info("Starting contract monitoring cycle...")

    try:
        conn = get_db_connection()

        # Get initial status
        initial_status = generate_status_report(conn)
        logger.info(f"Initial status: {initial_status['active_contracts']} active, "
                   f"{initial_status['inactive_contracts']} inactive, "
                   f"{initial_status['stale_24h']} stale (24h)")

        # Monitor for stale contracts
        stale_contracts = monitor_stale_contracts(conn, threshold_warn_hours)

        # Auto-mark very stale contracts as inactive
        marked_inactive = 0
        if not dry_run and stale_contracts:
            marked_inactive = auto_mark_inactive(conn, stale_contracts, threshold_inactive_hours)

        # Check for reactivations
        reactivated = 0
        if not dry_run:
            reactivated = check_reactivations(conn)

        # Get final status
        final_status = generate_status_report(conn)

        # Generate results
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dry_run': dry_run,
            'initial_status': initial_status,
            'final_status': final_status,
            'stale_contracts_found': len(stale_contracts),
            'marked_inactive': marked_inactive,
            'reactivated': reactivated,
            'health_improved': final_status['health_percentage'] > initial_status['health_percentage']
        }

        logger.info(f"Monitoring cycle complete: {marked_inactive} marked inactive, "
                   f"{reactivated} reactivated, health: {final_status['health_percentage']:.1f}%")

        conn.close()
        return results

    except Exception as e:
        logger.error(f"Error during monitoring cycle: {e}")
        raise

def main():
    """Main monitoring function."""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor contract health and mark delisted contracts')
    parser.add_argument('--warn-hours', type=int, default=24,
                       help='Hours before warning about stale contracts (default: 24)')
    parser.add_argument('--inactive-hours', type=int, default=48,
                       help='Hours before auto-marking as inactive (default: 48)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--report-only', action='store_true',
                       help='Only generate a status report')

    args = parser.parse_args()

    try:
        if args.report_only:
            conn = get_db_connection()
            report = generate_status_report(conn)
            conn.close()

            print("\n=== Contract Health Report ===")
            print(f"Total contracts: {report['total_contracts']}")
            print(f"Active contracts: {report['active_contracts']}")
            print(f"Inactive contracts: {report['inactive_contracts']}")
            print(f"Stale (24h): {report['stale_24h']}")
            print(f"Very stale (48h): {report['stale_48h']}")
            print(f"Health percentage: {report['health_percentage']:.1f}%")
            print("\nBy exchange:")
            for exchange, count in report['by_exchange'].items():
                print(f"  {exchange}: {count}")
        else:
            results = run_monitoring_cycle(
                threshold_warn_hours=args.warn_hours,
                threshold_inactive_hours=args.inactive_hours,
                dry_run=args.dry_run
            )

            if args.dry_run:
                print("\n[DRY RUN] No changes were made")

            print(f"\n=== Monitoring Results ===")
            print(f"Stale contracts found: {results['stale_contracts_found']}")
            print(f"Marked inactive: {results['marked_inactive']}")
            print(f"Reactivated: {results['reactivated']}")
            print(f"Health: {results['final_status']['health_percentage']:.1f}%")

    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()