"""
Configuration Validator
======================
Validates critical configuration settings only.
"""

import sys
from typing import List


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """
    Validates configuration settings for critical issues only.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.errors: List[str] = []
    
    def validate_all(self, config_module) -> bool:
        """
        Validate critical configuration settings only.
        
        Args:
            config_module: The imported configuration module
            
        Returns:
            True if all validations pass, False otherwise
        """
        self.errors.clear()
        
        # Only validate things that would cause runtime crashes
        self._validate_exchanges(config_module)
        self._validate_required_settings(config_module)
        self._validate_database_config(config_module)
        
        return len(self.errors) == 0
    
    def _validate_exchanges(self, config) -> None:
        """Validate exchange configuration basics."""
        exchanges = getattr(config, 'EXCHANGES', {})
        
        if not isinstance(exchanges, dict):
            self.errors.append("EXCHANGES must be a dictionary")
            return
        
        # Check boolean values
        for exchange_name, enabled in exchanges.items():
            if not isinstance(enabled, bool):
                self.errors.append(f"Exchange '{exchange_name}' enabled status must be boolean")
    
    def _validate_required_settings(self, config) -> None:
        """Validate settings that would cause crashes."""
        # Display limit must be positive integer
        display_limit = getattr(config, 'DISPLAY_LIMIT', None)
        if display_limit is not None:
            if not isinstance(display_limit, int) or display_limit < 1:
                self.errors.append("DISPLAY_LIMIT must be positive integer")
        
        # API delay must be non-negative number
        api_delay = getattr(config, 'API_DELAY', None)
        if api_delay is not None:
            if not isinstance(api_delay, (int, float)) or api_delay < 0:
                self.errors.append("API_DELAY must be non-negative number")
    
    def _validate_database_config(self, config) -> None:
        """Validate database config if database upload is enabled."""
        if getattr(config, 'ENABLE_DATABASE_UPLOAD', False):
            if not getattr(config, 'POSTGRES_HOST', None):
                self.errors.append("POSTGRES_HOST required when ENABLE_DATABASE_UPLOAD is True")
            if not getattr(config, 'POSTGRES_DATABASE', None):
                self.errors.append("POSTGRES_DATABASE required when ENABLE_DATABASE_UPLOAD is True")
            if not getattr(config, 'POSTGRES_USER', None):
                self.errors.append("POSTGRES_USER required when ENABLE_DATABASE_UPLOAD is True")
            if not getattr(config, 'POSTGRES_PASSWORD', None):
                self.errors.append("POSTGRES_PASSWORD required when ENABLE_DATABASE_UPLOAD is True")
    
    def get_validation_report(self) -> str:
        """Get formatted validation report."""
        if not self.errors:
            return "Configuration validation passed"
        
        report = ["CONFIGURATION ERRORS:"]
        for error in self.errors:
            report.append(f"  - {error}")
        
        return "\n".join(report)
    
    def raise_on_errors(self) -> None:
        """Raise ConfigurationError if there are validation errors."""
        if self.errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  • {error}" for error in self.errors)
            raise ConfigurationError(error_msg)


def validate_configuration(config_module) -> ConfigValidator:
    """
    Validate configuration and return validator instance.
    
    Args:
        config_module: The imported configuration module
        
    Returns:
        ConfigValidator instance with validation results
    """
    validator = ConfigValidator()
    validator.validate_all(config_module)
    return validator


def validate_and_exit_on_error(config_module) -> None:
    """
    Validate configuration and exit if errors are found.
    
    Args:
        config_module: The imported configuration module
    """
    validator = validate_configuration(config_module)
    
    # Show the report
    report = validator.get_validation_report()
    if report.strip():
        print(report)
    
    # Exit on errors
    if validator.errors:
        print("Cannot continue with invalid configuration.")
        sys.exit(1)