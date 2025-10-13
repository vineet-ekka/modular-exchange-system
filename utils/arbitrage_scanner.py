"""
Advanced Arbitrage Scanner with Z-Score Analysis
================================================
Compares funding rates and APRs across exchanges to find arbitrage opportunities.
Includes statistical significance analysis using z-scores and percentiles.
"""

from typing import List, Dict, Any, Optional
from itertools import combinations
import logging
import numpy as np
from utils.logger import setup_logger

logger = setup_logger("ArbitrageScanner")

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



def calculate_contract_level_arbitrage(min_spread: float = 0.001, top_n: int = 20, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
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
    from dotenv import load_dotenv
    from datetime import datetime, timedelta

    load_dotenv()

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
        # Fetch all contracts with their specific data and Z-scores
        # Filter out stale data (older than 3 days) and inactive contracts to avoid showing delisted contracts
        query = """
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
            WHERE ed.funding_rate IS NOT NULL
                AND ed.base_asset IS NOT NULL
                AND ed.last_updated > NOW() - INTERVAL '3 days'
                AND (cm.is_active = true OR cm.is_active IS NULL)
            ORDER BY ed.base_asset, ed.exchange, ed.symbol
        """

        cur.execute(query)
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
            exchanges = list(by_exchange.keys())
            for i in range(len(exchanges)):
                for j in range(i + 1, len(exchanges)):
                    ex1, ex2 = exchanges[i], exchanges[j]

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

                            # Calculate spread Z-score from historical data
                            spread_zscore = None
                            spread_mean = None
                            spread_std_dev = None

                            if apr_spread is not None:
                                try:
                                    # Query historical funding rates for both contracts
                                    hist_query = """
                                        WITH contract_history AS (
                                            SELECT
                                                h1.funding_time,
                                                h1.funding_rate as rate1,
                                                h1.funding_interval_hours as interval1,
                                                h2.funding_rate as rate2,
                                                h2.funding_interval_hours as interval2
                                            FROM funding_rates_historical h1
                                            INNER JOIN funding_rates_historical h2
                                                ON h1.funding_time = h2.funding_time
                                            WHERE h1.exchange = %s
                                                AND h1.symbol = %s
                                                AND h2.exchange = %s
                                                AND h2.symbol = %s
                                                AND h1.funding_time >= NOW() - INTERVAL '30 days'
                                                AND h1.funding_rate IS NOT NULL
                                                AND h2.funding_rate IS NOT NULL
                                        ),
                                        apr_spreads AS (
                                            SELECT
                                                ABS(
                                                    (rate1 * (365 * 24 / COALESCE(interval1, 8)) * 100) -
                                                    (rate2 * (365 * 24 / COALESCE(interval2, 8)) * 100)
                                                ) as apr_spread
                                            FROM contract_history
                                        )
                                        SELECT
                                            AVG(apr_spread) as mean_spread,
                                            STDDEV(apr_spread) as std_spread,
                                            COUNT(*) as data_points
                                        FROM apr_spreads
                                    """

                                    hist_cur.execute(hist_query, (
                                        long_exchange, long_contract['contract'],
                                        short_exchange, short_contract['contract']
                                    ))

                                    hist_result = hist_cur.fetchone()
                                    if hist_result and hist_result[0] is not None and hist_result[1] is not None:
                                        spread_mean = float(hist_result[0])
                                        spread_std_dev = float(hist_result[1])
                                        data_points = hist_result[2]

                                        # Calculate Z-score if we have enough data and non-zero std dev
                                        if data_points >= 30 and spread_std_dev > 0.001:  # Min 30 points and avoid division by near-zero
                                            spread_zscore = (apr_spread - spread_mean) / spread_std_dev
                                            # Clamp extreme values
                                            spread_zscore = max(-10, min(10, spread_zscore))

                                except Exception as e:
                                    logger.debug(f"Error calculating spread Z-score for {asset} {long_exchange}-{short_exchange}: {e}")

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