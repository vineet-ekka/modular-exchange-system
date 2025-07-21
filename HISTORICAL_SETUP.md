# Historical Data Collection Setup Guide

## Overview

The historical data collection system continuously fetches cryptocurrency perpetual futures data at regular intervals and stores it in a time-series database. This enables:

- **Trend Analysis**: Track funding rate changes over time
- **APR Monitoring**: Monitor annualized percentage rate fluctuations
- **Exchange Comparison**: Compare performance across exchanges
- **Trading Intelligence**: Build data-driven trading strategies

## Prerequisites

1. **Completed Basic Setup**: Ensure the main system (`python main.py`) works correctly
2. **Supabase Account**: Active Supabase project with credentials in `.env`
3. **Python 3.8+**: Required for the system to run
4. **Dependencies Installed**: Run `pip install -r requirements.txt`

## Step 1: Create the Historical Table

1. Log in to your Supabase dashboard
2. Go to the SQL Editor
3. Copy and paste the contents of `create_historical_table.sql`
4. Click "Run" to execute the SQL

Alternatively, you can run this SQL directly:

```sql
CREATE TABLE IF NOT EXISTS exchange_data_historical (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20),
    quote_asset VARCHAR(20),
    funding_rate DECIMAL(20, 10),
    funding_interval_hours DECIMAL(10, 2),
    apr DECIMAL(20, 2),
    index_price DECIMAL(20, 8),
    mark_price DECIMAL(20, 8),
    open_interest DECIMAL(30, 8),
    contract_type VARCHAR(50),
    market_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_exchange_data_historical_timestamp ON exchange_data_historical(timestamp DESC);
CREATE INDEX idx_exchange_data_historical_exchange_symbol ON exchange_data_historical(exchange, symbol);
```

## Step 2: Verify Table Creation

Run this query to verify the table was created successfully:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'exchange_data_historical';
```

You should see all columns including:
- `id`, `timestamp`, `exchange`, `symbol`
- `funding_rate`, `funding_interval_hours`, `apr`
- `mark_price`, `index_price`, `open_interest`
- And others...

## Step 3: Test Historical Collection

Run a test to ensure everything is working:

```bash
# Test with dry run (no database upload)
python main_historical.py --no-upload --duration 30 --interval 10

# Test with actual upload (short duration)
python main_historical.py --duration 60 --interval 20

# Check historical summary
python main_historical.py --summary
```

## ⚠️ Important Notes

1. **Always use `--duration` parameter** unless you want indefinite collection
   - Without duration: Runs forever (must stop with Ctrl+C)
   - With duration: Automatically stops after specified seconds

2. **Duration bug fixed (2025-07-22)**
   - Previous versions ignored the duration parameter
   - Update to latest code for proper duration handling

3. **Recommended test patterns**:
   - Quick test: `--interval 60 --duration 180` (3 fetches in 3 minutes)
   - Daily run: `--interval 300 --duration 86400` (5-min intervals for 24 hours)

4. **Check for stuck processes** (Windows):
   ```bash
   tasklist | findstr python
   ```

## Configuration

The historical collection settings are in `config/settings.py`:

```python
# Enable/disable historical collection
ENABLE_HISTORICAL_COLLECTION = True

# Fetch interval in seconds (default: 300 = 5 minutes)
HISTORICAL_FETCH_INTERVAL = 300

# Table name
HISTORICAL_TABLE_NAME = "exchange_data_historical"

# Retry settings
HISTORICAL_MAX_RETRIES = 3
HISTORICAL_BASE_BACKOFF = 60
```

## Usage Examples

### Command-Line Arguments

```bash
python main_historical.py [OPTIONS]

Options:
  --interval, -i    Fetch interval in seconds (default: 300)
  --duration, -d    Run duration in seconds (runs forever if not set)
  --summary, -s     Show historical data summary and exit
  --verbose, -v     Enable verbose output with detailed progress
  --no-upload       Disable database upload (dry run mode)
  --help, -h        Show help message
```

### Continuous Collection Examples

```bash
# Run indefinitely with default settings (5 min intervals)
# WARNING: Runs forever until stopped with Ctrl+C
python main_historical.py

# Run with custom interval (60 seconds)
# WARNING: Runs forever without --duration
python main_historical.py --interval 60

# Run for specific duration (2 hours = 7200 seconds)
# RECOMMENDED: Always use --duration for controlled runs
python main_historical.py --duration 7200

# Common usage patterns:
# - Quick test: 3 fetches over 3 minutes
python main_historical.py --interval 60 --duration 180

# - Production run: Every 5 minutes for 24 hours
python main_historical.py --interval 300 --duration 86400

# - High-frequency monitoring: Every 30 seconds for 1 hour
python main_historical.py --interval 30 --duration 3600

# Verbose mode with progress updates
python main_historical.py --verbose --duration 600

# Dry run without database upload
python main_historical.py --no-upload --duration 300

# Combine multiple options
python main_historical.py -i 120 -d 3600 -v
```

### Query Historical Data

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

# Get summary
summary = db.get_historical_summary()
print(f"Total records: {summary['total_records']}")
print(f"Date range: {summary['oldest_record']} to {summary['newest_record']}")
```

## System Features

### Real-Time Monitoring

The system provides comprehensive monitoring during operation:

1. **Progress Reports**: 
   - Total fetches, successful/failed counts
   - Records collected per fetch
   - Success rate percentage
   - Runtime statistics

2. **Health Status**:
   - Exchange API reliability scores (0-100)
   - OK/WARN/FAIL status indicators
   - 24-hour rolling window tracking

3. **Rate Limiting**:
   - Per-exchange rate limit status
   - Automatic backoff notifications
   - Token bucket visualization

4. **Error Recovery**:
   - Automatic retry with exponential backoff
   - Extended backoff after consecutive failures
   - Graceful degradation

### Data Storage

Historical data is stored with:
- **Timestamp precision**: Microsecond accuracy
- **No duplicates**: Each fetch creates new records
- **Efficient indexing**: Fast queries on time ranges
- **Unlimited retention**: No automatic deletion

## Troubleshooting

### Common Issues and Solutions

#### "Table doesn't exist" Error
```
Error: relation "public.exchange_data_historical" does not exist
```
**Solution:**
- Run the SQL script from Step 1
- Verify you're in the correct Supabase project
- Check the SQL Editor output for errors

#### Permission Denied
```
Error: permission denied for table exchange_data_historical
```
**Solution:**
- Ensure your Supabase key is a service role key (not anon key)
- Check RLS (Row Level Security) policies:
  ```sql
  -- Disable RLS for the table (if appropriate)
  ALTER TABLE exchange_data_historical DISABLE ROW LEVEL SECURITY;
  ```

#### Rate Limiting Issues
```
! Rate limit hit for Binance. Backing off for 60.0 seconds
```
**Solution:**
- This is normal - the system handles it automatically
- To reduce occurrences:
  - Increase `HISTORICAL_FETCH_INTERVAL` in settings
  - Reduce number of enabled exchanges
  - Check current limits: Watch console output

#### No Data Being Collected
**Checklist:**
1. Verify basic system works: `python main.py`
2. Check settings.py:
   ```python
   ENABLE_HISTORICAL_COLLECTION = True  # Must be True
   ENABLE_DATABASE_UPLOAD = True        # Must be True
   ```
3. Verify exchanges are enabled
4. Check internet connection
5. Look for error messages in console

#### Process Won't Stop After Duration
**Fixed in latest version (2025-07-22):**
- Previous bug: Duration parameter was ignored
- Now fixed: Process stops correctly after specified duration
- If still experiencing issues:
  1. Pull latest code from repository
  2. Check for stuck processes: `tasklist | findstr python`
  3. Kill stuck processes via Task Manager
  4. Always use `--duration` for controlled runs

#### Process Hangs or Times Out
**Windows-specific issue:**
- The continuous loop might appear to hang
- Use Ctrl+C to stop gracefully
- Always specify duration to avoid indefinite runs:
  ```bash
  python main_historical.py --duration 300
  ```

## Best Practices

1. **Start Small**: Test with short intervals first
2. **Monitor Initially**: Use `--verbose` flag when starting
3. **Check Health**: Review system health scores regularly
4. **Database Size**: Monitor table growth over time
5. **Backup Data**: Regular Supabase backups recommended

## Advanced Usage

### Custom Analysis Queries

```sql
-- Average funding rate by exchange over last 24 hours
SELECT 
    exchange,
    AVG(funding_rate) as avg_funding_rate,
    AVG(apr) as avg_apr,
    COUNT(*) as data_points
FROM exchange_data_historical
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY exchange
ORDER BY avg_apr DESC;

-- Top movers (biggest APR changes)
WITH latest_data AS (
    SELECT DISTINCT ON (exchange, symbol) 
        exchange, symbol, apr, timestamp
    FROM exchange_data_historical
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    ORDER BY exchange, symbol, timestamp DESC
),
previous_data AS (
    SELECT DISTINCT ON (exchange, symbol)
        exchange, symbol, apr
    FROM exchange_data_historical
    WHERE timestamp BETWEEN NOW() - INTERVAL '25 hours' AND NOW() - INTERVAL '24 hours'
    ORDER BY exchange, symbol, timestamp DESC
)
SELECT 
    l.exchange,
    l.symbol,
    l.apr as current_apr,
    p.apr as previous_apr,
    l.apr - p.apr as apr_change
FROM latest_data l
JOIN previous_data p ON l.exchange = p.exchange AND l.symbol = p.symbol
ORDER BY ABS(l.apr - p.apr) DESC
LIMIT 20;
```

## Changelog

### 2025-07-22
- **Updated**: Added warnings about duration parameter usage
- **Updated**: Clarified that without `--duration`, collection runs indefinitely
- **Added**: Information about duration bug fix
- **Added**: Recommended usage patterns and common examples
- **Enhanced**: Troubleshooting section with process management guidance

### 2025-07-21
- Initial release of historical data collection system
- Comprehensive setup guide with SQL scripts
- Usage examples and best practices
- Advanced query examples for data analysis