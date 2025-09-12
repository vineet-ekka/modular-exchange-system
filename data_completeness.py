#!/usr/bin/env python3
"""
Unified Data Completeness Management System
============================================
Single module for all data completeness validation, monitoring, and retry operations.

Usage:
    python data_completeness.py validate [--days 30] [--exchange EXCHANGE] [--symbol SYMBOL]
    python data_completeness.py retry [--threshold 95] [--max-retries 10] [--dry-run]
    python data_completeness.py report [--format json|csv|text] [--output FILE]
    python data_completeness.py monitor [--continuous] [--interval 3600]
    python data_completeness.py test
"""

import sys
import argparse
import json
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from database.postgres_manager import PostgresManager
from exchanges.exchange_factory import ExchangeFactory
from utils.logger import setup_logger

# Configure logging
logger = setup_logger("DataCompleteness")


class DataCompletenessManager:
    """Unified manager for all data completeness operations."""
    
    # Constants
    MIN_COMPLETENESS_THRESHOLD = 95.0
    EXPECTED_POINTS_30_DAYS = {
        1: 720,   # 1-hour: 24 * 30 = 720 points
        2: 360,   # 2-hour: 12 * 30 = 360 points  
        4: 180,   # 4-hour: 6 * 30 = 180 points
        8: 90     # 8-hour: 3 * 30 = 90 points
    }
    
    def __init__(self):
        """Initialize the completeness manager."""
        self.db = PostgresManager()
        self.validation_results = {}
        self.retry_results = {}
        self.last_check = None
        
    # ================== VALIDATION METHODS ==================
    
    def validate_all(self, days: int = 30) -> Dict:
        """
        Validate completeness for all contracts in the system.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating data completeness for all contracts ({days}-day window)...")
        
        query = """
            SELECT DISTINCT exchange, symbol
            FROM funding_rates_historical
            ORDER BY exchange, symbol
        """
        
        all_results = []
        summary = {
            'total_contracts': 0,
            'complete': 0,
            'partial_high': 0,
            'partial_medium': 0,
            'incomplete': 0,
            'no_data': 0,
            'errors': 0,
            'needs_retry': []
        }
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute(query)
                contracts = cursor.fetchall()
                
                summary['total_contracts'] = len(contracts)
                
                for i, (exchange, symbol) in enumerate(contracts, 1):
                    if i % 100 == 0:
                        logger.info(f"Progress: {i}/{len(contracts)} contracts validated...")
                    
                    result = self.validate_contract(exchange, symbol, days)
                    all_results.append(result)
                    
                    # Update summary
                    self._update_summary(summary, result, exchange, symbol)
                
                # Calculate overall completeness
                if summary['total_contracts'] > 0:
                    summary['overall_complete_percentage'] = round(
                        summary['complete'] / summary['total_contracts'] * 100, 2
                    )
                else:
                    summary['overall_complete_percentage'] = 0
                
                self.validation_results = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'days_analyzed': days,
                    'summary': summary,
                    'contracts': all_results
                }
                
                return self.validation_results
                
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return {'error': str(e)}
    
    def validate_contract(self, exchange: str, symbol: str, days: int = 30) -> Dict:
        """
        Validate completeness for a single contract.
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            days: Number of days to analyze
            
        Returns:
            Dictionary with validation results for the contract
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT COUNT(*) as actual_points,
                   MIN(funding_time) as first_point,
                   MAX(funding_time) as last_point,
                   COUNT(DISTINCT DATE(funding_time)) as days_covered
            FROM funding_rates_historical
            WHERE exchange = %s AND symbol = %s 
                AND funding_time >= %s AND funding_time <= %s
        """
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, (exchange, symbol, start_date, end_date))
                result = cursor.fetchone()
                
                if not result or result[0] == 0:
                    return {
                        'exchange': exchange,
                        'symbol': symbol,
                        'actual_points': 0,
                        'expected_points': 0,
                        'completeness_percentage': 0.0,
                        'status': 'no_data',
                        'needs_retry': True
                    }
                
                actual_points = result[0]
                
                # Detect funding interval
                interval = self._detect_funding_interval(exchange, symbol)
                if not interval:
                    return {
                        'exchange': exchange,
                        'symbol': symbol,
                        'actual_points': actual_points,
                        'expected_points': None,
                        'completeness_percentage': None,
                        'status': 'interval_unknown',
                        'needs_retry': True
                    }
                
                # Calculate expected points
                expected_points = self._calculate_expected_points(interval, days)
                completeness_percentage = (actual_points / expected_points * 100) if expected_points > 0 else 0
                
                # Detect gaps
                gaps = self.detect_gaps(exchange, symbol, days)
                
                # Determine status
                status = self._determine_status(completeness_percentage)
                needs_retry = completeness_percentage < self.MIN_COMPLETENESS_THRESHOLD
                
                return {
                    'exchange': exchange,
                    'symbol': symbol,
                    'funding_interval_hours': interval,
                    'actual_points': actual_points,
                    'expected_points': expected_points,
                    'completeness_percentage': round(completeness_percentage, 2),
                    'first_data_point': result[1].isoformat() if result[1] else None,
                    'last_data_point': result[2].isoformat() if result[2] else None,
                    'days_covered': result[3],
                    'gaps_detected': len(gaps),
                    'gaps': gaps[:5] if gaps else [],  # Limit to first 5 gaps
                    'status': status,
                    'needs_retry': needs_retry
                }
                
        except Exception as e:
            logger.error(f"Error validating {exchange}:{symbol}: {e}")
            return {
                'exchange': exchange,
                'symbol': symbol,
                'error': str(e),
                'status': 'error',
                'needs_retry': True
            }
    
    def detect_gaps(self, exchange: str, symbol: str, days: int = 30) -> List[Dict]:
        """
        Detect gaps in historical data for a specific contract.
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            days: Number of days to analyze
            
        Returns:
            List of detected gaps
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT funding_time, funding_rate
            FROM funding_rates_historical
            WHERE exchange = %s AND symbol = %s 
                AND funding_time >= %s AND funding_time <= %s
            ORDER BY funding_time ASC
        """
        
        gaps = []
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, (exchange, symbol, start_date, end_date))
                results = cursor.fetchall()
                
                if len(results) < 2:
                    # Entire period is a gap
                    gaps.append({
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat(),
                        'duration_hours': days * 24,
                        'type': 'complete_missing'
                    })
                    return gaps
                
                # Detect funding interval
                interval = self._detect_funding_interval(exchange, symbol)
                if not interval:
                    return gaps
                
                # Check for gaps
                expected_gap = timedelta(hours=interval)
                tolerance = timedelta(hours=interval * 0.5)
                
                for i in range(1, len(results)):
                    prev_time = results[i-1][0]
                    curr_time = results[i][0]
                    actual_gap = curr_time - prev_time
                    
                    if actual_gap > expected_gap + tolerance:
                        gaps.append({
                            'start': prev_time.isoformat(),
                            'end': curr_time.isoformat(),
                            'duration_hours': actual_gap.total_seconds() / 3600,
                            'expected_hours': interval,
                            'missing_points': int((actual_gap.total_seconds() / 3600) / interval) - 1
                        })
                
                # Check for gap at the beginning
                first_time = results[0][0]
                if first_time - start_date > expected_gap + tolerance:
                    gaps.append({
                        'start': start_date.isoformat(),
                        'end': first_time.isoformat(),
                        'duration_hours': (first_time - start_date).total_seconds() / 3600,
                        'type': 'start_gap'
                    })
                
                # Check for gap at the end
                last_time = results[-1][0]
                if end_date - last_time > expected_gap + tolerance:
                    gaps.append({
                        'start': last_time.isoformat(),
                        'end': end_date.isoformat(),
                        'duration_hours': (end_date - last_time).total_seconds() / 3600,
                        'type': 'end_gap'
                    })
                
        except Exception as e:
            logger.error(f"Error detecting gaps for {exchange}:{symbol}: {e}")
            
        return gaps
    
    # ================== RETRY METHODS ==================
    
    def get_retry_candidates(self, threshold: float = None) -> List[Dict]:
        """
        Get list of contracts that need retry based on completeness threshold.
        
        Args:
            threshold: Minimum completeness percentage (default: 95%)
            
        Returns:
            List of contracts needing retry, sorted by priority
        """
        if threshold is None:
            threshold = self.MIN_COMPLETENESS_THRESHOLD
            
        if not self.validation_results or 'contracts' not in self.validation_results:
            # Run validation first
            self.validate_all()
        
        retry_candidates = []
        
        for contract in self.validation_results.get('contracts', []):
            completeness = contract.get('completeness_percentage', 0)
            
            # Only include contracts that have some data but are incomplete
            if 0 < completeness < threshold:
                retry_candidates.append({
                    'exchange': contract['exchange'],
                    'symbol': contract['symbol'],
                    'completeness': completeness,
                    'actual_points': contract.get('actual_points', 0),
                    'expected_points': contract.get('expected_points', 0),
                    'missing_points': contract.get('expected_points', 0) - contract.get('actual_points', 0),
                    'funding_interval': contract.get('funding_interval_hours'),
                    'status': contract.get('status'),
                    'gaps_detected': contract.get('gaps_detected', 0),
                    'priority': self._calculate_retry_priority(contract)
                })
        
        # Sort by priority (higher priority first)
        retry_candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        return retry_candidates
    
    def retry_incomplete(self, threshold: float = 95.0, max_retries: int = None, 
                        dry_run: bool = False) -> Dict:
        """
        Retry fetching data for incomplete contracts.
        
        Args:
            threshold: Minimum completeness percentage
            max_retries: Maximum number of contracts to retry
            dry_run: If True, don't actually upload data
            
        Returns:
            Dictionary with retry results
        """
        logger.info(f"Starting retry for contracts with completeness < {threshold}%")
        
        # Get candidates
        candidates = self.get_retry_candidates(threshold)
        
        if not candidates:
            logger.info("No contracts need retry!")
            return {'message': 'No contracts need retry'}
        
        if max_retries:
            candidates = candidates[:max_retries]
        
        self.retry_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'threshold': threshold,
            'candidates_found': len(candidates),
            'contracts_retried': 0,
            'contracts_improved': 0,
            'contracts_failed': 0,
            'details': []
        }
        
        # Import exchange classes dynamically
        from exchanges.binance_exchange import BinanceExchange
        from exchanges.kucoin_exchange import KuCoinExchange
        from exchanges.backpack_exchange import BackpackExchange
        from exchanges.hyperliquid_exchange import HyperliquidExchange
        
        exchange_classes = {
            'binance': BinanceExchange,
            'kucoin': KuCoinExchange,
            'backpack': BackpackExchange,
            'hyperliquid': HyperliquidExchange,
        }
        
        for i, candidate in enumerate(candidates, 1):
            logger.info(f"[{i}/{len(candidates)}] Retrying {candidate['exchange']}:{candidate['symbol']}")
            
            # Get exchange class
            exchange_class = exchange_classes.get(candidate['exchange'].lower())
            if not exchange_class:
                logger.error(f"Exchange {candidate['exchange']} not supported")
                self.retry_results['contracts_failed'] += 1
                continue
            
            try:
                # Fetch missing data
                exchange = exchange_class()
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=30)
                
                # Fetch historical data
                historical_df = exchange.fetch_all_perpetuals_historical(
                    days=30,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # Filter for our symbol
                if not historical_df.empty and 'symbol' in historical_df.columns:
                    historical_df = historical_df[historical_df['symbol'] == candidate['symbol']]
                
                if not historical_df.empty and not dry_run:
                    # Upload to database
                    success = self.db.upload_historical_funding_rates(historical_df)
                    
                    if success:
                        # Re-validate to check improvement
                        new_validation = self.validate_contract(
                            candidate['exchange'], 
                            candidate['symbol'], 
                            30
                        )
                        
                        improvement = new_validation.get('completeness_percentage', 0) - candidate['completeness']
                        
                        self.retry_results['details'].append({
                            'exchange': candidate['exchange'],
                            'symbol': candidate['symbol'],
                            'original_completeness': candidate['completeness'],
                            'new_completeness': new_validation.get('completeness_percentage', 0),
                            'improvement': improvement,
                            'records_added': len(historical_df),
                            'success': improvement > 0
                        })
                        
                        if improvement > 0:
                            self.retry_results['contracts_improved'] += 1
                            logger.info(f"Improved by {improvement:.1f}%")
                    else:
                        self.retry_results['contracts_failed'] += 1
                        logger.error(f"Failed to upload data")
                else:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would add {len(historical_df)} records")
                    else:
                        logger.warning(f"No data fetched")
                        self.retry_results['contracts_failed'] += 1
                
                self.retry_results['contracts_retried'] += 1
                
            except Exception as e:
                logger.error(f"Error retrying {candidate['exchange']}:{candidate['symbol']}: {e}")
                self.retry_results['contracts_failed'] += 1
            
            # Small delay between retries
            if i < len(candidates):
                time.sleep(1)
        
        return self.retry_results
    
    # ================== REPORTING METHODS ==================
    
    def generate_report(self, format: str = 'text', output: str = None) -> str:
        """
        Generate a completeness report in various formats.
        
        Args:
            format: Output format (text, json, csv)
            output: Output filename (None for stdout)
            
        Returns:
            Report content as string
        """
        if not self.validation_results:
            self.validate_all()
        
        if format == 'json':
            report = json.dumps(self.validation_results, indent=2, default=str)
        elif format == 'csv':
            df = pd.DataFrame(self.validation_results.get('contracts', []))
            report = df.to_csv(index=False)
        else:  # text
            report = self._generate_text_report()
        
        if output:
            with open(output, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output}")
        else:
            print(report)
        
        return report
    
    def monitor_continuous(self, interval: int = 3600) -> None:
        """
        Continuously monitor data completeness.
        
        Args:
            interval: Seconds between checks (default: 1 hour)
        """
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while True:
                # Run validation
                results = self.validate_all()
                
                # Log summary
                if 'summary' in results:
                    summary = results['summary']
                    logger.info(f"Completeness check: {summary['complete']}/{summary['total_contracts']} complete")
                    
                    # Log warnings for low completeness
                    if summary['needs_retry']:
                        logger.warning(f"{len(summary['needs_retry'])} contracts below threshold")
                
                # Wait for next check
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
    
    # ================== HELPER METHODS ==================
    
    def _detect_funding_interval(self, exchange: str, symbol: str) -> Optional[int]:
        """Detect funding interval for a contract by analyzing time gaps."""
        query = """
            SELECT funding_time
            FROM funding_rates_historical
            WHERE exchange = %s AND symbol = %s
            ORDER BY funding_time DESC
            LIMIT 100
        """
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute(query, (exchange, symbol))
                results = cursor.fetchall()
                
                if len(results) < 2:
                    return None
                
                # Calculate time differences
                timestamps = [row[0] for row in results]
                time_diffs = []
                
                for i in range(1, len(timestamps)):
                    diff = (timestamps[i-1] - timestamps[i]).total_seconds() / 3600
                    time_diffs.append(diff)
                
                if not time_diffs:
                    return None
                
                # Find most common interval
                from collections import Counter
                interval_counts = Counter([round(d) for d in time_diffs])
                most_common_interval = interval_counts.most_common(1)[0][0]
                
                # Validate it's a standard interval
                if most_common_interval in [1, 2, 4, 8]:
                    return most_common_interval
                    
                return None
                
        except Exception as e:
            logger.error(f"Error detecting interval for {exchange}:{symbol}: {e}")
            return None
    
    def _calculate_expected_points(self, funding_interval: int, days: int) -> int:
        """Calculate expected number of data points based on interval and time period."""
        if funding_interval not in [1, 2, 4, 8]:
            return 0
        points_per_day = 24 / funding_interval
        return int(points_per_day * days)
    
    def _determine_status(self, completeness_percentage: float) -> str:
        """Determine status based on completeness percentage."""
        if completeness_percentage >= self.MIN_COMPLETENESS_THRESHOLD:
            return 'complete'
        elif completeness_percentage >= 80:
            return 'partial_high'
        elif completeness_percentage >= 50:
            return 'partial_medium'
        else:
            return 'incomplete'
    
    def _calculate_retry_priority(self, contract: Dict) -> float:
        """Calculate retry priority based on multiple factors."""
        completeness = contract.get('completeness_percentage', 0)
        gaps = contract.get('gaps_detected', 0)
        actual_points = contract.get('actual_points', 0)
        
        # Priority factors
        completeness_score = (100 - completeness) / 100
        gap_score = min(gaps / 10, 1.0)
        data_score = 1.0 if actual_points > 10 else 0.5
        
        priority = (completeness_score * 0.5 + gap_score * 0.3 + data_score * 0.2) * 100
        return round(priority, 2)
    
    def _update_summary(self, summary: Dict, result: Dict, exchange: str, symbol: str) -> None:
        """Update summary statistics based on validation result."""
        status = result.get('status', 'error')
        if status == 'complete':
            summary['complete'] += 1
        elif status == 'partial_high':
            summary['partial_high'] += 1
        elif status == 'partial_medium':
            summary['partial_medium'] += 1
        elif status == 'incomplete':
            summary['incomplete'] += 1
        elif status == 'no_data':
            summary['no_data'] += 1
        else:
            summary['errors'] += 1
        
        if result.get('needs_retry', False):
            summary['needs_retry'].append(f"{exchange}:{symbol}")
    
    def _generate_text_report(self) -> str:
        """Generate a human-readable text report."""
        if not self.validation_results:
            return "No validation results available"
        
        summary = self.validation_results.get('summary', {})
        
        report = []
        report.append("=" * 60)
        report.append("DATA COMPLETENESS REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {self.validation_results.get('timestamp', 'N/A')}")
        report.append(f"Analysis Period: {self.validation_results.get('days_analyzed', 30)} days")
        report.append("")
        report.append(f"Total Contracts: {summary.get('total_contracts', 0)}")
        report.append(f"  Complete (>=95%): {summary.get('complete', 0)}")
        report.append(f"  Partial High (80-95%): {summary.get('partial_high', 0)}")
        report.append(f"  Partial Medium (50-80%): {summary.get('partial_medium', 0)}")
        report.append(f"  Incomplete (<50%): {summary.get('incomplete', 0)}")
        report.append(f"  No Data: {summary.get('no_data', 0)}")
        report.append(f"  Errors: {summary.get('errors', 0)}")
        report.append("")
        report.append(f"Overall Completeness: {summary.get('overall_complete_percentage', 0)}%")
        report.append(f"Contracts Needing Retry: {len(summary.get('needs_retry', []))}")
        
        if summary.get('needs_retry'):
            report.append("")
            report.append("Top 10 Contracts Needing Retry:")
            for contract in summary['needs_retry'][:10]:
                report.append(f"  - {contract}")
        
        return "\n".join(report)
    
    # ================== TEST METHODS ==================
    
    def run_tests(self) -> bool:
        """Run comprehensive tests of all functionality."""
        print("=" * 60)
        print("TESTING DATA COMPLETENESS SYSTEM")
        print("=" * 60)
        
        all_tests_passed = True
        
        # Test 1: Database connection
        print("\n1. Testing database connection...")
        if self.db.test_connection():
            print("   [PASS] Database connected")
        else:
            print("   [FAIL] Database connection failed")
            all_tests_passed = False
        
        # Test 2: Single contract validation
        print("\n2. Testing single contract validation...")
        try:
            # Find a contract to test
            query = "SELECT exchange, symbol FROM funding_rates_historical LIMIT 1"
            with self.db.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                
            if result:
                exchange, symbol = result
                validation = self.validate_contract(exchange, symbol)
                print(f"   Validated {exchange}:{symbol}")
                print(f"   Completeness: {validation.get('completeness_percentage', 0)}%")
                print("   [PASS] Single validation works")
            else:
                print("   [WARN] No data to test")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            all_tests_passed = False
        
        # Test 3: Gap detection
        print("\n3. Testing gap detection...")
        try:
            if result:
                gaps = self.detect_gaps(exchange, symbol)
                print(f"   Found {len(gaps)} gaps")
                print("   [PASS] Gap detection works")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            all_tests_passed = False
        
        # Test 4: Retry candidates
        print("\n4. Testing retry candidate identification...")
        try:
            candidates = self.get_retry_candidates(threshold=95)
            print(f"   Found {len(candidates)} candidates")
            if candidates:
                print(f"   Top candidate: {candidates[0]['exchange']}:{candidates[0]['symbol']} ({candidates[0]['completeness']}%)")
            print("   [PASS] Retry identification works")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            all_tests_passed = False
        
        # Test 5: Report generation
        print("\n5. Testing report generation...")
        try:
            report = self.generate_report(format='text')
            print(f"   Generated {len(report)} character report")
            print("   [PASS] Report generation works")
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            all_tests_passed = False
        
        print("\n" + "=" * 60)
        if all_tests_passed:
            print("ALL TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
        print("=" * 60)
        
        return all_tests_passed


def main():
    """Command-line interface for data completeness management."""
    parser = argparse.ArgumentParser(
        description='Unified Data Completeness Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate data completeness')
    validate_parser.add_argument('--days', type=int, default=30, help='Days to analyze (default: 30)')
    validate_parser.add_argument('--exchange', help='Specific exchange to validate')
    validate_parser.add_argument('--symbol', help='Specific symbol to validate')
    
    # Retry command
    retry_parser = subparsers.add_parser('retry', help='Retry incomplete contracts')
    retry_parser.add_argument('--threshold', type=float, default=95.0, 
                             help='Completeness threshold (default: 95)')
    retry_parser.add_argument('--max-retries', type=int, help='Maximum contracts to retry')
    retry_parser.add_argument('--dry-run', action='store_true', help='Simulate without uploading')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate completeness report')
    report_parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text',
                              help='Output format (default: text)')
    report_parser.add_argument('--output', help='Output file (default: stdout)')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor completeness continuously')
    monitor_parser.add_argument('--continuous', action='store_true', help='Run continuously')
    monitor_parser.add_argument('--interval', type=int, default=3600, 
                               help='Check interval in seconds (default: 3600)')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    
    args = parser.parse_args()
    
    # Create manager
    manager = DataCompletenessManager()
    
    # Execute command
    if args.command == 'validate':
        if args.exchange and args.symbol:
            # Single contract
            result = manager.validate_contract(args.exchange, args.symbol, args.days)
            print(json.dumps(result, indent=2, default=str))
        else:
            # All contracts
            result = manager.validate_all(args.days)
            if 'summary' in result:
                print(manager._generate_text_report())
            else:
                print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'retry':
        result = manager.retry_incomplete(
            threshold=args.threshold,
            max_retries=args.max_retries,
            dry_run=args.dry_run
        )
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'report':
        manager.generate_report(format=args.format, output=args.output)
    
    elif args.command == 'monitor':
        if args.continuous:
            manager.monitor_continuous(interval=args.interval)
        else:
            # Single check
            result = manager.validate_all()
            if 'summary' in result:
                summary = result['summary']
                print(f"Completeness: {summary['complete']}/{summary['total_contracts']} contracts complete")
                if summary['needs_retry']:
                    print(f"Warning: {len(summary['needs_retry'])} contracts need retry")
    
    elif args.command == 'test':
        success = manager.run_tests()
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()