"""
Advanced Arbitrage Scanner with Z-Score Analysis
================================================
Compares funding rates and APRs across exchanges to find arbitrage opportunities.
Includes statistical significance analysis using z-scores and percentiles.
"""

from typing import List, Dict, Any, Optional
from itertools import combinations
import logging
import time
import numpy as np
from utils.logger import setup_logger

logger = setup_logger("ArbitrageScanner")


class SpreadStatsCache:
    """Simple time-based cache for spread statistics with 15s TTL."""
    def __init__(self):
        self._data = None
        self._timestamp = 0
        self._ttl = 15

    def get(self, key, ttl_seconds=15):
        if self._data and (time.time() - self._timestamp) < ttl_seconds:
            return self._data
        return None

    def set(self, key, value, ttl_seconds=15):
        self._data = value
        self._timestamp = time.time()


_spread_stats_cache = SpreadStatsCache()

def calculate_arbitrage_opportunities(
    funding_data: List[Dict[str, Any]],
    min_spread: float = 0.001,
    include_statistics: bool = True
) -> List[Dict[str, Any]]:
    """
    Find arbitrage opportunities from funding rate data with statistical analysis.

    Args:
        funding_data: List of funding rates by asset from /api/funding-rates-grid
        min_spread: Minimum spread to consider (default 0.1%)
        include_statistics: Whether to include z-scores and percentiles

    Returns:
        List of arbitrage opportunities sorted by significance and profit potential
    """
    opportunities = []

    # Import statistics modules if needed
    spread_stats = None
    if include_statistics:
        try:
            import os
            import psycopg2
            from dotenv import load_dotenv
            from utils.arbitrage_spread_statistics import ArbitrageSpreadStatistics

            load_dotenv()
            DB_CONFIG = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DATABASE', 'exchange_data'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'postgres123')
            }

            conn = psycopg2.connect(**DB_CONFIG)
            spread_stats = ArbitrageSpreadStatistics(conn)
        except Exception as e:
            logger.warning(f"Could not initialize spread statistics: {e}")
            spread_stats = None

    for asset_data in funding_data:
        asset = asset_data['asset']
        exchanges = asset_data['exchanges']

        # Extract z-scores for each exchange if available
        exchange_zscores = {}
        for ex, data in exchanges.items():
            if data and isinstance(data, dict):
                # Check for z_score in the data
                if 'z_score' in data:
                    exchange_zscores[ex] = data['z_score']
                # Also check for current_z_score (from funding_statistics table)
                elif 'current_z_score' in data:
                    exchange_zscores[ex] = data['current_z_score']

        # Skip if less than 2 exchanges have data
        valid_exchanges = {
            ex: data for ex, data in exchanges.items()
            if data.get('funding_rate') is not None and data.get('apr') is not None
        }

        if len(valid_exchanges) < 2:
            continue

        # Compare all exchange pairs
        for ex1, ex2 in combinations(valid_exchanges.keys(), 2):
            rate1 = valid_exchanges[ex1]['funding_rate']
            rate2 = valid_exchanges[ex2]['funding_rate']
            apr1 = valid_exchanges[ex1]['apr']
            apr2 = valid_exchanges[ex2]['apr']
            interval1 = valid_exchanges[ex1].get('funding_interval_hours', 8)
            interval2 = valid_exchanges[ex2].get('funding_interval_hours', 8)

            # Skip if both rates have the same sign (both positive or both negative)
            # True arbitrage only exists when rates have opposite signs
            if rate1 * rate2 > 0:
                continue

            # Calculate spread
            rate_spread = abs(rate1 - rate2)
            apr_spread = abs(apr1 - apr2)

            # Skip if spread is too small
            if rate_spread < min_spread:
                continue

            # Determine long and short positions
            # Since we filtered for opposite signs, one rate is positive and one is negative
            # Long position: Go long on the negative rate (receive payment)
            # Short position: Go short on the positive rate (receive payment)
            if rate1 < 0:  # rate1 is negative, rate2 is positive
                long_exchange = ex1
                short_exchange = ex2
                long_rate = rate1
                short_rate = rate2
                long_apr = apr1
                short_apr = apr2
                long_interval = interval1
                short_interval = interval2
            else:  # rate1 is positive, rate2 is negative
                long_exchange = ex2
                short_exchange = ex1
                long_rate = rate2
                short_rate = rate1
                long_apr = apr2
                short_apr = apr1
                long_interval = interval2
                short_interval = interval1

            # Convert rate spread to percentage
            rate_spread_pct = rate_spread * 100

            # Get individual z-scores
            long_zscore = exchange_zscores.get(long_exchange)
            short_zscore = exchange_zscores.get(short_exchange)

            # Initialize statistical fields
            spread_zscore = None
            percentile = None
            is_significant = False
            significance_score = 0
            data_points = 0

            # Get spread statistics if available
            if spread_stats:
                try:
                    spread_stats_data = spread_stats.get_spread_statistics(
                        asset, long_exchange, short_exchange, rate_spread
                    )

                    spread_zscore = spread_stats_data.get('z_score')
                    percentile = spread_stats_data.get('percentile')
                    is_significant = spread_stats_data.get('is_significant', False)
                    data_points = spread_stats_data.get('data_points', 0)

                    # Calculate significance score
                    significance_score = spread_stats.calculate_significance_score(
                        long_zscore, short_zscore, spread_zscore
                    )

                    # Record this spread for future statistics
                    spread_stats.record_spread(
                        asset, long_exchange, short_exchange,
                        long_rate, short_rate, apr_spread
                    )
                except Exception as e:
                    logger.debug(f"Could not get spread statistics for {asset} {long_exchange}-{short_exchange}: {e}")

            # Build opportunity dictionary
            opportunity = {
                'asset': asset,
                'long_exchange': long_exchange,
                'short_exchange': short_exchange,
                'long_rate': long_rate,
                'short_rate': short_rate,
                'long_apr': long_apr,
                'short_apr': short_apr,
                'long_interval_hours': long_interval,
                'short_interval_hours': short_interval,
                'rate_spread': rate_spread,
                'rate_spread_pct': rate_spread_pct,
                'apr_spread': apr_spread,
                'arbitrage_type': 'opposite_sign'  # True arbitrage: receive on both positions
            }

            # Add statistical fields if available
            if include_statistics:
                opportunity.update({
                    'long_zscore': long_zscore,
                    'short_zscore': short_zscore,
                    'spread_zscore': spread_zscore,
                    'percentile': percentile,
                    'is_significant': is_significant,
                    'significance_score': significance_score,
                    'data_points': data_points
                })

            opportunities.append(opportunity)

    # Close database connection if we opened one
    if spread_stats and hasattr(spread_stats, 'conn'):
        try:
            spread_stats.conn.close()
        except:
            pass

    # Sort by significance score (if available), then by spread
    if include_statistics:
        opportunities.sort(key=lambda x: (
            -x.get('significance_score', 0),  # Higher significance first
            -x['rate_spread_pct']  # Higher spread first
        ))
    else:
        opportunities.sort(key=lambda x: x['rate_spread_pct'], reverse=True)

    return opportunities

def get_top_opportunities(
    funding_data: List[Dict[str, Any]],
    top_n: int = 10,
    min_spread: float = 0.001,
    include_statistics: bool = True
) -> Dict[str, Any]:
    """
    Get top N arbitrage opportunities with summary statistics.

    Args:
        funding_data: Funding rates data from API
        top_n: Number of top opportunities to return
        min_spread: Minimum spread threshold
        include_statistics: Whether to include z-scores and percentiles

    Returns:
        Dictionary with top opportunities and statistics
    """
    all_opportunities = calculate_arbitrage_opportunities(funding_data, min_spread, include_statistics)

    # Get top opportunities
    top_opportunities = all_opportunities[:top_n]

    # Calculate basic statistics
    stats = {
        'total_opportunities': len(all_opportunities),
        'average_spread': sum(o['rate_spread_pct'] for o in all_opportunities) / len(all_opportunities) if all_opportunities else 0,
        'max_spread': max((o['rate_spread_pct'] for o in all_opportunities), default=0),
        'max_apr_spread': max((o['apr_spread'] for o in all_opportunities), default=0),
        'most_common_long_exchange': max(
            set(o['long_exchange'] for o in all_opportunities),
            key=lambda x: sum(1 for o in all_opportunities if o['long_exchange'] == x),
            default=None
        ) if all_opportunities else None,
        'most_common_short_exchange': max(
            set(o['short_exchange'] for o in all_opportunities),
            key=lambda x: sum(1 for o in all_opportunities if o['short_exchange'] == x),
            default=None
        ) if all_opportunities else None,
    }

    # Add statistical summary if included
    if include_statistics and all_opportunities:
        significant_opps = [o for o in all_opportunities if o.get('is_significant', False)]
        extreme_opps = [o for o in all_opportunities if o.get('spread_zscore') and abs(o['spread_zscore']) > 3]

        stats.update({
            'significant_count': len(significant_opps),
            'extreme_count': len(extreme_opps),
            'avg_significance_score': sum(o.get('significance_score', 0) for o in all_opportunities) / len(all_opportunities),
            'with_statistics': sum(1 for o in all_opportunities if o.get('spread_zscore') is not None)
        })

    return {
        'opportunities': top_opportunities,
        'statistics': stats
    }


def batch_calculate_spread_statistics(cur, logger, cache=None) -> Dict:
    """
    Pre-calculate spread statistics for all potential contract pairs in ONE query.
    Replaces 20,000+ individual queries with a single batch operation.

    This is the critical performance optimization that reduces response time
    from 3-16 minutes to 1-3 seconds.

    Args:
        cur: Database cursor
        logger: Logger instance
        cache: Optional cache instance for 15s TTL caching

    Returns:
        Dictionary mapping (ex1, sym1, ex2, sym2) -> {mean, std_dev, data_points}
    """
    import time

    cache_key = 'spread_statistics_batch'
    if cache:
        cached = cache.get(cache_key, ttl_seconds=15)
        if cached:
            logger.info("Using cached spread statistics (15s TTL)")
            return cached

    start_time = time.time()

    spread_stats_query = """
    WITH contract_pairs AS (
        SELECT DISTINCT
            h1.exchange as ex1,
            h1.symbol as sym1,
            h2.exchange as ex2,
            h2.symbol as sym2,
            h1.base_asset
        FROM funding_rates_historical h1
        INNER JOIN funding_rates_historical h2
            ON h1.base_asset = h2.base_asset
            AND h1.funding_time = h2.funding_time
            AND h1.exchange < h2.exchange  -- Avoid duplicates (alphabetical ordering)
        WHERE h1.funding_time >= NOW() - INTERVAL '30 days'
            AND h1.funding_rate IS NOT NULL
            AND h2.funding_rate IS NOT NULL
    ),
    spread_calculations AS (
        SELECT
            cp.ex1, cp.sym1, cp.ex2, cp.sym2,
            AVG(ABS(
                (h1.funding_rate * (365*24/COALESCE(h1.funding_interval_hours,8)) * 100) -
                (h2.funding_rate * (365*24/COALESCE(h2.funding_interval_hours,8)) * 100)
            )) as mean_spread,
            CASE
                WHEN COUNT(*) > 1 THEN
                    STDDEV(ABS(
                        (h1.funding_rate * (365*24/COALESCE(h1.funding_interval_hours,8)) * 100) -
                        (h2.funding_rate * (365*24/COALESCE(h2.funding_interval_hours,8)) * 100)
                    ))
                ELSE NULL
            END as std_spread,
            COUNT(*) as data_points
        FROM contract_pairs cp
        INNER JOIN funding_rates_historical h1
            ON cp.ex1 = h1.exchange AND cp.sym1 = h1.symbol
        INNER JOIN funding_rates_historical h2
            ON cp.ex2 = h2.exchange AND cp.sym2 = h2.symbol
            AND h1.funding_time = h2.funding_time
        WHERE h1.funding_time >= NOW() - INTERVAL '30 days'
            AND h1.funding_rate IS NOT NULL
            AND h2.funding_rate IS NOT NULL
        GROUP BY cp.ex1, cp.sym1, cp.ex2, cp.sym2
        HAVING COUNT(*) >= 30  -- Minimum data points for reliable Z-score
    )
    SELECT * FROM spread_calculations
    """

    try:
        cur.execute(spread_stats_query)

        # Build lookup dictionary
        spread_cache = {}
        row_count = 0

        for row in cur.fetchall():
            # Create bidirectional lookup - both (ex1,sym1,ex2,sym2) and (ex2,sym2,ex1,sym1)
            # This ensures we can find the stats regardless of order
            key1 = (row[0], row[1], row[2], row[3])  # ex1, sym1, ex2, sym2
            key2 = (row[2], row[3], row[0], row[1])  # ex2, sym2, ex1, sym1

            stats = {
                'mean': float(row[4]) if row[4] else None,
                'std_dev': float(row[5]) if row[5] else None,
                'data_points': int(row[6])
            }

            spread_cache[key1] = stats
            spread_cache[key2] = stats  # Same stats for reverse lookup
            row_count += 1

        elapsed = time.time() - start_time
        logger.info(f"Batch spread statistics calculated: {row_count} pairs in {elapsed:.2f}s")

        if cache and spread_cache:
            cache.set(cache_key, spread_cache, ttl_seconds=15)
            logger.info("Cached spread statistics for 15s")

        return spread_cache

    except Exception as e:
        logger.error(f"Error in batch spread statistics calculation: {e}")
        return {}



def calculate_contract_level_arbitrage(
    min_spread: float = 0.001,
    top_n: int = 20,
    page: int = 1,
    page_size: int = 20,
    # NEW FILTER PARAMETERS
    assets: Optional[List[str]] = None,
    exchanges: Optional[List[str]] = None,
    intervals: Optional[List[int]] = None,
    min_apr: Optional[float] = None,
    max_apr: Optional[float] = None,
    min_oi_either: Optional[float] = None,
    min_oi_combined: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate arbitrage opportunities at the contract level with correct Z-scores.
    This function fetches individual contract data and compares specific contracts
    across exchanges, ensuring Z-scores match the actual contracts being compared.

    Args:
        min_spread: Minimum spread to consider (e.g., 0.001 = 0.1%)
        top_n: Total number of top opportunities (deprecated, use page_size instead)
        page: Page number for pagination (1-indexed)
        page_size: Number of results per page

    Returns:
        Dictionary with contract-specific arbitrage opportunities and pagination info
    """
    import psycopg2
    import os
    import math
    import logging
    from dotenv import load_dotenv
    from datetime import datetime, timedelta

    load_dotenv()

    # Set up logger
    logger = logging.getLogger(__name__)

    # Database configuration
    DB_CONFIG = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DATABASE', 'exchange_data'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres123')
    }

    # Create database connection
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create a second cursor for spread Z-score queries
    hist_cur = conn.cursor()

    try:
        # Build WHERE clause dynamically for SQL-level filters
        where_conditions = [
            "ed.funding_rate IS NOT NULL",
            "ed.base_asset IS NOT NULL",
            "ed.last_updated > NOW() - INTERVAL '3 days'",
            "(cm.is_active = true OR cm.is_active IS NULL)"
        ]
        params = []

        # Asset filter (SQL-level - very fast)
        if assets:
            where_conditions.append("ed.base_asset = ANY(%s)")
            params.append(assets)

        # Exchange filter moved to post-processing to show ALL opportunities
        # involving selected exchanges, not just between selected exchanges
        # (Commented out SQL filter - now handled after finding opportunities)
        # if exchanges:
        #     where_conditions.append("ed.exchange = ANY(%s)")
        #     params.append(exchanges)

        where_clause = " AND ".join(where_conditions)

        # Fetch all contracts with their specific data and Z-scores
        # Filter out stale data (older than 3 days) and inactive contracts to avoid showing delisted contracts
        query = f"""
            SELECT
                ed.base_asset,
                ed.symbol as contract,
                ed.exchange,
                ed.funding_rate,
                ed.apr,
                ed.funding_interval_hours,
                ed.open_interest,
                fs.current_z_score,
                fs.current_percentile,
                fs.mean_30d,
                fs.std_dev_30d
            FROM exchange_data ed
            LEFT JOIN funding_statistics fs
                ON ed.exchange = fs.exchange AND ed.symbol = fs.symbol
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE {where_clause}
            ORDER BY ed.base_asset, ed.exchange, ed.symbol
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        # Group contracts by base asset
        contracts_by_asset = {}
        for row in rows:
            asset = row[0]  # base_asset
            if asset not in contracts_by_asset:
                contracts_by_asset[asset] = []

            contracts_by_asset[asset].append({
                'contract': row[1],
                'exchange': row[2],
                'funding_rate': float(row[3]) if row[3] else None,
                'apr': float(row[4]) if row[4] else None,
                'funding_interval_hours': row[5] or 8,
                'open_interest': float(row[6]) if row[6] else None,
                'z_score': float(row[7]) if row[7] else None,
                'percentile': float(row[8]) if row[8] else None,
                'mean_30d': float(row[9]) if row[9] else None,
                'std_dev_30d': float(row[10]) if row[10] else None
            })

        # CRITICAL OPTIMIZATION: Pre-calculate all spread statistics in one batch query
        # This replaces 20,000+ individual queries with a single operation
        logger.info("Calculating batch spread statistics...")
        spread_cache = batch_calculate_spread_statistics(hist_cur, logger, cache=_spread_stats_cache)
        logger.info(f"Spread cache populated with {len(spread_cache)} entries")

        opportunities = []

        # Compare contracts across exchanges for each asset
        for asset, contracts in contracts_by_asset.items():
            # Group contracts by exchange
            by_exchange = {}
            for contract in contracts:
                exchange = contract['exchange']
                if exchange not in by_exchange:
                    by_exchange[exchange] = []
                by_exchange[exchange].append(contract)

            # Compare all contract pairs across different exchanges
            exchange_list = list(by_exchange.keys())
            for i in range(len(exchange_list)):
                for j in range(i + 1, len(exchange_list)):
                    ex1, ex2 = exchange_list[i], exchange_list[j]

                    # Compare each contract from ex1 with each from ex2
                    for c1 in by_exchange[ex1]:
                        for c2 in by_exchange[ex2]:
                            if c1['funding_rate'] is None or c2['funding_rate'] is None:
                                continue

                            # Skip if both rates have the same sign (both positive or both negative)
                            # True arbitrage only exists when rates have opposite signs
                            if c1['funding_rate'] * c2['funding_rate'] > 0:
                                continue

                            rate_spread = abs(c1['funding_rate'] - c2['funding_rate'])
                            if rate_spread < min_spread:
                                continue

                            # Determine long and short positions
                            # Since we filtered for opposite signs, one rate is positive and one is negative
                            # Long position: Go long on the negative rate (receive payment)
                            # Short position: Go short on the positive rate (receive payment)
                            if c1['funding_rate'] < 0:  # c1 is negative, c2 is positive
                                long_contract = c1
                                short_contract = c2
                                long_exchange = ex1
                                short_exchange = ex2
                            else:  # c1 is positive, c2 is negative
                                long_contract = c2
                                short_contract = c1
                                long_exchange = ex2
                                short_exchange = ex1

                            # Safe APR spread calculation
                            apr_spread = None
                            if long_contract['apr'] is not None and short_contract['apr'] is not None:
                                try:
                                    apr_spread = abs(long_contract['apr'] - short_contract['apr'])
                                    if math.isnan(apr_spread) or math.isinf(apr_spread):
                                        apr_spread = None
                                except:
                                    apr_spread = None

                            # OPTIMIZED: Look up spread Z-score from pre-calculated cache
                            # This replaces the individual query that was executed 20,000+ times
                            spread_zscore = None
                            spread_mean = None
                            spread_std_dev = None
                            data_points = 0

                            if apr_spread is not None:
                                # Create cache key - try both contract orders
                                cache_key = (
                                    long_exchange, long_contract['contract'],
                                    short_exchange, short_contract['contract']
                                )

                                spread_stats = spread_cache.get(cache_key)

                                if spread_stats:
                                    spread_mean = spread_stats['mean']
                                    spread_std_dev = spread_stats['std_dev']
                                    data_points = spread_stats['data_points']

                                    # Calculate Z-score if we have valid standard deviation
                                    # Handle edge case where std_dev might be None or zero
                                    if spread_std_dev and spread_std_dev > 0.001:
                                        spread_zscore = (apr_spread - spread_mean) / spread_std_dev
                                        # Clamp extreme values to prevent outliers
                                        spread_zscore = max(-10, min(10, spread_zscore))
                                    else:
                                        # If no variance, Z-score is undefined
                                        spread_zscore = None

                                else:
                                    # No historical data available for this pair
                                    # This is normal for new contracts or rarely traded pairs
                                    logger.debug(f"No historical spread data for {asset} {long_exchange}:{long_contract['contract']} - {short_exchange}:{short_contract['contract']}")

                            # Calculate new practical metrics with safe division
                            long_interval = long_contract['funding_interval_hours'] or 8
                            short_interval = short_contract['funding_interval_hours'] or 8

                            # 1. Effective Hourly Rate (funding per hour) - safe division
                            try:
                                long_hourly_rate = long_contract['funding_rate'] / long_interval if long_interval > 0 else 0
                                short_hourly_rate = short_contract['funding_rate'] / short_interval if short_interval > 0 else 0
                                effective_hourly_spread = abs(long_hourly_rate - short_hourly_rate)
                            except:
                                long_hourly_rate = 0
                                short_hourly_rate = 0
                                effective_hourly_spread = 0

                            # 2. Synchronized Period Comparison (over LCM period)
                            try:
                                # Calculate LCM of intervals
                                gcd = math.gcd(int(long_interval), int(short_interval))
                                lcm_hours = (long_interval * short_interval) // gcd if gcd > 0 else max(long_interval, short_interval)

                                # Calculate cumulative funding over synchronized period
                                long_sync_funding = long_contract['funding_rate'] * (lcm_hours / long_interval) if long_interval > 0 else 0
                                short_sync_funding = short_contract['funding_rate'] * (lcm_hours / short_interval) if short_interval > 0 else 0
                                sync_period_spread = abs(long_sync_funding - short_sync_funding)
                            except Exception as e:
                                lcm_hours = max(long_interval, short_interval)
                                long_sync_funding = long_contract['funding_rate'] if long_interval == short_interval else 0
                                short_sync_funding = short_contract['funding_rate'] if long_interval == short_interval else 0
                                sync_period_spread = abs(long_sync_funding - short_sync_funding) if long_interval == short_interval else 0

                            # 3. Daily Funding Comparison (24-hour cumulative) - safe division
                            try:
                                long_daily_funding = long_contract['funding_rate'] * (24 / long_interval) if long_interval > 0 else 0
                                short_daily_funding = short_contract['funding_rate'] * (24 / short_interval) if short_interval > 0 else 0
                                daily_spread = abs(long_daily_funding - short_daily_funding)
                            except:
                                long_daily_funding = 0
                                short_daily_funding = 0
                                daily_spread = 0

                            # Calculate periodic funding spreads for different time horizons
                            weekly_spread = daily_spread * 7 if daily_spread else 0
                            monthly_spread = daily_spread * 30 if daily_spread else 0
                            quarterly_spread = daily_spread * 90 if daily_spread else 0
                            yearly_spread = daily_spread * 365 if daily_spread else 0

                            opportunity = {
                                'asset': asset,
                                'arbitrage_type': 'opposite_sign',  # True arbitrage: receive on both positions
                                # Contract-specific information
                                'long_contract': long_contract['contract'],
                                'long_exchange': long_exchange,
                                'long_rate': long_contract['funding_rate'],
                                'long_apr': long_contract['apr'],
                                'long_interval_hours': long_contract['funding_interval_hours'],
                                'long_zscore': long_contract['z_score'],
                                'long_percentile': long_contract['percentile'],
                                'long_open_interest': long_contract['open_interest'],
                                # Short contract
                                'short_contract': short_contract['contract'],
                                'short_exchange': short_exchange,
                                'short_rate': short_contract['funding_rate'],
                                'short_apr': short_contract['apr'],
                                'short_interval_hours': short_contract['funding_interval_hours'],
                                'short_zscore': short_contract['z_score'],
                                'short_percentile': short_contract['percentile'],
                                'short_open_interest': short_contract['open_interest'],
                                # Spreads
                                'rate_spread': rate_spread,
                                'rate_spread_pct': rate_spread * 100,
                                'apr_spread': apr_spread,
                                # Spread Z-score statistics
                                'spread_zscore': spread_zscore,
                                'spread_mean': spread_mean,
                                'spread_std_dev': spread_std_dev,
                                # New practical metrics
                                'long_hourly_rate': long_hourly_rate,
                                'short_hourly_rate': short_hourly_rate,
                                'effective_hourly_spread': effective_hourly_spread,
                                'sync_period_hours': lcm_hours,
                                'long_sync_funding': long_sync_funding,
                                'short_sync_funding': short_sync_funding,
                                'sync_period_spread': sync_period_spread,
                                'long_daily_funding': long_daily_funding,
                                'short_daily_funding': short_daily_funding,
                                'daily_spread': daily_spread,
                                # Periodic funding spreads (aggregate returns over different periods)
                                'weekly_spread': weekly_spread,
                                'monthly_spread': monthly_spread,
                                'quarterly_spread': quarterly_spread,
                                'yearly_spread': yearly_spread,
                                # Statistical significance - use spread Z-score if available
                                'is_significant': (
                                    (spread_zscore is not None and abs(spread_zscore) > 2) or
                                    (long_contract['z_score'] is not None and abs(long_contract['z_score']) > 2) or
                                    (short_contract['z_score'] is not None and abs(short_contract['z_score']) > 2)
                                )
                            }

                            # Calculate combined open interest if available
                            if long_contract['open_interest'] and short_contract['open_interest']:
                                opportunity['combined_open_interest'] = (
                                    long_contract['open_interest'] + short_contract['open_interest']
                                )

                            opportunities.append(opportunity)

        # Apply Python-level filters after pairing calculation
        # These filters operate on calculated values that weren't available at SQL time

        # Debug logging for exchange filter
        logger.info(f"Exchange filter - Input exchanges: {exchanges}")
        logger.info(f"Exchange filter - Opportunities before filter: {len(opportunities)}")

        # Filter by exchanges - show opportunities BETWEEN selected exchanges
        # When multiple exchanges are selected, show only opportunities where BOTH
        # the long and short positions are in the selected exchanges
        if exchanges:
            # Normalize exchange names for case-insensitive matching
            # Frontend sends lowercase ("binance"), database stores specific casing ("Binance", "ByBit", "KuCoin", etc.)
            EXCHANGE_NAME_MAP = {
                'binance': 'Binance',
                'bybit': 'ByBit',
                'kucoin': 'KuCoin',
                'mexc': 'MEXC',
                'dydx': 'dYdX',
                'backpack': 'Backpack',
                'hyperliquid': 'Hyperliquid',
                'drift': 'Drift',
                'aster': 'Aster',
                'lighter': 'Lighter',
                'pacifica': 'Pacifica',
                'paradex': 'Paradex',
                'hibachi': 'Hibachi',
                'orderly': 'Orderly',
                'deribit': 'Deribit'
            }

            normalized_exchanges = set()
            for ex in exchanges:
                # Try exact match first, then lowercase match, then capitalize as fallback
                if ex in EXCHANGE_NAME_MAP.values():
                    normalized_exchanges.add(ex)
                elif ex.lower() in EXCHANGE_NAME_MAP:
                    normalized_exchanges.add(EXCHANGE_NAME_MAP[ex.lower()])
                else:
                    # Fallback: capitalize first letter
                    normalized_exchanges.add(ex.capitalize())

            logger.info(f"Exchange filter - Normalized exchanges: {normalized_exchanges}")

            filtered_opportunities = []

            # Different logic based on number of selected exchanges:
            # - Single exchange: Show ALL opportunities involving that exchange (OR logic)
            # - Multiple exchanges: Show ONLY opportunities BETWEEN selected exchanges (AND logic)
            if len(normalized_exchanges) == 1:
                # Single exchange: show all opportunities involving it
                for o in opportunities:
                    long_ex = o.get('long_exchange')
                    short_ex = o.get('short_exchange')
                    if long_ex in normalized_exchanges or short_ex in normalized_exchanges:
                        filtered_opportunities.append(o)
                logger.info(f"Exchange filter - Opportunities involving selected exchange: {len(filtered_opportunities)}")
            else:
                # Multiple exchanges: show only opportunities between selected exchanges
                for o in opportunities:
                    long_ex = o.get('long_exchange')
                    short_ex = o.get('short_exchange')
                    if long_ex in normalized_exchanges and short_ex in normalized_exchanges:
                        filtered_opportunities.append(o)
                logger.info(f"Exchange filter - Opportunities BETWEEN selected exchanges: {len(filtered_opportunities)}")
            if len(filtered_opportunities) > 0:
                logger.info(f"Exchange filter - Sample result: {filtered_opportunities[0].get('long_exchange')} <-> {filtered_opportunities[0].get('short_exchange')}")
            opportunities = filtered_opportunities
        else:
            logger.info("Exchange filter - No exchanges specified, showing all opportunities")

        # Filter by funding intervals
        if intervals:
            opportunities = [o for o in opportunities
                           if o.get('long_interval_hours') in intervals
                           or o.get('short_interval_hours') in intervals]

        # Filter by APR spread range
        if min_apr is not None:
            opportunities = [o for o in opportunities if o.get('apr_spread', 0) >= min_apr]

        if max_apr is not None:
            opportunities = [o for o in opportunities if o.get('apr_spread', 0) <= max_apr]

        # Filter by open interest (either side)
        if min_oi_either is not None:
            opportunities = [o for o in opportunities
                           if (o.get('long_open_interest', 0) or 0) >= min_oi_either
                           or (o.get('short_open_interest', 0) or 0) >= min_oi_either]

        # Filter by combined open interest
        if min_oi_combined is not None:
            opportunities = [o for o in opportunities
                           if o.get('combined_open_interest', 0) >= min_oi_combined]

        # Sort by daily spread (highest first) - more practical than APR
        opportunities.sort(key=lambda x: x.get('daily_spread', 0) or 0, reverse=True)

        # Calculate total count and pagination
        total_opportunities = len(opportunities)
        total_pages = math.ceil(total_opportunities / page_size) if page_size > 0 else 1

        # Ensure page is within valid range
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        # Calculate offset and get paginated results
        offset = (page - 1) * page_size
        end_offset = offset + page_size
        paginated_opportunities = opportunities[offset:end_offset]

        # Calculate statistics (on all opportunities, not just paginated)
        stats = {
            'total_opportunities': total_opportunities,
            'average_spread': sum(o['rate_spread_pct'] for o in opportunities) / len(opportunities) if opportunities else 0,
            'max_spread': max((o['rate_spread_pct'] for o in opportunities), default=0),
            'max_apr_spread': max((o['apr_spread'] for o in opportunities if o['apr_spread']), default=0),
            'max_daily_spread': max((o['daily_spread'] for o in opportunities), default=0) * 100,  # Convert to percentage
            'max_hourly_spread': max((o['effective_hourly_spread'] for o in opportunities), default=0) * 100,  # Convert to percentage
            'significant_count': sum(1 for o in opportunities if o['is_significant']),
            'contracts_analyzed': len(rows)
        }

        # Add pagination info
        pagination = {
            'total': total_opportunities,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }

        return {
            'opportunities': paginated_opportunities,
            'statistics': stats,
            'pagination': pagination
        }

    except Exception as e:
        logger.error(f"Error calculating contract-level arbitrage: {e}")
        raise
    finally:
        hist_cur.close()
        cur.close()
        conn.close()