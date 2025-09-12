#!/usr/bin/env python3
"""
Retry Incomplete Contracts
===========================
Automatically retry fetching historical data for contracts with low completeness.
Uses the backfill completeness validator to identify contracts needing retry.
"""

import sys
import time
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from exchanges.binance_exchange import BinanceExchange
from exchanges.kucoin_exchange import KuCoinExchange
from exchanges.backpack_exchange import BackpackExchange
from exchanges.hyperliquid_exchange import HyperliquidExchange
from database.postgres_manager import PostgresManager
from utils.backfill_completeness import BackfillCompletenessValidator
from utils.logger import setup_logger

logger = setup_logger("RetryIncomplete")

# Exchange mapping
EXCHANGE_CLASSES = {
    'binance': BinanceExchange,
    'kucoin': KuCoinExchange,
    'backpack': BackpackExchange,
    'hyperliquid': HyperliquidExchange,
}


class RetryIncompleteContracts:
    """Retry mechanism for incomplete contract data."""
    
    def __init__(self, threshold: float = 95.0, days: int = 30, dry_run: bool = False):
        """
        Initialize retry mechanism.
        
        Args:
            threshold: Minimum completeness percentage required (default 95%)
            days: Number of days to analyze/fetch (default 30)
            dry_run: If True, fetch data but don't upload to database
        """
        self.threshold = threshold
        self.days = days
        self.dry_run = dry_run
        self.db_manager = None
        self.validator = BackfillCompletenessValidator()
        
        # Track retry results
        self.retry_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'threshold': threshold,
            'days': days,
            'contracts_analyzed': 0,
            'contracts_needing_retry': 0,
            'contracts_retried': 0,
            'contracts_improved': 0,
            'contracts_failed': 0,
            'details': []
        }
        
    def initialize(self) -> bool:
        """Initialize database connection."""
        try:
            if not self.dry_run:
                self.db_manager = PostgresManager()
                if not self.db_manager.test_connection():
                    logger.error("Database connection failed!")
                    return False
                logger.info("Database connection successful")
            else:
                logger.info("Dry run mode - database operations disabled")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def identify_incomplete_contracts(self) -> List[Dict]:
        """
        Identify contracts with completeness below threshold.
        
        Returns:
            List of contracts needing retry with their details
        """
        logger.info(f"Identifying contracts with completeness < {self.threshold}%...")
        
        # Run validation to get current completeness
        validation_results = self.validator.validate_all_contracts(self.days)
        
        if 'error' in validation_results:
            logger.error(f"Validation failed: {validation_results['error']}")
            return []
        
        incomplete_contracts = []
        
        for contract in validation_results.get('contracts', []):
            completeness = contract.get('completeness_percentage', 0)
            
            if completeness < self.threshold:
                # Only retry if we have some data (not completely missing)
                if contract.get('actual_points', 0) > 0:
                    incomplete_contracts.append({
                        'exchange': contract['exchange'],
                        'symbol': contract['symbol'],
                        'completeness': completeness,
                        'actual_points': contract.get('actual_points', 0),
                        'expected_points': contract.get('expected_points', 0),
                        'gaps': contract.get('gaps_detected', 0),
                        'funding_interval': contract.get('funding_interval_hours'),
                        'status': contract.get('status')
                    })
        
        self.retry_results['contracts_analyzed'] = len(validation_results.get('contracts', []))
        self.retry_results['contracts_needing_retry'] = len(incomplete_contracts)
        
        logger.info(f"Found {len(incomplete_contracts)} contracts with completeness < {self.threshold}%")
        
        return incomplete_contracts
    
    def fetch_missing_data(self, exchange_name: str, symbol: str, gaps: List[Dict] = None) -> pd.DataFrame:
        """
        Fetch missing historical data for a specific contract.
        
        Args:
            exchange_name: Exchange name
            symbol: Contract symbol
            gaps: Optional list of specific gap periods to fetch
            
        Returns:
            DataFrame with fetched historical data
        """
        try:
            # Get exchange class
            exchange_class = EXCHANGE_CLASSES.get(exchange_name.lower())
            if not exchange_class:
                logger.error(f"Exchange {exchange_name} not supported")
                return pd.DataFrame()
            
            # Initialize exchange
            exchange = exchange_class()
            
            # Determine date range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=self.days)
            
            logger.info(f"Fetching {exchange_name}:{symbol} from {start_time.date()} to {end_time.date()}")
            
            # Try to fetch historical data for this specific symbol
            # This approach varies by exchange implementation
            if hasattr(exchange, 'fetch_perpetual_historical'):
                # Use single symbol fetch if available
                historical_df = exchange.fetch_perpetual_historical(
                    symbol=symbol,
                    start_time=start_time,
                    end_time=end_time
                )
            else:
                # Fall back to fetching all and filtering
                logger.warning(f"{exchange_name} doesn't support single symbol fetch, using batch fetch")
                historical_df = exchange.fetch_all_perpetuals_historical(
                    days=self.days,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Filter for our symbol
                if not historical_df.empty and 'symbol' in historical_df.columns:
                    historical_df = historical_df[historical_df['symbol'] == symbol]
            
            if not historical_df.empty:
                logger.info(f"Fetched {len(historical_df)} records for {exchange_name}:{symbol}")
            else:
                logger.warning(f"No data fetched for {exchange_name}:{symbol}")
            
            return historical_df
            
        except Exception as e:
            logger.error(f"Error fetching data for {exchange_name}:{symbol}: {e}")
            return pd.DataFrame()
    
    def retry_contract(self, contract: Dict) -> Dict:
        """
        Retry fetching data for a single incomplete contract.
        
        Args:
            contract: Contract details from identify_incomplete_contracts
            
        Returns:
            Result dictionary with retry outcome
        """
        exchange = contract['exchange']
        symbol = contract['symbol']
        original_completeness = contract['completeness']
        
        logger.info(f"Retrying {exchange}:{symbol} (current completeness: {original_completeness:.1f}%)")
        
        result = {
            'exchange': exchange,
            'symbol': symbol,
            'original_completeness': original_completeness,
            'new_completeness': original_completeness,
            'records_added': 0,
            'success': False,
            'error': None
        }
        
        try:
            # Fetch missing data
            historical_df = self.fetch_missing_data(exchange, symbol)
            
            if historical_df.empty:
                result['error'] = "No data fetched"
                return result
            
            # Upload to database if not dry run
            if not self.dry_run and self.db_manager:
                success = self.db_manager.upload_historical_funding_rates(historical_df)
                
                if success:
                    result['records_added'] = len(historical_df)
                    
                    # Re-validate to get new completeness
                    new_validation = self.validator.validate_contract(exchange, symbol, self.days)
                    result['new_completeness'] = new_validation.get('completeness_percentage', original_completeness)
                    
                    if result['new_completeness'] > original_completeness:
                        result['success'] = True
                        logger.info(f"SUCCESS: {exchange}:{symbol} improved: {original_completeness:.1f}% -> {result['new_completeness']:.1f}%")
                    else:
                        logger.warning(f"WARNING: {exchange}:{symbol} no improvement: {result['new_completeness']:.1f}%")
                else:
                    result['error'] = "Upload failed"
            else:
                # Dry run
                result['records_added'] = len(historical_df)
                result['success'] = True
                logger.info(f"[DRY RUN] Would add {len(historical_df)} records for {exchange}:{symbol}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error retrying {exchange}:{symbol}: {e}")
        
        return result
    
    def run(self, max_retries: int = None) -> Dict:
        """
        Run the retry process for all incomplete contracts.
        
        Args:
            max_retries: Maximum number of contracts to retry (None for all)
            
        Returns:
            Summary of retry results
        """
        # Initialize
        if not self.initialize():
            return {'error': 'Initialization failed'}
        
        # Identify incomplete contracts
        incomplete_contracts = self.identify_incomplete_contracts()
        
        if not incomplete_contracts:
            logger.info("No contracts need retry!")
            return self.retry_results
        
        # Sort by completeness (lowest first) to prioritize worst cases
        incomplete_contracts.sort(key=lambda x: x['completeness'])
        
        # Limit number of retries if specified
        if max_retries:
            incomplete_contracts = incomplete_contracts[:max_retries]
            logger.info(f"Limiting retry to first {max_retries} contracts")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting retry for {len(incomplete_contracts)} contracts")
        logger.info(f"{'='*60}\n")
        
        # Retry each contract
        for i, contract in enumerate(incomplete_contracts, 1):
            logger.info(f"\n[{i}/{len(incomplete_contracts)}] Processing {contract['exchange']}:{contract['symbol']}")
            
            result = self.retry_contract(contract)
            self.retry_results['details'].append(result)
            self.retry_results['contracts_retried'] += 1
            
            if result['success']:
                if result['new_completeness'] > result['original_completeness']:
                    self.retry_results['contracts_improved'] += 1
            else:
                self.retry_results['contracts_failed'] += 1
            
            # Small delay between retries to avoid overwhelming APIs
            if i < len(incomplete_contracts):
                time.sleep(1)
        
        # Print summary
        self.print_summary()
        
        # Save report
        self.save_report()
        
        return self.retry_results
    
    def print_summary(self):
        """Print retry summary to console."""
        print("\n" + "="*60)
        print("RETRY INCOMPLETE CONTRACTS SUMMARY")
        print("="*60)
        print(f"Timestamp: {self.retry_results['timestamp']}")
        print(f"Threshold: {self.retry_results['threshold']}%")
        print(f"Analysis Period: {self.retry_results['days']} days")
        print(f"\nContracts Analyzed: {self.retry_results['contracts_analyzed']}")
        print(f"Contracts Needing Retry: {self.retry_results['contracts_needing_retry']}")
        print(f"Contracts Retried: {self.retry_results['contracts_retried']}")
        print(f"  Improved: {self.retry_results['contracts_improved']}")
        print(f"  Failed: {self.retry_results['contracts_failed']}")
        
        if self.retry_results['details']:
            print("\nTop Improvements:")
            improvements = [d for d in self.retry_results['details'] if d['new_completeness'] > d['original_completeness']]
            improvements.sort(key=lambda x: x['new_completeness'] - x['original_completeness'], reverse=True)
            
            for detail in improvements[:5]:
                improvement = detail['new_completeness'] - detail['original_completeness']
                print(f"  {detail['exchange']}:{detail['symbol']}: {detail['original_completeness']:.1f}% -> {detail['new_completeness']:.1f}% (+{improvement:.1f}%)")
    
    def save_report(self, filename: str = None):
        """Save retry report to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"retry_incomplete_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.retry_results, f, indent=2, default=str)
        
        logger.info(f"Report saved to: {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Retry incomplete historical data contracts')
    parser.add_argument('--threshold', type=float, default=95.0,
                       help='Minimum completeness threshold percentage (default: 95)')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to analyze (default: 30)')
    parser.add_argument('--max-retries', type=int, default=None,
                       help='Maximum number of contracts to retry (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Fetch data but do not upload to database')
    
    args = parser.parse_args()
    
    # Create retry instance
    retry = RetryIncompleteContracts(
        threshold=args.threshold,
        days=args.days,
        dry_run=args.dry_run
    )
    
    # Run retry process
    results = retry.run(max_retries=args.max_retries)
    
    # Return exit code based on success
    if 'error' in results:
        sys.exit(1)
    elif results['contracts_failed'] > 0:
        sys.exit(2)  # Partial failure
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()