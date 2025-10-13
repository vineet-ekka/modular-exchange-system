"""
Arbitrage Spread Statistics Module
===================================
Calculates z-scores and percentiles for funding rate spreads between exchanges.
Tracks historical spreads and provides statistical significance analysis.
"""

import numpy as np
from scipy import stats
from typing import Dict, Optional, Tuple, List
import psycopg2
from datetime import datetime, timezone
import logging
from utils.logger import setup_logger


class ArbitrageSpreadStatistics:
    """Calculate and track statistics for arbitrage spreads."""

    def __init__(self, db_connection):
        """
        Initialize the spread statistics calculator.

        Args:
            db_connection: PostgreSQL database connection
        """
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self.logger = setup_logger("ArbitrageSpreadStats")


    def get_spread_statistics(self, asset: str, exchange_a: str, exchange_b: str,
                             current_spread: float) -> Dict:
        """
        Calculate z-score and percentile for current spread.

        Args:
            asset: Asset symbol (e.g., 'BTC')
            exchange_a: First exchange name
            exchange_b: Second exchange name
            current_spread: Current funding rate spread

        Returns:
            Dictionary with statistical metrics
        """
        # Normalize exchange order for consistent lookup
        ex_a, ex_b = sorted([exchange_a, exchange_b])

        try:
            # Try to get from materialized view first (fast)
            query = """
                SELECT mean_spread, std_dev_spread, median_spread,
                       p95_spread, p99_spread, min_spread, max_spread, data_points
                FROM mv_arbitrage_spread_stats
                WHERE asset = %s AND exchange_a = %s AND exchange_b = %s
            """
            self.cursor.execute(query, (asset, ex_a, ex_b))
            result = self.cursor.fetchone()

            if result and result[7] >= 30:  # Need at least 30 data points
                mean, std_dev, median, p95, p99, min_val, max_val, count = result

                if std_dev and std_dev > 0:
                    # Calculate z-score
                    z_score = (abs(current_spread) - mean) / std_dev

                    # Get historical data for percentile calculation
                    hist_query = """
                        SELECT ABS(funding_rate_spread)
                        FROM arbitrage_spreads_historical
                        WHERE asset = %s
                            AND LEAST(exchange_long, exchange_short) = %s
                            AND GREATEST(exchange_long, exchange_short) = %s
                            AND recorded_at >= NOW() - INTERVAL '30 days'
                        ORDER BY ABS(funding_rate_spread)
                    """
                    self.cursor.execute(hist_query, (asset, ex_a, ex_b))
                    historical_spreads = [row[0] for row in self.cursor.fetchall() if row[0] is not None]

                    if historical_spreads:
                        percentile = stats.percentileofscore(historical_spreads, abs(current_spread))
                    else:
                        percentile = None

                    return {
                        'z_score': round(z_score, 2),
                        'percentile': round(percentile, 1) if percentile else None,
                        'mean': float(mean) if mean else None,
                        'std_dev': float(std_dev) if std_dev else None,
                        'median': float(median) if median else None,
                        'p95': float(p95) if p95 else None,
                        'p99': float(p99) if p99 else None,
                        'min': float(min_val) if min_val else None,
                        'max': float(max_val) if max_val else None,
                        'data_points': int(count),
                        'is_significant': abs(z_score) > 2,
                        'is_extreme': abs(z_score) > 3,
                        'has_data': True
                    }

            # Return empty stats if insufficient data
            return {
                'z_score': None,
                'percentile': None,
                'mean': None,
                'std_dev': None,
                'median': None,
                'data_points': int(result[7]) if result else 0,
                'has_data': False,
                'insufficient_data': True
            }

        except Exception as e:
            self.logger.error(f"Error getting spread statistics: {e}")
            return {
                'z_score': None,
                'percentile': None,
                'has_data': False,
                'error': str(e)
            }

    def record_spread(self, asset: str, exchange_long: str, exchange_short: str,
                     long_rate: float, short_rate: float, apr_spread: float) -> bool:
        """
        Record current spread to historical table.

        Args:
            asset: Asset symbol
            exchange_long: Exchange to go long
            exchange_short: Exchange to go short
            long_rate: Funding rate on long exchange
            short_rate: Funding rate on short exchange
            apr_spread: APR spread between exchanges

        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            query = """
                INSERT INTO arbitrage_spreads_historical
                (asset, exchange_long, exchange_short, long_rate, short_rate,
                 funding_rate_spread, apr_spread)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset, exchange_long, exchange_short, recorded_at)
                DO NOTHING
            """
            spread = short_rate - long_rate  # Short pays long

            self.cursor.execute(query, (
                asset, exchange_long, exchange_short,
                long_rate, short_rate, spread, apr_spread
            ))
            self.conn.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error recording spread: {e}")
            self.conn.rollback()
            return False

    def batch_record_spreads(self, spreads: List[Dict]) -> int:
        """
        Record multiple spreads at once for efficiency.

        Args:
            spreads: List of spread dictionaries

        Returns:
            Number of spreads successfully recorded
        """
        if not spreads:
            return 0

        try:
            query = """
                INSERT INTO arbitrage_spreads_historical
                (asset, exchange_long, exchange_short, long_rate, short_rate,
                 funding_rate_spread, apr_spread)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset, exchange_long, exchange_short, recorded_at)
                DO NOTHING
            """

            data = []

            for spread in spreads:
                funding_spread = spread['short_rate'] - spread['long_rate']
                data.append((
                    spread['asset'],
                    spread['exchange_long'],
                    spread['exchange_short'],
                    spread['long_rate'],
                    spread['short_rate'],
                    funding_spread,
                    spread['apr_spread']
                ))

            self.cursor.executemany(query, data)
            self.conn.commit()

            return len(data)

        except Exception as e:
            self.logger.error(f"Error batch recording spreads: {e}")
            self.conn.rollback()
            return 0

    def refresh_statistics_view(self) -> bool:
        """
        Refresh the materialized view for updated statistics.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_arbitrage_spread_stats")
            self.conn.commit()
            self.logger.info("Successfully refreshed spread statistics view")
            return True

        except Exception as e:
            self.logger.error(f"Error refreshing statistics view: {e}")
            self.conn.rollback()
            return False

    def get_spread_history(self, asset: str, exchange_a: str, exchange_b: str,
                          hours: int = 24) -> List[Dict]:
        """
        Get historical spread data for charting.

        Args:
            asset: Asset symbol
            exchange_a: First exchange
            exchange_b: Second exchange
            hours: Number of hours of history to retrieve

        Returns:
            List of historical spread data points
        """
        ex_a, ex_b = sorted([exchange_a, exchange_b])

        try:
            query = """
                SELECT recorded_at, funding_rate_spread, apr_spread
                FROM arbitrage_spreads_historical
                WHERE asset = %s
                    AND LEAST(exchange_long, exchange_short) = %s
                    AND GREATEST(exchange_long, exchange_short) = %s
                    AND recorded_at >= NOW() - INTERVAL '%s hours'
                ORDER BY recorded_at DESC
            """

            self.cursor.execute(query, (asset, ex_a, ex_b, hours))

            history = []
            for row in self.cursor.fetchall():
                history.append({
                    'timestamp': row[0].isoformat(),
                    'funding_spread': float(row[1]) if row[1] else 0,
                    'apr_spread': float(row[2]) if row[2] else 0
                })

            return history

        except Exception as e:
            self.logger.error(f"Error getting spread history: {e}")
            return []

    def calculate_significance_score(self, long_z: Optional[float],
                                    short_z: Optional[float],
                                    spread_z: Optional[float]) -> float:
        """
        Calculate combined significance score for an arbitrage opportunity.

        Args:
            long_z: Z-score of long exchange funding rate
            short_z: Z-score of short exchange funding rate
            spread_z: Z-score of the spread

        Returns:
            Combined significance score (0-10 scale)
        """
        if long_z is None or short_z is None:
            if spread_z:
                base_score = min(10, abs(spread_z) * 2)
            else:
                base_score = 0
        else:
            # How opposite are the z-scores? (best case for arbitrage)
            divergence = abs((long_z or 0) - (short_z or 0))

            # How extreme are individual rates?
            magnitude = (abs(long_z or 0) + abs(short_z or 0)) / 2

            # Are they opposite signs? (ideal for arbitrage)
            opposite_signs = 1.5 if (long_z * short_z) < 0 else 1.0

            if spread_z is not None:
                # We have historical spread data
                base_score = (
                    abs(spread_z) * 0.5 +      # Historical spread significance
                    divergence * 0.3 +          # How opposite the rates are
                    magnitude * 0.2             # How extreme individual rates are
                ) * opposite_signs
            else:
                # No historical spread data yet
                base_score = (
                    divergence * 0.6 +          # More weight on divergence
                    magnitude * 0.4             # Some weight on magnitude
                ) * opposite_signs

        # Scale to 0-10 range
        return min(10, base_score * 2)

