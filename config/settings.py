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
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

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
    'drift': True,        # Enabled - 61 perpetual contracts (Solana DEX)
    'aster': True,        # Enabled - Aster DEX perpetual contracts (OPTIMIZED)
    'lighter': True,      # Enabled - Lighter blockchain perpetual contracts
    'bybit': True,        # Enabled - 696 perpetual contracts (668 linear + 28 inverse)
    'pacifica': True,     # Enabled - Pacifica Finance perpetual contracts
    'hibachi': True,      # Enabled - Hibachi DEX perpetual contracts
    'deribit': True,      # Enabled - Deribit perpetual contracts
    'mexc': True,         # Enabled - MEXC perpetual contracts
    'dydx': True,         # Enabled - dYdX v4 perpetual contracts
    'edgex': False,       # Disabled - EdgeX API not accessible
    'apex': False,        # Disabled - ApeX API not accessible
    'kraken': False       # Ready but disabled
}

# =============================================================================
# DATA FETCHING SETTINGS
# =============================================================================
# Enable/disable fetching open interest data (can cause API errors)
ENABLE_OPEN_INTEREST_FETCH = True

# Enable/disable fetching funding rate data
ENABLE_FUNDING_RATE_FETCH = True

# WebSocket functionality has been removed

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
HISTORICAL_ALIGN_TO_MIDNIGHT = True  # Align start time to midnight UTC (end time is always current time)
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

# Z-score calculation interval in seconds (default: 30 seconds)
# Aligned with data collection interval for maximum freshness
ZSCORE_CALCULATION_INTERVAL = 30

# Zone-based scheduling intervals (for optimized updates)
# Active zone: contracts with |Z| > 2.0 (volatile, need frequent updates)
ZSCORE_ACTIVE_ZONE_INTERVAL = 30

# Stable zone: contracts with |Z| <= 2.0 (stable, less frequent updates OK)
ZSCORE_STABLE_ZONE_INTERVAL = 60

# =============================================================================
# STALE DATA MANAGEMENT SETTINGS
# =============================================================================
# Hours after which data is considered stale and contracts may be marked as delisted
STALE_DATA_THRESHOLD_HOURS = 24  # Mark as inactive after this period

# Hours after which stale data is removed from the database
STALE_DATA_REMOVAL_HOURS = 48    # Remove from DB after this period

# Enable automatic cleanup of delisted contracts
AUTO_CLEANUP_DELISTED = True     # Enable automatic cleanup during collection

# Filter inactive contracts from API responses
FILTER_INACTIVE_CONTRACTS = True  # Hide inactive contracts in API endpoints

# Maximum age of data to serve via API (in days)
API_MAX_DATA_AGE_DAYS = 3         # Don't serve data older than this

# =============================================================================
# EXCHANGE-SPECIFIC FILTERING SETTINGS
# =============================================================================
# Drift: Minimum 24h trading volume threshold to consider contract active
# Set to 0.0 to filter out all zero-volume contracts (recommended)
DRIFT_MIN_VOLUME_THRESHOLD = 0.0  # Filters out zombie contracts with no trading activity

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================
# Validation is now done in exchange-data-collector.py when the system starts