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
# PostgreSQL database connection details (loaded from environment variables)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "exchange_data")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Database table name where data will be stored
DATABASE_TABLE_NAME = os.getenv("DATABASE_TABLE_NAME", "exchange_data")

# =============================================================================
# EXCHANGE SETTINGS
# =============================================================================
# Enable/disable specific exchanges (True = enabled, False = disabled)
EXCHANGES = {
    'backpack': True,     # Enabled - 43 perpetual contracts
    'binance': True,      # Enabled - 547 perpetual contracts
    'kucoin': True,       # Enabled - 477 perpetual contracts
    'hyperliquid': True,  # Enabled - 171 perpetual contracts
    'deribit': False,     # Ready but disabled
    'kraken': False       # Ready but disabled
}

# =============================================================================
# DATA FETCHING SETTINGS
# =============================================================================
# Enable/disable fetching open interest data (can cause API errors)
ENABLE_OPEN_INTEREST_FETCH = True

# Enable/disable fetching funding rate data
ENABLE_FUNDING_RATE_FETCH = True

# Sequential collection mode - stagger exchange API calls to reduce load
ENABLE_SEQUENTIAL_COLLECTION = False

# Delay between different exchanges in sequential mode (seconds)
# Example: Binance at 0s, KuCoin at 30s, Kraken at 60s, etc.
EXCHANGE_COLLECTION_DELAY = 30

# =============================================================================
# DATA PROCESSING SETTINGS
# =============================================================================
# How many top results to show in the display table
DISPLAY_LIMIT = 100

# Default sorting column for the display table
# Options: 'funding_rate', 'mark_price', 'open_interest', 'exchange', 'symbol'
DEFAULT_SORT_COLUMN = "apr"

# Sort order (True = ascending, False = descending)
DEFAULT_SORT_ASCENDING = True

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================
# CSV export filename
CSV_FILENAME = "unified_exchange_data.csv"

# Enable/disable different output methods
ENABLE_CSV_EXPORT = False
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
HISTORICAL_CSV_FILENAME = "historical-exchange-data"

# Maximum retry attempts for failed fetches
HISTORICAL_MAX_RETRIES = 3

# Synchronized historical window settings
HISTORICAL_SYNC_ENABLED = True  # Use synchronized date ranges across exchanges
HISTORICAL_ALIGN_TO_MIDNIGHT = True  # Align start/end times to midnight UTC
HISTORICAL_WINDOW_DAYS = 30  # Default window size in days

# Base backoff time in seconds for retries
HISTORICAL_BASE_BACKOFF = 60

# =============================================================================
# Z-SCORE CALCULATION SETTINGS
# =============================================================================
# Number of days to use for Z-score calculation window (default: 30 days)
# This determines how many days of historical data are used to calculate
# the mean, standard deviation, and percentiles for Z-score analysis
ZSCORE_CALCULATION_DAYS = 30

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================
# Validation is now done in exchange-data-collector.py when the system starts