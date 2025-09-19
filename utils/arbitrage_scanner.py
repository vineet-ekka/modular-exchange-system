"""
Advanced Arbitrage Scanner with Z-Score Analysis
================================================
Compares funding rates and APRs across exchanges to find arbitrage opportunities.
Includes statistical significance analysis using z-scores and percentiles.
"""

from typing import List, Dict, Any, Optional
from itertools import combinations
import logging
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
            from database.postgres_manager import get_db_connection
            from utils.arbitrage_spread_statistics import ArbitrageSpreadStatistics

            conn = get_db_connection()
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

            # Calculate spread
            rate_spread = abs(rate1 - rate2)
            apr_spread = abs(apr1 - apr2)

            # Skip if spread is too small
            if rate_spread < min_spread:
                continue

            # Determine long and short positions
            if rate1 > rate2:
                long_exchange = ex2
                short_exchange = ex1
                long_rate = rate2
                short_rate = rate1
                long_apr = apr2
                short_apr = apr1
                long_interval = interval2
                short_interval = interval1
            else:
                long_exchange = ex1
                short_exchange = ex2
                long_rate = rate1
                short_rate = rate2
                long_apr = apr1
                short_apr = apr2
                long_interval = interval1
                short_interval = interval2

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
                'apr_spread': apr_spread
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


def calculate_contract_level_arbitrage(min_spread: float = 0.001, top_n: int = 20) -> Dict[str, Any]:
    """
    Calculate arbitrage opportunities at the contract level with correct Z-scores.
    This function fetches individual contract data and compares specific contracts
    across exchanges, ensuring Z-scores match the actual contracts being compared.

    Returns:
        Dictionary with contract-specific arbitrage opportunities
    """
    import psycopg2
    import os
    from dotenv import load_dotenv

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

    try:
        # Fetch all contracts with their specific data and Z-scores
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
            WHERE ed.funding_rate IS NOT NULL
                AND ed.base_asset IS NOT NULL
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

                            rate_spread = abs(c1['funding_rate'] - c2['funding_rate'])
                            if rate_spread < min_spread:
                                continue

                            # Determine long and short positions
                            if c1['funding_rate'] > c2['funding_rate']:
                                long_contract = c2
                                short_contract = c1
                                long_exchange = ex2
                                short_exchange = ex1
                            else:
                                long_contract = c1
                                short_contract = c2
                                long_exchange = ex1
                                short_exchange = ex2

                            apr_spread = abs(long_contract['apr'] - short_contract['apr']) if (
                                long_contract['apr'] is not None and short_contract['apr'] is not None
                            ) else None

                            opportunity = {
                                'asset': asset,
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
                                # Statistical significance
                                'is_significant': (
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

        # Sort by APR spread (highest first)
        opportunities.sort(key=lambda x: x.get('apr_spread', 0) or 0, reverse=True)

        # Get top opportunities
        top_opportunities = opportunities[:top_n]

        # Calculate statistics
        stats = {
            'total_opportunities': len(opportunities),
            'average_spread': sum(o['rate_spread_pct'] for o in opportunities) / len(opportunities) if opportunities else 0,
            'max_spread': max((o['rate_spread_pct'] for o in opportunities), default=0),
            'max_apr_spread': max((o['apr_spread'] for o in opportunities if o['apr_spread']), default=0),
            'significant_count': sum(1 for o in opportunities if o['is_significant']),
            'contracts_analyzed': len(rows)
        }

        return {
            'opportunities': top_opportunities,
            'statistics': stats
        }

    except Exception as e:
        logger.error(f"Error calculating contract-level arbitrage: {e}")
        raise
    finally:
        cur.close()
        conn.close()