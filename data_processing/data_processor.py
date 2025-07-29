"""
Data Processor
==============
Handles data analysis, display, and export functionality.
"""

import pandas as pd
import time
from typing import Optional
from config.settings import (
    DISPLAY_LIMIT, DEFAULT_SORT_COLUMN, DEFAULT_SORT_ASCENDING,
    CSV_FILENAME, ENABLE_CSV_EXPORT, ENABLE_CONSOLE_DISPLAY
)
from utils.data_validator import validate_exchange_data, DataValidationError


class DataProcessor:
    """
    Handles data processing, analysis, and display functionality.
    """
    
    def __init__(self, data: pd.DataFrame, validate_data: bool = True):
        """
        Initialize the data processor.
        
        Args:
            data: DataFrame to process
            validate_data: Whether to validate input data (default: True)
            
        Raises:
            DataValidationError: If data validation fails critically
            ValueError: If data is invalid or empty
        """
        # Input validation
        if not isinstance(data, pd.DataFrame):
            raise ValueError(f"Expected pandas DataFrame, got {type(data)}")
        
        # Validate data if requested
        self.quality_score = 100.0
        if validate_data and not data.empty:
            validator = validate_exchange_data(data, strict=False)
            self.quality_score = validator.quality_score
            validation_report = validator.get_validation_report()
            
            # Print validation report if there are issues
            if validator.errors or validator.warnings:
                print("\n" + "="*60)
                print("DATA VALIDATION REPORT")
                print("="*60)
                print(validation_report)
            
            # Raise on critical errors
            validator.raise_on_errors()
        
        self.data = data
        
        # Calculate APR if funding data is available
        if not self.data.empty and 'funding_rate' in self.data.columns and 'funding_interval_hours' in self.data.columns:
            self._calculate_apr()
        
        self.unified_columns = [
            'exchange', 'symbol', 'base_asset', 'quote_asset', 
            'funding_rate', 'funding_interval_hours', 'apr', 'index_price', 
            'mark_price', 'open_interest', 
            'contract_type', 'market_type'
        ]
    
    def _calculate_apr(self):
        """
        Calculate APR (Annual Percentage Rate) from funding rate and interval.
        Formula: APR = funding_rate * (8760 / funding_interval_hours)
        Where 8760 = hours in a year (365 * 24)
        """
        # Calculate APR for rows with valid funding data
        mask = (
            self.data['funding_rate'].notna() & 
            self.data['funding_interval_hours'].notna() & 
            (self.data['funding_interval_hours'] > 0)
        )
        
        # Calculate APR where data is valid
        # Multiply by 100 to convert to percentage
        self.data.loc[mask, 'apr'] = (
            self.data.loc[mask, 'funding_rate'] * 
            (8760 / self.data.loc[mask, 'funding_interval_hours']) * 100
        )
        
        # Set APR to None for invalid data
        self.data.loc[~mask, 'apr'] = None
    
    def _format_funding_rate(self, value):
        """
        Format funding rate to avoid scientific notation.
        
        Args:
            value: The funding rate value
            
        Returns:
            Formatted string
        """
        if pd.isna(value):
            return "N/A"
        
        # Use 18 decimal places for all funding rates
        return f"{value:.18f}"
    
    def display_summary(self):
        """Display summary statistics"""
        if self.data.empty:
            print("No data to display")
            return
        
        print("\n" + "="*80)
        print("UNIFIED EXCHANGE DATA SUMMARY")
        print("="*80)
        
        # Exchange breakdown
        exchange_counts = self.data['exchange'].value_counts()
        print(f"\nContracts by Exchange:")
        for exchange, count in exchange_counts.items():
            print(f"  {exchange}: {count}")
        
        # Market type breakdown
        market_counts = self.data['market_type'].value_counts()
        print(f"\nContracts by Market Type:")
        for market_type, count in market_counts.items():
            print(f"  {market_type}: {count}")
        
        # Funding rate statistics
        funding_rates = self.data['funding_rate'].dropna()
        if not funding_rates.empty:
            print(f"\nFunding Rate Statistics:")
            print(f"  Average: {funding_rates.mean():.6f}")
            print(f"  Median: {funding_rates.median():.6f}")
            print(f"  Min: {funding_rates.min():.6f}")
            print(f"  Max: {funding_rates.max():.6f}")
        
        print("\n" + "="*80)
    
    def display_table(self, limit: Optional[int] = None, 
                     sort_by: Optional[str] = None, 
                     ascending: Optional[bool] = None):
        """
        Display the unified table.
        
        Args:
            limit: Number of rows to display (None for all)
            sort_by: Column to sort by (None for default)
            ascending: Sort order (None for default)
            
        Raises:
            ValueError: If parameters are invalid
        """
        if self.data.empty:
            print("No data to display")
            return
        
        # Input validation
        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError(f"limit must be positive integer, got {limit}")
            if limit > 10000:
                print("! Warning: Large limit value may cause memory issues")
        
        if sort_by is not None:
            if not isinstance(sort_by, str):
                raise ValueError(f"sort_by must be string, got {type(sort_by)}")
            if sort_by not in self.data.columns:
                available_columns = list(self.data.columns)
                raise ValueError(f"sort_by column '{sort_by}' not found. Available: {available_columns}")
        
        if ascending is not None and not isinstance(ascending, bool):
            raise ValueError(f"ascending must be boolean, got {type(ascending)}")
        
        # Use defaults if not specified
        limit = limit if limit is not None else DISPLAY_LIMIT
        sort_by = sort_by if sort_by is not None else DEFAULT_SORT_COLUMN
        ascending = ascending if ascending is not None else DEFAULT_SORT_ASCENDING
        
        # Sort the data
        if sort_by in self.data.columns:
            df_sorted = self.data.sort_values(sort_by, ascending=ascending, na_position='last')
        else:
            df_sorted = self.data
        
        # Display columns with better formatting
        display_columns = [
            'exchange', 'symbol', 'base_asset', 'quote_asset', 
            'funding_rate', 'apr', 'open_interest'
        ]
        
        # Filter to existing columns
        available_columns = [col for col in display_columns if col in df_sorted.columns]
        
        print(f"\nUNIFIED PERPETUAL FUTURES DATA (Top {limit}, sorted by {sort_by}):")
        print("-" * 120)
        
        # Format the display
        display_df = df_sorted[available_columns].head(limit).copy()
        
        # Format numeric columns for better display
        for col in ['funding_rate', 'apr', 'mark_price', 'index_price', 'open_interest']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: self._format_funding_rate(x) if pd.notna(x) and col == 'funding_rate' 
                    else f"{x:.2f}%" if pd.notna(x) and col == 'apr'
                    else f"{x:.2f}" if pd.notna(x) and col in ['mark_price', 'index_price']
                    else f"{x:,.0f}" if pd.notna(x) and col == 'open_interest'
                    else "N/A"
                )
        
        # Format datetime columns (removed next_funding_time)
        
        # Ensure exchange column is properly displayed
        if 'exchange' in display_df.columns:
            display_df['exchange'] = display_df['exchange'].fillna('Unknown')
        
        print(display_df.to_string(index=False, max_colwidth=15))
    
    def export_to_csv(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Export unified data to CSV.
        
        Args:
            filename: CSV filename (None for default)
            
        Returns:
            Filename where data was exported, or None if failed
        """
        if self.data.empty:
            print("No data to export")
            return None
        
        if not ENABLE_CSV_EXPORT:
            print("CSV export is disabled in settings")
            return None
        
        filename = filename if filename is not None else CSV_FILENAME
        
        try:
            # Create a copy of data for export
            export_df = self.data.copy()
            
            # Format numeric columns to avoid scientific notation
            numeric_columns = ['funding_rate', 'index_price', 'mark_price', 'open_interest', 'apr']
            
            for col in numeric_columns:
                if col in export_df.columns:
                    if col == 'funding_rate':
                        # Format funding rate with 18 decimal places
                        export_df[col] = export_df[col].apply(
                            lambda x: f"{x:.18f}" if pd.notna(x) else ""
                        )
                    elif col in ['index_price', 'mark_price']:
                        # Format prices with appropriate decimals
                        export_df[col] = export_df[col].apply(
                            lambda x: f"{x:.8f}" if pd.notna(x) and x < 0.01
                            else f"{x:.6f}" if pd.notna(x) and x < 1
                            else f"{x:.2f}" if pd.notna(x)
                            else ""
                        )
                    elif col == 'open_interest':
                        # Format open interest as float with 2 decimals
                        export_df[col] = export_df[col].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) else ""
                        )
                    elif col == 'apr':
                        # Format APR with 2 decimals
                        export_df[col] = export_df[col].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) else ""
                        )
            
            export_df.to_csv(filename, index=False)
            print(f"\nOK Data exported to: {filename}")
            return filename
        except PermissionError:
            # Try with a different filename if permission denied
            alt_filename = f"exchange_data_{int(time.time())}.csv"
            export_df.to_csv(alt_filename, index=False)
            print(f"\nOK Data exported to: {alt_filename} (original filename was locked)")
            return alt_filename
        except Exception as e:
            print(f"\n! Could not export to CSV: {str(e)}")
            return None
    
    def get_filtered_data(self, filters: dict = None) -> pd.DataFrame:
        """
        Get filtered data based on criteria.
        
        Args:
            filters: Dictionary of column:value pairs to filter by
            
        Returns:
            Filtered DataFrame
        """
        if filters is None:
            return self.data
        
        filtered_data = self.data.copy()
        
        for column, value in filters.items():
            if column in filtered_data.columns:
                if isinstance(value, (list, tuple)):
                    filtered_data = filtered_data[filtered_data[column].isin(value)]
                else:
                    filtered_data = filtered_data[filtered_data[column] == value]
        
        return filtered_data
    
    def get_top_funding_rates(self, limit: int = 10, ascending: bool = False) -> pd.DataFrame:
        """
        Get top funding rates.
        
        Args:
            limit: Number of results to return
            ascending: Sort order
            
        Returns:
            DataFrame with top funding rates
        """
        if self.data.empty or 'funding_rate' not in self.data.columns:
            return pd.DataFrame()
        
        return self.data.nlargest(limit, 'funding_rate') if not ascending else self.data.nsmallest(limit, 'funding_rate')
    
    def get_exchange_data(self, exchange: str) -> pd.DataFrame:
        """
        Get data for a specific exchange.
        
        Args:
            exchange: Name of the exchange
            
        Returns:
            DataFrame for the specified exchange
        """
        if self.data.empty or 'exchange' not in self.data.columns:
            return pd.DataFrame()
        
        return self.data[self.data['exchange'] == exchange]
    
    def get_statistics(self) -> dict:
        """
        Get comprehensive statistics about the data.
        
        Returns:
            Dictionary with various statistics
        """
        if self.data.empty:
            return {}
        
        stats = {
            'total_contracts': len(self.data),
            'exchanges': self.data['exchange'].value_counts().to_dict(),
            'market_types': self.data['market_type'].value_counts().to_dict(),
        }
        
        # Funding rate statistics
        if 'funding_rate' in self.data.columns:
            funding_rates = self.data['funding_rate'].dropna()
            if not funding_rates.empty:
                stats['funding_rate_stats'] = {
                    'mean': float(funding_rates.mean()),
                    'median': float(funding_rates.median()),
                    'min': float(funding_rates.min()),
                    'max': float(funding_rates.max()),
                    'std': float(funding_rates.std()),
                }
        
        # Price statistics
        for price_col in ['mark_price', 'index_price']:
            if price_col in self.data.columns:
                prices = self.data[price_col].dropna()
                if not prices.empty:
                    stats[f'{price_col}_stats'] = {
                        'mean': float(prices.mean()),
                        'median': float(prices.median()),
                        'min': float(prices.min()),
                        'max': float(prices.max()),
                    }
        
        return stats 