# =============================================================================
# EXCHANGE DATA SYSTEM CONFIGURATION
# =============================================================================
# This file contains all the settings that you can easily modify
# without needing to understand the code structure.

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration validation is now optional
# Run main.py to automatically validate settings

# =============================================================================
# DATABASE SETTINGS
# =============================================================================
# Your Supabase database connection details (loaded from environment variables)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Database table name where data will be stored
DATABASE_TABLE_NAME = os.getenv("DATABASE_TABLE_NAME", "exchange_data")

# =============================================================================
# EXCHANGE SETTINGS
# =============================================================================
# Enable/disable specific exchanges (True = enabled, False = disabled)
EXCHANGES = {
    "backpack": True,
    "binance": True,
    "kucoin": True,
    "deribit": True,
    # Add new exchanges here as they become available
    # "new_exchange": True,
}

# =============================================================================
# DATA FETCHING SETTINGS
# =============================================================================
# Enable/disable fetching open interest data (can cause API errors)
ENABLE_OPEN_INTEREST_FETCH = True

# Enable/disable fetching funding rate data
ENABLE_FUNDING_RATE_FETCH = True

# =============================================================================
# DATA PROCESSING SETTINGS
# =============================================================================
# How many top results to show in the display table
DISPLAY_LIMIT = 50

# Default sorting column for the display table
# Options: 'funding_rate', 'mark_price', 'open_interest', 'exchange', 'symbol'
DEFAULT_SORT_COLUMN = 'symbol'

# Sort order (True = ascending, False = descending)
DEFAULT_SORT_ASCENDING = False

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================
# CSV export filename
CSV_FILENAME = "unified_exchange_data.csv"

# Enable/disable different output methods
ENABLE_CSV_EXPORT = True
ENABLE_DATABASE_UPLOAD = True
ENABLE_CONSOLE_DISPLAY = True

# =============================================================================
# RATE LIMITING SETTINGS
# =============================================================================
# Delay between API calls to avoid rate limiting (in seconds)
API_DELAY = 0.5

# =============================================================================
# DEBUG SETTINGS
# =============================================================================
# Enable debug mode for more detailed output
DEBUG_MODE = False

# Show sample data during upload (for debugging)
SHOW_SAMPLE_DATA = False 

# =============================================================================
# HISTORICAL DATA COLLECTION SETTINGS
# =============================================================================
# Enable/disable continuous historical data collection
ENABLE_HISTORICAL_COLLECTION = True

# Fetch interval in seconds (default: 300 = 5 minutes)
HISTORICAL_FETCH_INTERVAL = 300

# Historical table name in Supabase
HISTORICAL_TABLE_NAME = "exchange_data_historical"

# Historical CSV filename (timestamp will be appended)
HISTORICAL_CSV_FILENAME = "historical_exchange_data"

# Maximum retry attempts for failed fetches
HISTORICAL_MAX_RETRIES = 3

# Base backoff time in seconds for retries
HISTORICAL_BASE_BACKOFF = 60

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================
# Validation is now done in main.py when the system starts