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
            'funding_interval_hours', 'index_price', 'mark_price',
            'open_interest', 'contract_type', 'market_type'
        ]
    
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