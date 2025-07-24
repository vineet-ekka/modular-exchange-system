# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

### Key Files to Know
- **config/settings.py** - User configuration (exchanges, display, output, historical)
- **main.py** - Entry point for real-time data collection
- **main_historical.py** - Entry point for continuous historical collection
- **.env** - Sensitive credentials (Supabase URL/key)
- **exchanges/** - Exchange-specific implementations
- **data_processing/data_processor.py** - APR calculation and display logic
- **utils/rate_limiter.py** - Smart rate limiting system
- **utils/continuous_fetcher.py** - Continuous collection engine
- **database/supabase_manager.py** - Database operations (regular + historical)

### Common Tasks
- **Run the system (single)**: `python main.py`
- **Run in loop mode**: `python main.py --loop --duration 3600`
- **Run historical collection (with duration)**: `python main_historical.py --duration 3600`
- **View historical summary**: `python main_historical.py --summary`
- **Test imports**: `python -c "from main import ExchangeDataSystem"`
- **Check Git status**: `git status`
- **Run CI locally**: Install flake8, black, isort and run them
- **View logs**: Check console output (no log files by default)
- **Check for stuck processes**: `tasklist | findstr python` (Windows)
- **Add APR column to database**: Run `add_apr_column.sql` in Supabase SQL Editor
- **View historical CSV**: Open `historical_exchange_data.csv` (cumulative data)

## Project Overview

A modular cryptocurrency exchange data system that fetches perpetual futures data from multiple exchanges (Backpack, Binance, KuCoin, Deribit), normalizes it, calculates APR, and can export to CSV or upload to Supabase database. Features both real-time data collection and continuous historical time-series storage.

## Essential Commands

### Running the System
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Then edit with your Supabase credentials

# Ensure APR column exists in main table
# Run add_apr_column.sql in Supabase SQL Editor

# For historical collection, create table first
# Run create_historical_table.sql in Supabase SQL Editor

# Run real-time data collection (single run)
python main.py

# Run real-time data in loop mode (UPSERT to main table)
python main.py --loop --duration 3600  # 1 hour
python main.py --loop --interval 60 --duration 180  # Every minute for 3 minutes
python main.py --loop --quiet  # Continuous with minimal output

# Run historical data collection (INSERT to historical table)
python main_historical.py --duration 3600  # 1 hour
python main_historical.py --interval 60 --duration 180  # 3 fetches in 3 minutes

# View historical summary
python main_historical.py --summary

# Run usage examples
python example_usage.py
```

### Configuration
- **Primary configuration**: `config/settings.py` - Toggle exchanges, set display limits, enable/disable features
- **Environment variables**: `.env` file for sensitive credentials (Supabase URL/key)
- **.env.example exists**: Copy and edit with your credentials:
  ```
  SUPABASE_URL=your_url
  SUPABASE_KEY=your_key
  DATABASE_TABLE_NAME=exchange_data
  ```
- **CSV Export**: Historical data automatically exports to `historical_exchange_data.csv`

## Main.py vs Main_historical.py

### Key Differences
- **main.py --loop**: Updates real-time data using UPSERT (overwrites existing records)
  - Target table: `exchange_data` (configured in settings)
  - Use case: Keep latest funding rates for current trading decisions
  - Data retention: Only keeps most recent data per exchange/symbol
  
- **main_historical.py**: Preserves all data using INSERT (never overwrites)
  - Target table: `exchange_data_historical` 
  - Use case: Build time-series data for trend analysis
  - Data retention: Keeps all historical records with timestamps

### When to Use Which
- Use `main.py --loop` for: Real-time dashboards, current funding rates, live monitoring
- Use `main_historical.py` for: Historical analysis, trend tracking, backtesting

## Architecture Overview

### Core Flow
1. **main.py** → ExchangeDataSystem orchestrates the entire flow
2. **ExchangeFactory** → Creates and manages exchange instances based on config
3. **Exchange implementations** → Fetch raw data from APIs (async for Binance open interest)
4. **DataProcessor** → Normalizes data, calculates APR, validates quality
5. **Output** → CSV export and/or Supabase batch upload (UPSERT on exchange+symbol)

### Key Design Patterns

#### Factory Pattern
- `exchange_factory.py` manages all exchange instances
- Easy to add new exchanges by implementing BaseExchange interface

#### Health Monitoring
- Global health tracker monitors API success/failure rates
- 24-hour rolling window for reliability scoring
- Integrated into base_exchange.py for automatic tracking
- Real-time status indicators (OK/WARN/FAIL)

#### Rate Limiting
- Token bucket algorithm with per-exchange limits
- Automatic 429 response handling with backoff
- Thread-safe operations
- Configurable limits per exchange

#### Data Validation
- Business-focused validation (not academic)
- Quality scoring (0-100) instead of verbose warnings
- Focus on: data freshness, exchange coverage, price sanity

#### Performance Optimizations
- Async bulk fetching for Binance open interest (19.5x speedup)
- Architectural filtering removes non-trading contracts before API calls
- Batch database uploads (100 records/batch)
- Smart rate limiting prevents API bans

### Data Pipeline

#### Unified Columns
All exchanges normalize to these columns:
- exchange, symbol, base_asset, quote_asset
- funding_rate, funding_interval_hours, apr
- index_price, mark_price, open_interest
- contract_type, market_type

#### APR Calculation
- Formula: `APR = funding_rate * (8760 / funding_interval_hours) * 100`
- Calculated in DataProcessor after data collection
- Handles null values gracefully
- **Now properly uploaded to database** (fixed 2025-07-22)

## Critical Implementation Details

### Exchange-Specific Quirks
- **Binance**: Separate USD-M and COIN-M markets, filters non-trading contracts
- **KuCoin**: Different funding time field names, millisecond conversions needed
- **Backpack**: Simple REST API, funding interval in milliseconds
- **Deribit**: Fixed 8-hour funding intervals, open interest in contracts (converted to USD)

### Windows Compatibility
- All Unicode characters replaced with ASCII (no emojis)
- Handles Windows path separators
- Encoding issues resolved
- SIGTERM signal handling adapted for Windows

### Database Operations
- **Regular table**: Uses UPSERT with conflict on (exchange, symbol)
- **Historical table**: Uses INSERT to preserve all records
- Batch uploads for performance (100 records/batch)
- Datetime columns converted to ISO format strings
- Timezone-aware timestamp handling
- **APR column**: Now included in uploads (ensure column exists with `add_apr_column.sql`)

## Testing Approach
**Note**: No automated test framework exists. Testing is done by:
1. Running `python main.py` and observing output
2. Running `python main_historical.py --no-upload --duration 60` for dry run
3. Database connection test runs automatically
4. Performance metrics tracked in console output
5. Health monitoring provides real-time feedback
6. GitHub Actions CI runs on push (linting, imports)

## Common Modifications

### Add New Exchange
1. Create `exchanges/newexchange_exchange.py` inheriting from BaseExchange
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to exchange_classes dict in `exchange_factory.py`
4. Add to EXCHANGES dict in `config/settings.py`

### Change Data Display
- Modify display_columns in `data_processor.py` display_table() method
- Adjust formatting in the same method for new columns
- Update unified_columns if adding new data fields

### Adjust Performance
- `API_DELAY` in settings.py for basic rate limiting (deprecated)
- Use `rate_limiter.set_rate_limit()` for per-exchange limits
- Batch size in `supabase_manager.py` (currently 100)
- Max concurrent requests in `binance_exchange.py` (currently 20)
- `HISTORICAL_FETCH_INTERVAL` for collection frequency

## Git Workflow

### Branches
- **master**: Stable production code
- **feature/historical-data-collection**: Current development branch
- Create feature branches for new functionality: `git checkout -b feature/new-feature`

### Common Git Commands
```bash
# Check status
git status

# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature: description"

# Push to GitHub
git push

# Create pull request
gh pr create --title "Add feature" --body "Description of changes"
```

### GitHub Actions CI/CD
The repository includes automated testing on push:
- Python 3.8, 3.9, 3.10, 3.11 compatibility
- Code linting with flake8
- Code formatting checks with black and isort
- Configuration validation
- Import testing

## Historical Data Collection System ✅ IMPLEMENTED

The historical data collection system is now fully implemented and ready for use:

### NEW: CSV Export Feature (2025-07-24)
- Historical data now automatically exports to CSV alongside database uploads
- Single cumulative file: `historical_exchange_data.csv`
- Headers written on first run, data appended on subsequent runs
- Configured via `HISTORICAL_CSV_FILENAME` in settings.py
- Works when `ENABLE_CSV_EXPORT = True`

### Components Implemented
1. **utils/rate_limiter.py**
   - Token bucket algorithm with per-exchange limits
   - Automatic 429 backoff handling
   - Thread-safe operations
   - Real-time status monitoring

2. **utils/continuous_fetcher.py** ✅ FIXED (2025-07-22)
   - Continuous data collection at configurable intervals
   - Graceful shutdown with signal handling
   - Exponential backoff on failures
   - Progress reporting and statistics
   - **Duration parameter now works correctly** (fixed bug where it was ignored)

3. **main_historical.py**
   - Command-line interface for historical collection
   - Arguments: --interval, --duration, --summary, --verbose
   - Dry run mode with --no-upload
   - Integration with health monitoring

4. **Enhanced database/supabase_manager.py**
   - `upload_historical_data()` - INSERT operations for time-series data
   - `fetch_historical_data()` - Query with time range and filters
   - `get_historical_summary()` - Overview of historical data
   - Proper timestamp handling and timezone support

### Configuration (in settings.py)
```python
ENABLE_HISTORICAL_COLLECTION = True
HISTORICAL_FETCH_INTERVAL = 300  # seconds
HISTORICAL_TABLE_NAME = "exchange_data_historical"
HISTORICAL_CSV_FILENAME = "historical_exchange_data"  # CSV export filename
HISTORICAL_MAX_RETRIES = 3
HISTORICAL_BASE_BACKOFF = 60
```

### Database Schema
Historical table includes:
- All standard columns (exchange, symbol, funding_rate, apr, etc.)
- `timestamp` column for time-series tracking
- Recommended indexes: timestamp, (exchange, symbol, timestamp)

### Usage Examples

#### Real-Time Loop Mode (main.py --loop)
```bash
# Quick test: Every 30 seconds for 5 minutes
python main.py --loop --interval 30 --duration 300

# Production dashboard: Every minute, quiet mode
python main.py --loop --interval 60 --quiet

# Default settings: Every 5 minutes for 1 hour
python main.py --loop --duration 3600

# 24-hour continuous update
python main.py --loop --duration 86400 --quiet

# Indefinite run (Ctrl+C to stop) - USE WITH CAUTION
python main.py --loop --interval 300
```

#### Historical Collection (main_historical.py)
```bash
# Start continuous collection (WARNING: runs indefinitely without --duration!)
python main_historical.py --duration 3600  # ALWAYS specify duration

# Custom interval (60 seconds) for 30 minutes
python main_historical.py --interval 60 --duration 1800

# Quick test: 3 fetches in 3 minutes
python main_historical.py --interval 60 --duration 180

# Production run: Every 5 minutes for 24 hours
python main_historical.py --interval 300 --duration 86400

# View historical data summary
python main_historical.py --summary

# Dry run without uploading
python main_historical.py --no-upload --duration 300
```

⚠️ **CRITICAL**: Always use `--duration` parameter unless you explicitly want indefinite collection. Without it, the process runs forever until manually stopped.

### Performance Metrics (Loop Mode)

Based on production testing with `--interval 30 --duration 300`:
- **Throughput**: 1,010 contracts per run
- **Execution time**: ~16 seconds per complete cycle
- **Success rate**: 100% (10/10 runs successful)
- **Database performance**: <2 seconds for 1,010 UPSERT operations
- **Memory usage**: Stable, no leaks detected
- **API reliability**: All exchanges maintained 100% health score

### Recommended Settings

| Use Case | Command | Rationale |
|----------|---------|-----------|
| Development | `--loop --interval 60 --duration 300` | Quick 5-minute test |
| Staging | `--loop --interval 300 --duration 3600` | 1-hour validation |
| Production | `--loop --interval 300 --quiet` | Continuous with minimal logs |
| Dashboard | `--loop --interval 60 --quiet` | Real-time updates |

## Important Notes
- System designed for non-coders to modify via settings.py
- Validation focuses on business logic, not data purity
- Health monitoring provides actionable intelligence
- All times internally handled as UTC
- Git repository initialized with .gitignore and .env.example
- GitHub repository: https://github.com/vineet-ekka/modular-exchange-system
- Historical data collection fully implemented and tested
- Rate limiting prevents API bans automatically
- Windows compatibility ensured throughout

## Key Principles
1. **Business Focus**: Validation and features target trading needs, not academic purity
2. **User Friendly**: Non-coders can modify via settings.py
3. **Resilient**: Graceful degradation, automatic retries, health monitoring
4. **Performance**: Async operations, batch uploads, smart filtering
5. **Extensible**: Factory pattern makes adding exchanges straightforward

## Common Issues & Solutions

### Loop Mode Issues (main.py --loop)
- **High CPU usage**: Use longer intervals (300s instead of 30s)
- **Database conflicts**: UPSERT handles this automatically
- **Memory growth**: Restart periodically for very long runs
- **Quiet mode not working**: Check if ENABLE_CONSOLE_DISPLAY is True in settings
- **Process won't stop**: Use Ctrl+C or set --duration limit

### Historical Collection Issues
- **Table doesn't exist**: Run `create_historical_table.sql` in Supabase
- **Process runs forever**: ALWAYS use `--duration` flag (bug fixed 2025-07-22)
- **Stuck processes**: Check with `tasklist | findstr python`, kill via Task Manager
- **Rate limit errors**: Normal, system handles automatically
- **Duration not working**: Update to latest code (fixed in continuous_fetcher.py)

### Database Issues
- **Connection failed**: Check `.env` file credentials
- **Permission denied**: Ensure service role key (not anon key)
- **Upload failures**: Check if table exists and RLS is disabled
- **Duplicate key errors**: For loop mode, ensure UPSERT conflict resolution
- **APR column missing**: Run `add_apr_column.sql` in Supabase SQL Editor

### Performance Issues
- **Slow fetches**: Reduce concurrent requests or enabled exchanges
- **Memory usage**: Batch size is optimized at 100 records
- **API timeouts**: Increase timeout in aiohttp settings
- **Interval too short**: Minimum recommended is 30 seconds

### Development Tips
- Always test with `--no-upload` first (historical mode only)
- Use `--duration` for controlled test runs
- Use `--quiet` for production deployments
- Check health scores regularly
- Monitor rate limiter status in output

## Recent Changes

### 2025-07-24
- **Deribit Exchange Added**:
  - New exchange implementation in `exchanges/deribit_exchange.py`
  - Supports all perpetual contracts (BTC, ETH, SOL, MATIC, USDC)
  - Uses 8-hour funding interval (standard display rate)
  - Note: Deribit uses continuous millisecond-level funding payments
  - Converts open interest from contracts to USD
  - Added to exchange factory and settings
  
- **Historical CSV Export**:
  - Historical data now exports to single cumulative CSV file
  - File: `historical_exchange_data.csv` (appends on each collection)
  - Headers written on first run only
  - Configured via `HISTORICAL_CSV_FILENAME` setting
  - Works alongside Supabase uploads for dual storage

### 2025-07-22

### APR Column Fix ✅ FIXED
- **Issue**: APR column was missing from database uploads
- **Root Cause**: APR was not included in `table_columns` list in `supabase_manager.py`
- **Fix**: 
  - Updated `table_columns` to include 'apr' in the correct position
  - Created `add_apr_column.sql` script for existing databases
- **Impact**: APR values now successfully upload to Supabase
- **Verification**: Tested with loop mode, confirmed APR values appear in database

### Loop Mode for main.py ✅ NEW
- **Feature**: Added continuous loop mode to main.py for real-time updates
- **Implementation**: 
  - `--loop` flag enables continuous mode with UPSERT operations
  - `--interval` sets seconds between runs (default: 300)
  - `--duration` limits total runtime (prevents indefinite runs)
  - `--quiet` suppresses detailed output for production
- **Performance**: Tested with 10 successful runs in 5 minutes, 100% success rate
- **Use Case**: Live dashboards, real-time monitoring, current funding rates

### Duration Parameter Fix
- **Issue**: Historical collection ignored the `--duration` parameter, running indefinitely
- **Fix**: Modified `continuous_fetcher.py` to properly check duration within the main loop
- **Files Changed**:
  - `utils/continuous_fetcher.py`: Added duration parameter to `start()` method and internal checks
  - `main_historical.py`: Simplified to pass duration directly to fetcher
- **Impact**: Historical collection now stops correctly after specified duration

### Documentation Updates
- Updated README.md with clearer historical collection examples
- Added troubleshooting for stuck processes
- Emphasized importance of using `--duration` parameter
- Added changelog sections to track changes

### Best Practices Going Forward
1. **Always specify duration** for controlled collection runs (both loop modes)
2. **Check for stuck processes** before starting new runs
3. **Use shorter durations** for testing (e.g., `--duration 180` for 3 minutes)
4. **Monitor Supabase table growth** when running long collections
5. **Use --quiet mode** for production deployments to reduce log noise
6. **Ensure APR column exists** in database before running uploads