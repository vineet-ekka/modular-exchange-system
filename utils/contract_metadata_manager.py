"""
Contract Metadata Manager
=========================
Manages the contract_metadata table to keep it synchronized with live data.
Handles new listings, delistings, and metadata updates automatically.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
import psycopg2
from psycopg2.extras import execute_batch
from utils.logger import setup_logger


class ContractMetadataManager:
    """
    Manages contract metadata synchronization and updates.
    Ensures contract_metadata table remains the single source of truth.
    """
    
    def __init__(self, db_connection):
        """
        Initialize the metadata manager.
        
        Args:
            db_connection: PostgreSQL connection object
        """
        self.db_connection = db_connection
        self.cursor = db_connection.cursor()
        self.logger = setup_logger("ContractMetadataManager")
        
        # Ensure metadata table exists
        self._ensure_metadata_table_exists()
    
    def _ensure_metadata_table_exists(self):
        """Ensure the contract_metadata table exists."""
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS contract_metadata (
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                base_asset VARCHAR(20),
                funding_interval_hours INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE,
                first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_validated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                data_quality_score NUMERIC(5,2) DEFAULT 100.0,
                notes TEXT,
                PRIMARY KEY (exchange, symbol)
            );
            
            -- Add indexes if they don't exist
            CREATE INDEX IF NOT EXISTS idx_metadata_exchange ON contract_metadata(exchange);
            CREATE INDEX IF NOT EXISTS idx_metadata_symbol ON contract_metadata(symbol);
            CREATE INDEX IF NOT EXISTS idx_metadata_active ON contract_metadata(is_active);
            CREATE INDEX IF NOT EXISTS idx_metadata_interval ON contract_metadata(funding_interval_hours);
            """
            
            self.cursor.execute(create_table_sql)
            
            # Add last_seen_at column if it doesn't exist
            self.cursor.execute("""
                ALTER TABLE contract_metadata 
                ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """)
            
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error ensuring metadata table exists: {e}")
            self.db_connection.rollback()
    
    def sync_with_exchange_data(self) -> Dict[str, Any]:
        """
        Main synchronization method to keep metadata in sync with exchange_data.
        
        Returns:
            Dictionary with sync statistics
        """
        try:
            stats = {
                'new_listings': 0,
                'delistings': 0,
                'updates': 0,
                'errors': 0,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Step 1: Detect and add new listings
            new_contracts = self.detect_new_listings()
            if new_contracts:
                added = self.add_new_contracts(new_contracts)
                stats['new_listings'] = added
                self.logger.info(f"Added {added} new contracts to metadata")
            
            # Step 2: Update existing contracts
            updated = self.update_existing_contracts()
            stats['updates'] = updated
            
            # Step 3: Detect and mark delistings
            delisted = self.detect_delistings()
            if delisted:
                marked = self.mark_contracts_inactive(delisted)
                stats['delistings'] = marked
                self.logger.info(f"Marked {marked} contracts as delisted")
            
            # Step 4: Update validation timestamps
            self.update_validation_timestamps()
            
            self.logger.info(f"Metadata sync complete: {stats['new_listings']} new, "
                           f"{stats['updates']} updated, {stats['delistings']} delisted")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error during metadata sync: {e}")
            self.db_connection.rollback()
            return {'error': str(e)}
    
    def detect_new_listings(self) -> List[Tuple[str, str]]:
        """
        Detect contracts that are in exchange_data but not in contract_metadata.
        
        Returns:
            List of (exchange, symbol) tuples for new contracts
        """
        try:
            query = """
            SELECT DISTINCT ed.exchange, ed.symbol
            FROM exchange_data ed
            WHERE NOT EXISTS (
                SELECT 1 FROM contract_metadata cm
                WHERE cm.exchange = ed.exchange AND cm.symbol = ed.symbol
            )
            """
            
            self.cursor.execute(query)
            new_contracts = self.cursor.fetchall()
            
            if new_contracts:
                self.logger.info(f"Detected {len(new_contracts)} new contract listings")
                for exchange, symbol in new_contracts[:5]:  # Log first 5
                    self.logger.info(f"  New: {exchange} - {symbol}")
            
            return new_contracts
            
        except Exception as e:
            self.logger.error(f"Error detecting new listings: {e}")
            return []
    
    def add_new_contracts(self, contracts: List[Tuple[str, str]]) -> int:
        """
        Add new contracts to the metadata table.
        
        Args:
            contracts: List of (exchange, symbol) tuples
            
        Returns:
            Number of contracts added
        """
        if not contracts:
            return 0
        
        try:
            # Get full data for new contracts from exchange_data
            placeholders = ','.join(['(%s, %s)'] * len(contracts))
            flat_params = [item for contract in contracts for item in contract]
            
            query = f"""
            INSERT INTO contract_metadata (
                exchange, symbol, base_asset, funding_interval_hours,
                first_seen_at, last_seen_at, last_validated, is_active,
                notes
            )
            SELECT 
                ed.exchange,
                ed.symbol,
                ed.base_asset,
                ed.funding_interval_hours,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                true,
                'Auto-detected new listing on ' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD')
            FROM exchange_data ed
            WHERE (ed.exchange, ed.symbol) IN ({placeholders})
            ON CONFLICT (exchange, symbol) DO NOTHING
            """
            
            self.cursor.execute(query, flat_params)
            added = self.cursor.rowcount
            self.db_connection.commit()
            
            return added
            
        except Exception as e:
            self.logger.error(f"Error adding new contracts: {e}")
            self.db_connection.rollback()
            return 0
    
    def detect_delistings(self, inactive_threshold_hours: int = 24) -> List[Tuple[str, str]]:
        """
        Detect contracts that are in metadata but no longer in exchange_data.
        
        Args:
            inactive_threshold_hours: Hours since last seen to consider delisted
            
        Returns:
            List of (exchange, symbol) tuples for delisted contracts
        """
        try:
            query = """
            SELECT cm.exchange, cm.symbol
            FROM contract_metadata cm
            WHERE cm.is_active = true
            AND NOT EXISTS (
                SELECT 1 FROM exchange_data ed
                WHERE ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            )
            """
            
            self.cursor.execute(query)
            potentially_delisted = self.cursor.fetchall()
            
            if potentially_delisted:
                self.logger.warning(f"Detected {len(potentially_delisted)} potentially delisted contracts")
                for exchange, symbol in potentially_delisted[:5]:  # Log first 5
                    self.logger.warning(f"  Delisted: {exchange} - {symbol}")
            
            return potentially_delisted
            
        except Exception as e:
            self.logger.error(f"Error detecting delistings: {e}")
            return []
    
    def mark_contracts_inactive(self, contracts: List[Tuple[str, str]]) -> int:
        """
        Mark contracts as inactive (delisted).
        
        Args:
            contracts: List of (exchange, symbol) tuples
            
        Returns:
            Number of contracts marked inactive
        """
        if not contracts:
            return 0
        
        try:
            # Update contracts to inactive
            placeholders = ','.join(['(%s, %s)'] * len(contracts))
            flat_params = [item for contract in contracts for item in contract]
            
            query = f"""
            UPDATE contract_metadata
            SET 
                is_active = false,
                notes = COALESCE(notes || E'\\n', '') || 
                       'Marked as delisted on ' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD')
            WHERE (exchange, symbol) IN ({placeholders})
            AND is_active = true
            """
            
            self.cursor.execute(query, flat_params)
            marked = self.cursor.rowcount
            self.db_connection.commit()
            
            return marked
            
        except Exception as e:
            self.logger.error(f"Error marking contracts inactive: {e}")
            self.db_connection.rollback()
            return 0
    
    def update_existing_contracts(self) -> int:
        """
        Update metadata for existing contracts (funding intervals, last_seen, etc).
        
        Returns:
            Number of contracts updated
        """
        try:
            # Update funding intervals and last_seen timestamps
            query = """
            UPDATE contract_metadata cm
            SET 
                funding_interval_hours = ed.funding_interval_hours,
                base_asset = ed.base_asset,
                last_seen_at = CURRENT_TIMESTAMP,
                last_validated = CURRENT_TIMESTAMP
            FROM exchange_data ed
            WHERE cm.exchange = ed.exchange 
            AND cm.symbol = ed.symbol
            AND (
                cm.funding_interval_hours != ed.funding_interval_hours
                OR cm.base_asset IS DISTINCT FROM ed.base_asset
                OR cm.last_validated < CURRENT_TIMESTAMP - INTERVAL '1 hour'
            )
            """
            
            self.cursor.execute(query)
            updated = self.cursor.rowcount
            
            if updated > 0:
                self.logger.info(f"Updated metadata for {updated} contracts")
            
            self.db_connection.commit()
            return updated
            
        except Exception as e:
            self.logger.error(f"Error updating existing contracts: {e}")
            self.db_connection.rollback()
            return 0
    
    def update_validation_timestamps(self):
        """Update last_validated for all active contracts seen in exchange_data."""
        try:
            query = """
            UPDATE contract_metadata cm
            SET last_validated = CURRENT_TIMESTAMP
            FROM exchange_data ed
            WHERE cm.exchange = ed.exchange 
            AND cm.symbol = ed.symbol
            AND cm.is_active = true
            """
            
            self.cursor.execute(query)
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating validation timestamps: {e}")
            self.db_connection.rollback()
    
    def reactivate_contract(self, exchange: str, symbol: str) -> bool:
        """
        Reactivate a previously delisted contract if it appears again.
        
        Args:
            exchange: Exchange name
            symbol: Contract symbol
            
        Returns:
            True if reactivated, False otherwise
        """
        try:
            query = """
            UPDATE contract_metadata
            SET 
                is_active = true,
                last_seen_at = CURRENT_TIMESTAMP,
                notes = COALESCE(notes || E'\\n', '') || 
                       'Reactivated on ' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD')
            WHERE exchange = %s AND symbol = %s AND is_active = false
            """
            
            self.cursor.execute(query, (exchange, symbol))
            reactivated = self.cursor.rowcount > 0
            
            if reactivated:
                self.logger.info(f"Reactivated contract: {exchange} - {symbol}")
                self.db_connection.commit()
            
            return reactivated
            
        except Exception as e:
            self.logger.error(f"Error reactivating contract {exchange} {symbol}: {e}")
            self.db_connection.rollback()
            return False
    
    def get_metadata_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the metadata table.
        
        Returns:
            Dictionary with metadata statistics
        """
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total_contracts,
                COUNT(CASE WHEN is_active THEN 1 END) as active_contracts,
                COUNT(CASE WHEN NOT is_active THEN 1 END) as inactive_contracts,
                COUNT(CASE WHEN last_validated > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 1 END) as recently_validated,
                COUNT(CASE WHEN first_seen_at > CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 1 END) as new_24h,
                COUNT(CASE WHEN first_seen_at > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 1 END) as new_7d,
                MIN(first_seen_at) as oldest_contract,
                MAX(first_seen_at) as newest_contract,
                MAX(last_validated) as last_sync
            FROM contract_metadata
            """
            
            self.cursor.execute(stats_query)
            result = self.cursor.fetchone()
            
            if result:
                return {
                    'total_contracts': result[0],
                    'active_contracts': result[1],
                    'inactive_contracts': result[2],
                    'recently_validated': result[3],
                    'new_listings_24h': result[4],
                    'new_listings_7d': result[5],
                    'oldest_contract': result[6],
                    'newest_contract': result[7],
                    'last_sync': result[8]
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting metadata stats: {e}")
            return {}
    
    def get_recent_changes(self, hours: int = 24) -> Dict[str, List]:
        """
        Get recent changes in contracts (new listings and delistings).
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with 'new_listings' and 'delistings' lists
        """
        try:
            # Get new listings
            new_query = """
            SELECT exchange, symbol, first_seen_at
            FROM contract_metadata
            WHERE first_seen_at > CURRENT_TIMESTAMP - INTERVAL %s
            ORDER BY first_seen_at DESC
            """
            
            self.cursor.execute(new_query, (f'{hours} hours',))
            new_listings = [
                {'exchange': row[0], 'symbol': row[1], 'listed_at': row[2]}
                for row in self.cursor.fetchall()
            ]
            
            # Get recent delistings
            delisted_query = """
            SELECT exchange, symbol, last_seen_at
            FROM contract_metadata
            WHERE is_active = false
            AND last_validated > CURRENT_TIMESTAMP - INTERVAL %s
            ORDER BY last_validated DESC
            """
            
            self.cursor.execute(delisted_query, (f'{hours} hours',))
            delistings = [
                {'exchange': row[0], 'symbol': row[1], 'delisted_at': row[2]}
                for row in self.cursor.fetchall()
            ]
            
            return {
                'new_listings': new_listings,
                'delistings': delistings
            }
            
        except Exception as e:
            self.logger.error(f"Error getting recent changes: {e}")
            return {'new_listings': [], 'delistings': []}