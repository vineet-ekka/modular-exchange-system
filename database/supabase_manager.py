"""
Supabase Database Manager
========================
Handles all database operations with Supabase.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from supabase import create_client, Client
from config.settings import (
    SUPABASE_URL, SUPABASE_KEY, DATABASE_TABLE_NAME,
    ENABLE_DATABASE_UPLOAD, SHOW_SAMPLE_DATA
)
from datetime import datetime
import config.settings as settings


class SupabaseManager:
    """
    Manages all Supabase database operations.
    """
    
    def __init__(self):
        """
        Initialize the Supabase client.
        """
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table_name = DATABASE_TABLE_NAME
        
        # Define table columns exactly as in Supabase
        self.table_columns = [
            'exchange', 'symbol', 'base_asset', 'quote_asset', 'funding_rate',
            'funding_interval_hours', 'apr', 'index_price', 'mark_price',
            'open_interest', 'contract_type', 'market_type'
        ]
        
        # Historical table columns (includes timestamp)
        self.historical_table_columns = self.table_columns + ['timestamp']
        
        # Historical table name (will be configurable in settings)
        self.historical_table_name = getattr(settings, 'HISTORICAL_TABLE_NAME', 'exchange_data_historical')
    
    def upload_data(self, data: pd.DataFrame) -> bool:
        """
        Upload DataFrame to Supabase.
        
        Args:
            data: DataFrame to upload
            
        Returns:
            True if successful, False otherwise
        """
        if not ENABLE_DATABASE_UPLOAD:
            print("Database upload is disabled in settings")
            return False
        
        if data.empty:
            print("No data to upload")
            return False
        
        try:
            # Prepare data for upload
            df_to_upload = self._prepare_data_for_upload(data)
            
            if df_to_upload.empty:
                print("No valid data to upload after preparation")
                return False
            
            # Convert to records
            records = df_to_upload.to_dict(orient='records')
            
            # Show sample data if enabled
            if SHOW_SAMPLE_DATA and records:
                print("Sample row to upload:", records[0])
                print("All columns:", list(df_to_upload.columns))
                print("Sample row types:", {k: type(v).__name__ for k, v in records[0].items()})
                print("Sample row values:", {k: repr(v) for k, v in records[0].items()})
            
            # Upload data in batches for better performance
            batch_size = 100  # Supabase typically handles 100-1000 records well
            total_uploaded = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                try:
                    # Use upsert to avoid duplicates based on exchange and symbol
                    self.client.table(self.table_name).upsert(
                        batch, 
                        on_conflict='exchange,symbol'
                    ).execute()
                    total_uploaded += len(batch)
                    print(f"  Uploaded batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size} ({len(batch)} records)")
                except Exception as e:
                    print(f"! Error uploading batch {i//batch_size + 1}: {e}")
                    # Try individual upload for failed batch
                    for record in batch:
                        try:
                            self.client.table(self.table_name).upsert(
                                record, 
                                on_conflict='exchange,symbol'
                            ).execute()
                            total_uploaded += 1
                        except:
                            pass
            
            print(f"OK Uploaded {total_uploaded}/{len(records)} rows to Supabase table '{self.table_name}'")
            return total_uploaded > 0
            
        except Exception as e:
            print(f"X Error uploading to Supabase: {e}")
            return False
    
    def _prepare_data_for_upload(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for upload to Supabase.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Prepared DataFrame ready for upload
        """
        # Only keep columns that exist in the table
        available_columns = [col for col in self.table_columns if col in df.columns]
        df_to_upload = df[available_columns].copy()
        
        # Convert datetime columns to ISO format strings
        for col in df_to_upload.columns:
            if pd.api.types.is_datetime64_any_dtype(df_to_upload[col]):
                df_to_upload[col] = df_to_upload[col].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Replace NaN, inf, -inf with None
        df_to_upload = df_to_upload.replace([np.nan, np.inf, -np.inf], None)
        
        # Remove rows that are completely empty
        df_to_upload = df_to_upload.dropna(how='all')
        
        return df_to_upload
    
    def fetch_data(self, filters: Dict = None) -> pd.DataFrame:
        """
        Fetch data from Supabase.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            DataFrame with fetched data
        """
        try:
            query = self.client.table(self.table_name).select('*')
            
            # Apply filters if provided
            if filters:
                for column, value in filters.items():
                    if isinstance(value, (list, tuple)):
                        query = query.in_(column, value)
                    else:
                        query = query.eq(column, value)
            
            response = query.execute()
            
            if response.data:
                return pd.DataFrame(response.data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"X Error fetching from Supabase: {e}")
            return pd.DataFrame()
    
    def delete_data(self, filters: Dict = None) -> bool:
        """
        Delete data from Supabase.
        
        Args:
            filters: Optional filters to specify what to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = self.client.table(self.table_name).delete()
            
            # Apply filters if provided
            if filters:
                for column, value in filters.items():
                    if isinstance(value, (list, tuple)):
                        query = query.in_(column, value)
                    else:
                        query = query.eq(column, value)
            
            response = query.execute()
            print(f"OK Deleted {len(response.data) if response.data else 0} rows from Supabase")
            return True
            
        except Exception as e:
            print(f"X Error deleting from Supabase: {e}")
            return False
    
    def get_table_info(self) -> Dict:
        """
        Get information about the database table.
        
        Returns:
            Dictionary with table information
        """
        try:
            # Get total count
            count_response = self.client.table(self.table_name).select('*', count='exact').execute()
            total_count = count_response.count if hasattr(count_response, 'count') else 0
            
            # Get sample data
            sample_response = self.client.table(self.table_name).select('*').limit(1).execute()
            sample_data = sample_response.data[0] if sample_response.data else {}
            
            return {
                'table_name': self.table_name,
                'total_rows': total_count,
                'columns': list(sample_data.keys()) if sample_data else [],
                'sample_row': sample_data
            }
            
        except Exception as e:
            print(f"X Error getting table info: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """
        Test the connection to Supabase.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch a single row
            response = self.client.table(self.table_name).select('*').limit(1).execute()
            print("OK Supabase connection successful")
            return True
            
        except Exception as e:
            print(f"X Supabase connection failed: {e}")
            return False 
    
    def upload_historical_data(self, data: pd.DataFrame) -> bool:
        """
        Upload DataFrame to historical table with timestamp.
        Uses INSERT (not UPSERT) to preserve all historical records.
        
        Args:
            data: DataFrame to upload (must include timestamp column)
            
        Returns:
            True if successful, False otherwise
        """
        if not ENABLE_DATABASE_UPLOAD:
            print("Database upload is disabled in settings")
            return False
        
        if data.empty:
            print("No data to upload")
            return False
        
        # Check if timestamp column exists
        if 'timestamp' not in data.columns:
            print("! Error: Historical data must include timestamp column")
            return False
        
        try:
            # Prepare data for historical upload
            df_to_upload = self._prepare_historical_data(data)
            
            if df_to_upload.empty:
                print("No valid data to upload after preparation")
                return False
            
            # Convert to records
            records = df_to_upload.to_dict(orient='records')
            
            # Show sample data if enabled
            if SHOW_SAMPLE_DATA and records:
                print("Sample historical row to upload:", records[0])
            
            # Upload data in batches (using INSERT, not UPSERT)
            batch_size = 100
            total_uploaded = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                try:
                    # Use insert to preserve all historical records
                    self.client.table(self.historical_table_name).insert(batch).execute()
                    total_uploaded += len(batch)
                    print(f"  Uploaded historical batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size} ({len(batch)} records)")
                except Exception as e:
                    print(f"! Error uploading historical batch {i//batch_size + 1}: {e}")
                    # Continue with next batch on error
            
            print(f"OK Uploaded {total_uploaded}/{len(records)} rows to historical table '{self.historical_table_name}'")
            return total_uploaded > 0
            
        except Exception as e:
            print(f"X Error uploading to historical table: {e}")
            return False
    
    def _prepare_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for historical upload.
        
        Args:
            df: Raw DataFrame with timestamp
            
        Returns:
            Prepared DataFrame ready for historical upload
        """
        # Get available columns from historical columns list
        available_columns = [col for col in self.historical_table_columns if col in df.columns]
        df_to_upload = df[available_columns].copy()
        
        # Ensure timestamp is in ISO format
        if 'timestamp' in df_to_upload.columns:
            if pd.api.types.is_datetime64_any_dtype(df_to_upload['timestamp']):
                df_to_upload['timestamp'] = df_to_upload['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
            else:
                # Try to convert to datetime if it's a string
                try:
                    df_to_upload['timestamp'] = pd.to_datetime(df_to_upload['timestamp']).dt.strftime('%Y-%m-%dT%H:%M:%S%z')
                except:
                    pass
        
        # Convert other datetime columns to ISO format strings
        for col in df_to_upload.columns:
            if col != 'timestamp' and pd.api.types.is_datetime64_any_dtype(df_to_upload[col]):
                df_to_upload[col] = df_to_upload[col].dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Replace NaN, inf, -inf with None
        df_to_upload = df_to_upload.replace([np.nan, np.inf, -np.inf], None)
        
        # Remove rows that are completely empty
        df_to_upload = df_to_upload.dropna(how='all')
        
        return df_to_upload
    
    def fetch_historical_data(self, 
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None,
                            exchanges: Optional[List[str]] = None,
                            symbols: Optional[List[str]] = None,
                            limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch historical data with time range and filters.
        
        Args:
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            exchanges: List of exchanges to filter
            symbols: List of symbols to filter
            limit: Maximum number of records to return
            
        Returns:
            DataFrame with historical data
        """
        try:
            query = self.client.table(self.historical_table_name).select('*')
            
            # Apply time range filters
            if start_time:
                query = query.gte('timestamp', start_time.isoformat())
            if end_time:
                query = query.lte('timestamp', end_time.isoformat())
            
            # Apply exchange filter
            if exchanges:
                query = query.in_('exchange', exchanges)
            
            # Apply symbol filter
            if symbols:
                query = query.in_('symbol', symbols)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Order by timestamp descending (most recent first)
            query = query.order('timestamp', desc=True)
            
            response = query.execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                # Convert timestamp back to datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"X Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def get_historical_summary(self) -> Dict:
        """
        Get summary statistics for historical table.
        
        Returns:
            Dictionary with summary stats
        """
        try:
            # Get total count
            count_response = self.client.table(self.historical_table_name).select('*', count='exact').execute()
            total_count = count_response.count if hasattr(count_response, 'count') else 0
            
            # Get time range
            oldest = self.client.table(self.historical_table_name).select('timestamp').order('timestamp').limit(1).execute()
            newest = self.client.table(self.historical_table_name).select('timestamp').order('timestamp', desc=True).limit(1).execute()
            
            oldest_time = oldest.data[0]['timestamp'] if oldest.data else None
            newest_time = newest.data[0]['timestamp'] if newest.data else None
            
            # Get unique exchanges and symbols count
            exchanges_response = self.client.table(self.historical_table_name).select('exchange').execute()
            symbols_response = self.client.table(self.historical_table_name).select('symbol').execute()
            
            unique_exchanges = len(set(row['exchange'] for row in exchanges_response.data)) if exchanges_response.data else 0
            unique_symbols = len(set(row['symbol'] for row in symbols_response.data)) if symbols_response.data else 0
            
            return {
                'table_name': self.historical_table_name,
                'total_records': total_count,
                'oldest_record': oldest_time,
                'newest_record': newest_time,
                'unique_exchanges': unique_exchanges,
                'unique_symbols': unique_symbols
            }
            
        except Exception as e:
            print(f"X Error getting historical summary: {e}")
            return {}