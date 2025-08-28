"""
Settings Manager
================
Handles reading, writing, and validation of system settings.
Provides hot-reload capability and settings history.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import importlib
import sys
from copy import deepcopy

class SettingsManager:
    """
    Manages system configuration with validation and persistence.
    """
    
    def __init__(self):
        """Initialize the settings manager."""
        self.settings_file = Path("config/settings.py")
        self.backup_dir = Path("config/backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.settings_cache = {}
        self.load_current_settings()
    
    def load_current_settings(self) -> Dict[str, Any]:
        """
        Load current settings from settings.py.
        
        Returns:
            Dictionary of current settings
        """
        try:
            # Import or reimport the settings module
            if 'config.settings' in sys.modules:
                importlib.reload(sys.modules['config.settings'])
            else:
                import config.settings
            
            settings_module = sys.modules['config.settings']
            
            # Extract all uppercase variables (settings)
            settings = {}
            for name in dir(settings_module):
                if name.isupper():
                    value = getattr(settings_module, name)
                    # Convert to JSON-serializable format
                    if isinstance(value, (str, int, float, bool, dict, list)):
                        settings[name] = value
                    elif value is None:
                        settings[name] = None
            
            self.settings_cache = settings
            return settings
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current settings organized by category.
        
        Returns:
            Categorized settings dictionary
        """
        raw_settings = self.load_current_settings()
        
        # Organize settings by category
        categorized = {
            "exchanges": {
                "enabled": raw_settings.get("EXCHANGES", {}),
                "collection_mode": "sequential" if raw_settings.get("ENABLE_SEQUENTIAL_COLLECTION", True) else "parallel",
                "collection_delay": raw_settings.get("EXCHANGE_COLLECTION_DELAY", 30)
            },
            "data_fetching": {
                "enable_funding_rate": raw_settings.get("ENABLE_FUNDING_RATE_FETCH", True),
                "enable_open_interest": raw_settings.get("ENABLE_OPEN_INTEREST_FETCH", True),
                "api_delay": raw_settings.get("API_DELAY", 0.5),
                "display_limit": raw_settings.get("DISPLAY_LIMIT", 100),
                "sort_column": raw_settings.get("DEFAULT_SORT_COLUMN", "exchange"),
                "sort_ascending": raw_settings.get("DEFAULT_SORT_ASCENDING", True)
            },
            "historical": {
                "enable_collection": raw_settings.get("ENABLE_HISTORICAL_COLLECTION", True),
                "fetch_interval": raw_settings.get("HISTORICAL_FETCH_INTERVAL", 300),
                "max_retries": raw_settings.get("HISTORICAL_MAX_RETRIES", 3),
                "base_backoff": raw_settings.get("HISTORICAL_BASE_BACKOFF", 60)
            },
            "database": {
                "host": raw_settings.get("POSTGRES_HOST", "localhost"),
                "port": raw_settings.get("POSTGRES_PORT", "5432"),
                "database": raw_settings.get("POSTGRES_DATABASE", "exchange_data"),
                "user": raw_settings.get("POSTGRES_USER", "postgres"),
                "table_name": raw_settings.get("DATABASE_TABLE_NAME", "exchange_data"),
                "historical_table": raw_settings.get("HISTORICAL_TABLE_NAME", "exchange_data_historical")
            },
            "output": {
                "enable_csv": raw_settings.get("ENABLE_CSV_EXPORT", False),
                "enable_database": raw_settings.get("ENABLE_DATABASE_UPLOAD", True),
                "enable_console": raw_settings.get("ENABLE_CONSOLE_DISPLAY", True),
                "csv_filename": raw_settings.get("CSV_FILENAME", "unified_exchange_data.csv")
            },
            "debug": {
                "debug_mode": raw_settings.get("DEBUG_MODE", False),
                "show_sample_data": raw_settings.get("SHOW_SAMPLE_DATA", False)
            }
        }
        
        return categorized
    
    def validate_settings(self, settings: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate settings before applying.
        
        Args:
            settings: Settings dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate exchanges
        if "exchanges" in settings:
            exchanges = settings["exchanges"].get("enabled", {})
            if not isinstance(exchanges, dict):
                errors.append("Exchanges must be a dictionary")
            elif not any(exchanges.values()):
                errors.append("At least one exchange must be enabled")
            
            delay = settings["exchanges"].get("collection_delay", 30)
            if not isinstance(delay, (int, float)) or delay < 0 or delay > 300:
                errors.append("Collection delay must be between 0 and 300 seconds")
        
        # Validate data fetching
        if "data_fetching" in settings:
            api_delay = settings["data_fetching"].get("api_delay", 0.5)
            if not isinstance(api_delay, (int, float)) or api_delay < 0 or api_delay > 10:
                errors.append("API delay must be between 0 and 10 seconds")
            
            display_limit = settings["data_fetching"].get("display_limit", 100)
            if not isinstance(display_limit, int) or display_limit < 1 or display_limit > 1000:
                errors.append("Display limit must be between 1 and 1000")
        
        # Validate historical settings
        if "historical" in settings:
            interval = settings["historical"].get("fetch_interval", 300)
            if not isinstance(interval, int) or interval < 30 or interval > 3600:
                errors.append("Fetch interval must be between 30 and 3600 seconds")
            
            retries = settings["historical"].get("max_retries", 3)
            if not isinstance(retries, int) or retries < 0 or retries > 10:
                errors.append("Max retries must be between 0 and 10")
        
        # Validate database settings
        if "database" in settings:
            port = settings["database"].get("port", "5432")
            try:
                port_int = int(port)
                if port_int < 1 or port_int > 65535:
                    errors.append("Database port must be between 1 and 65535")
            except:
                errors.append("Database port must be a valid number")
        
        return (len(errors) == 0, errors)
    
    def backup_current_settings(self) -> str:
        """
        Create a backup of current settings.
        
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"settings_backup_{timestamp}.py"
        
        try:
            shutil.copy2(self.settings_file, backup_file)
            return str(backup_file)
        except Exception as e:
            print(f"Error creating backup: {e}")
            return ""
    
    def update_settings(self, new_settings: Dict[str, Any]) -> tuple[bool, str]:
        """
        Update settings file with new values.
        
        Args:
            new_settings: Categorized settings dictionary
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate settings first
            is_valid, errors = self.validate_settings(new_settings)
            if not is_valid:
                return False, f"Validation errors: {'; '.join(errors)}"
            
            # Create backup
            backup_path = self.backup_current_settings()
            if not backup_path:
                return False, "Failed to create backup"
            
            # Read current settings file
            with open(self.settings_file, 'r') as f:
                lines = f.readlines()
            
            # Update specific settings
            updated_lines = self._update_settings_lines(lines, new_settings)
            
            # Write updated settings
            with open(self.settings_file, 'w') as f:
                f.writelines(updated_lines)
            
            # Reload settings
            self.load_current_settings()
            
            return True, f"Settings updated successfully. Backup saved to {backup_path}"
            
        except Exception as e:
            return False, f"Error updating settings: {str(e)}"
    
    def _update_settings_lines(self, lines: List[str], new_settings: Dict[str, Any]) -> List[str]:
        """
        Update specific lines in settings file.
        
        Args:
            lines: Current file lines
            new_settings: New settings to apply
            
        Returns:
            Updated lines
        """
        updated = lines.copy()
        
        # Map categorized settings back to variable names
        updates = {}
        
        if "exchanges" in new_settings:
            updates["EXCHANGES"] = new_settings["exchanges"]["enabled"]
            mode = new_settings["exchanges"]["collection_mode"]
            updates["ENABLE_SEQUENTIAL_COLLECTION"] = (mode == "sequential")
            updates["EXCHANGE_COLLECTION_DELAY"] = new_settings["exchanges"]["collection_delay"]
        
        if "data_fetching" in new_settings:
            df = new_settings["data_fetching"]
            updates["ENABLE_FUNDING_RATE_FETCH"] = df.get("enable_funding_rate", True)
            updates["ENABLE_OPEN_INTEREST_FETCH"] = df.get("enable_open_interest", True)
            updates["API_DELAY"] = df.get("api_delay", 0.5)
            updates["DISPLAY_LIMIT"] = df.get("display_limit", 100)
            updates["DEFAULT_SORT_COLUMN"] = df.get("sort_column", "exchange")
            updates["DEFAULT_SORT_ASCENDING"] = df.get("sort_ascending", True)
        
        if "historical" in new_settings:
            hist = new_settings["historical"]
            updates["ENABLE_HISTORICAL_COLLECTION"] = hist.get("enable_collection", True)
            updates["HISTORICAL_FETCH_INTERVAL"] = hist.get("fetch_interval", 300)
            updates["HISTORICAL_MAX_RETRIES"] = hist.get("max_retries", 3)
            updates["HISTORICAL_BASE_BACKOFF"] = hist.get("base_backoff", 60)
        
        if "output" in new_settings:
            out = new_settings["output"]
            updates["ENABLE_CSV_EXPORT"] = out.get("enable_csv", False)
            updates["ENABLE_DATABASE_UPLOAD"] = out.get("enable_database", True)
            updates["ENABLE_CONSOLE_DISPLAY"] = out.get("enable_console", True)
            updates["CSV_FILENAME"] = out.get("csv_filename", "unified_exchange_data.csv")
        
        if "debug" in new_settings:
            updates["DEBUG_MODE"] = new_settings["debug"].get("debug_mode", False)
            updates["SHOW_SAMPLE_DATA"] = new_settings["debug"].get("show_sample_data", False)
        
        # Apply updates to lines
        for i, line in enumerate(updated):
            for var_name, new_value in updates.items():
                if line.strip().startswith(f"{var_name} ="):
                    if isinstance(new_value, str):
                        updated[i] = f'{var_name} = "{new_value}"\n'
                    elif isinstance(new_value, dict):
                        # Format dict nicely
                        dict_str = json.dumps(new_value, indent=4)
                        dict_str = dict_str.replace('"', "'").replace("true", "True").replace("false", "False")
                        updated[i] = f'{var_name} = {dict_str}\n'
                    else:
                        updated[i] = f'{var_name} = {new_value}\n'
                    break
        
        return updated
    
    def restore_backup(self, backup_filename: str) -> tuple[bool, str]:
        """
        Restore settings from a backup file.
        
        Args:
            backup_filename: Name of backup file to restore
            
        Returns:
            Tuple of (success, message)
        """
        try:
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                return False, f"Backup file {backup_filename} not found"
            
            # Create a backup of current settings first
            current_backup = self.backup_current_settings()
            
            # Restore from backup
            shutil.copy2(backup_path, self.settings_file)
            
            # Reload settings
            self.load_current_settings()
            
            return True, f"Settings restored from {backup_filename}"
            
        except Exception as e:
            return False, f"Error restoring backup: {str(e)}"
    
    def get_backups(self) -> List[Dict[str, Any]]:
        """
        Get list of available backup files.
        
        Returns:
            List of backup file information
        """
        backups = []
        for backup_file in self.backup_dir.glob("settings_backup_*.py"):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        
        # Sort by timestamp descending
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def export_settings(self) -> Dict[str, Any]:
        """
        Export current settings as JSON.
        
        Returns:
            Settings dictionary for export
        """
        return {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "settings": self.get_settings()
        }
    
    def import_settings(self, settings_json: Dict[str, Any]) -> tuple[bool, str]:
        """
        Import settings from JSON.
        
        Args:
            settings_json: Settings dictionary to import
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if "settings" not in settings_json:
                return False, "Invalid settings format"
            
            # Validate and apply imported settings
            return self.update_settings(settings_json["settings"])
            
        except Exception as e:
            return False, f"Error importing settings: {str(e)}"