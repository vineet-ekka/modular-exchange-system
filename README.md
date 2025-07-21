# Modular Exchange Data System

A modular, easy-to-edit system for fetching and processing exchange data from multiple cryptocurrency exchanges.

## 🎯 Purpose

This system is designed to be **easy for non-coders to modify** while maintaining professional code structure. You can easily:

- Enable/disable exchanges
- Change database settings
- Modify display options
- Add new exchanges
- Adjust rate limiting

## 📁 Project Structure

```
modular_exchange_system/
├── config/
│   └── settings.py          # ⭐ EASY TO EDIT - All your settings here!
├── exchanges/
│   ├── base_exchange.py     # Base class for all exchanges
│   ├── backpack_exchange.py # Backpack exchange module
│   ├── binance_exchange.py  # Binance exchange module
│   ├── kucoin_exchange.py   # KuCoin exchange module
│   └── exchange_factory.py  # Manages all exchanges
├── data_processing/
│   └── data_processor.py    # Handles data analysis and display
├── database/
│   └── supabase_manager.py  # Database operations
├── utils/
│   ├── logger.py            # Logging utilities
│   ├── health_tracker.py    # Exchange health monitoring
│   ├── rate_limiter.py      # Smart rate limiting
│   └── continuous_fetcher.py # Continuous data collection
├── main.py                  # ⭐ MAIN ENTRY POINT - Real-time data
├── main_historical.py       # ⭐ ENTRY POINT - Historical collection
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the project root and add your secrets:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_service_role_key_here
DATABASE_TABLE_NAME=exchange_data
```

⚠️ **IMPORTANT**: Never commit the `.env` file to version control. It contains sensitive credentials.

### 3. Configure Other Settings
Edit `config/settings.py` for non-sensitive settings:

```python
# Enable/disable exchanges
EXCHANGES = {
    "backpack": True,   # Set to False to disable
    "binance": True,    # Set to False to disable
    "kucoin": True,     # Set to False to disable
}

# Display settings
DISPLAY_LIMIT = 30  # How many rows to show
```

### 4. Create Database Tables
If using historical data collection, create the historical table in Supabase:
- Go to your Supabase dashboard
- Navigate to SQL Editor
- Run the SQL from `create_historical_table.sql`

### 5. Run the System

**For real-time data collection:**
```bash
python main.py
```

**For historical data collection:**
```bash
python main_historical.py
```

## ⭐ Features

### Real-Time Data Collection
- Fetches perpetual futures data from multiple exchanges
- Calculates annualized percentage rates (APR) from funding rates
- Exports to CSV and uploads to Supabase database
- Health monitoring for exchange API reliability
- Displays funding rates with APR calculations

### Historical Data Collection
- **Continuous Collection**: Automatically fetches data at regular intervals
- **Time-Series Storage**: Preserves all historical data with timestamps
- **Flexible Querying**: Filter by time range, exchange, or symbol
- **Resilient Operation**: Handles failures gracefully with retry logic
- **Progress Reporting**: Real-time statistics and monitoring

### Smart Rate Limiting
- **Per-Exchange Limits**: Respects individual exchange rate limits
- **Token Bucket Algorithm**: Smooth request distribution
- **Automatic 429 Handling**: Backs off when rate limited
- **Real-Time Monitoring**: Shows rate limit status

### Health Monitoring
- **Exchange Reliability**: Tracks API success/failure rates
- **24-Hour Window**: Rolling health scores for each exchange
- **System Health**: Overall system health assessment
- **Status Indicators**: Clear OK/WARN/FAIL status

## ⭐ Easy Customization for Non-Coders

### 🔧 Configuration (`config/settings.py`)

This is the **main file you'll edit**. Everything is clearly documented:

#### Database Settings
Database credentials are now stored securely in the `.env` file:
```bash
# In .env file (not in code!)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DATABASE_TABLE_NAME=exchange_data
```

#### Exchange Settings
```python
EXCHANGES = {
    "backpack": True,   # Enable/disable Backpack
    "binance": True,    # Enable/disable Binance
    "kucoin": True,     # Enable/disable KuCoin
}
```

#### Display Settings
```python
DISPLAY_LIMIT = 30                    # How many rows to show
DEFAULT_SORT_COLUMN = 'funding_rate'  # Sort by this column
DEFAULT_SORT_ASCENDING = False        # Sort order
```

#### Output Settings
```python
ENABLE_CSV_EXPORT = True      # Export to CSV file
ENABLE_DATABASE_UPLOAD = True # Upload to database
ENABLE_CONSOLE_DISPLAY = True # Show results in console
```

#### Rate Limiting
```python
API_DELAY = 0.5  # Delay between API calls (seconds)
```

#### Historical Collection Settings
```python
ENABLE_HISTORICAL_COLLECTION = True  # Enable historical data collection
HISTORICAL_FETCH_INTERVAL = 300      # Fetch every 5 minutes
HISTORICAL_TABLE_NAME = "exchange_data_historical"
HISTORICAL_MAX_RETRIES = 3           # Retry failed fetches
HISTORICAL_BASE_BACKOFF = 60         # Base backoff time in seconds
```

### 🔄 Adding New Exchanges

To add a new exchange, create a new file in `exchanges/`:

1. **Create the exchange file** (e.g., `exchanges/new_exchange.py`):
```python
from .base_exchange import BaseExchange

class NewExchange(BaseExchange):
    def __init__(self, enabled: bool = True):
        super().__init__("NewExchange", enabled)
    
    def fetch_data(self):
        # Your API calls here
        pass
    
    def normalize_data(self, df):
        # Your data transformation here
        pass
```

2. **Add to factory** in `exchanges/exchange_factory.py`:
```python
from .new_exchange import NewExchange

exchange_classes = {
    'backpack': BackpackExchange,
    'binance': BinanceExchange,
    'kucoin': KuCoinExchange,
    'new_exchange': NewExchange,  # Add this line
}
```

3. **Enable in settings** in `config/settings.py`:
```python
EXCHANGES = {
    "backpack": True,
    "binance": True,
    "kucoin": True,
    "new_exchange": True,  # Add this line
}
```

## 📊 What the System Does

1. **Fetches Data** from enabled exchanges (Backpack, Binance, KuCoin)
2. **Normalizes Data** into a unified format
3. **Displays Summary** with statistics
4. **Shows Table** of top funding rates
5. **Exports to CSV** file
6. **Uploads to Supabase** database

## 📈 Output Examples

### Summary Display
```
================================================================================
UNIFIED EXCHANGE DATA SUMMARY
================================================================================

Contracts by Exchange:
  Binance: 245
  Backpack: 89
  KuCoin: 156

Contracts by Market Type:
  Binance USD-M: 180
  Binance COIN-M: 65
  Backpack PERP: 89
  KuCoin Futures: 156

Funding Rate Statistics:
  Average: 0.000123
  Median: 0.000098
  Min: -0.000456
  Max: 0.000789
```

### Data Table
```
UNIFIED PERPETUAL FUTURES DATA (Top 30, sorted by funding_rate):
------------------------------------------------------------------------------------------------------------------------
exchange  symbol    base_asset  quote_asset  funding_rate  funding_interval_hours  mark_price  index_price  open_interest
Binance   BTCUSDT   BTC         USDT         0.000789     8.0                     43250.50    43248.75     1,234,567
Backpack  ETH-PERP  ETH         USD          0.000654     8.0                     2650.25     2649.80      567,890
```

## 🔧 Advanced Usage

### Programmatic Access
```python
from main import ExchangeDataSystem

# Create system
system = ExchangeDataSystem()

# Run the system
success = system.run()

# Get statistics
stats = system.get_statistics()
print(f"Total contracts: {stats['total_contracts']}")

# Get specific exchange data
binance_data = system.get_exchange_data("Binance")

# Get top funding rates
top_rates = system.get_top_funding_rates(limit=10)
```

### Database Operations
```python
from database.supabase_manager import SupabaseManager

# Create database manager
db = SupabaseManager()

# Test connection
db.test_connection()

# Fetch data from database
data = db.fetch_data({'exchange': 'Binance'})

# Get table info
info = db.get_table_info()
```

### Historical Data Collection

**Setting up Historical Collection:**
1. First, create the historical table in Supabase (see `HISTORICAL_SETUP.md`)
2. Configure settings in `config/settings.py`:
```python
ENABLE_HISTORICAL_COLLECTION = True
HISTORICAL_FETCH_INTERVAL = 300  # 5 minutes
HISTORICAL_TABLE_NAME = "exchange_data_historical"
```

**Running Historical Collection:**
```bash
# Run continuous historical data collection (indefinitely)
python main_historical.py

# Run with custom interval (60 seconds)
python main_historical.py --interval 60

# Run for specific duration (2 hours = 7200 seconds)
python main_historical.py --duration 7200

# Common examples:
# - Test run: 3 fetches over 3 minutes
python main_historical.py --interval 60 --duration 180

# - Production run: Every 5 minutes for 24 hours
python main_historical.py --interval 300 --duration 86400

# View historical data summary
python main_historical.py --summary

# Dry run without database upload
python main_historical.py --no-upload --duration 60

# Verbose mode (shows top APR contracts)
python main_historical.py --verbose --duration 300
```

⚠️ **IMPORTANT**: The `--duration` parameter ensures the collection stops after the specified time. Without it, the collection runs indefinitely until manually stopped with Ctrl+C.

**Querying Historical Data:**
```python
from database.supabase_manager import SupabaseManager
from datetime import datetime, timedelta

db = SupabaseManager()

# Get last 24 hours of data
end_time = datetime.now()
start_time = end_time - timedelta(hours=24)
historical_data = db.fetch_historical_data(
    start_time=start_time,
    end_time=end_time,
    exchanges=['binance', 'kucoin'],
    limit=1000
)

# Get historical summary
summary = db.get_historical_summary()
print(f"Total records: {summary['total_records']:,}")
print(f"Date range: {summary['oldest_record']} to {summary['newest_record']}")
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check your Supabase URL and key in `.env` file
   - Ensure your Supabase project is active
   - Verify credentials are correct

2. **No Data Retrieved**
   - Check if exchanges are enabled in `config/settings.py`
   - Verify internet connection
   - Check if exchange APIs are working
   - Review health status output

3. **Rate Limiting Errors**
   - The system handles rate limits automatically
   - Check console for backoff messages
   - Adjust fetch intervals if needed

4. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.8+ required)

5. **Historical Collection Issues**
   - Ensure historical table exists in Supabase
   - Check `HISTORICAL_SETUP.md` for setup instructions
   - Verify `ENABLE_HISTORICAL_COLLECTION = True`
   - Use `--summary` to check table status
   - **Duration not working**: Update to latest code - bug fixed on 2025-07-22
   - **Process won't stop**: Always use `--duration` parameter or Ctrl+C
   - **Check for stuck processes**: `tasklist | findstr python` (Windows)

### Debug Mode
Enable debug mode in `config/settings.py`:
```python
DEBUG_MODE = True
SHOW_SAMPLE_DATA = True
```

## 📝 File Descriptions

- **`main.py`**: Main entry point for real-time data collection
- **`main_historical.py`**: Entry point for continuous historical collection
- **`config/settings.py`**: ⭐ **EASY TO EDIT** - All your configuration here
- **`.env`**: Sensitive credentials (Supabase URL/key)
- **`exchanges/`**: Exchange-specific modules
  - `base_exchange.py`: Base class all exchanges inherit from
  - `exchange_factory.py`: Manages exchange instances
  - Individual exchange implementations (backpack, binance, kucoin)
- **`data_processing/data_processor.py`**: APR calculation and display logic
- **`database/supabase_manager.py`**: Database operations (regular & historical)
- **`utils/`**: Utility modules
  - `logger.py`: Logging functionality
  - `health_tracker.py`: Exchange health monitoring
  - `rate_limiter.py`: Smart rate limiting
  - `continuous_fetcher.py`: Continuous collection engine
  - `data_validator.py`: Business-focused validation
- **`create_historical_table.sql`**: SQL to create historical table
- **`HISTORICAL_SETUP.md`**: Setup guide for historical collection

## 🎯 Key Benefits for Non-Coders

1. **Single Configuration File**: Everything you need to change is in `config/settings.py`
2. **Clear Documentation**: Every setting is explained with comments
3. **Modular Design**: Easy to add new exchanges without touching existing code
4. **Error Handling**: System continues even if one exchange fails
5. **Flexible Output**: Choose what to display, export, or upload
6. **Rate Limiting**: Built-in protection against API limits

## 🤝 Contributing

To add a new exchange:
1. Create new file in `exchanges/`
2. Inherit from `BaseExchange`
3. Implement `fetch_data()` and `normalize_data()` methods
4. Add to `exchange_factory.py`
5. Enable in `config/settings.py`

## 📋 Changelog

### 2025-07-22
- **Fixed**: Historical collection duration parameter now works correctly
  - The `--duration` flag properly stops collection after specified time
  - No more indefinite running when duration is set
- **Updated**: README with clearer historical collection examples
- **Added**: Troubleshooting guidance for stuck processes

### 2025-07-21
- Initial release with historical data collection system
- Smart rate limiting implementation
- Health monitoring system
- Support for Backpack, Binance, and KuCoin exchanges
