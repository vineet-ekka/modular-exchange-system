# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-exchange cryptocurrency funding rate tracking system with real-time data collection, historical analysis, and professional dashboard visualization. Supports Binance, KuCoin, Backpack, and Hyperliquid exchanges, tracking 1,240+ perpetual contracts across 600+ unique assets.

## Environment Setup

### Prerequisites Check
```bash
# Check Python version (3.8+ required)
python --version

# Check Node.js version (16+ required)
node --version

# Check Docker is running
docker ps
```

### Initial Setup
```bash
# Create .env from template
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt

# Install dashboard dependencies
cd dashboard && npm install && cd ..

# Start PostgreSQL
docker-compose up -d
```

## Key Architecture

### System Components
- **Backend API**: FastAPI server (`api.py`) serving data from PostgreSQL
- **Frontend Dashboard**: React 19 TypeScript app with Tailwind CSS (`dashboard/`)
- **Data Collector**: Main orchestrator (`main.py`) with exchange factory pattern
- **Database**: PostgreSQL via Docker with two main tables (real-time and historical)
- **Exchange Modules**: Factory pattern with base class inheritance (`exchanges/`)
- **Backfill System**: Unified historical data collection (`scripts/unified_historical_backfill.py`)

### Data Flow
1. **Real-time**: Exchange APIs → Exchange modules → Data processor → PostgreSQL → API → Dashboard
2. **Historical**: Exchange APIs → Backfill script → Batch processing → PostgreSQL
3. **Rate Limiting**: Sequential collection with configurable delays between exchanges
4. **Error Recovery**: Health tracker monitors failures, automatic retries with exponential backoff

## Common Development Commands

### Start Everything
```bash
python start.py  # One-command startup for entire system

# Windows alternative
start.bat  # Double-click or run in cmd
```

### Docker Management
```bash
# Start just PostgreSQL
docker-compose up -d postgres

# Start PostgreSQL with pgAdmin interface
docker-compose up -d

# View pgAdmin at http://localhost:5050
# Credentials: admin@exchange.local / admin123

# Stop all containers
docker-compose down

# Stop and remove volumes (CAUTION: removes all data)
docker-compose down -v
```

### Code Quality & Formatting
```bash
# Format Python code with black
black .

# Sort imports with isort
isort .

# Lint Python code with flake8
flake8 . --max-line-length=120

# Validate configuration
python config/validator.py

# Verify all imports work correctly
python -c "import main; import api; import database.postgres_manager"
```

### Individual Components
```bash
# API Server
python api.py

# Dashboard
cd dashboard && npm start

# Data Collector
python main.py --loop --interval 30 --quiet

# PostgreSQL
docker-compose up -d postgres
```

### Testing
```bash
# Test all exchanges
python tests/test_all_exchanges.py

# Test database connection
python tests/test_db.py

# Test specific exchange
python tests/test_hyperliquid.py

# Test synchronized date windows
python tests/test_synchronized_dates.py

# Test unified date simulation
python tests/test_unified_dates_simulation.py

# Test normalization (if test file exists)
python test_normalization.py

# Dashboard tests
cd dashboard && npm test

# Run specific dashboard test
cd dashboard && npm test -- --testNamePattern="AssetFundingGrid"

# Run dashboard tests in watch mode
cd dashboard && npm test -- --watchAll

# Test coverage for dashboard
cd dashboard && npm test -- --coverage
```

### Data Management
```bash
# Historical backfill (30 days, all exchanges) - Recommended way
python run_backfill.py --days 30 --parallel

# Alternative: Direct script execution
python scripts/unified_historical_backfill.py --days 30 --parallel

# Specific exchanges backfill
python scripts/unified_historical_backfill.py --days 30 --exchanges binance kucoin

# Fill data gaps
python fill_data_gaps.py

# Quick update for recent data
python quick_update.py

# Fix funding intervals
python scripts/fix_funding_intervals.py

# Fix Hyperliquid-specific gaps
python scripts/hyperliquid_gap_filler.py

# Database tools
python database_tools.py check    # Check database status
python database_tools.py clear --quick  # Clear all data
python database_tools.py backup  # Backup database

# Verify backfill results
cat .unified_backfill.status  # Check backfill status and record counts

# Windows: Check backfill status
type .unified_backfill.status
```

### Build & Deploy
```bash
# Build React dashboard
cd dashboard && npm run build

# Type check TypeScript
cd dashboard && npx tsc --noEmit

# Install Python dependencies
pip install -r requirements.txt
pip install fastapi uvicorn  # Additional API dependencies

# Verify all dependencies installed
python -c "import fastapi, uvicorn, pandas, psycopg2, aiohttp"
```

## Important Configuration Files

### Main Settings
- `config/settings.py` - Main system configuration (exchanges, intervals, display)
- `config/sequential_config.py` - Sequential collection schedules
- `config/settings_manager.py` - Runtime settings management API
- `.env` - Database credentials and environment variables
- `.env.example` - Template for environment variables

### Key Configuration Options
```python
# config/settings.py
EXCHANGES = {
    'binance': True,      # 547 contracts
    'kucoin': True,       # 477 contracts  
    'backpack': True,     # 43 contracts
    'hyperliquid': True,  # 171 contracts
}

ENABLE_SEQUENTIAL_COLLECTION = True  # Stagger API calls
EXCHANGE_COLLECTION_DELAY = 30      # Seconds between exchanges
```

### Environment Variables (.env)
```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
DATABASE_TABLE_NAME=exchange_data
HISTORICAL_TABLE_NAME=exchange_data_historical
```

## Exchange-Specific Considerations

### Symbol Normalization
- KuCoin uses `XBT` for Bitcoin (normalized to `BTC`)
- Hyperliquid uses simple names (`BTC` not `BTCUSDT`)
- Backpack uses `_USDC_PERP` suffix

### Base Asset Normalization (Prefix Handling)
Tokens with special prefixes are normalized to their base asset across all exchanges:

#### Binance Prefixes:
- `1000` prefix (e.g., `1000SHIBUSDT` → `SHIB`) - Represents 1,000 units
- `1000000` prefix (e.g., `1000000MOGUSDT` → `MOG`) - Represents 1,000,000 units

#### KuCoin Prefixes (check in order):
- `1000000` prefix (e.g., `1000000MOGUSDTM` → `MOG`) - Remove 7 characters
- `10000` prefix (e.g., `10000CATUSDTM` → `CAT`) - Remove 5 characters  
- `1000` prefix (e.g., `1000BONKUSDTM` → `BONK`) - Remove 4 characters

#### Hyperliquid & Backpack Prefixes:
- `k` prefix (e.g., `kPEPE` → `PEPE`, `kBONK` → `BONK`) - Represents thousands

#### Special Cases (NOT normalized):
- `1INCH` - Legitimate token name
- `1MBABYDOGE` - Legitimate token name

### Funding Intervals
- **Binance**: Mixed (1h, 4h, 8h)
- **KuCoin**: Mixed (1h, 2h, 4h, 8h)
- **Backpack**: All 1 hour
- **Hyperliquid**: All 1 hour

### APR Calculation Formula
```python
# Based on funding interval
if funding_interval_hours == 1:
    apr = funding_rate * 8760 * 100  # 365 * 24
elif funding_interval_hours == 4:
    apr = funding_rate * 2190 * 100  # 365 * 24 / 4
elif funding_interval_hours == 8:
    apr = funding_rate * 1095 * 100  # 365 * 24 / 8
```

## Adding New Features

### New Exchange Integration
1. Create module in `exchanges/` inheriting from `base_exchange.py`
2. Implement required methods:
   - `fetch_data()` - Real-time data collection
   - `normalize_data()` - Data standardization
   - `fetch_all_perpetuals_historical()` - Historical backfill (optional)
3. Add to `EXCHANGES` dict in `config/settings.py`
4. Register in `exchange_factory.py`
5. For historical support, add to `EXCHANGE_CLASSES` in `scripts/unified_historical_backfill.py`

### New API Endpoint
1. Add endpoint in `api.py` following FastAPI patterns
2. Use `get_db_connection()` for database access
3. Return JSON-serializable data

### New Dashboard Component
1. Create component in `dashboard/src/components/`
2. Follow existing patterns (TypeScript, Tailwind CSS)
3. Use `services/api.ts` for API calls
4. Import in relevant page component

## Database Schema

### Main Table: exchange_data
```sql
exchange VARCHAR(50)
symbol VARCHAR(50) 
base_asset VARCHAR(20)
quote_asset VARCHAR(20)
funding_rate NUMERIC(20, 10)
funding_interval_hours INTEGER
apr NUMERIC(20, 10)
index_price NUMERIC(20, 10)
mark_price NUMERIC(20, 10)
open_interest NUMERIC(30, 10)
contract_type VARCHAR(50)
market_type VARCHAR(50)
timestamp TIMESTAMP WITH TIME ZONE
UNIQUE(exchange, symbol)
```

### Historical Table: funding_rates_historical
```sql
exchange VARCHAR(50)
symbol VARCHAR(50)
funding_rate NUMERIC(20, 10)
funding_time TIMESTAMP WITH TIME ZONE
mark_price NUMERIC(20, 10)
funding_interval_hours INTEGER
UNIQUE(exchange, symbol, funding_time)
```

## Error Handling Patterns

- Use try/except blocks with specific error logging
- Record failures in health tracker for monitoring
- Implement exponential backoff for API retries
- Validate configuration before running (`config/validator.py`)

## Performance Considerations

- Sequential collection prevents API rate limiting
- Database uses UPSERT to prevent duplicates
- Frontend uses lazy loading for contract details
- Composite indexes on (exchange, symbol, funding_time)
- Connection pooling for concurrent database access

## Troubleshooting

### Common Issues & Solutions

#### Duplicate Assets in Dashboard (e.g., "1000BONK" and "BONK")
- **Cause**: Incorrect base asset normalization for prefix tokens
- **Solution**: Check normalization functions in exchange modules:
  - Real-time: `normalize_data()` method
  - Historical: `_extract_base_asset()` or equivalent methods
- **Verification**: Run `python -c "... check base_asset normalization ..."`

#### Binance Data Not Visible During Backfill
- Binance data IS being fetched (check `.unified_backfill.status` file)
- Enhanced logging added with print statements for visibility
- Look for "BINANCE:" prefixed messages in console output
- Verify with: `cat .unified_backfill.status | grep -A5 binance`

#### Port Already in Use
```bash
# Windows - Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Windows - Find and kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <process_id> /F
```

#### Database Connection Failed
```bash
# Check PostgreSQL container status
docker ps | grep postgres

# Restart PostgreSQL
docker-compose restart postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test database connection
python tests/test_db.py
```

#### No Data Showing in Dashboard
```bash
# Check API is running
curl http://localhost:8000/api/health

# Test data collection manually
python main.py

# Check for data in database
python database_tools.py check
```

#### Missing npm Dependencies
```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
```

## Important Files & Locations

### Status Files (Auto-generated)
- `.backfill.status` - Tracks backfill progress
- `.unified_backfill.status` - Unified backfill status
- `.hyperliquid_backfill.status` - Hyperliquid-specific status

### Log Output
- Console output from each component
- API logs at http://localhost:8000/docs for debugging
- Database logs via `docker-compose logs postgres`

### Configuration Backups
- `config/backups/` - Auto-saved settings backups

### Key Python Dependencies
- `pandas>=1.5.0` - Data manipulation and analysis
- `requests>=2.28.0` - Synchronous HTTP client
- `aiohttp>=3.8.0` - Asynchronous HTTP client for concurrent requests
- `psycopg2-binary>=2.9.0` - PostgreSQL database adapter
- `python-dotenv>=1.0.0` - Environment variable management
- `asyncio-throttle>=1.0.0` - Rate limiting for async operations
- `numpy>=1.21.0` - Numerical operations support
- `fastapi` & `uvicorn` - Web framework and ASGI server (install separately)

### Key Dashboard Dependencies
- `react@19.1.1` - UI framework
- `typescript@4.9.5` - Type safety for JavaScript
- `tailwindcss@3.4.17` - Utility-first CSS framework
- `axios@1.11.0` - HTTP client for API calls
- `recharts@3.1.2` - Chart components
- `react-router-dom@7.8.0` - Routing
- `date-fns@4.1.0` - Date manipulation
- `clsx@2.1.1` - Conditional className utility

## Recent Updates

### 2025-08-28
- **Fixed base asset normalization across all exchanges**:
  - Binance: Handles `1000` and `1000000` prefixes correctly
  - KuCoin: Fixed handling of `1000000`, `10000`, and `1000` prefixes (checked in order)
  - Hyperliquid: Normalizes `k` prefix tokens (e.g., `kPEPE` → `PEPE`)
  - Backpack: Normalizes `k` prefix tokens
- **Unified asset display**: Same asset now appears once in dashboard instead of multiple entries
- **Fixed edge cases**: Properly handles `10000CATUSDTM` → `CAT`, `1000000MOGUSDTM` → `MOG`

### 2025-08-27
- Fixed Hyperliquid API query handling for proper data display
- Enhanced Binance backfill logging visibility (added print statements in binance_exchange.py)
- Improved backfill progress reporting for all exchanges
- Added multiple backfill status tracking files
- Implemented settings management with web interface
- Added shutdown button to dashboard header
- Enhanced historical data synchronization

## Development Tips

### When Working with Exchanges
- Always check rate limits in exchange modules
- Use sequential collection to avoid API throttling
- Test individual exchanges before full system test
- Monitor health tracker for failures

### When Modifying Database
- Always use UPSERT operations to prevent duplicates
- Test migrations on local database first
- Keep indexes updated for new query patterns
- Use parameterized queries for security

### When Updating Dashboard
- Run TypeScript checks before committing
- Test with both empty and full datasets
- Verify responsive design on different screen sizes
- Check console for React warnings

### Performance Monitoring
```bash
# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/funding-rates-grid

# Check database query performance
python -c "from database.postgres_manager import PostgresManager; pm = PostgresManager(); pm.check_connection()"

# Monitor memory usage during collection
python main.py --loop --interval 30 --quiet
```

## Project Structure Overview

### Core Modules
- `main.py` - Data collection orchestrator with loop management
- `api.py` - FastAPI server with 17+ endpoints
- `start.py` - System startup orchestrator (one-command launch)
- `run_backfill.py` - Historical data backfill wrapper
- `database_tools.py` - Database management utilities
- `fill_data_gaps.py` - Data gap detection and repair
- `quick_update.py` - Fast recent data update
- `shutdown_dashboard.py` - Graceful system shutdown

### Exchange Modules (`exchanges/`)
- `base_exchange.py` - Abstract base class for all exchanges
- `exchange_factory.py` - Factory pattern for exchange instantiation
- `binance_exchange.py` - Binance implementation (547 contracts)
- `kucoin_exchange.py` - KuCoin implementation (477 contracts)
- `backpack_exchange.py` - Backpack implementation (43 contracts)
- `hyperliquid_exchange.py` - Hyperliquid implementation (171 contracts)

### Dashboard (`dashboard/`)
- React 19 with TypeScript
- `src/components/Grid/` - Data grid components (AssetFundingGrid, HistoricalFundingView)
- `src/components/Cards/` - Stat cards and summaries
- `src/components/Layout/` - Header, footer, navigation
- `src/components/Settings/` - Configuration management UI
- `src/components/Ticker/` - Real-time ticker display
- `src/pages/` - Page components for routing
- `src/services/api.ts` - API client service

### Database (`database/`)
- `postgres_manager.py` - Connection pooling and query execution
- Two-table schema: real-time and historical data

### Configuration (`config/`)
- `settings.py` - Main configuration hub
- `sequential_config.py` - Collection scheduling
- `settings_manager.py` - Runtime settings management API
- `backups/` - Automatic configuration backups

### Scripts (`scripts/`)
- `unified_historical_backfill.py` - Main historical data collector
- `fix_funding_intervals.py` - Repair incorrect interval data
- `hyperliquid_gap_filler.py` - Hyperliquid-specific gap repair
- `historical_updater.py` - Update historical data
- Windows batch files for PostgreSQL management

### Tests (`tests/`)
- `test_all_exchanges.py` - Full exchange integration test
- `test_db.py` - Database connection test
- `test_hyperliquid.py` - Hyperliquid-specific tests
- `test_synchronized_dates.py` - Date synchronization test
- `test_unified_dates_simulation.py` - Unified date simulation