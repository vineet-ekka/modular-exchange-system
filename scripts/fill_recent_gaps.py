#!/usr/bin/env python3
"""
Fill recent data gaps for all exchanges.
Fetches the last 24-48 hours of data for contracts with gaps.

This script is designed to fix the common issue where historical APIs
don't return the most recent data (typically last 12-24 hours).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import psycopg2
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Dict, List
import asyncio
import time

from exchanges.binance_exchange import BinanceExchange
from exchanges.kucoin_exchange import KuCoinExchange
from exchanges.hyperliquid_exchange import HyperliquidExchange
from exchanges.backpack_exchange import BackpackExchange
from database.postgres_manager import PostgresManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GapFiller')


class RecentGapFiller:
    def __init__(self, hours_to_fetch: int = 24):
        """
        Initialize the gap filler.
        
        Args:
            hours_to_fetch: Number of hours to fetch (default 24)
        """
        self.hours_to_fetch = hours_to_fetch
        self.db = PostgresManager()
        self.exchanges = {
            'Binance': BinanceExchange(),
            'KuCoin': KuCoinExchange(),
            'Hyperliquid': HyperliquidExchange(),
            'Backpack': BackpackExchange()
        }
        
    def identify_gaps(self, min_gap_hours: float = 6) -> Dict[str, List[str]]:
        """
        Identify contracts with data gaps.
        
        Args:
            min_gap_hours: Minimum gap in hours to consider (default 6)
            
        Returns:
            Dictionary mapping exchange to list of symbols with gaps
        """
        query = """
        WITH latest_data AS (
            SELECT 
                exchange,
                symbol,
                MAX(funding_time) as last_funding,
                EXTRACT(EPOCH FROM (NOW() - MAX(funding_time)))/3600 as hours_gap
            FROM funding_rates_historical
            GROUP BY exchange, symbol
        )
        SELECT 
            exchange,
            symbol,
            last_funding,
            ROUND(hours_gap, 1) as hours_behind
        FROM latest_data
        WHERE hours_gap > %s
        ORDER BY exchange, hours_gap DESC
        """
        
        df = pd.read_sql(query, self.db.connection, params=(min_gap_hours,))
        
        gaps = {}
        for _, row in df.iterrows():
            exchange = row['exchange']
            if exchange not in gaps:
                gaps[exchange] = []
            gaps[exchange].append({
                'symbol': row['symbol'],
                'last_funding': row['last_funding'],
                'hours_behind': row['hours_behind']
            })
        
        # Log summary
        for exchange, contracts in gaps.items():
            logger.info(f"{exchange}: {len(contracts)} contracts with gaps > {min_gap_hours}h")
            if contracts:
                worst = max(contracts, key=lambda x: x['hours_behind'])
                logger.info(f"  Worst gap: {worst['symbol']} ({worst['hours_behind']:.1f} hours)")
        
        return gaps
    
    def fill_binance_gaps(self, symbols: List[Dict]) -> int:
        """
        Fill gaps for Binance contracts.
        
        Args:
            symbols: List of symbol dictionaries with gap info
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Filling gaps for {len(symbols)} Binance contracts")
        
        total_inserted = 0
        exchange = self.exchanges['Binance']
        
        # Process in batches
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}")
            
            for contract in batch:
                symbol = contract['symbol']
                last_funding = contract['last_funding']
                
                # Calculate date range
                end_time = datetime.now(timezone.utc)
                # Start from last known data point or 48 hours ago, whichever is more recent
                start_time = max(
                    last_funding - timedelta(hours=1),  # Overlap by 1 hour
                    end_time - timedelta(hours=48)
                )
                
                try:
                    # Fetch historical data
                    logger.info(f"  Fetching {symbol} from {start_time} to {end_time}")
                    
                    # Determine market type (USD-M vs COIN-M)
                    market_type = 'COIN-M' if '_' in symbol else 'USD-M'
                    
                    df = exchange.fetch_historical_funding_rates(
                        symbol=symbol,
                        market_type=market_type,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if df is not None and not df.empty:
                        # Store in database - upload_historical_funding_rates expects a DataFrame
                        initial_count = len(df)
                        success = self.db.upload_historical_funding_rates(df)
                        if success:
                            total_inserted += initial_count
                            logger.info(f"    Inserted {initial_count} records for {symbol}")
                        else:
                            logger.error(f"    Failed to insert records for {symbol}")
                    else:
                        logger.warning(f"    No data returned for {symbol}")
                        
                except Exception as e:
                    logger.error(f"    Error fetching {symbol}: {e}")
                
                # Rate limiting
                time.sleep(0.2)
        
        return total_inserted
    
    def fill_hyperliquid_gaps(self, symbols: List[Dict]) -> int:
        """
        Fill gaps for Hyperliquid contracts.
        
        Args:
            symbols: List of symbol dictionaries with gap info
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Filling gaps for {len(symbols)} Hyperliquid contracts")
        
        total_inserted = 0
        exchange = self.exchanges['Hyperliquid']
        
        # Hyperliquid requires fetching all contracts at once
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=5)  # Fetch last 5 days to cover gaps
        
        try:
            logger.info(f"Fetching Hyperliquid data for last 5 days")
            
            # Hyperliquid needs to fetch each coin individually
            all_data = []
            for contract in symbols[:10]:  # Limit to 10 for testing
                coin = contract['symbol'].replace('USDC', '')  # Remove USDC suffix
                try:
                    df = exchange.fetch_historical_funding_rates(coin=coin, days=5)
                    if df is not None and not df.empty:
                        all_data.extend(df.to_dict('records'))
                        logger.info(f"  Got {len(df)} records for {coin}")
                except Exception as e:
                    logger.error(f"  Error fetching {coin}: {e}")
            
            if all_data:
                # Filter to only contracts with gaps
                gap_symbols = {s['symbol'] for s in symbols}
                filtered_data = [d for d in all_data if d['symbol'] in gap_symbols]
                
                if filtered_data:
                    # Convert to DataFrame for database insertion
                    df = pd.DataFrame(filtered_data)
                    df['exchange'] = 'Hyperliquid'
                    initial_count = len(df)
                    success = self.db.upload_historical_funding_rates(df)
                    if success:
                        total_inserted += initial_count
                        logger.info(f"Inserted {initial_count} records for Hyperliquid")
                    else:
                        logger.error("Failed to insert Hyperliquid records")
                else:
                    logger.warning("No relevant data found for gap contracts")
            else:
                logger.warning("No data returned from Hyperliquid")
                
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid data: {e}")
        
        return total_inserted
    
    def fill_kucoin_gaps(self, symbols: List[Dict]) -> int:
        """
        Fill gaps for KuCoin contracts.
        
        Args:
            symbols: List of symbol dictionaries with gap info
            
        Returns:
            Number of records inserted
        """
        if not symbols:
            return 0
            
        logger.info(f"Filling gaps for {len(symbols)} KuCoin contracts")
        
        total_inserted = 0
        exchange = self.exchanges['KuCoin']
        
        for contract in symbols:
            symbol = contract['symbol']
            
            # For LEVERUSDTM, need special handling as it's been delisted
            if symbol == 'LEVERUSDTM':
                logger.warning(f"Skipping {symbol} - likely delisted")
                continue
            
            try:
                # KuCoin doesn't have historical funding API
                # We can only get current funding rate
                logger.info(f"  Fetching current data for {symbol}")
                current_data = exchange.fetch_data()
                
                # Filter for this symbol
                symbol_data = [d for d in current_data if d['symbol'] == symbol]
                
                if symbol_data:
                    # This will only add the current funding rate
                    # Better than nothing for filling small gaps
                    df = pd.DataFrame(symbol_data)
                    df['exchange'] = 'KuCoin'
                    df['funding_time'] = datetime.now(timezone.utc)  # Use current time
                    success = self.db.upload_historical_funding_rates(df)
                    if success:
                        total_inserted += 1
                        logger.info(f"    Added current funding rate for {symbol}")
                    else:
                        logger.error(f"    Failed to add current rate for {symbol}")
                    
            except Exception as e:
                logger.error(f"    Error fetching {symbol}: {e}")
        
        return total_inserted
    
    def run(self, min_gap_hours: float = 6):
        """
        Run the gap filling process.
        
        Args:
            min_gap_hours: Minimum gap in hours to consider
        """
        logger.info("=" * 60)
        logger.info("RECENT DATA GAP FILLER")
        logger.info("=" * 60)
        logger.info(f"Fetching last {self.hours_to_fetch} hours of data")
        logger.info(f"Minimum gap threshold: {min_gap_hours} hours")
        logger.info("=" * 60)
        
        # Identify gaps
        gaps = self.identify_gaps(min_gap_hours)
        
        if not gaps:
            logger.info("No significant gaps found!")
            return
        
        # Process each exchange
        total_inserted = 0
        
        # Binance
        if 'Binance' in gaps:
            inserted = self.fill_binance_gaps(gaps['Binance'])
            total_inserted += inserted
            logger.info(f"Binance: Inserted {inserted} records")
        
        # Hyperliquid
        if 'Hyperliquid' in gaps:
            inserted = self.fill_hyperliquid_gaps(gaps['Hyperliquid'])
            total_inserted += inserted
            logger.info(f"Hyperliquid: Inserted {inserted} records")
        
        # KuCoin
        if 'KuCoin' in gaps:
            inserted = self.fill_kucoin_gaps(gaps['KuCoin'])
            total_inserted += inserted
            logger.info(f"KuCoin: Inserted {inserted} records")
        
        # Backpack typically doesn't have gaps
        if 'Backpack' in gaps:
            logger.info(f"Backpack has {len(gaps['Backpack'])} gaps but uses real-time only")
        
        # Summary
        logger.info("=" * 60)
        logger.info("GAP FILLING COMPLETE")
        logger.info(f"Total records inserted: {total_inserted}")
        logger.info("=" * 60)
        
        # Re-check gaps
        new_gaps = self.identify_gaps(min_gap_hours)
        if new_gaps:
            remaining = sum(len(contracts) for contracts in new_gaps.values())
            logger.warning(f"Still {remaining} contracts with gaps > {min_gap_hours}h")
        else:
            logger.info("All gaps successfully filled!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fill recent data gaps')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours of data to fetch (default: 24)')
    parser.add_argument('--min-gap', type=float, default=6,
                        help='Minimum gap in hours to consider (default: 6)')
    
    args = parser.parse_args()
    
    filler = RecentGapFiller(hours_to_fetch=args.hours)
    filler.run(min_gap_hours=args.min_gap)


if __name__ == '__main__':
    main()