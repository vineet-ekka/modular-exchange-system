# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL RULES

### File Deletion Policy
**NEVER delete files without DOUBLE CONFIRMATION from the user.** When asked to delete or remove files:
1. First, list the files that would be deleted and explain what they are
2. Ask for explicit confirmation: "Are you sure you want to delete these files?"
3. Only proceed with deletion after receiving a second, clear confirmation
4. Documentation files (*.md), specification files, and tasklists are NOT temporary files

### Commit Policy
**NEVER commit changes unless the user explicitly asks you to.** It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.

### File Creation Policy
- ALWAYS prefer editing existing files in the codebase
- NEVER write new files unless explicitly required
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested

### Code Modification Policy
- ALWAYS read files before editing them using the Read tool
- NEVER make assumptions about file contents - read them first
- When modifying TypeScript files, ensure type checking passes: `cd dashboard && npx tsc --noEmit`
- When modifying Python files, verify imports are correct and available

## Quick Start

```bash
# Start everything (one command)
python start.py

# Check system status
curl -s http://localhost:8000/api/health

# Windows alternative for curl
python -c "import requests; print(requests.get('http://localhost:8000/api/health').json())"
```

## Essential Commands

### Pre-commit Checks (Always run before committing)
```bash
# Type check TypeScript - MUST run before commits
cd dashboard && npx tsc --noEmit

# Test critical functionality  
python database_tools.py check

# Format Python code (if black installed)
black . --line-length=120
```

### Build & Test
```bash
# Build dashboard
cd dashboard && npm run build

# Run dashboard tests (interactive mode)
cd dashboard && npm test

# Run dashboard tests (CI mode - single run)
cd dashboard && CI=true npm test

# Install Python dependencies (if imports fail)
pip install -r requirements.txt
pip install fastapi uvicorn psutil

# Note: No Python test framework configured yet
# Test exchanges manually with commands in "Testing Individual Components" section
```

### System Control
```bash
# Start everything
python start.py

# Individual components
python api.py                              # API server (port 8000)
cd dashboard && npm start                  # Dashboard (port 3000)
python main.py --loop --interval 30        # Data collector

# Clean shutdown of dashboard
python shutdown_dashboard.py

# Check background processes (Claude Code)
/bashes

# Monitor collector output (Claude Code)
BashOutput tool with bash_id="<id>"

# Kill stuck process (Claude Code)
KillBash tool with shell_id="<id>"
```

### Data Operations
```bash
# Test individual exchange modules
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); print(f'Backpack: {len(e.fetch_data())} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); print(f'Hyperliquid: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kraken_exchange import KrakenExchange; e=KrakenExchange(); print(f'Kraken: {len(e.fetch_data())} contracts')"

# Historical backfill (30 days, all exchanges)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Check database connection
python database_tools.py check

# Clear database (careful!)
python database_tools.py clear --quick

# Fix funding intervals
python scripts/fix_funding_intervals.py

# Fill Hyperliquid gaps (hourly funding)
python scripts/hyperliquid_gap_filler.py
```

## Architecture Overview

### System Components
- **Data Collector** (`main.py`): Fetches funding rates every 30 seconds from 5 exchanges
- **FastAPI Backend** (`api.py`): 27+ endpoints serving PostgreSQL data
- **React Dashboard** (`dashboard/`): TypeScript frontend with real-time updates
- **Exchange Modules** (`exchanges/`): Factory pattern with BaseExchange inheritance
- **PostgreSQL Database**: Two tables - real-time and 30-day historical
- **Start Script** (`start.py`): Orchestrates all services, handles prerequisites, manages subprocesses

### Key Architecture Patterns

1. **Factory Pattern**: `ExchangeFactory` creates exchange instances from `BaseExchange`
   - All exchanges inherit from `exchanges/base_exchange.py`
   - Factory in `exchanges/exchange_factory.py` manages instances
   - Easy to add new exchanges by implementing `fetch_data()` and `normalize_data()`

2. **Rate Limiting**: Sequential collection with configurable delays
   - Configured in `config/sequential_config.py`
   - Default schedule: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s), Kraken (240s)
   - Multiple schedule profiles: default, fast, conservative, priority

3. **Symbol Normalization**: All exchanges normalize to base assets
   - Handled in each exchange's `normalize_data()` method
   - Examples: `1000SHIB` → `SHIB`, `kPEPE` → `PEPE`, `XBTUSDTM` → `BTC`

4. **Database Strategy**: 
   - UPSERT operations prevent duplicates
   - Composite indexes on (exchange, symbol) for performance
   - Unique index on (exchange, symbol, funding_time) for historical data
   - Connection pooling through `database/postgres_manager.py`

5. **Background Tasks**: 
   - Data collector runs as subprocess via `start.py`
   - Logs to `data_collector.log`
   - Health tracking in `utils/health_tracker.py`

6. **Real-time Updates**:
   - Data collector fetches from exchanges every 30 seconds
   - Dashboard components poll API endpoints every 30 seconds
   - No WebSocket implementation - uses polling for simplicity and reliability

### Data Flow Architecture
```
Exchange APIs → Rate Limiter → Exchange Modules → Normalization 
    → PostgreSQL → FastAPI → React Dashboard
```

### Key Files & Responsibilities
- `start.py` - System orchestrator, launches all services
- `api.py` - FastAPI server with all endpoints
- `main.py` - Data collection coordinator
- `config/settings.py` - Central configuration
- `config/sequential_config.py` - Collection timing configuration
- `database/postgres_manager.py` - All database operations
- `exchanges/base_exchange.py` - Abstract base for all exchanges
- `exchanges/exchange_factory.py` - Exchange instance management
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main grid component
- `utils/rate_limiter.py` - API rate limiting
- `utils/health_tracker.py` - System health monitoring

## Critical Implementation Details

### Exchange Module Structure
All exchanges must inherit from `BaseExchange` and implement:
- `fetch_data()`: Get raw API data
- `normalize_data()`: Convert to unified format with these columns:
  - exchange, symbol, base_asset, quote_asset, funding_rate
  - funding_interval_hours, apr, index_price, mark_price, open_interest

### Database Schema
```sql
-- Real-time table
CREATE TABLE exchange_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50),
    symbol VARCHAR(50),
    base_asset VARCHAR(50),
    quote_asset VARCHAR(50),
    funding_rate NUMERIC,
    funding_interval_hours INTEGER,
    apr NUMERIC,
    index_price NUMERIC,
    mark_price NUMERIC,
    open_interest NUMERIC,
    last_updated TIMESTAMP WITH TIME ZONE
);

-- Historical table  
CREATE TABLE funding_rates_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50),
    symbol VARCHAR(50),
    base_asset VARCHAR(50),
    quote_asset VARCHAR(50),
    funding_rate NUMERIC,
    funding_interval_hours INTEGER,
    apr NUMERIC,
    index_price NUMERIC,
    mark_price NUMERIC,
    open_interest NUMERIC,
    funding_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
);

-- Performance indexes
CREATE INDEX idx_exchange_symbol ON exchange_data(exchange, symbol);
CREATE UNIQUE INDEX idx_unique_funding ON funding_rates_historical(exchange, symbol, funding_time);
```

## Symbol Normalization Rules

All exchanges normalize to base assets:
- **Numeric Prefixes**: `1000SHIB` → `SHIB`, `10000CAT` → `CAT`, `1000000MOG` → `MOG`
- **Special Cases**: `1MBABYDOGE` → `BABYDOGE`, `1000X` → `X` (KuCoin)
- **Letter Prefixes**: `kPEPE` → `PEPE` (Hyperliquid/Backpack)
- **Exchange Specific**: `XBTUSDTM` → `BTC` (KuCoin Bitcoin)

## API Endpoints

### Core Data Endpoints
- `GET /api/funding-rates-grid` - Asset-based grid view with all contracts
- `GET /api/historical-funding-by-asset/{asset}` - 30-day historical by asset
- `GET /api/contracts-by-asset/{asset}` - List all contracts for an asset
- `GET /api/current-funding/{asset}` - Current funding for specific asset
- `GET /api/statistics` - System statistics and counts
- `GET /api/top-apr/{limit}` - Top funding rates by APR
- `GET /api/funding-sparkline/{symbol}` - Sparkline data for charts

### System Control
- `GET /api/health` - System health check
- `GET/PUT /api/settings` - Configuration management
- `POST /api/settings/validate` - Validate settings
- `POST /api/settings/reset` - Reset to defaults
- `GET /api/settings/backups` - List backup configurations
- `POST /api/settings/restore` - Restore from backup

### Backfill Management
- `GET /api/backfill-status` - Current backfill status
- `POST /api/backfill/start` - Start historical backfill
- `POST /api/backfill/stop` - Stop running backfill

### Data Export
- `GET /api/settings/export` - Export current configuration
- `POST /api/settings/import` - Import configuration

## Dashboard Architecture

### Component Structure
- `AssetFundingGrid.tsx` - Main grid with 600+ assets
- `HistoricalFundingView.tsx` - Historical table view (no charts)
- `HistoricalFundingViewContract.tsx` - Contract-specific historical view
- `LiveFundingTicker.tsx` - Real-time ticker
- `BackfillProgress.tsx` - Backfill status display
- `Settings/` - Configuration components

### Key Features
- **Asset Grid**: Expandable rows showing all contracts per asset (600+ assets)
- **Smart Search**: Searches both assets and contracts, auto-expands matches
- **Historical Tables**: Shows funding rate history from latest to oldest
- **Live Updates**: 30-second refresh cycle synchronized with data collector
- **Performance**: Debounced search (300ms), lazy loading contracts, React.memo optimization
- **Auto-refresh**: Dashboard components poll API every 30 seconds for real-time updates

## Development Workflow

### Adding a New Exchange
1. Create `exchanges/newexchange_exchange.py` inheriting from `BaseExchange`
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to `exchange_factory.py` imports and creation logic
4. Add to `config/settings.py` EXCHANGES dictionary
5. Add to `config/sequential_config.py` schedule
6. Test with: `python -c "from exchanges.newexchange_exchange import NewExchange; e=NewExchange(); print(e.fetch_data())"`

### Testing Exchange Data
```python
# Test single exchange
from exchanges.kucoin_exchange import KuCoinExchange
e = KuCoinExchange()
data = e.fetch_data()
print(f"Raw data: {len(data)} contracts")
normalized = e.normalize_data(data)
print(f"Normalized: {len(normalized)} contracts")

# Test all exchanges
from exchanges.exchange_factory import ExchangeFactory
factory = ExchangeFactory({'binance': True, 'kucoin': True, 'backpack': True, 'hyperliquid': True, 'kraken': True})
for name, exchange in factory.exchanges.items():
    data = exchange.fetch_data()
    print(f"{name}: {len(data)} contracts")
```

### Database Operations
```python
# Direct database access
from database.postgres_manager import PostgresManager
db = PostgresManager()
df = db.get_all_data()
print(f"Total records: {len(df)}")

# Check historical data
historical = db.get_historical_funding("BTCUSDT", days=7)
print(f"Historical records: {len(historical)}")

# Execute custom queries
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM exchange_data")
        count = cur.fetchone()[0]
        print(f"Total records: {count}")
```

## Troubleshooting Guide

### System Not Starting
```bash
# Check if PostgreSQL is running
docker ps | findstr postgres  # Windows
docker ps | grep postgres      # Linux/Mac

# If not running, start it
docker-compose up -d postgres

# If ports are blocked
netstat -ano | findstr :8000  # Check API port
netstat -ano | findstr :3000  # Check dashboard port
taskkill /PID <pid> /F         # Kill blocking process (Windows)
```

### No Data Showing
```bash
# Check PostgreSQL is running
docker ps  # Should show exchange_postgres

# Test data collection
python main.py

# Verify API is working
curl http://localhost:8000/api/funding-rates-grid  # Linux/Mac
python -c "import requests; print(requests.get('http://localhost:8000/api/health').json())"  # Windows

# Check collector log
type data_collector.log  # Windows
cat data_collector.log   # Linux/Mac
```

### Data Collector Issues
```bash
# Manual start with debug output
python main.py --loop --interval 30

# Test specific exchange
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(e.fetch_data())"

# Check background process (Claude Code)
/bashes
BashOutput tool with bash_id="<id>"
```

### Database Issues
```bash
# Test connection
python database_tools.py check

# Restart PostgreSQL
docker-compose restart postgres

# Reset database (careful!)
python database_tools.py clear --quick
python database_tools.py init
```

### Stuck Backfill
```bash
# Remove lock file
del .unified_backfill.status  # Windows
rm .unified_backfill.status   # Linux/Mac

# Force restart via API
curl -X POST http://localhost:8000/api/backfill/stop
curl -X POST http://localhost:8000/api/backfill/start
```

### Dashboard Issues
- **Port 3000 in use**: Check `netstat -ano | findstr :3000`
- **Not updating**: Dashboard polls every 30s by design (not a bug)
- **TypeScript errors**: Run `cd dashboard && npx tsc --noEmit`
- **Clear cache**: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

## Performance Optimization

### Database Queries
- Use indexed columns (exchange, symbol) in WHERE clauses
- Limit result sets with LIMIT clauses
- Use connection pooling (already configured)
- Batch inserts with execute_batch()

### API Response Times
- Asset grid endpoint uses aggregation for performance
- Historical data limited to 30 days by default
- Pagination available on large result sets
- Caching headers set for static data

### Dashboard Performance
- Virtual scrolling for large lists
- Debounced search (300ms delay)
- Lazy loading of historical data
- No unnecessary re-renders (React.memo)

## Environment Setup

### Prerequisites
- Python 3.8+ (`python --version`)
- Node.js 16+ (`node --version`)
- Docker Desktop running (`docker ps`)
- PostgreSQL container (`docker-compose up -d postgres`)

### Environment Variables
Required `.env` file in project root:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

### Python Dependencies
```bash
pip install -r requirements.txt
# Core dependencies:
# pandas>=1.5.0
# requests>=2.28.0
# psycopg2-binary>=2.9.0
# numpy>=1.21.0
# python-dotenv>=1.0.0
# aiohttp>=3.8.0
# asyncio-throttle>=1.0.0
# fastapi, uvicorn, psutil (for API and system monitoring)
```

### Node Dependencies
```bash
cd dashboard
npm install
# Key packages:
# react, react-dom - Core React
# recharts - Charting library (removed from historical views)
# axios - HTTP client
# date-fns - Date formatting
# typescript - Type checking
# tailwindcss - Styling
```

## Files to Never Commit
- `.unified_backfill.status`, `.backfill.status` - Backfill progress tracking
- `.unified_backfill.lock` - Backfill lock file
- `data_collector.log` - Collector output (can grow large)
- `temp_data.json` - Temporary data storage
- `.env` - Environment secrets (use .env.example as template)
- `node_modules/` - NPM packages
- `__pycache__/` - Python bytecode
- `.venv/` - Python virtual environment

## Git Workflow

When creating commits:
1. **ALWAYS run type check first**: `cd dashboard && npx tsc --noEmit`
2. Format Python code: `black . --line-length=120` (if installed)
3. Test critical functionality: `python database_tools.py check`
4. Use batch git commands: `git status`, `git diff`, `git log`
5. **NEVER commit unless explicitly asked by the user**

## Testing Individual Components

### Test Exchange Modules (Quick validation)
```bash
# Test single exchange connection and data fetch
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"

# Test all exchanges at once
python -c "
from exchanges.exchange_factory import ExchangeFactory
factory = ExchangeFactory({'binance': True, 'kucoin': True, 'backpack': True, 'hyperliquid': True, 'kraken': True})
for name, exchange in factory.exchanges.items():
    try:
        data = exchange.fetch_data()
        print(f'{name}: {len(data)} contracts - OK')
    except Exception as e:
        print(f'{name}: FAILED - {e}')
"
```

### Test API Endpoints
```bash
# Test core endpoints
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/statistics | python -m json.tool
curl -s http://localhost:8000/api/funding-rates-grid | head -100
```

### Test Database Connection
```bash
# Quick database check
python database_tools.py check

# Verify tables exist
python -c "
from database.postgres_manager import PostgresManager
db = PostgresManager()
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public'\")
        tables = cur.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')
"
```

## Common Pitfalls & Patterns

### Exchange Data Normalization
All exchanges have specific normalization patterns for base assets that MUST be handled:
- **Binance**: `1000SHIB` → `SHIB`, `1000000MOG` → `MOG`, `1MBABYDOGE` → `BABYDOGE`
- **KuCoin**: `1000X` → `X` (special case), `XBTUSDTM` → `BTC`, numeric prefixes
- **Backpack/Hyperliquid**: `kPEPE` → `PEPE` (k-prefix tokens)

### Database Patterns
- **ALWAYS use UPSERT**: Prevents duplicates with ON CONFLICT clauses
- **Use indexed columns**: (exchange, symbol) for WHERE clauses
- **Connection pooling**: Already configured in `database/postgres_manager.py`
- **Real-time table**: Cleared and repopulated every 30 seconds
- **Historical table**: Uses unique constraint on (exchange, symbol, funding_time)

### React Dashboard Patterns
- **Polling intervals**: All components poll every 30 seconds to sync with collector
- **Search optimization**: Use debounced search (300ms delay already configured)
- **Performance**: Components use React.memo, lazy loading for contracts
- **Type safety**: All API responses need proper TypeScript interfaces

### API Endpoint Patterns
- **Asset vs Symbol**: Assets are normalized (BTC), symbols are exchange-specific (BTCUSDT)
- **Grid endpoints**: Return aggregated data by asset with contract lists
- **Historical endpoints**: Support time ranges (1D, 7D, 30D) via query params
- **Error responses**: Always return proper HTTP status codes with error messages

## Available Scripts

### Main Scripts
- `start.py` - Launch entire system with one command
- `api.py` - FastAPI backend server
- `main.py` - Data collection coordinator
- `database_tools.py` - Database management utilities
- `shutdown_dashboard.py` - Clean shutdown of React dashboard

### Utility Scripts (scripts/)
- `unified_historical_backfill.py` - Backfill historical data for all exchanges
- `fix_funding_intervals.py` - Correct funding interval calculations
- `hyperliquid_gap_filler.py` - Fill gaps in Hyperliquid hourly funding data

## Recent Updates and Changes

### UI Component Changes
- **Chart removal**: Historical funding views now show table-only view (charts removed)
- **Time range buttons removed**: No more 1D/7D/30D selectors
- **Table ordering**: Historical data tables show latest entries first (reversed order)
- **Simplified interface**: Focus on tabular data display

### Dashboard Behavior
- Dashboard components intentionally poll every 30 seconds for real-time data
- This matches the data collector's 30-second update cycle
- Polling intervals: Main grid (30s), Stats (30s), Live ticker (30s), Historical views (30s)

## Important Behavioral Notes

### TypeScript Type Checking
- TypeScript type check (`npx tsc --noEmit`) MUST pass before committing
- Dashboard uses TypeScript 4.9.5 with strict type checking
- Common type issues to watch for:
  - Missing type definitions for API responses
  - Incorrect prop types in React components
  - Undefined variable access

### Exchange-Specific Considerations
- **Binance**: Returns most contracts, handle rate limits carefully
- **KuCoin**: Special symbol normalization (XBTUSDTM → BTC)
- **Hyperliquid**: Hourly funding intervals (not 8-hour)
- **Backpack**: Limited contracts but fast API
- **Kraken**: Returns futures data in unique format

### Database Performance
- Real-time table is cleared and repopulated every update cycle
- Historical table can grow large (269,381+ records)
- Indexes are critical for query performance
- Use UPSERT pattern to prevent duplicates

### Error Handling Patterns
- All exchange modules should handle network errors gracefully
- Return empty list on API failure, don't crash
- Log errors to console but continue operation
- Dashboard shows "No data" message when API fails

## Current Development Focus

### Z-Score Statistical Monitoring (In Progress)
Implementing statistical analysis for funding rates as specified in `Z_score.md`:
- **Component**: New `ContractZScoreGrid.tsx` (do NOT modify AssetFundingGrid)
- **Display**: Flat list of 1,240 contracts with virtual scrolling (react-window)
- **Sorting**: Primary by |Z-score| descending
- **Colors**: Blue-orange scale only (no red/green)
- **Database**: New `funding_statistics` table with z-score calculations
- **Status**: See `tasklist.md` for implementation progress

#### Z-Score Implementation Critical Requirements
From `Z_score.md` (lines 1083-1118) - These are NON-NEGOTIABLE:
1. **FLAT LIST** - 1,240 individual contracts, NO asset grouping
2. **Virtual Scrolling REQUIRED** - Must use react-window for performance
3. **Blue-Orange Colors ONLY** - NO red/green colors
4. **Primary Sort by |Z-score|** - Descending by absolute value
5. **Dynamic Row Heights** - 40px standard, 120px for |Z| ≥ 2.0
6. **New Component** - ContractZScoreGrid.tsx, NOT modifying AssetFundingGrid

## Missing Required Packages

### Python Dependencies
The following packages are required but not in requirements.txt:
```bash
pip install fastapi uvicorn psutil scipy black
```

### React Dependencies for Z-Score Implementation
```bash
cd dashboard
npm install react-window react-window-infinite-loader @types/react-window
```