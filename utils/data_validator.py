"""
Data Validator
=============
Business logic validation for exchange data quality.
"""

import pandas as pd
from typing import List
from datetime import datetime, timezone


class DataValidationError(Exception):
    """Raised when data validation fails critically."""
    pass


class DataValidator:
    """
    Validates exchange data for business-critical issues.
    """
    
    def __init__(self):
        """Initialize the data validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_score: float = 0.0
    
    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate DataFrame for business-critical issues.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if validation passes, False if critical errors found
        """
        self.errors.clear()
        self.warnings.clear()
        
        if df.empty:
            self.warnings.append("No data available")
            self.quality_score = 0.0
            return True
        
        # Only validate things that actually matter for business decisions
        self._validate_required_columns(df)
        self._validate_data_freshness(df)
        self._validate_exchange_coverage(df)
        self._validate_price_sanity(df)
        self._check_duplicates(df)
        
        # Calculate quality score
        self.quality_score = self._calculate_quality_score(df)
        
        return len(self.errors) == 0
    
    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """Check for absolutely required columns."""
        required = ['exchange', 'symbol', 'base_asset', 'quote_asset']
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.errors.append(f"Missing critical columns: {missing}")
    
    def _validate_data_freshness(self, df: pd.DataFrame) -> None:
        """Check if data is fresh enough to be actionable."""
        if 'timestamp' in df.columns:
            now = datetime.now(timezone.utc)
            latest = df['timestamp'].max()
            if pd.notna(latest):
                age_minutes = (now - latest).total_seconds() / 60
                if age_minutes > 10:
                    self.warnings.append(f"Data is {age_minutes:.1f} minutes old")
                if age_minutes > 30:
                    self.errors.append("Data too stale for trading decisions")
    
    def _validate_exchange_coverage(self, df: pd.DataFrame) -> None:
        """Check if we have data from expected exchanges."""
        if 'exchange' not in df.columns:
            return
            
        present_exchanges = set(df['exchange'].unique())
        critical_exchanges = {'Binance', 'Backpack'}  # Your most important ones
        
        missing_critical = critical_exchanges - present_exchanges
        if missing_critical:
            self.errors.append(f"Missing critical exchanges: {list(missing_critical)}")
        
        if len(present_exchanges) < 2:
            self.warnings.append("Only one exchange providing data")
    
    def _validate_price_sanity(self, df: pd.DataFrame) -> None:
        """Check for obviously wrong prices across exchanges."""
        if 'base_asset' not in df.columns or 'mark_price' not in df.columns:
            return
        
        # Check BTC price consistency across exchanges
        btc_data = df[(df['base_asset'] == 'BTC') & df['mark_price'].notna()]
        if len(btc_data) > 1:
            prices = btc_data['mark_price']
            spread_pct = (prices.max() - prices.min()) / prices.mean() * 100
            if spread_pct > 1.0:  # 1% spread seems suspicious
                self.warnings.append(f"BTC price spread across exchanges: {spread_pct:.1f}%")
            if spread_pct > 5.0:  # 5% spread is definitely wrong
                self.errors.append("Extreme price differences suggest data issues")
    
    def _check_duplicates(self, df: pd.DataFrame) -> None:
        """Check for duplicate exchange-symbol pairs."""
        if 'exchange' in df.columns and 'symbol' in df.columns:
            duplicates = df.duplicated(subset=['exchange', 'symbol'])
            if duplicates.any():
                count = duplicates.sum()
                self.errors.append(f"{count} duplicate exchange-symbol pairs")
    
    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """Calculate data quality score 0-100."""
        if df.empty:
            return 0.0
        
        score = 100.0
        
        # Deduct for missing exchanges
        present_exchanges = set(df['exchange'].unique()) if 'exchange' in df.columns else set()
        expected_exchanges = {'Binance', 'Backpack', 'KuCoin'}
        missing_ratio = len(expected_exchanges - present_exchanges) / len(expected_exchanges)
        score -= missing_ratio * 30
        
        # Deduct for missing data
        if 'funding_rate' in df.columns:
            missing_funding = df['funding_rate'].isna().sum() / len(df)
            score -= missing_funding * 20
        
        # Deduct for stale data
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            age_minutes = (datetime.now(timezone.utc) - df['timestamp'].max()).total_seconds() / 60
            if age_minutes > 5:
                score -= min(age_minutes / 2, 25)  # Max 25 point deduction
        
        # Deduct for errors and warnings
        score -= len(self.errors) * 15
        score -= len(self.warnings) * 5
        
        return max(0.0, score)
    
    def get_validation_report(self) -> str:
        """Get formatted validation report with actionable information."""
        report = []
        
        # Quality score first
        report.append(f"Data Quality Score: {self.quality_score:.1f}/100")
        report.append("")
        
        if self.errors:
            report.append("CRITICAL ISSUES:")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")
        
        if self.warnings:
            report.append("WARNINGS:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")
        
        if not self.errors and not self.warnings:
            report.append("Data validation passed")
        
        return "\n".join(report)
    
    def raise_on_errors(self) -> None:
        """Raise DataValidationError if there are critical errors."""
        if self.errors:
            error_msg = f"Data quality check failed (score: {self.quality_score:.1f}):\n"
            error_msg += "\n".join(f"  • {error}" for error in self.errors)
            raise DataValidationError(error_msg)


def validate_exchange_data(df: pd.DataFrame, strict: bool = False) -> DataValidator:
    """
    Validate exchange data and return validator instance.
    
    Args:
        df: DataFrame to validate
        strict: If True, warnings become errors (ignored for now)
        
    Returns:
        DataValidator instance with validation results
    """
    validator = DataValidator()
    validator.validate_dataframe(df)
    return validator