#!/usr/bin/env python3
"""
Historical Funding Rate Updater
================================
Continuously updates historical funding rates with hourly checks.
"""

import sys
import time
import signal
import threading
import schedule
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from exchanges.binance_exchange import BinanceExchange
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger

logger = setup_logger("HistoricalUpdater")


class HistoricalFundingUpdater:
    """Manages continuous updates of historical funding rates."""
    
    def __init__(self):
        """Initialize the updater."""
        self.exchange = BinanceExchange()
        self.db_manager = PostgresManager()
        self.running = False
        self.shutdown_event = threading.Event()
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'last_update': None
        }
    
    def update_symbol(self, symbol: str, market_type: str = 'USD-M') -> bool:
        """
        Update historical funding rates for a specific symbol.
        
        Args:
            symbol: Trading symbol
            market_type: Market type (USD-M or COIN-M)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the latest funding time from database
            latest_time = self.db_manager.get_latest_funding_time('Binance', symbol)
            
            if latest_time:
                # Fetch only new data since last update
                start_time = latest_time + timedelta(seconds=1)
                logger.debug(f"Updating {symbol} from {start_time}")
            else:
                # No existing data, fetch last 30 days
                start_time = datetime.now(timezone.utc) - timedelta(days=30)
                logger.debug(f"No existing data for {symbol}, fetching last 30 days")
            
            end_time = datetime.now(timezone.utc)
            
            # Skip if we're already up to date (within 1 hour)
            if latest_time and (end_time - latest_time).total_seconds() < 3600:
                logger.debug(f"{symbol} is up to date")
                return True
            
            # Fetch historical data
            df = self.exchange.fetch_historical_funding_rates(
                symbol=symbol,
                market_type=market_type,
                start_time=start_time,
                end_time=end_time
            )
            
            if df.empty:
                logger.debug(f"No new data for {symbol}")
                return True
            
            # Upload to database
            success = self.db_manager.upload_historical_funding_rates(df)
            
            if success:
                logger.info(f"Updated {symbol}: {len(df)} new records")
                return True
            else:
                logger.error(f"Failed to upload data for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating {symbol}: {e}")
            return False
    
    def update_all_symbols(self):
        """Update all Binance perpetual symbols."""
        logger.info("Starting hourly update for all symbols...")
        start_time = time.time()
        
        try:
            # Get list of all perpetual symbols
            usdm_symbols = self.exchange._get_perpetual_symbols('USD-M')
            coinm_symbols = self.exchange._get_perpetual_symbols('COIN-M')
            
            total_symbols = len(usdm_symbols) + len(coinm_symbols)
            updated_count = 0
            failed_count = 0
            
            # Update USD-M symbols
            for symbol in usdm_symbols:
                if self.shutdown_event.is_set():
                    logger.info("Shutdown requested, stopping updates")
                    break
                
                if self.update_symbol(symbol, 'USD-M'):
                    updated_count += 1
                else:
                    failed_count += 1
                
                # Small delay to respect rate limits
                time.sleep(0.1)
            
            # Update COIN-M symbols
            for symbol in coinm_symbols:
                if self.shutdown_event.is_set():
                    logger.info("Shutdown requested, stopping updates")
                    break
                
                if self.update_symbol(symbol, 'COIN-M'):
                    updated_count += 1
                else:
                    failed_count += 1
                
                # Small delay to respect rate limits
                time.sleep(0.1)
            
            # Update statistics
            self.update_stats['total_updates'] += 1
            self.update_stats['successful_updates'] += updated_count
            self.update_stats['failed_updates'] += failed_count
            self.update_stats['last_update'] = datetime.now(timezone.utc)
            
            execution_time = time.time() - start_time
            logger.info(f"Update completed: {updated_count}/{total_symbols} symbols updated in {execution_time:.2f}s")
            
            if failed_count > 0:
                logger.warning(f"{failed_count} symbols failed to update")
            
        except Exception as e:
            logger.error(f"Error in update_all_symbols: {e}")
    
    def run_scheduler(self, interval_minutes: int = 60):
        """
        Run the scheduler for continuous updates.
        
        Args:
            interval_minutes: Minutes between updates (default: 60)
        """
        self.running = True
        
        logger.info("="*60)
        logger.info("HISTORICAL FUNDING RATE UPDATER")
        logger.info("="*60)
        logger.info(f"Update interval: {interval_minutes} minutes")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)
        
        # Schedule the updates
        schedule.every(interval_minutes).minutes.do(self.update_all_symbols)
        
        # Run initial update
        logger.info("Running initial update...")
        self.update_all_symbols()
        
        # Main scheduler loop
        while self.running and not self.shutdown_event.is_set():
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Scheduler stopped")
        self._print_statistics()
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.shutdown_event.set()
    
    def _print_statistics(self):
        """Print update statistics."""
        logger.info("="*60)
        logger.info("UPDATE STATISTICS")
        logger.info("="*60)
        logger.info(f"Total update cycles: {self.update_stats['total_updates']}")
        logger.info(f"Successful symbol updates: {self.update_stats['successful_updates']}")
        logger.info(f"Failed symbol updates: {self.update_stats['failed_updates']}")
        if self.update_stats['last_update']:
            logger.info(f"Last update: {self.update_stats['last_update']}")
        logger.info("="*60)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("\nShutdown signal received...")
    if 'updater' in globals():
        updater.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Continuously update historical funding rates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with hourly updates (default)
  python historical_updater.py
  
  # Run with 30-minute updates
  python historical_updater.py --interval 30
  
  # Run single update and exit
  python historical_updater.py --once
        """
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=60,
        help='Update interval in minutes (default: 60)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run single update and exit'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.interval < 5 or args.interval > 1440:
        logger.error("Interval must be between 5 and 1440 minutes")
        return 1
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run updater
    global updater
    updater = HistoricalFundingUpdater()
    
    try:
        if args.once:
            # Run single update
            logger.info("Running single update...")
            updater.update_all_symbols()
            updater._print_statistics()
        else:
            # Run continuous scheduler
            updater.run_scheduler(interval_minutes=args.interval)
    except Exception as e:
        logger.error(f"Updater failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())