"""
Fix Data Pipeline Architecture
===============================
This script fixes the fundamental architectural issues in the data pipeline:
1. Creates contract_metadata table (single source of truth)
2. Populates it with correct funding intervals
3. Fixes wrong intervals in historical data
4. Validates and corrects data inconsistencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime, timezone
import logging
import pandas as pd
from database.postgres_manager import PostgresManager
from utils.logger import setup_logger

class DataPipelineFixer:
    def __init__(self):
        self.db = PostgresManager()
        self.cursor = self.db.cursor
        self.logger = setup_logger("DataPipelineFixer")
        
    def create_metadata_table(self):
        """Create the contract_metadata table as single source of truth."""
        try:
            # Drop table if exists (for clean slate)
            self.cursor.execute("DROP TABLE IF EXISTS contract_metadata CASCADE")
            
            # Create new metadata table
            create_table_sql = """
            CREATE TABLE contract_metadata (
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                base_asset VARCHAR(20),
                funding_interval_hours INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE,
                first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_validated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                data_quality_score NUMERIC(5,2) DEFAULT 100.0,
                notes TEXT,
                PRIMARY KEY (exchange, symbol)
            );
            
            -- Create indexes for performance
            CREATE INDEX idx_metadata_exchange ON contract_metadata(exchange);
            CREATE INDEX idx_metadata_symbol ON contract_metadata(symbol);
            CREATE INDEX idx_metadata_active ON contract_metadata(is_active);
            CREATE INDEX idx_metadata_interval ON contract_metadata(funding_interval_hours);
            """
            
            self.cursor.execute(create_table_sql)
            self.db.connection.commit()
            self.logger.info("Successfully created contract_metadata table")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating metadata table: {e}")
            self.db.connection.rollback()
            return False
    
    def populate_metadata_from_current(self):
        """Populate contract_metadata from current exchange_data (source of truth for intervals)."""
        try:
            # Get current contract data with correct funding intervals
            query = """
            INSERT INTO contract_metadata (
                exchange, symbol, base_asset, funding_interval_hours, 
                first_seen_at, last_validated
            )
            SELECT 
                exchange,
                symbol,
                base_asset,
                funding_interval_hours,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM exchange_data
            ON CONFLICT (exchange, symbol) 
            DO UPDATE SET
                funding_interval_hours = EXCLUDED.funding_interval_hours,
                last_validated = CURRENT_TIMESTAMP
            """
            
            self.cursor.execute(query)
            rows_affected = self.cursor.rowcount
            self.db.connection.commit()
            
            self.logger.info(f"Populated {rows_affected} contracts in metadata table")
            return rows_affected
            
        except Exception as e:
            self.logger.error(f"Error populating metadata: {e}")
            self.db.connection.rollback()
            return 0
    
    def detect_and_fix_wrong_intervals(self):
        """Detect and fix contracts with wrong funding intervals in historical data."""
        try:
            # Find mismatches between current (correct) and historical (potentially wrong)
            detect_query = """
            SELECT 
                cm.exchange,
                cm.symbol,
                cm.funding_interval_hours as correct_interval,
                hist_intervals.wrong_interval,
                hist_intervals.record_count
            FROM contract_metadata cm
            INNER JOIN (
                SELECT 
                    exchange,
                    symbol,
                    funding_interval_hours as wrong_interval,
                    COUNT(*) as record_count
                FROM funding_rates_historical
                GROUP BY exchange, symbol, funding_interval_hours
            ) hist_intervals
            ON cm.exchange = hist_intervals.exchange 
            AND cm.symbol = hist_intervals.symbol
            WHERE cm.funding_interval_hours != hist_intervals.wrong_interval
            """
            
            self.cursor.execute(detect_query)
            mismatches = self.cursor.fetchall()
            
            if not mismatches:
                self.logger.info("No funding interval mismatches found")
                return 0
            
            self.logger.warning(f"Found {len(mismatches)} contracts with wrong intervals")
            
            # Fix each mismatch
            total_fixed = 0
            for exchange, symbol, correct_interval, wrong_interval, record_count in mismatches:
                self.logger.info(f"Fixing {exchange} {symbol}: {wrong_interval}h -> {correct_interval}h ({record_count} records)")
                
                fix_query = """
                UPDATE funding_rates_historical
                SET funding_interval_hours = %s
                WHERE exchange = %s AND symbol = %s
                """
                
                self.cursor.execute(fix_query, (correct_interval, exchange, symbol))
                fixed_count = self.cursor.rowcount
                total_fixed += fixed_count
                
                # Add note to metadata
                note = f"Fixed interval from {wrong_interval}h to {correct_interval}h on {datetime.now(timezone.utc).isoformat()}"
                self.cursor.execute(
                    "UPDATE contract_metadata SET notes = COALESCE(notes || E'\\n', '') || %s WHERE exchange = %s AND symbol = %s",
                    (note, exchange, symbol)
                )
            
            self.db.connection.commit()
            self.logger.info(f"Fixed {total_fixed} historical records")
            return total_fixed
            
        except Exception as e:
            self.logger.error(f"Error fixing intervals: {e}")
            self.db.connection.rollback()
            return 0
    
    def add_contract_creation_dates(self):
        """Detect and store contract creation dates based on historical data."""
        try:
            # Find the earliest funding time for each contract
            query = """
            UPDATE contract_metadata cm
            SET created_at = earliest.min_time
            FROM (
                SELECT 
                    exchange,
                    symbol,
                    MIN(funding_time) as min_time
                FROM funding_rates_historical
                GROUP BY exchange, symbol
            ) earliest
            WHERE cm.exchange = earliest.exchange 
            AND cm.symbol = earliest.symbol
            """
            
            self.cursor.execute(query)
            updated = self.cursor.rowcount
            
            # For contracts with very recent data, mark them as potentially new
            new_contract_query = """
            UPDATE contract_metadata
            SET notes = COALESCE(notes || E'\\n', '') || 'Potentially new contract (< 7 days of history)'
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
            """
            
            self.cursor.execute(new_contract_query)
            self.db.connection.commit()
            
            self.logger.info(f"Updated creation dates for {updated} contracts")
            return updated
            
        except Exception as e:
            self.logger.error(f"Error adding creation dates: {e}")
            self.db.connection.rollback()
            return 0
    
    def validate_data_quality(self):
        """Validate data quality and flag issues."""
        try:
            # Check for contracts with too little historical data
            quality_query = """
            WITH data_counts AS (
                SELECT 
                    cm.exchange,
                    cm.symbol,
                    cm.funding_interval_hours,
                    COUNT(frh.funding_time) as actual_points,
                    CASE 
                        WHEN cm.created_at IS NOT NULL THEN
                            LEAST(
                                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - cm.created_at)) / 3600 / cm.funding_interval_hours,
                                30 * 24 / cm.funding_interval_hours
                            )
                        ELSE 30 * 24 / cm.funding_interval_hours
                    END as expected_points
                FROM contract_metadata cm
                LEFT JOIN funding_rates_historical frh
                ON cm.exchange = frh.exchange AND cm.symbol = frh.symbol
                GROUP BY cm.exchange, cm.symbol, cm.funding_interval_hours, cm.created_at
            )
            UPDATE contract_metadata cm
            SET data_quality_score = LEAST(100, (dc.actual_points::numeric / NULLIF(dc.expected_points, 0)) * 100)
            FROM data_counts dc
            WHERE cm.exchange = dc.exchange AND cm.symbol = dc.symbol
            """
            
            self.cursor.execute(quality_query)
            self.db.connection.commit()
            
            # Report on data quality
            report_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN data_quality_score >= 90 THEN 1 END) as excellent,
                COUNT(CASE WHEN data_quality_score >= 70 AND data_quality_score < 90 THEN 1 END) as good,
                COUNT(CASE WHEN data_quality_score >= 50 AND data_quality_score < 70 THEN 1 END) as fair,
                COUNT(CASE WHEN data_quality_score < 50 THEN 1 END) as poor
            FROM contract_metadata
            """
            
            self.cursor.execute(report_query)
            total, excellent, good, fair, poor = self.cursor.fetchone()
            
            self.logger.info(f"Data Quality Report:")
            self.logger.info(f"  Total contracts: {total}")
            self.logger.info(f"  Excellent (90-100%): {excellent}")
            self.logger.info(f"  Good (70-90%): {good}")
            self.logger.info(f"  Fair (50-70%): {fair}")
            self.logger.info(f"  Poor (<50%): {poor}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating data quality: {e}")
            self.db.connection.rollback()
            return False
    
    def show_problem_contracts(self):
        """Show the status of previously problematic contracts."""
        try:
            query = """
            SELECT 
                cm.exchange,
                cm.symbol,
                cm.funding_interval_hours,
                cm.created_at,
                cm.data_quality_score,
                fs.data_points,
                fs.expected_points,
                cm.notes
            FROM contract_metadata cm
            LEFT JOIN funding_statistics fs
            ON cm.exchange = fs.exchange AND cm.symbol = fs.symbol
            WHERE cm.symbol IN ('NEWTUSDTM', 'kSHIB_USDC_PERP')
            """
            
            df = pd.read_sql(query, self.db.connection)
            print("\n" + "="*80)
            print("PROBLEM CONTRACTS STATUS:")
            print("="*80)
            for _, row in df.iterrows():
                print(f"\n{row['exchange']} - {row['symbol']}:")
                print(f"  Funding interval: {row['funding_interval_hours']} hours")
                print(f"  Created at: {row['created_at']}")
                print(f"  Data quality: {row['data_quality_score']:.1f}%")
                print(f"  Data points: {row['data_points']}/{row['expected_points']}")
                if row['notes']:
                    print(f"  Notes: {row['notes'][:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error showing problem contracts: {e}")
    
    def run_full_fix(self):
        """Run the complete fix process."""
        print("\n" + "="*80)
        print("STARTING DATA PIPELINE FIX")
        print("="*80)
        
        # Step 1: Create metadata table
        print("\n1. Creating contract_metadata table...")
        if not self.create_metadata_table():
            return False
        
        # Step 2: Populate from current data
        print("\n2. Populating metadata from current exchange data...")
        count = self.populate_metadata_from_current()
        print(f"   Added {count} contracts to metadata table")
        
        # Step 3: Fix wrong intervals
        print("\n3. Detecting and fixing wrong funding intervals...")
        fixed = self.detect_and_fix_wrong_intervals()
        print(f"   Fixed {fixed} historical records")
        
        # Step 4: Add creation dates
        print("\n4. Adding contract creation dates...")
        updated = self.add_contract_creation_dates()
        print(f"   Updated {updated} contracts with creation dates")
        
        # Step 5: Validate data quality
        print("\n5. Validating data quality...")
        self.validate_data_quality()
        
        # Step 6: Show problem contracts
        print("\n6. Checking previously problematic contracts...")
        self.show_problem_contracts()
        
        print("\n" + "="*80)
        print("DATA PIPELINE FIX COMPLETED")
        print("="*80)
        
        return True


if __name__ == "__main__":
    fixer = DataPipelineFixer()
    success = fixer.run_full_fix()
    
    if success:
        print("\n✓ Pipeline fix completed successfully!")
        print("Next step: Update zscore_calculator.py to use the metadata table")
    else:
        print("\n✗ Pipeline fix encountered errors. Check logs for details.")