#!/usr/bin/env python3
"""
Backfill Completeness Validator
Validates data completeness for historical funding rates per tasklist.md Section 7 (lines 219-233)

Features:
- Pre-fetch interval detection for smart date ranges
- Per-symbol completeness tracking
- Gap detection for missing time periods
- Expected vs actual data points comparison
- Completeness reports generation
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgres_manager import PostgresManager


class BackfillCompletenessValidator:
    """Validates completeness of historical funding rate data"""
    
    # Expected data points for 30-day window based on funding interval
    # From tasklist.md lines 226-229
    EXPECTED_POINTS_30_DAYS = {
        1: 720,   # 1-hour: 24 * 30 = 720 points
        2: 360,   # 2-hour: 12 * 30 = 360 points
        4: 180,   # 4-hour: 6 * 30 = 180 points
        8: 90     # 8-hour: 3 * 30 = 90 points
    }
    
    # Minimum completeness threshold for quality data
    MIN_COMPLETENESS_THRESHOLD = 95.0  # 95% as per tasklist line 224
    
    def __init__(self):
        self.db = PostgresManager()
        self.validation_results = {}
        
    def detect_funding_interval(self, exchange: str, symbol: str) -> Optional[int]:
        """
        Detect funding interval for a contract by analyzing time gaps
        """
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
                
                # Calculate time differences between consecutive funding times
                timestamps = [row[0] for row in results]
                time_diffs = []
                
                for i in range(1, len(timestamps)):
                    diff = (timestamps[i-1] - timestamps[i]).total_seconds() / 3600  # Convert to hours
                    time_diffs.append(diff)
                
                if not time_diffs:
                    return None
                
                # Find most common interval (mode)
                from collections import Counter
                interval_counts = Counter([round(d) for d in time_diffs])
                most_common_interval = interval_counts.most_common(1)[0][0]
                
                # Validate it's a standard interval
                if most_common_interval in [1, 2, 4, 8]:
                    return most_common_interval
                    
                return None
                
        except Exception as e:
            print(f"Error detecting interval for {exchange}:{symbol}: {e}")
            return None
    
    def calculate_expected_points(self, funding_interval: int, days: int) -> int:
        """
        Calculate expected number of data points based on interval and time period
        """
        if funding_interval not in [1, 2, 4, 8]:
            return 0
            
        points_per_day = 24 / funding_interval
        return int(points_per_day * days)
    
    def detect_gaps(self, exchange: str, symbol: str, days: int = 30) -> List[Dict]:
        """
        Detect gaps in historical data for a specific contract
        """
        from datetime import timezone as tz
        end_date = datetime.now(tz.utc)
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
                interval = self.detect_funding_interval(exchange, symbol)
                if not interval:
                    return gaps
                
                # Check for gaps
                expected_gap = timedelta(hours=interval)
                tolerance = timedelta(hours=interval * 0.5)  # 50% tolerance
                
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
            print(f"Error detecting gaps for {exchange}:{symbol}: {e}")
            
        return gaps
    
    def validate_contract(self, exchange: str, symbol: str, days: int = 30) -> Dict:
        """
        Validate completeness for a single contract
        """
        from datetime import timezone as tz
        end_date = datetime.now(tz.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get actual data points
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
                first_point = result[1]
                last_point = result[2]
                days_covered = result[3]
                
                # Detect funding interval
                interval = self.detect_funding_interval(exchange, symbol)
                if not interval:
                    # Can't determine expected points without interval
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
                expected_points = self.calculate_expected_points(interval, days)
                completeness_percentage = (actual_points / expected_points * 100) if expected_points > 0 else 0
                
                # Detect gaps
                gaps = self.detect_gaps(exchange, symbol, days)
                
                # Determine status and if retry is needed
                if completeness_percentage >= self.MIN_COMPLETENESS_THRESHOLD:
                    status = 'complete'
                    needs_retry = False
                elif completeness_percentage >= 80:
                    status = 'partial_high'
                    needs_retry = True
                elif completeness_percentage >= 50:
                    status = 'partial_medium'
                    needs_retry = True
                else:
                    status = 'incomplete'
                    needs_retry = True
                
                return {
                    'exchange': exchange,
                    'symbol': symbol,
                    'funding_interval_hours': interval,
                    'actual_points': actual_points,
                    'expected_points': expected_points,
                    'completeness_percentage': round(completeness_percentage, 2),
                    'first_data_point': first_point.isoformat() if first_point else None,
                    'last_data_point': last_point.isoformat() if last_point else None,
                    'days_covered': days_covered,
                    'gaps_detected': len(gaps),
                    'gaps': gaps[:5] if gaps else [],  # Limit to first 5 gaps
                    'status': status,
                    'needs_retry': needs_retry
                }
                
        except Exception as e:
            print(f"Error validating {exchange}:{symbol}: {e}")
            return {
                'exchange': exchange,
                'symbol': symbol,
                'error': str(e),
                'status': 'error',
                'needs_retry': True
            }
    
    def validate_all_contracts(self, days: int = 30) -> Dict:
        """
        Validate completeness for all contracts in the system
        """
        print(f"\nValidating data completeness for all contracts ({days}-day window)...")
        
        # Get all unique exchange-symbol pairs
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
                        print(f"  Progress: {i}/{len(contracts)} contracts validated...")
                    
                    result = self.validate_contract(exchange, symbol, days)
                    all_results.append(result)
                    
                    # Update summary
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
            print(f"Error during validation: {e}")
            return {'error': str(e)}
    
    def get_smart_date_range(self, exchange: str, symbol: str) -> Tuple[datetime, datetime]:
        """
        Get smart date range based on funding interval for optimal backfill
        From tasklist.md lines 226-229
        """
        interval = self.detect_funding_interval(exchange, symbol)
        
        if not interval:
            # Default to 30 days if interval unknown
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            return start_date, end_date
        
        # Calculate optimal days based on interval to get ~720 points
        if interval == 1:
            days = 30    # 720 points
        elif interval == 2:
            days = 60    # 720 points
        elif interval == 4:
            days = 120   # 720 points
        elif interval == 8:
            days = 240   # 720 points
        else:
            days = 30    # Default
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    def get_retry_candidates(self, threshold: float = None) -> List[Dict]:
        """
        Get list of contracts that need retry based on completeness threshold.
        Enhanced to provide more actionable information for retry mechanism.
        """
        if threshold is None:
            threshold = self.MIN_COMPLETENESS_THRESHOLD
            
        if not self.validation_results or 'contracts' not in self.validation_results:
            # Run validation first
            self.validate_all_contracts()
        
        retry_candidates = []
        
        for contract in self.validation_results.get('contracts', []):
            completeness = contract.get('completeness_percentage', 0)
            
            # Only include contracts that have some data but are incomplete
            # Skip contracts with no data at all (they need initial backfill, not retry)
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
                    'gaps': contract.get('gaps', []),
                    'priority': self._calculate_retry_priority(contract)
                })
        
        # Sort by priority (higher priority first)
        retry_candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        return retry_candidates
    
    def _calculate_retry_priority(self, contract: Dict) -> float:
        """
        Calculate retry priority based on multiple factors.
        Higher score = higher priority for retry.
        """
        completeness = contract.get('completeness_percentage', 0)
        gaps = contract.get('gaps_detected', 0)
        actual_points = contract.get('actual_points', 0)
        
        # Priority factors:
        # 1. Inverse of completeness (lower completeness = higher priority)
        completeness_score = (100 - completeness) / 100
        
        # 2. Number of gaps (more gaps = higher priority)
        gap_score = min(gaps / 10, 1.0)  # Normalize to 0-1
        
        # 3. Has substantial data already (prefer contracts with some data)
        data_score = 1.0 if actual_points > 10 else 0.5
        
        # Combined priority score
        priority = (completeness_score * 0.5 + gap_score * 0.3 + data_score * 0.2) * 100
        
        return round(priority, 2)
    
    def save_report(self, filename: str = None) -> str:
        """
        Save validation report to JSON file with enhanced retry information.
        """
        if not self.validation_results:
            print("No validation results to save. Run validate_all_contracts() first.")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backfill_completeness_report_{timestamp}.json"
        
        # Add retry candidates to report
        retry_candidates = self.get_retry_candidates()
        enhanced_report = dict(self.validation_results)
        enhanced_report['retry_candidates'] = {
            'count': len(retry_candidates),
            'threshold': self.MIN_COMPLETENESS_THRESHOLD,
            'top_priority': retry_candidates[:10] if retry_candidates else []
        }
        
        with open(filename, 'w') as f:
            json.dump(enhanced_report, f, indent=2, default=str)
        
        print(f"Report saved to: {filename}")
        return filename
    
    def print_summary(self) -> None:
        """
        Print validation summary to console
        """
        if not self.validation_results or 'summary' not in self.validation_results:
            print("No validation results available.")
            return
        
        summary = self.validation_results['summary']
        
        print("\n" + "="*60)
        print("BACKFILL COMPLETENESS VALIDATION SUMMARY")
        print("="*60)
        print(f"Timestamp: {self.validation_results['timestamp']}")
        print(f"Analysis Period: {self.validation_results['days_analyzed']} days")
        print(f"\nTotal Contracts: {summary['total_contracts']}")
        print(f"  Complete (>=95%): {summary['complete']} ({summary['complete']/summary['total_contracts']*100:.1f}%)")
        print(f"  Partial High (80-95%): {summary['partial_high']}")
        print(f"  Partial Medium (50-80%): {summary['partial_medium']}")
        print(f"  Incomplete (<50%): {summary['incomplete']}")
        print(f"  No Data: {summary['no_data']}")
        print(f"  Errors: {summary['errors']}")
        print(f"\nOverall Completeness: {summary['overall_complete_percentage']}%")
        print(f"Contracts Needing Retry: {len(summary['needs_retry'])}")
        
        if summary['needs_retry'][:5]:  # Show first 5
            print("\nTop candidates for retry:")
            for contract in summary['needs_retry'][:5]:
                print(f"  - {contract}")


if __name__ == "__main__":
    # Run validation
    validator = BackfillCompletenessValidator()
    
    # Validate all contracts
    results = validator.validate_all_contracts(days=30)
    
    # Print summary
    validator.print_summary()
    
    # Get retry candidates
    retry_candidates = validator.get_retry_candidates()
    if retry_candidates:
        print(f"\n🔄 Found {len(retry_candidates)} contracts needing retry")
        for candidate in retry_candidates[:5]:
            print(f"  {candidate['exchange']}:{candidate['symbol']} - {candidate['completeness']}% complete")
    
    # Save report
    validator.save_report()