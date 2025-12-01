"""
Z-Score Statistical Calculator Module
=====================================
Calculates Z-scores and statistical metrics for funding rates.
Following Z_score.md specification EXACTLY - NO DEVIATIONS

References:
- Z-score formula: Z_score.md line 14
- Confidence levels: Z_score.md lines 159-165
- Data pipeline: Z_score.md lines 205-224
- Percentile ranking: Z_score.md lines 230-239
- Statistical independence: Z_score.md lines 250-258
"""

import statistics
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import execute_values
from scipy import stats
import logging
from utils.logger import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class ZScoreCalculator:
    """
    Calculates Z-scores and statistical metrics for funding rate analysis.
    Processes each exchange-contract pair independently to maintain market microstructure.
    """
    
    def __init__(self, db_connection, window_days: int = None):
        """
        Initialize the Z-score calculator.
        
        Args:
            db_connection: PostgreSQL database connection
            window_days: Historical window for calculations (default: from settings)
        """
        from config.settings import ZSCORE_CALCULATION_DAYS
        
        self.db_connection = db_connection
        self.cursor = db_connection.cursor()
        self.window_days = window_days if window_days is not None else ZSCORE_CALCULATION_DAYS
        self.logger = setup_logger("ZScoreCalculator")
        
    def calculate_zscore(self, current_value: float, mean: float, std_dev: float) -> Optional[float]:
        """
        Calculate Z-score using the formula: (Current - Mean) / StdDev
        Reference: Z_score.md line 14
        
        Args:
            current_value: Current funding rate or APR
            mean: Historical mean
            std_dev: Historical standard deviation
            
        Returns:
            Z-score or None if std_dev is 0
        """
        if std_dev == 0 or std_dev is None:
            return None
        return (current_value - mean) / std_dev
    
    def fetch_historical_data(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """
        Data Retrieval Phase - Fetch 30-day historical data for a contract.
        Reference: Z_score.md lines 205-208, tasklist lines 79-82
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            
        Returns:
            Dict with funding rates, APR values, and metadata
        """
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.window_days)
            
            # Query funding_rates_historical table with time window
            # Using CURRENT_TIMESTAMP - INTERVAL for consistent 30-day window
            query = """
                SELECT 
                    funding_rate,
                    funding_time,
                    funding_interval_hours,
                    mark_price
                FROM funding_rates_historical
                WHERE exchange = %s 
                    AND symbol = %s
                    AND funding_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND funding_rate IS NOT NULL
                ORDER BY funding_time DESC
            """
            
            self.cursor.execute(query, (exchange, symbol, self.window_days))
            rows = self.cursor.fetchall()
            
            if not rows:
                self.logger.warning(f"No historical data for {exchange} {symbol}")
                return {'funding_rates': [], 'apr_values': [], 'funding_interval_hours': None}
            
            # Extract data and calculate APR
            funding_rates = []
            apr_values = []
            funding_interval_hours = rows[0][2] if rows else 8  # Default to 8 hours
            
            for row in rows:
                funding_rate = float(row[0]) if row[0] is not None else None
                interval_hours = row[2] or funding_interval_hours
                
                if funding_rate is not None:
                    funding_rates.append(funding_rate)
                    # Calculate APR: funding_rate * (24/interval_hours) * 365
                    apr = funding_rate * (24 / interval_hours) * 365 * 100  # Convert to percentage
                    apr_values.append(apr)
            
            return {
                'funding_rates': funding_rates,
                'apr_values': apr_values,
                'funding_interval_hours': funding_interval_hours,
                'data_count': len(funding_rates)
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {exchange} {symbol}: {e}")
            return {'funding_rates': [], 'apr_values': [], 'funding_interval_hours': None}
    
    def validate_data_quality(self, data_points: int, funding_interval_hours: int, contract_age_days: float = None) -> Tuple[str, float, int]:
        """
        Data Validation Phase - Assign confidence levels based on data points.
        Reference: Z_score.md lines 159-165, tasklist lines 84-93
        
        Args:
            data_points: Number of actual data points
            funding_interval_hours: Funding interval in hours
            contract_age_days: Age of the contract in days (optional)
            
        Returns:
            Tuple of (confidence_level, completeness_percentage, expected_points)
        """
        # Calculate expected points based on contract age if provided
        if contract_age_days is not None and contract_age_days < self.window_days:
            # For new contracts, expected points based on actual age
            expected_points = int((contract_age_days * 24) / funding_interval_hours)
        else:
            # For older contracts, use full window
            expected_points = int((self.window_days * 24) / funding_interval_hours)
        
        completeness_percentage = (data_points / expected_points * 100) if expected_points > 0 else 0
        
        # Assign confidence levels per specification
        if data_points < 10:
            confidence = 'none'  # Skip calculation
        elif data_points < 30:
            confidence = 'low'   # Calculate with warning
        elif data_points < 90:
            confidence = 'medium'
        elif data_points < 180:
            confidence = 'high'
        else:
            confidence = 'very_high'
        
        return confidence, completeness_percentage, expected_points
    
    def compute_statistics(self, data_points: List[float]) -> Optional[Dict[str, float]]:
        """
        Statistical Computation Phase - Calculate mean, std_dev, min, max.
        Reference: Z_score.md lines 214-219, tasklist lines 95-100
        
        Args:
            data_points: List of funding rates or APR values
            
        Returns:
            Dict with statistical measures or None if insufficient data
        """
        # Remove null values WITHOUT interpolation (line 96, 215)
        clean_data = [x for x in data_points if x is not None]
        
        if len(clean_data) < 2:  # Need at least 2 points for std_dev
            return None
        
        try:
            mean_val = statistics.mean(clean_data)
            std_dev_val = statistics.stdev(clean_data) if len(clean_data) > 1 else 0
            min_val = min(clean_data)
            max_val = max(clean_data)
            
            return {
                'mean': mean_val,
                'std_dev': std_dev_val,
                'min': min_val,
                'max': max_val
            }
        except Exception as e:
            self.logger.error(f"Error computing statistics: {e}")
            return None
    
    def calculate_percentile_rank(self, value: float, historical_values: List[float]) -> int:
        """
        Percentile Ranking Phase - Calculate percentile rank (0-100).
        Reference: Z_score.md lines 230-239, tasklist lines 102-105
        
        Args:
            value: Current value to rank
            historical_values: List of historical values
            
        Returns:
            Percentile rank (0-100)
        """
        if not historical_values:
            return 50  # Default to median
        
        try:
            # Use scipy for accurate percentile calculation
            percentile = stats.percentileofscore(historical_values, value, kind='rank')
            return int(percentile)
        except Exception as e:
            self.logger.error(f"Error calculating percentile: {e}")
            return 50
    
    def get_contract_metadata(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get contract metadata from the metadata table (single source of truth).
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            
        Returns:
            Dict with contract metadata including correct funding interval
        """
        try:
            query = """
                SELECT 
                    funding_interval_hours,
                    created_at,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - COALESCE(created_at, CURRENT_TIMESTAMP - INTERVAL '30 days'))) / 86400 as age_days,
                    data_quality_score
                FROM contract_metadata
                WHERE exchange = %s AND symbol = %s
                LIMIT 1
            """
            self.cursor.execute(query, (exchange, symbol))
            row = self.cursor.fetchone()
            
            if not row:
                # Fallback to exchange_data if metadata doesn't exist yet
                return self.get_metadata_from_exchange_data(exchange, symbol)
            
            return {
                'funding_interval_hours': row[0],
                'created_at': row[1],
                'age_days': min(float(row[2]), self.window_days) if row[2] else self.window_days,
                'data_quality_score': float(row[3]) if row[3] else 100.0
            }
        except Exception as e:
            self.logger.error(f"Error getting metadata for {exchange} {symbol}: {e}")
            return None
    
    def get_metadata_from_exchange_data(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fallback method to get metadata from exchange_data table.
        """
        try:
            query = """
                SELECT funding_interval_hours
                FROM exchange_data
                WHERE exchange = %s AND symbol = %s
                LIMIT 1
            """
            self.cursor.execute(query, (exchange, symbol))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'funding_interval_hours': row[0] or 8,
                'created_at': None,
                'age_days': self.window_days,
                'data_quality_score': 100.0
            }
        except Exception as e:
            self.logger.error(f"Error getting exchange data for {exchange} {symbol}: {e}")
            return None
    
    def get_current_funding(self, exchange: str, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current funding rate from exchange_data table.
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            
        Returns:
            Dict with current funding rate and APR
        """
        try:
            query = """
                SELECT funding_rate, funding_interval_hours
                FROM exchange_data
                WHERE exchange = %s AND symbol = %s
                LIMIT 1
            """
            self.cursor.execute(query, (exchange, symbol))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            funding_rate = float(row[0]) if row[0] is not None else 0
            interval_hours = row[1] or 8
            apr = funding_rate * (24 / interval_hours) * 365 * 100
            
            return {
                'rate': funding_rate,
                'apr': apr,
                'interval_hours': interval_hours
            }
        except Exception as e:
            self.logger.error(f"Error getting current funding for {exchange} {symbol}: {e}")
            return None
    
    def update_funding_statistics(self, exchange: str, symbol: str, stats: Dict[str, Any]) -> bool:
        """
        Update funding_statistics table with calculated values.
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            stats: Dictionary with all calculated statistics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # UPSERT query - insert or update on conflict
            query = """
                INSERT INTO funding_statistics (
                    exchange, symbol, base_asset,
                    current_funding_rate, current_apr,
                    current_z_score, current_z_score_apr,
                    current_percentile, current_percentile_apr,
                    mean_30d, std_dev_30d, min_30d, max_30d,
                    mean_30d_apr, std_dev_30d_apr, min_30d_apr, max_30d_apr,
                    data_points, expected_points, completeness_percentage,
                    confidence_level, calculated_at, last_updated
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, NOW(), NOW()
                )
                ON CONFLICT (exchange, symbol)
                DO UPDATE SET
                    current_funding_rate = EXCLUDED.current_funding_rate,
                    current_apr = EXCLUDED.current_apr,
                    current_z_score = EXCLUDED.current_z_score,
                    current_z_score_apr = EXCLUDED.current_z_score_apr,
                    current_percentile = EXCLUDED.current_percentile,
                    current_percentile_apr = EXCLUDED.current_percentile_apr,
                    mean_30d = EXCLUDED.mean_30d,
                    std_dev_30d = EXCLUDED.std_dev_30d,
                    min_30d = EXCLUDED.min_30d,
                    max_30d = EXCLUDED.max_30d,
                    mean_30d_apr = EXCLUDED.mean_30d_apr,
                    std_dev_30d_apr = EXCLUDED.std_dev_30d_apr,
                    min_30d_apr = EXCLUDED.min_30d_apr,
                    max_30d_apr = EXCLUDED.max_30d_apr,
                    data_points = EXCLUDED.data_points,
                    expected_points = EXCLUDED.expected_points,
                    completeness_percentage = EXCLUDED.completeness_percentage,
                    confidence_level = EXCLUDED.confidence_level,
                    last_updated = NOW()
            """
            
            # Extract base asset from symbol (simplified - may need enhancement)
            base_asset = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
            
            self.cursor.execute(query, (
                exchange, symbol, base_asset,
                stats.get('current_funding_rate'),
                stats.get('current_apr'),
                stats.get('z_score'),
                stats.get('z_score_apr'),
                stats.get('percentile'),
                stats.get('percentile_apr'),
                stats.get('mean_30d'),
                stats.get('std_dev_30d'),
                stats.get('min_30d'),
                stats.get('max_30d'),
                stats.get('mean_30d_apr'),
                stats.get('std_dev_30d_apr'),
                stats.get('min_30d_apr'),
                stats.get('max_30d_apr'),
                stats.get('data_points'),
                stats.get('expected_points'),
                stats.get('completeness_percentage'),
                stats.get('confidence_level')
            ))
            
            self.db_connection.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating statistics for {exchange} {symbol}: {e}")
            self.db_connection.rollback()
            return False
    
    def process_contract(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Process a single exchange-contract pair independently.
        Reference: Z_score.md lines 250-258 - Statistical Independence
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            
        Returns:
            Dictionary with all calculated statistics or None
        """
        try:
            # 0. Get contract metadata (NEW - single source of truth)
            metadata = self.get_contract_metadata(exchange, symbol)
            if not metadata:
                self.logger.warning(f"No metadata found for {exchange} {symbol}")
                return None
            
            # 1. Data Retrieval Phase
            historical = self.fetch_historical_data(exchange, symbol)
            
            if not historical['funding_rates']:
                return None
            
            # 2. Data Validation Phase (UPDATED - use metadata interval and age)
            confidence, completeness, expected = self.validate_data_quality(
                historical['data_count'],
                metadata['funding_interval_hours'],  # Use metadata interval, not historical
                metadata['age_days']  # Pass contract age for proper calculation
            )
            
            # Skip if confidence is 'none' (insufficient data)
            if confidence == 'none':
                self.logger.info(f"Skipping {exchange} {symbol} - insufficient data ({historical['data_count']} points)")
                return None
            
            # 3. Statistical Computation Phase
            stats_funding = self.compute_statistics(historical['funding_rates'])
            stats_apr = self.compute_statistics(historical['apr_values'])
            
            if not stats_funding or not stats_apr:
                return None
            
            # 4. Get current funding rate
            current = self.get_current_funding(exchange, symbol)
            if not current:
                return None
            
            # 5. Calculate Z-scores
            z_score = self.calculate_zscore(
                current['rate'],
                stats_funding['mean'],
                stats_funding['std_dev']
            )
            
            z_score_apr = self.calculate_zscore(
                current['apr'],
                stats_apr['mean'],
                stats_apr['std_dev']
            )
            
            # 6. Percentile Ranking Phase
            percentile = self.calculate_percentile_rank(
                current['rate'],
                historical['funding_rates']
            )
            
            percentile_apr = self.calculate_percentile_rank(
                current['apr'],
                historical['apr_values']
            )
            
            # Compile all statistics
            result = {
                'exchange': exchange,
                'symbol': symbol,
                'current_funding_rate': current['rate'],
                'current_apr': current['apr'],
                'z_score': z_score,
                'z_score_apr': z_score_apr,
                'percentile': percentile,
                'percentile_apr': percentile_apr,
                'mean_30d': stats_funding['mean'],
                'std_dev_30d': stats_funding['std_dev'],
                'min_30d': stats_funding['min'],
                'max_30d': stats_funding['max'],
                'mean_30d_apr': stats_apr['mean'],
                'std_dev_30d_apr': stats_apr['std_dev'],
                'min_30d_apr': stats_apr['min'],
                'max_30d_apr': stats_apr['max'],
                'data_points': historical['data_count'],
                'expected_points': expected,
                'completeness_percentage': completeness,
                'confidence_level': confidence
            }
            
            # Update database
            self.update_funding_statistics(exchange, symbol, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {exchange} {symbol}: {e}")
            return None
    
    def get_contracts_by_zone(self, zone: str = None) -> List[Tuple[str, str]]:
        """
        Get contracts filtered by update zone.
        
        Args:
            zone: 'active', 'stable', or None for all
            
        Returns:
            List of (exchange, symbol) tuples
        """
        try:
            if zone:
                query = """
                    SELECT DISTINCT fs.exchange, fs.symbol
                    FROM funding_statistics fs
                    WHERE fs.update_zone = %s
                    ORDER BY fs.exchange, fs.symbol
                """
                self.cursor.execute(query, (zone,))
            else:
                query = """
                    SELECT DISTINCT exchange, symbol
                    FROM exchange_data
                    ORDER BY exchange, symbol
                """
                self.cursor.execute(query)
            
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error getting contracts by zone {zone}: {e}")
            return []
    
    def update_contract_zones(self, all_stats: List[Dict[str, Any]]) -> None:
        """
        Update the zone classification for contracts based on their Z-scores.
        Active: |Z-score| > 2.0 (high volatility, needs frequent updates)
        Stable: |Z-score| <= 2.0 (low volatility, less frequent updates)
        """
        try:
            for stats in all_stats:
                z_score = stats.get('z_score')
                if z_score is not None:
                    new_zone = 'active' if abs(z_score) > 2.0 else 'stable'
                else:
                    new_zone = 'stable'  # Default to stable if no Z-score
                
                # Update zone in the stats dict for batch update
                stats['update_zone'] = new_zone
            
            self.logger.info(f"Updated zones for {len(all_stats)} contracts")
            
        except Exception as e:
            self.logger.error(f"Error updating contract zones: {e}")
    
    def get_all_active_contracts(self) -> List[Tuple[str, str]]:
        """
        Get list of all active exchange-contract pairs.
        
        Returns:
            List of (exchange, symbol) tuples
        """
        try:
            query = """
                SELECT DISTINCT exchange, symbol
                FROM exchange_data
                ORDER BY exchange, symbol
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error getting active contracts: {e}")
            return []
    
    def fetch_all_historical_data_batch(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        Batch fetch 30-day historical data for ALL contracts in a single query.
        Performance optimization: Replace 1,265 individual queries with 1 batch query.
        Reference: tasklist.md lines 54-69
        
        Returns:
            Dictionary keyed by (exchange, symbol) with historical data
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.window_days)
            
            # Single batch query for ALL contracts with time window
            # Using CURRENT_TIMESTAMP - INTERVAL for consistent window
            query = """
                SELECT 
                    exchange,
                    symbol,
                    funding_rate,
                    funding_time,
                    funding_interval_hours,
                    mark_price
                FROM funding_rates_historical
                WHERE funding_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND funding_rate IS NOT NULL
                ORDER BY exchange, symbol, funding_time DESC
            """
            
            self.cursor.execute(query, (self.window_days,))
            rows = self.cursor.fetchall()
            
            # Group by contract in memory
            data_by_contract = {}
            for row in rows:
                key = (row[0], row[1])  # (exchange, symbol)
                if key not in data_by_contract:
                    data_by_contract[key] = {
                        'funding_rates': [],
                        'apr_values': [],
                        'funding_interval_hours': row[4] or 8,
                        'data_count': 0
                    }
                
                funding_rate = float(row[2]) if row[2] is not None else None
                interval_hours = row[4] or data_by_contract[key]['funding_interval_hours']
                
                if funding_rate is not None:
                    data_by_contract[key]['funding_rates'].append(funding_rate)
                    # Calculate APR
                    apr = funding_rate * (24 / interval_hours) * 365 * 100
                    data_by_contract[key]['apr_values'].append(apr)
                    data_by_contract[key]['data_count'] += 1
            
            self.logger.info(f"Batch fetched historical data for {len(data_by_contract)} contracts")
            return data_by_contract
            
        except Exception as e:
            self.logger.error(f"Error in batch historical fetch: {e}")
            return {}
    
    def get_all_current_funding_batch(self) -> Dict[Tuple[str, str], Dict[str, float]]:
        """
        Batch fetch current funding rates for ALL contracts.
        Performance optimization: Single query instead of individual queries.
        
        Returns:
            Dictionary keyed by (exchange, symbol) with current funding data
        """
        try:
            query = """
                SELECT exchange, symbol, funding_rate, funding_interval_hours
                FROM exchange_data
                WHERE funding_rate IS NOT NULL
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            
            current_data = {}
            for row in rows:
                funding_rate = float(row[2]) if row[2] is not None else 0
                interval_hours = row[3] or 8
                apr = funding_rate * (24 / interval_hours) * 365 * 100
                
                current_data[(row[0], row[1])] = {
                    'rate': funding_rate,
                    'apr': apr,
                    'interval_hours': interval_hours
                }
            
            return current_data
            
        except Exception as e:
            self.logger.error(f"Error in batch current funding fetch: {e}")
            return {}
    
    def get_all_metadata_batch(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        Batch fetch metadata for ALL contracts.
        
        Returns:
            Dictionary keyed by (exchange, symbol) with contract metadata
        """
        try:
            # First try contract_metadata table
            query = """
                SELECT 
                    exchange,
                    symbol,
                    funding_interval_hours,
                    created_at,
                    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - COALESCE(created_at, CURRENT_TIMESTAMP - INTERVAL '30 days'))) / 86400 as age_days,
                    data_quality_score
                FROM contract_metadata
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            
            metadata = {}
            for row in rows:
                metadata[(row[0], row[1])] = {
                    'funding_interval_hours': row[2] or 8,
                    'created_at': row[3],
                    'age_days': min(float(row[4]), self.window_days) if row[4] else self.window_days,
                    'data_quality_score': float(row[5]) if row[5] else 100.0
                }
            
            # Fallback to exchange_data for missing contracts
            if len(metadata) < 1200:  # Expected ~1,260 contracts
                query = """
                    SELECT DISTINCT exchange, symbol, funding_interval_hours
                    FROM exchange_data
                """
                self.cursor.execute(query)
                rows = self.cursor.fetchall()
                
                for row in rows:
                    key = (row[0], row[1])
                    if key not in metadata:
                        metadata[key] = {
                            'funding_interval_hours': row[2] or 8,
                            'created_at': None,
                            'age_days': self.window_days,
                            'data_quality_score': 100.0
                        }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error in batch metadata fetch: {e}")
            return {}
    
    def batch_update_funding_statistics(self, all_stats: List[Dict[str, Any]]) -> bool:
        """
        Batch update funding_statistics table with all calculated values.
        Performance optimization: Single transaction for all updates.
        Reference: tasklist.md lines 71-79
        
        Args:
            all_stats: List of dictionaries with statistics for all contracts
            
        Returns:
            True if successful
        """
        try:
            from psycopg2.extras import execute_values
            
            # Prepare values for batch insert
            values = []
            for stats in all_stats:
                base_asset = stats['symbol'].replace('USDT', '').replace('USD', '').replace('PERP', '')
                values.append((
                    stats['exchange'], stats['symbol'], base_asset,
                    stats.get('current_funding_rate'),
                    stats.get('current_apr'),
                    stats.get('z_score'),
                    stats.get('z_score_apr'),
                    stats.get('percentile'),
                    stats.get('percentile_apr'),
                    stats.get('mean_30d'),
                    stats.get('std_dev_30d'),
                    stats.get('min_30d'),
                    stats.get('max_30d'),
                    stats.get('mean_30d_apr'),
                    stats.get('std_dev_30d_apr'),
                    stats.get('min_30d_apr'),
                    stats.get('max_30d_apr'),
                    stats.get('data_points'),
                    stats.get('expected_points'),
                    stats.get('completeness_percentage'),
                    stats.get('confidence_level'),
                    stats.get('funding_interval_hours', 8),  # Add funding interval
                    stats.get('update_zone', 'stable')  # Add update zone
                ))
            
            # Batch UPSERT using execute_values
            query = """
                INSERT INTO funding_statistics (
                    exchange, symbol, base_asset,
                    current_funding_rate, current_apr,
                    current_z_score, current_z_score_apr,
                    current_percentile, current_percentile_apr,
                    mean_30d, std_dev_30d, min_30d, max_30d,
                    mean_30d_apr, std_dev_30d_apr, min_30d_apr, max_30d_apr,
                    data_points, expected_points, completeness_percentage,
                    confidence_level, funding_interval_hours, update_zone, calculated_at, last_updated
                ) VALUES %s
                ON CONFLICT (exchange, symbol)
                DO UPDATE SET
                    current_funding_rate = EXCLUDED.current_funding_rate,
                    current_apr = EXCLUDED.current_apr,
                    current_z_score = EXCLUDED.current_z_score,
                    current_z_score_apr = EXCLUDED.current_z_score_apr,
                    current_percentile = EXCLUDED.current_percentile,
                    current_percentile_apr = EXCLUDED.current_percentile_apr,
                    mean_30d = EXCLUDED.mean_30d,
                    std_dev_30d = EXCLUDED.std_dev_30d,
                    min_30d = EXCLUDED.min_30d,
                    max_30d = EXCLUDED.max_30d,
                    mean_30d_apr = EXCLUDED.mean_30d_apr,
                    std_dev_30d_apr = EXCLUDED.std_dev_30d_apr,
                    min_30d_apr = EXCLUDED.min_30d_apr,
                    max_30d_apr = EXCLUDED.max_30d_apr,
                    data_points = EXCLUDED.data_points,
                    expected_points = EXCLUDED.expected_points,
                    completeness_percentage = EXCLUDED.completeness_percentage,
                    confidence_level = EXCLUDED.confidence_level,
                    funding_interval_hours = EXCLUDED.funding_interval_hours,
                    update_zone = EXCLUDED.update_zone,
                    last_updated = NOW()
            """
            
            # Add NOW() values to template (23 %s placeholders + NOW(), NOW())
            template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"
            
            execute_values(
                self.cursor,
                query,
                values,
                template=template,
                page_size=100
            )
            
            self.db_connection.commit()
            self.logger.info(f"Batch updated {len(values)} contracts in funding_statistics")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in batch statistics update: {e}")
            self.db_connection.rollback()
            return False
    
    def process_contracts_by_zone(self, zone: str) -> Dict[str, Any]:
        """
        Process only contracts in a specific update zone.
        Performance optimization: Process volatile contracts more frequently.
        
        Args:
            zone: 'active' or 'stable'
            
        Returns:
            Summary statistics
        """
        start_time = datetime.now()
        
        # Get contracts for specified zone
        contracts = self.get_contracts_by_zone(zone)
        
        if not contracts:
            return {
                'zone': zone,
                'total_contracts': 0,
                'processed': 0,
                'duration_seconds': 0
            }
        
        self.logger.info(f"Processing {len(contracts)} contracts in {zone} zone")
        
        # Batch fetch data for zone contracts
        contract_keys = set(contracts)
        
        # Fetch all data
        all_historical_data = self.fetch_all_historical_data_batch()
        all_current_data = self.get_all_current_funding_batch()
        all_metadata = self.get_all_metadata_batch()
        
        # Filter for zone contracts only
        historical_data = {k: v for k, v in all_historical_data.items() if k in contract_keys}
        current_data = {k: v for k, v in all_current_data.items() if k in contract_keys}
        metadata = {k: all_metadata.get(k, {
            'funding_interval_hours': 8,
            'age_days': self.window_days,
            'data_quality_score': 100.0
        }) for k in contract_keys}
        
        # Process contracts
        all_stats = []
        processed = 0
        
        for exchange, symbol in contracts:
            try:
                key = (exchange, symbol)
                
                if key not in historical_data or key not in current_data:
                    continue
                
                historical = historical_data[key]
                current = current_data[key]
                meta = metadata[key]
                
                # Validate and process
                confidence, completeness, expected = self.validate_data_quality(
                    historical['data_count'],
                    meta['funding_interval_hours'],
                    meta['age_days']
                )
                
                if confidence == 'none' or not historical['funding_rates']:
                    continue
                
                # Compute statistics
                stats_funding = self.compute_statistics(historical['funding_rates'])
                stats_apr = self.compute_statistics(historical['apr_values'])
                
                if not stats_funding or not stats_apr:
                    continue
                
                # Calculate Z-scores
                z_score = self.calculate_zscore(
                    current['rate'],
                    stats_funding['mean'],
                    stats_funding['std_dev']
                )
                
                z_score_apr = self.calculate_zscore(
                    current['apr'],
                    stats_apr['mean'],
                    stats_apr['std_dev']
                )
                
                # Calculate percentiles
                percentile = self.calculate_percentile_rank(
                    current['rate'],
                    historical['funding_rates']
                )
                
                percentile_apr = self.calculate_percentile_rank(
                    current['apr'],
                    historical['apr_values']
                )
                
                # Compile result
                result = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'current_funding_rate': current['rate'],
                    'current_apr': current['apr'],
                    'z_score': z_score,
                    'z_score_apr': z_score_apr,
                    'percentile': percentile,
                    'percentile_apr': percentile_apr,
                    'mean_30d': stats_funding['mean'],
                    'std_dev_30d': stats_funding['std_dev'],
                    'min_30d': stats_funding['min'],
                    'max_30d': stats_funding['max'],
                    'mean_30d_apr': stats_apr['mean'],
                    'std_dev_30d_apr': stats_apr['std_dev'],
                    'min_30d_apr': stats_apr['min'],
                    'max_30d_apr': stats_apr['max'],
                    'data_points': historical['data_count'],
                    'expected_points': expected,
                    'completeness_percentage': completeness,
                    'confidence_level': confidence,
                    'funding_interval_hours': current.get('interval_hours', 8)
                }
                
                all_stats.append(result)
                processed += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {exchange} {symbol}: {e}")
        
        # Update zones and database
        self.update_contract_zones(all_stats)
        if all_stats:
            self.batch_update_funding_statistics(all_stats)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'zone': zone,
            'total_contracts': len(contracts),
            'processed': processed,
            'duration_seconds': duration
        }
    
    def _process_contract_batch(self, contract_batch: List[Tuple[str, str]], 
                                historical_data: Dict, current_data: Dict, 
                                metadata: Dict) -> Tuple[List[Dict], int, int]:
        """
        Process a batch of contracts in a single thread.
        Returns: (stats_list, skipped_count, error_count)
        """
        batch_stats = []
        batch_skipped = 0
        batch_errors = 0
        
        for exchange, symbol in contract_batch:
            try:
                key = (exchange, symbol)
                
                # Skip if no data available
                if key not in historical_data or key not in current_data:
                    batch_skipped += 1
                    continue
                
                historical = historical_data[key]
                current = current_data[key]
                meta = metadata.get(key, {
                    'funding_interval_hours': 8,
                    'age_days': self.window_days,
                    'data_quality_score': 100.0
                })
                
                # Validate data quality
                confidence, completeness, expected = self.validate_data_quality(
                    historical['data_count'],
                    meta['funding_interval_hours'],
                    meta['age_days']
                )
                
                # Skip if insufficient data
                if confidence == 'none' or not historical['funding_rates']:
                    batch_skipped += 1
                    continue
                
                # Compute statistics
                stats_funding = self.compute_statistics(historical['funding_rates'])
                stats_apr = self.compute_statistics(historical['apr_values'])
                
                if not stats_funding or not stats_apr:
                    batch_skipped += 1
                    continue
                
                # Calculate Z-scores
                z_score = self.calculate_zscore(
                    current['rate'],
                    stats_funding['mean'],
                    stats_funding['std_dev']
                )
                
                z_score_apr = self.calculate_zscore(
                    current['apr'],
                    stats_apr['mean'],
                    stats_apr['std_dev']
                )
                
                # Calculate percentiles
                percentile = self.calculate_percentile_rank(
                    current['rate'],
                    historical['funding_rates']
                )
                
                percentile_apr = self.calculate_percentile_rank(
                    current['apr'],
                    historical['apr_values']
                )
                
                # Compile statistics
                result = {
                    'exchange': exchange,
                    'symbol': symbol,
                    'current_funding_rate': current['rate'],
                    'current_apr': current['apr'],
                    'z_score': z_score,
                    'z_score_apr': z_score_apr,
                    'percentile': percentile,
                    'percentile_apr': percentile_apr,
                    'mean_30d': stats_funding['mean'],
                    'std_dev_30d': stats_funding['std_dev'],
                    'min_30d': stats_funding['min'],
                    'max_30d': stats_funding['max'],
                    'mean_30d_apr': stats_apr['mean'],
                    'std_dev_30d_apr': stats_apr['std_dev'],
                    'min_30d_apr': stats_apr['min'],
                    'max_30d_apr': stats_apr['max'],
                    'data_points': historical['data_count'],
                    'expected_points': expected,
                    'completeness_percentage': completeness,
                    'confidence_level': confidence,
                    'funding_interval_hours': current.get('interval_hours', 8)
                }
                
                batch_stats.append(result)
                
            except Exception as e:
                self.logger.error(f"Error processing {exchange} {symbol}: {e}")
                batch_errors += 1
        
        return batch_stats, batch_skipped, batch_errors
    
    def process_all_contracts(self) -> Dict[str, Any]:
        """
        OPTIMIZED: Process all ~1,265 contracts using batch operations with PARALLEL PROCESSING.
        Performance target: < 1 second (from 6+ seconds).
        Reference: tasklist.md lines 49-80, Phase 2 parallel processing
        
        Returns:
            Summary statistics of the processing run
        """
        start_time = time.perf_counter()  # More precise timing
        
        self.logger.info("Starting PARALLEL BATCH Z-score calculation")
        
        # Step 1: Batch fetch ALL data (still sequential as DB queries are fast)
        self.logger.info("Step 1: Fetching all data in batch...")
        fetch_start = time.perf_counter()
        historical_data = self.fetch_all_historical_data_batch()
        current_data = self.get_all_current_funding_batch()
        metadata = self.get_all_metadata_batch()
        fetch_duration = time.perf_counter() - fetch_start
        self.logger.info(f"Data fetch completed in {fetch_duration:.3f}s")
        
        # Get all active contracts
        contracts = self.get_all_active_contracts()
        total_contracts = len(contracts)
        
        # Determine optimal number of workers (8 seems good for CPU-bound tasks)
        num_workers = min(8, max(4, total_contracts // 150))  # 4-8 workers
        batch_size = max(1, total_contracts // num_workers)
        
        self.logger.info(f"Processing {total_contracts} contracts with {num_workers} parallel workers")
        
        # Step 2: Split contracts into batches for parallel processing
        contract_batches = []
        for i in range(0, total_contracts, batch_size):
            batch = contracts[i:i + batch_size]
            contract_batches.append(batch)
        
        # Step 3: Process batches in parallel
        process_start = time.perf_counter()
        all_stats = []
        total_skipped = 0
        total_errors = 0
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all batch processing tasks
            futures = [
                executor.submit(
                    self._process_contract_batch,
                    batch,
                    historical_data,
                    current_data,
                    metadata
                )
                for batch in contract_batches
            ]
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    batch_stats, batch_skipped, batch_errors = future.result()
                    all_stats.extend(batch_stats)
                    total_skipped += batch_skipped
                    total_errors += batch_errors
                except Exception as e:
                    self.logger.error(f"Batch processing failed: {e}")
                    total_errors += 1
        
        process_duration = time.perf_counter() - process_start
        self.logger.info(f"Parallel processing completed in {process_duration:.3f}s")
        
        processed = len(all_stats)
        
        # Step 4: Update zones based on new Z-scores
        zone_start = time.perf_counter()
        self.update_contract_zones(all_stats)
        zone_duration = time.perf_counter() - zone_start
        
        # Step 5: Batch update database
        db_start = time.perf_counter()
        self.logger.info("Step 5: Batch updating database...")
        if all_stats:
            success = self.batch_update_funding_statistics(all_stats)
            if not success:
                self.logger.error("Batch database update failed")
        db_duration = time.perf_counter() - db_start
        self.logger.info(f"Database update completed in {db_duration:.3f}s")
        
        # Calculate performance metrics
        total_duration = time.perf_counter() - start_time
        
        summary = {
            'total_contracts': total_contracts,
            'processed': processed,
            'skipped': total_skipped,
            'errors': total_errors,
            'duration_seconds': total_duration,
            'contracts_per_second': processed / total_duration if total_duration > 0 else 0,
            'contracts_processed': processed,  # For compatibility
            'performance_breakdown': {
                'data_fetch_ms': fetch_duration * 1000,
                'processing_ms': process_duration * 1000,
                'zone_update_ms': zone_duration * 1000,
                'db_update_ms': db_duration * 1000,
                'total_ms': total_duration * 1000,
                'parallel_workers': num_workers
            }
        }
        
        self.logger.info(f"PARALLEL Z-score calculation complete: {processed} processed, {total_skipped} skipped, {total_errors} errors in {total_duration:.3f}s")
        self.logger.info(f"Performance breakdown: Fetch={fetch_duration:.3f}s, Process={process_duration:.3f}s, DB={db_duration:.3f}s")
        
        # Performance check
        if total_duration <= 1.0:
            self.logger.info(f"Performance target MET: {total_duration:.3f}s <= 1.0s")
        else:
            self.logger.warning(f"Performance target MISSED: {total_duration:.3f}s > 1.0s (Target improvement needed)")
        
        return summary


# Example usage and testing function
def test_calculator():
    """Test the Z-score calculator with a sample contract."""
    import psycopg2
    from config.settings import (
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE,
        POSTGRES_USER, POSTGRES_PASSWORD
    )
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DATABASE,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        # Create calculator
        calculator = ZScoreCalculator(conn)
        
        # Test with a single contract
        result = calculator.process_contract('Binance', 'BTCUSDT')
        
        if result:
            print(f"Test successful for Binance BTCUSDT:")
            print(f"  Z-score: {result.get('z_score', 'N/A'):.4f}" if result.get('z_score') else "  Z-score: N/A")
            print(f"  Percentile: {result.get('percentile', 'N/A')}")
            print(f"  Confidence: {result.get('confidence_level', 'N/A')}")
            print(f"  Data points: {result.get('data_points', 0)}/{result.get('expected_points', 0)}")
        else:
            print("No result - insufficient data or error")
        
        conn.close()
        
    except Exception as e:
        print(f"Test failed: {e}")


def main():
    """Main loop for continuous Z-score calculation."""
    import time
    import psycopg2
    from config.settings import (
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE,
        POSTGRES_USER, POSTGRES_PASSWORD
    )

    logger = setup_logger("ZScoreCalculatorMain")
    logger.info("Starting Z-score calculator service with zone-based scheduling...")

    from config.settings import (
        ZSCORE_CALCULATION_INTERVAL,
        ZSCORE_ACTIVE_ZONE_INTERVAL,
        ZSCORE_STABLE_ZONE_INTERVAL
    )
    ERROR_RETRY_DELAY = 30

    update_count = 0
    error_count = 0
    last_active_update = 0
    last_stable_update = 0
    first_run = True
    check_interval = min(ZSCORE_ACTIVE_ZONE_INTERVAL, ZSCORE_STABLE_ZONE_INTERVAL) / 2

    while True:
        try:
            current_time = time.time()
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DATABASE,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            calculator = ZScoreCalculator(conn, window_days=30)

            if first_run:
                logger.info("Initial full update of all contracts to establish zones...")
                result = calculator.process_all_contracts()
                logger.info(f"Initial update: {result.get('processed', 0)} contracts in {result.get('duration_seconds', 0):.2f}s")
                last_active_update = current_time
                last_stable_update = current_time
                first_run = False
                update_count += 1
            else:
                if current_time - last_active_update >= ZSCORE_ACTIVE_ZONE_INTERVAL:
                    logger.info("Updating active zone contracts (|Z| > 2.0)...")
                    result = calculator.process_contracts_by_zone('active')
                    logger.info(f"Active zone: {result.get('processed', 0)} contracts in {result.get('duration_seconds', 0):.2f}s")
                    last_active_update = current_time
                    update_count += 1

                if current_time - last_stable_update >= ZSCORE_STABLE_ZONE_INTERVAL:
                    logger.info("Updating stable zone contracts (|Z| <= 2.0)...")
                    result = calculator.process_contracts_by_zone('stable')
                    logger.info(f"Stable zone: {result.get('processed', 0)} contracts in {result.get('duration_seconds', 0):.2f}s")
                    last_stable_update = current_time
                    update_count += 1

            conn.close()

            if update_count % 20 == 0:
                logger.info(f"Status: {update_count} zone updates, {error_count} errors")

            time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            error_count += 1
            logger.error(f"Error in main loop: {e}")
            time.sleep(ERROR_RETRY_DELAY)

    logger.info(f"Z-score calculator stopped. Total updates: {update_count}, Errors: {error_count}")

if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_calculator()
    else:
        main()