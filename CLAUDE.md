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
- **Run the system**: `python main.py`
- **Run historical collection (with duration)**: `python main_historical.py --duration 3600`
- **View historical summary**: `python main_historical.py --summary`
- **Test imports**: `python -c "from main import ExchangeDataSystem"`
- **Check Git status**: `git status`
- **Run CI locally**: Install flake8, black, isort and run them
- **View logs**: Check console output (no log files by default)
- **Check for stuck processes**: `tasklist | findstr python` (Windows)

## Project Overview

A modular cryptocurrency exchange data system that fetches perpetual futures data from multiple exchanges (Backpack, Binance, KuCoin), normalizes it, calculates APR, and can export to CSV or upload to Supabase database. Features both real-time data collection and continuous historical time-series storage.

## Essential Commands

### Running the System
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Then edit with your Supabase credentials

# For historical collection, create table first
# Run create_historical_table.sql in Supabase SQL Editor

# Run real-time data collection
python main.py

# Run historical data collection (ALWAYS specify duration!)
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

## Critical Implementation Details

### Exchange-Specific Quirks
- **Binance**: Separate USD-M and COIN-M markets, filters non-trading contracts
- **KuCoin**: Different funding time field names, millisecond conversions needed
- **Backpack**: Simple REST API, funding interval in milliseconds

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
HISTORICAL_MAX_RETRIES = 3
HISTORICAL_BASE_BACKOFF = 60
```

### Database Schema
Historical table includes:
- All standard columns (exchange, symbol, funding_rate, apr, etc.)
- `timestamp` column for time-series tracking
- Recommended indexes: timestamp, (exchange, symbol, timestamp)

### Usage Examples
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

## Important Notes
- System designed for non-coders to modify via settings.py
- Validation focuses on business logic, not data purity
- Health monitoring provides actionable intelligence
- All times internally handled as UTC
- Git repository initialized with .gitignore and .env.example
- GitHub repository: https://github.com/estalocanegro/modular-exchange-system
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

### Performance Issues
- **Slow fetches**: Reduce concurrent requests or enabled exchanges
- **Memory usage**: Batch size is optimized at 100 records
- **API timeouts**: Increase timeout in aiohttp settings

### Development Tips
- Always test with `--no-upload` first
- Use `--verbose` for debugging
- Check health scores regularly
- Monitor rate limiter status in output

## Recent Changes (2025-07-22)

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
1. **Always specify duration** for controlled historical collection runs
2. **Check for stuck processes** before starting new runs
3. **Use shorter durations** for testing (e.g., `--duration 180` for 3 minutes)
4. **Monitor Supabase table growth** when running long collections