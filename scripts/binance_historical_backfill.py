#!/usr/bin/env python3
"""
Binance Historical Funding Rate Backfill
========================================
One-time script to backfill 30 days of historical funding rates for all Binance perpetuals.
"""

import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from exchanges.binance_exchange import BinanceExchange
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger

logger = setup_logger("BinanceBackfill")


def run_backfill(days: int = 30, batch_size: int = 10, dry_run: bool = False):
    """
    Run the historical funding rate backfill for Binance.
    
    Args:
        days: Number of days to backfill
        batch_size: Number of symbols to process in each batch
        dry_run: If True, fetch data but don't upload to database
    """
    logger.info("="*60)
    logger.info("BINANCE HISTORICAL FUNDING RATE BACKFILL")
    logger.info("="*60)
    logger.info(f"Days to backfill: {days}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("="*60)
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        exchange = BinanceExchange()
        
        if not dry_run:
            db_manager = PostgresManager()
            
            # Test database connection
            if not db_manager.test_connection():
                logger.error("Database connection failed!")
                return False
            logger.info("Database connection successful")
        else:
            logger.info("Dry run mode - database operations disabled")
            db_manager = None
        
        # Start the backfill
        logger.info(f"Starting backfill for {days} days of historical data...")
        start_time = time.time()
        
        # Fetch all historical data
        historical_df = exchange.fetch_all_perpetuals_historical(
            days=days, 
            batch_size=batch_size
        )
        
        if historical_df.empty:
            logger.warning("No historical data fetched!")
            return False
        
        # Show statistics
        logger.info("="*60)
        logger.info("BACKFILL STATISTICS")
        logger.info("="*60)
        logger.info(f"Total records fetched: {len(historical_df):,}")
        logger.info(f"Unique symbols: {historical_df['symbol'].nunique()}")
        logger.info(f"Date range: {historical_df['funding_time'].min()} to {historical_df['funding_time'].max()}")
        
        # Show sample data
        logger.info("\nSample records:")
        sample = historical_df.head(5)
        for _, row in sample.iterrows():
            try:
                rate_val = float(row['funding_rate']) if pd.notna(row['funding_rate']) else 0.0
                logger.info(f"  {row['symbol']}: {row['funding_time']} - Rate: {rate_val:.6f}")
            except:
                logger.info(f"  {row['symbol']}: {row['funding_time']} - Rate: {row['funding_rate']}")
        
        # Upload to database if not dry run
        if not dry_run and db_manager:
            logger.info("\nUploading to database...")
            success = db_manager.upload_historical_funding_rates(historical_df)
            
            if success:
                logger.info("Data successfully uploaded to database!")
            else:
                logger.error("Failed to upload data to database")
                return False
        else:
            logger.info("\nDry run - skipping database upload")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        logger.info("="*60)
        logger.info(f"Backfill completed in {execution_time:.2f} seconds")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Backfill historical funding rates from Binance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full 30-day backfill
  python binance_historical_backfill.py
  
  # Run 7-day backfill
  python binance_historical_backfill.py --days 7
  
  # Dry run (no database upload)
  python binance_historical_backfill.py --dry-run
  
  # Custom batch size for rate limiting
  python binance_historical_backfill.py --batch-size 5
        """
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=30,
        help='Number of days to backfill (default: 30)'
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=10,
        help='Number of symbols to process in each batch (default: 10)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not upload to database'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.days < 1 or args.days > 90:
        logger.error("Days must be between 1 and 90")
        return 1
    
    if args.batch_size < 1 or args.batch_size > 50:
        logger.error("Batch size must be between 1 and 50")
        return 1
    
    # Run the backfill
    success = run_backfill(
        days=args.days,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())