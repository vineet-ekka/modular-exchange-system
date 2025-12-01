"""
PostgreSQL Database Manager
===========================
Handles all database operations using local PostgreSQL.
"""

import os
import json
import pandas as pd
import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_batch, Json
from psycopg2 import sql
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from utils.logger import setup_logger
from config.settings import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    DATABASE_TABLE_NAME,
    HISTORICAL_TABLE_NAME,
    SHOW_SAMPLE_DATA
)


class PostgresManager:
    """
    Manager class for PostgreSQL database operations.

    Usage as context manager (recommended):
        with PostgresManager() as db:
            db.upload_data(dataframe)

    Usage without context manager:
        db = PostgresManager()
        try:
            db.upload_data(dataframe)
        finally:
            db.close()
    """

    def __init__(self):
        """
        Initialize the PostgreSQL manager with connection pooling.
        """
        self.logger = setup_logger("PostgresManager")

        # Database configuration
        self.config = {
            'host': POSTGRES_HOST,
            'port': POSTGRES_PORT,
            'database': POSTGRES_DATABASE,
            'user': POSTGRES_USER,
            'password': POSTGRES_PASSWORD
        }

        # Table names
        self.table_name = DATABASE_TABLE_NAME
        self.historical_table_name = HISTORICAL_TABLE_NAME

        # Initialize connection pool (5-20 connections)
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=5,
                maxconn=20,
                **self.config
            )
            self.logger.info("Successfully created PostgreSQL connection pool (5-20 connections)")
        except Exception as e:
            self.logger.error(f"Failed to create connection pool: {e}")
            raise

        # Maintain backward compatibility: keep one connection for existing code
        self.connection = self.pool.getconn()
        self.cursor = self.connection.cursor()

        # Create tables if they don't exist
        self._create_tables()

    def __enter__(self):
        """
        Context manager entry. Returns self for use in 'with' statements.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit. Ensures connections are properly closed.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate exceptions
        """
        self.close()
        return False

    @contextmanager
    def get_connection(self):
        """
        Context manager for acquiring and releasing connections from the pool.

        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
                conn.commit()
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def _disconnect(self):
        """
        Close all connections in the pool.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.pool.putconn(self.connection)
        if self.pool:
            self.pool.closeall()
            self.logger.info("Closed all connections in the pool")

    def _check_pool_health(self):
        """
        Check if the connection pool is healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            return True
        except Exception as e:
            self.logger.warning(f"Pool health check failed: {e}")
            return False

    def _recreate_pool(self, max_retries=3):
        """
        Recreate the connection pool with exponential backoff.
        Attempts to recover from total pool failure.
        """
        import time

        for attempt in range(max_retries):
            try:
                if self.pool:
                    self.pool.closeall()

                self.pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=5,
                    maxconn=20,
                    **self.config
                )

                self.connection = self.pool.getconn()
                self.cursor = self.connection.cursor()

                self.logger.info(f"Successfully recreated connection pool (attempt {attempt + 1})")
                return True

            except Exception as e:
                wait_time = 2 ** attempt
                self.logger.error(f"Failed to recreate pool (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        self.logger.critical("Failed to recreate connection pool after all retries")
        return False

    def ensure_connection(self):
        """
        Ensure the pool is healthy. Recreate if necessary.
        Call this before critical operations.
        """
        if not self._check_pool_health():
            self.logger.warning("Pool unhealthy, attempting to recreate...")
            return self._recreate_pool()
        return True

    def _create_tables(self):
        """
        Create necessary tables if they don't exist.
        """
        try:
            # Create main exchange_data table
            create_main_table = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                base_asset VARCHAR(20),
                quote_asset VARCHAR(20),
                funding_rate NUMERIC(20, 10),
                funding_interval_hours INTEGER,
                apr NUMERIC(20, 10),
                index_price NUMERIC(20, 10),
                mark_price NUMERIC(20, 10),
                open_interest NUMERIC(30, 10),
                contract_type VARCHAR(50),
                market_type VARCHAR(50),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exchange, symbol)
            );
            """
            
            # Create historical table
            create_historical_table = f"""
            CREATE TABLE IF NOT EXISTS {self.historical_table_name} (
                id SERIAL PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                base_asset VARCHAR(20),
                quote_asset VARCHAR(20),
                funding_rate NUMERIC(20, 10),
                funding_interval_hours INTEGER,
                apr NUMERIC(20, 10),
                index_price NUMERIC(20, 10),
                mark_price NUMERIC(20, 10),
                open_interest NUMERIC(30, 10),
                contract_type VARCHAR(50),
                market_type VARCHAR(50),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Create indexes for better performance
            create_indexes = f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_exchange ON {self.table_name}(exchange);
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_symbol ON {self.table_name}(symbol);
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_base_asset ON {self.table_name}(base_asset);
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_apr ON {self.table_name}(apr DESC);
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp ON {self.table_name}(timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_{self.historical_table_name}_exchange ON {self.historical_table_name}(exchange);
            CREATE INDEX IF NOT EXISTS idx_{self.historical_table_name}_symbol ON {self.historical_table_name}(symbol);
            CREATE INDEX IF NOT EXISTS idx_{self.historical_table_name}_base_asset ON {self.historical_table_name}(base_asset);
            CREATE INDEX IF NOT EXISTS idx_{self.historical_table_name}_timestamp ON {self.historical_table_name}(timestamp DESC);
            """

            # Create streaming data table for WebSocket feeds
            create_streaming_table = """
            CREATE TABLE IF NOT EXISTS streaming_data (
                id SERIAL PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                market_type VARCHAR(20),
                funding_rate NUMERIC(20, 10),
                mark_price NUMERIC(20, 10),
                index_price NUMERIC(20, 10),
                next_funding_time TIMESTAMP WITH TIME ZONE,
                stream_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                server_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(exchange, symbol)
            );
            """

            # Create WebSocket connection status table
            create_connection_table = """
            CREATE TABLE IF NOT EXISTS websocket_connections (
                id SERIAL PRIMARY KEY,
                connection_name VARCHAR(100) NOT NULL UNIQUE,
                exchange VARCHAR(50) NOT NULL,
                market_type VARCHAR(20),
                status VARCHAR(20) NOT NULL,
                url TEXT,
                connected_at TIMESTAMP WITH TIME ZONE,
                disconnected_at TIMESTAMP WITH TIME ZONE,
                messages_received BIGINT DEFAULT 0,
                bytes_received BIGINT DEFAULT 0,
                reconnect_count INTEGER DEFAULT 0,
                last_message_time TIMESTAMP WITH TIME ZONE,
                last_error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """

            # Create streaming indexes
            create_streaming_indexes = """
            CREATE INDEX IF NOT EXISTS idx_streaming_data_exchange_symbol
                ON streaming_data(exchange, symbol);
            CREATE INDEX IF NOT EXISTS idx_streaming_data_timestamp
                ON streaming_data(stream_timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_websocket_connections_status
                ON websocket_connections(status);
            """

            self.cursor.execute(create_main_table)
            self.cursor.execute(create_historical_table)
            self.cursor.execute(create_indexes)
            self.cursor.execute(create_streaming_table)
            self.cursor.execute(create_connection_table)
            self.cursor.execute(create_streaming_indexes)
            self.connection.commit()
            
            self.logger.info("Database tables created/verified successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
            raise
    
    def get_connection(self):
        """
        Get a new database connection.
        For compatibility with modules expecting get_connection().
        """
        import psycopg2
        return psycopg2.connect(**self.config)
    
    def return_connection(self, conn):
        """
        Return a database connection (close it).
        For compatibility with modules expecting return_connection().
        """
        if conn:
            try:
                conn.close()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")

    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self.cursor.execute("SELECT 1")
            result = self.cursor.fetchone()
            return result[0] == 1
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def upload_historical_funding_rates(self, df: pd.DataFrame) -> bool:
        """
        Upload historical funding rates to the dedicated historical table.
        
        Args:
            df: DataFrame containing historical funding rate data
            
        Returns:
            True if successful, False otherwise
        """
        if df.empty:
            self.logger.warning("No historical data to upload (empty DataFrame)")
            return False
        
        try:
            # Ensure we have the required columns
            required_columns = ['exchange', 'symbol', 'funding_rate', 'funding_time', 
                              'funding_interval_hours']
            
            for col in required_columns:
                if col not in df.columns:
                    self.logger.error(f"Missing required column: {col}")
                    return False
            
            # Prepare data for insertion (using itertuples for 100x performance vs iterrows)
            records = []
            for row in df.itertuples(index=False):
                # Safely access optional fields using hasattr
                mark_price = float(row.mark_price) if hasattr(row, 'mark_price') and pd.notna(row.mark_price) else None
                base_asset = row.base_asset if hasattr(row, 'base_asset') else None

                record = (
                    row.exchange,
                    row.symbol,
                    float(row.funding_rate) if pd.notna(row.funding_rate) else None,
                    row.funding_time,
                    mark_price,
                    int(row.funding_interval_hours),
                    base_asset
                )
                records.append(record)
            
            # Insert query with ON CONFLICT handling - including base_asset
            insert_query = """
                INSERT INTO funding_rates_historical 
                (exchange, symbol, funding_rate, funding_time, mark_price, funding_interval_hours, base_asset)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (exchange, symbol, funding_time) 
                DO UPDATE SET 
                    funding_rate = EXCLUDED.funding_rate,
                    mark_price = EXCLUDED.mark_price,
                    funding_interval_hours = EXCLUDED.funding_interval_hours,
                    base_asset = EXCLUDED.base_asset
            """
            
            # Batch insert with increased page size for better performance
            execute_batch(self.cursor, insert_query, records, page_size=500)
            self.connection.commit()
            
            self.logger.info(f"Successfully uploaded {len(records)} historical funding rate records")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload historical funding rates: {e}")
            self.connection.rollback()
            return False
    
    def get_latest_funding_time(self, exchange: str, symbol: str) -> Optional[datetime]:
        """
        Get the latest funding time for a symbol from the historical table.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            
        Returns:
            Latest funding time or None if no data exists
        """
        try:
            query = """
                SELECT MAX(funding_time) as latest_time
                FROM funding_rates_historical
                WHERE exchange = %s AND symbol = %s
            """
            self.cursor.execute(query, (exchange, symbol))
            result = self.cursor.fetchone()
            
            if result and result[0]:
                return result[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get latest funding time: {e}")
            return None
    
    def upload_data(self, df: pd.DataFrame, historical: bool = False) -> bool:
        """
        Upload DataFrame to PostgreSQL database.
        
        Args:
            df: DataFrame containing exchange data
            historical: If True, upload to historical table
            
        Returns:
            True if successful, False otherwise
        """
        if df.empty:
            self.logger.warning("No data to upload (empty DataFrame)")
            return False
        
        try:
            # Choose table
            table = self.historical_table_name if historical else self.table_name
            
            # Prepare data
            df_copy = df.copy()

            # Remove batch tracking columns if they exist (defensive programming)
            # These columns are used for tracking during collection but not stored in database
            columns_to_drop = ['batch_id', 'collection_timestamp', 'volume_24h', 'premium']
            for col in columns_to_drop:
                if col in df_copy.columns:
                    df_copy = df_copy.drop(columns=[col])
                    self.logger.debug(f"Removed tracking column '{col}' before database insertion")

            # Add timestamp if not present
            if 'timestamp' not in df_copy.columns:
                df_copy['timestamp'] = datetime.now(timezone.utc)

            # Add last_updated for main table
            if not historical and 'last_updated' not in df_copy.columns:
                df_copy['last_updated'] = datetime.now(timezone.utc)

            # Double-check to ensure batch_id is truly removed
            # Filter out any columns that shouldn't be in the database
            valid_columns = ['exchange', 'symbol', 'base_asset', 'quote_asset',
                           'funding_rate', 'funding_interval_hours', 'apr',
                           'index_price', 'mark_price', 'open_interest',
                           'contract_type', 'market_type', 'timestamp', 'last_updated',
                           'volume_24h_quote', 'index_mark_spread']

            # Only keep columns that exist in both the dataframe and valid_columns
            columns_to_keep = [col for col in df_copy.columns if col in valid_columns or historical]
            df_copy = df_copy[columns_to_keep]

            # Handle NaT values in timestamp columns
            import pandas as pd
            import numpy as np
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]) or 'time' in col.lower():
                    # Replace NaT with None (which becomes NULL in PostgreSQL)
                    df_copy[col] = df_copy[col].replace({pd.NaT: None})

            # Convert DataFrame to list of tuples
            columns = df_copy.columns.tolist()
            values = df_copy.values.tolist()
            
            if SHOW_SAMPLE_DATA and len(values) > 0:
                self.logger.info(f"Sample data (first row): {dict(zip(columns, values[0]))}")
            
            if historical:
                # For historical table, always INSERT
                insert_query = sql.SQL("""
                    INSERT INTO {} ({}) VALUES ({})
                """).format(
                    sql.Identifier(table),
                    sql.SQL(', ').join(map(sql.Identifier, columns)),
                    sql.SQL(', ').join(sql.Placeholder() * len(columns))
                )
                
                execute_batch(self.cursor, insert_query, values, page_size=500)
                
            else:
                # For main table, use UPSERT (INSERT ... ON CONFLICT UPDATE)
                insert_query = sql.SQL("""
                    INSERT INTO {} ({}) VALUES ({})
                    ON CONFLICT (exchange, symbol)
                    DO UPDATE SET
                        funding_rate = EXCLUDED.funding_rate,
                        funding_interval_hours = EXCLUDED.funding_interval_hours,
                        apr = EXCLUDED.apr,
                        index_price = EXCLUDED.index_price,
                        mark_price = EXCLUDED.mark_price,
                        open_interest = EXCLUDED.open_interest,
                        contract_type = EXCLUDED.contract_type,
                        market_type = EXCLUDED.market_type,
                        base_asset = EXCLUDED.base_asset,
                        quote_asset = EXCLUDED.quote_asset,
                        timestamp = EXCLUDED.timestamp,
                        last_updated = EXCLUDED.last_updated
                """).format(
                    sql.Identifier(table),
                    sql.SQL(', ').join(map(sql.Identifier, columns)),
                    sql.SQL(', ').join(sql.Placeholder() * len(columns))
                )

                execute_batch(self.cursor, insert_query, values, page_size=500)
            
            self.connection.commit()
            
            self.logger.info(f"Successfully uploaded {len(df)} records to {table}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload data: {e}")
            self.connection.rollback()
            return False
    
    def fetch_data(self, query: str = None, limit: int = None) -> pd.DataFrame:
        """
        Fetch data from the database.
        
        Args:
            query: SQL query to execute (optional)
            limit: Number of records to fetch
            
        Returns:
            DataFrame with fetched data
        """
        try:
            if query:
                df = pd.read_sql_query(query, self.connection)
            else:
                if limit:
                    query = f"SELECT * FROM {self.table_name} ORDER BY timestamp DESC LIMIT {limit}"
                else:
                    query = f"SELECT * FROM {self.table_name} ORDER BY timestamp DESC"
                df = pd.read_sql_query(query, self.connection)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch data: {e}")
            return pd.DataFrame()
    
    def get_historical_summary(self) -> Dict[str, Any]:
        """
        Get summary of historical data.
        
        Returns:
            Dictionary with summary statistics
        """
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT exchange) as exchanges,
                COUNT(DISTINCT symbol) as symbols,
                MIN(timestamp) as earliest_record,
                MAX(timestamp) as latest_record,
                AVG(apr) as avg_apr
            FROM {self.historical_table_name}
            """
            
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, result))
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get historical summary: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """
        Remove historical data older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            True if successful
        """
        try:
            query = f"""
            DELETE FROM {self.historical_table_name}
            WHERE timestamp < NOW() - INTERVAL '{days} days'
            """

            self.cursor.execute(query)
            deleted = self.cursor.rowcount
            self.connection.commit()

            self.logger.info(f"Deleted {deleted} records older than {days} days")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            self.connection.rollback()
            return False

    def cleanup_historical_funding_rates(self, days: int = 30) -> int:
        """
        Remove historical funding rate data older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of records deleted (or -1 if error)
        """
        try:
            query = """
            DELETE FROM funding_rates_historical
            WHERE funding_time < NOW() - INTERVAL %s
            """

            self.cursor.execute(query, (f'{days} days',))
            deleted_count = self.cursor.rowcount
            self.connection.commit()

            self.logger.info(f"Deleted {deleted_count} historical funding rate records older than {days} days")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup historical funding rates: {e}")
            self.connection.rollback()
            return -1
    
    def close(self):
        """
        Explicitly close all connections. Use this instead of relying on __del__.
        """
        self._disconnect()

    def __del__(self):
        """
        Cleanup on deletion (unreliable - prefer explicit close()).
        """
        try:
            self._disconnect()
        except Exception:
            pass