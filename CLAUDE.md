# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL RULES

### File Management
- **NEVER delete files without DOUBLE CONFIRMATION** - List files and explain before deletion
- **ALWAYS prefer editing existing files** - Never create new files unless explicitly required
- **NEVER proactively create documentation files** (*.md) unless explicitly requested
- **ALWAYS read files before editing** using the Read tool - never assume contents

### Git Operations
- **NEVER commit unless explicitly asked** - User must request commits explicitly
- **ALWAYS run pre-commit checks** before committing (see commands below)
- **NEVER update git config** - Leave git configuration unchanged
- **ALWAYS use HEREDOC for multi-line commit messages** to ensure proper formatting

### Code Standards
- **TypeScript**: Always run `cd dashboard && npx tsc --noEmit` before commits
- **Python**: Verify imports exist, use type hints where possible
- **Testing**: No formal test framework for Python. React uses type checking only.
- **Imports**: Check if packages exist in requirements.txt or package.json before using
- **NO COMMENTS**: Do not add code comments unless explicitly requested

### Windows-Specific Notes
- Use `type` instead of `cat` for viewing files
- Use `dir` instead of `ls` if needed
- Use `taskkill /PID <pid> /F` instead of `kill -9`
- Python commands use `python` prefix (not `python3`)
- Use `netstat -ano | findstr :PORT` to find processes on ports

### Required Python Packages
When writing Python code, these packages are available:
- pandas, requests, psycopg2-binary, numpy, python-dotenv
- aiohttp, asyncio-throttle, redis
- **IMPORTANT - Install these manually** (not in requirements.txt yet):
  - `fastapi` - Required for API server
  - `uvicorn` - Required for running FastAPI
  - `psutil` - Required for system monitoring
  - `scipy` - Optional for statistical operations
- Check requirements.txt for exact versions before using

### Required Frontend Packages
When writing React/TypeScript code, these are available:
- React 19, TypeScript 4.9.5, React Router v7.8.0, Tailwind CSS
- axios, date-fns, recharts, react-window (for virtualization)
- clsx for conditional CSS classes

## Quick Start

### Prerequisites
- **Docker Desktop** must be running (provides PostgreSQL, Redis, pgAdmin)
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Additional Python packages** (install manually):
  ```bash
  pip install fastapi uvicorn psutil scipy
  ```

```bash
# Start everything with one command
python start.py

# This automatically handles:
# - Prerequisites check (Python, Node, Docker)
# - PostgreSQL database startup via Docker (port 5432)
# - Redis cache startup via Docker (port 6379)
# - pgAdmin web interface (port 5050)
# - API server (FastAPI on port 8000)
# - React dashboard (port 3000)
# - Data collector (30-second updates, logs to data_collector.log)
# - Historical backfill (30-day rolling window)
# - Z-score calculator (zone-based updates)

# Verify everything is running
curl http://localhost:8000/api/health         # Should return {"status":"healthy"}
curl http://localhost:3000                    # Should load dashboard

# Shutdown
python shutdown_dashboard.py

# Monitor background processes (Claude Code specific)
/bashes                              # List all background processes
BashOutput tool with bash_id="<id>" # View output of specific process
KillShell tool with shell_id="<id>" # Kill specific process

# Example: Check if start.py is running properly
# 1. Run /bashes to see all processes
# 2. Find the process ID for "python start.py"
# 3. Use BashOutput tool to see its output
```

## Essential Commands

### Pre-commit Checks (MUST run before any commit)
```bash
cd dashboard && npx tsc --noEmit              # TypeScript check (REQUIRED)
python database_tools.py check                # Database connectivity
```

### Development Commands
```bash
# Build & Test
cd dashboard && npm run build                 # Production build
cd dashboard && npm test                      # Run tests (no test files currently)
cd dashboard && npx tsc --noEmit              # TypeScript check only

# Individual Components
python api.py                                 # API server only (port 8000)
cd dashboard && npm start                     # Dashboard only (port 3000)
python main.py --loop --interval 30           # Data collector only
python utils/zscore_calculator.py             # Z-score calculator only
python shutdown_dashboard.py                  # Clean shutdown of all services

# Database Operations
python database_tools.py check                # Test connection
python database_tools.py clear --quick        # Clear all data (CAUTION)
python database_tools.py status               # Show detailed table stats
python scripts/unified_historical_backfill.py --days 30 --parallel  # Backfill all exchanges (fastest)
python scripts/unified_historical_backfill.py --days 7 --exchanges binance  # Specific exchange
python scripts/fill_recent_gaps.py            # Fill any gaps in recent data
python scripts/collect_spread_history.py      # Collect arbitrage spread data
python scripts/cleanup_delisted_contracts.py  # Remove stale contracts

# Performance Testing
python scripts/test_performance.py            # Z-score performance
curl -s http://localhost:8000/api/health/performance | python -m json.tool

# Redis Cache Testing
python -c "from utils.redis_cache import RedisCache; cache=RedisCache(); print('Redis:' if cache.is_available() else 'Fallback:')"
```

### Single Component Testing
```bash
# Test specific exchange
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(len(e.fetch_data()))"

# Test database connection
python database_tools.py check

# Test API endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/funding-rates-grid | python -m json.tool
curl "http://localhost:8000/api/arbitrage/opportunities?min_spread=0.001" | python -m json.tool

# Test Z-score performance
python scripts/test_performance.py
```

### Troubleshooting Commands
```bash
# Check services
curl http://localhost:8000/api/health
curl http://localhost:3000

# Port conflicts (Windows)
netstat -ano | findstr :8000
netstat -ano | findstr :3000
taskkill /PID <pid> /F

# Check logs
type data_collector.log                       # Windows
cat data_collector.log                        # Linux/Mac

# Docker status
docker ps                                     # Check if PostgreSQL/Redis running
docker-compose logs postgres                 # View PostgreSQL logs
docker-compose logs redis                    # View Redis logs
docker-compose restart postgres              # Restart database
docker-compose restart redis                 # Restart Redis cache
docker-compose up -d pgadmin                 # Start pgAdmin interface

# pgAdmin Access (optional database GUI)
# URL: http://localhost:5050
# Email: admin@exchange.local
# Password: admin123
```

## High-Level Architecture

### System Overview
- **Scale**: 1,260+ contracts across 600+ unique assets from 4 exchanges (Binance, KuCoin, Backpack, Hyperliquid)
- **Update Cycle**: 30-second real-time refresh with sequential API calls
- **Database**: PostgreSQL with 5 tables (real-time, historical, statistics, metadata, arbitrage)
- **Backend**: FastAPI (port 8000) with 28+ endpoints including arbitrage detection
- **Frontend**: React 19/TypeScript (port 3000) with 30-second polling
- **Caching**: Redis for API responses (5s TTL contracts, 10s summary) with 512MB memory limit
- **Z-Score System**: Parallel processing <1s for all contracts, zone-based updates
- **Arbitrage System**: Cross-exchange funding rate spread detection and APR calculation
- **Container Stack**:
  - PostgreSQL (port 5432) - Main database
  - Redis (port 6379) - Caching layer
  - pgAdmin (port 5050) - Database GUI (admin@exchange.local/admin123)

### Data Flow
```
Exchange APIs → Rate Limiter → Normalization → PostgreSQL → FastAPI → React Dashboard
                                                    ↓            ↓         ↓
                                            Z-Score Calculator  Redis   Arbitrage
                                                               Cache    Detection
```

### Key Patterns

1. **Exchange Factory Pattern** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange`
   - Implement `fetch_data()` and `normalize_data()`
   - Factory creates instances: `ExchangeFactory.create_exchange(name)`
   - Parallel mode adds `batch_id` for tracking (removed before DB insertion)
   - Use `ExchangeFactory.create_all()` for all enabled exchanges

2. **Sequential Collection** (`config/sequential_config.py`)
   - Staggered delays: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s), Kraken (240s)
   - Prevents API rate limiting across exchanges
   - Can switch between sequential/parallel modes via `ENABLE_SEQUENTIAL_COLLECTION`

3. **Symbol Normalization** (Critical for consistency)
   - Handles prefixes: `1000SHIB` → `SHIB`, `kPEPE` → `PEPE`, `1MBABYDOGE` → `BABYDOGE`
   - Each exchange implements in `normalize_data()` method
   - Ensures unique symbol across exchanges

4. **Z-Score System** (`utils/zscore_calculator.py`)
   - Zone-based updates: Active (|Z|>2) every 30s, Stable every 2min
   - Performance: <1s calculation, <100ms API response
   - Caching: 5s TTL for contracts, 10s for summary
   - Parallel processing with ThreadPoolExecutor

5. **Column Whitelisting** (`database/postgres_manager.py`)
   - Tracking columns (`batch_id`, `collection_timestamp`) used internally
   - Automatically filtered out before database insertion
   - Valid columns explicitly whitelisted to prevent SQL errors

6. **Arbitrage Detection** (`utils/arbitrage_scanner.py`)
   - Compares funding rates across all exchange pairs
   - Calculates APR spreads accounting for different funding intervals
   - No fee calculations (pure funding rate arbitrage)
   - Dashboard at `/arbitrage` route

## Database Schema

```sql
-- Real-time data (current funding rates)
exchange_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20),
    quote_asset VARCHAR(20),
    funding_rate NUMERIC(20, 10),
    funding_interval_hours INTEGER,
    apr NUMERIC(20, 10),
    index_price NUMERIC(20, 10),
    mark_price NUMERIC(20, 10),
    open_interest NUMERIC(30, 10),
    contract_type VARCHAR(50),
    market_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    volume_24h_quote NUMERIC(30, 10),
    index_mark_spread NUMERIC(20, 10),
    UNIQUE(exchange, symbol)
)

-- Historical data (30-day rolling window)
funding_rates_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_rate NUMERIC(20, 10) NOT NULL,
    funding_time TIMESTAMP WITH TIME ZONE NOT NULL,
    mark_price NUMERIC(20, 10),
    funding_interval_hours INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, funding_time)
)

-- Statistical metrics (Z-scores, percentiles)
funding_statistics (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    current_z_score NUMERIC(10, 4),
    current_percentile NUMERIC(5, 2),
    mean_30d NUMERIC(20, 10),
    std_dev_30d NUMERIC(20, 10),
    median_30d NUMERIC(20, 10),
    min_30d NUMERIC(20, 10),
    max_30d NUMERIC(20, 10),
    data_points INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol)
)

-- Contract metadata (funding intervals, creation time)
contract_metadata (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_interval_hours INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol)
)

-- Arbitrage spreads (cross-exchange opportunities)
arbitrage_spreads (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(50) NOT NULL,
    exchange_a VARCHAR(50) NOT NULL,
    exchange_b VARCHAR(50) NOT NULL,
    funding_rate_a NUMERIC(20, 10),
    funding_rate_b NUMERIC(20, 10),
    apr_spread NUMERIC(20, 10),
    timestamp TIMESTAMP WITH TIME ZONE,
    UNIQUE(asset, exchange_a, exchange_b, timestamp)
)
```

## Funding Rate and APR Calculations

### APR Calculation Formula
```python
# APR = funding_rate × periods_per_year × 100
# Periods per year depends on funding interval:
periods_per_year = (365 × 24) / funding_interval_hours

# Exchange-specific intervals:
# Binance: 8-hour (1,095 periods/year)
# KuCoin: 4 or 8-hour (2,190 or 1,095 periods/year)
# Backpack: 1-hour (8,760 periods/year)
# Hyperliquid: 1-hour (8,760 periods/year)
```

### Arbitrage APR Spread
```python
# APR spread is the absolute difference between two exchanges' APRs
apr_spread = abs(exchange_a_apr - exchange_b_apr)
# This represents the annualized profit from funding rate differential
```

## Key API Endpoints

### Core Data Endpoints
- `/api/funding-rates` - All contracts with pagination (limit/offset)
- `/api/funding-rates-grid` - Asset-grouped view across exchanges
- `/api/statistics` - System-wide statistics
- `/api/exchanges` - List of active exchanges
- `/api/unique-assets` - All unique base assets

### Z-Score Endpoints
- `/api/contracts-with-zscores` - All contracts with Z-score data
- `/api/zscore-summary` - Summary statistics
- `/api/health/performance` - Performance metrics

### Arbitrage Endpoints
- `/api/arbitrage/opportunities?min_spread=0.001&top_n=20` - Arbitrage opportunities
  - `min_spread`: Minimum funding rate spread (0.001 = 0.1%)
  - `top_n`: Number of top opportunities to return

### Historical Data Endpoints
- `/api/historical-funding-by-asset/{asset}?days=7` - Historical rates for an asset
- `/api/funding-sparkline/{symbol}?exchange={exchange}&hours=24` - Sparkline data

## Environment Variables

Create `.env` file in project root:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123  # Must match docker-compose.yml
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Important Notes**:
- The password **must be `postgres123`** to match docker-compose.yml configuration
- System defaults to `postgres` in settings.py if no .env file exists (will cause connection errors)
- Redis configuration: 512MB max memory with LRU eviction policy
- pgAdmin credentials are separate: admin@exchange.local / admin123

## Common Workflows

### Adding New Exchange
1. Create new exchange module in `exchanges/` inheriting from `BaseExchange`
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to `exchanges/exchange_factory.py`
4. Update `config/settings.py` EXCHANGES dict
5. Add to `config/sequential_config.py` schedule
6. Test: `python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"`

### Checking System Health
```bash
# Check all components at once
python database_tools.py check && curl http://localhost:8000/api/health && curl http://localhost:3000

# Monitor real-time data collection
type data_collector.log | findstr "OK"        # Windows
tail -f data_collector.log | grep "OK"        # Linux/Mac

# Check Z-score performance
curl http://localhost:8000/api/health/performance
```

### Modifying Dashboard Components
1. Check existing patterns in `dashboard/src/components/`
2. Use TypeScript with proper types
3. Follow existing Tailwind CSS patterns (no inline styles)
4. Test: `cd dashboard && npx tsc --noEmit`
5. Build: `cd dashboard && npm run build`

### Database Schema Changes
1. Create migration script in `sql/` directory
2. Update relevant models in Python code
3. Test locally first: `python database_tools.py check`
4. Document changes in schema section

## Core Files for Understanding

### System Entry Points
- `start.py` - One-command orchestrator (starts everything)
- `api.py` - FastAPI backend with 28+ endpoints including Z-score and arbitrage
- `main.py` - Data collection coordinator with health tracking
- `shutdown_dashboard.py` - Clean shutdown utility
- `database_tools.py` - Database management CLI

### Exchange Integration
- `exchanges/base_exchange.py` - Abstract base class (all exchanges inherit)
- `exchanges/exchange_factory.py` - Factory pattern for exchange instances
- `exchanges/binance_exchange.py` - Binance perpetual futures (547 contracts)
- `exchanges/kucoin_exchange.py` - KuCoin perpetual futures (477 contracts)
- `exchanges/backpack_exchange.py` - Backpack perpetual futures (43 contracts)
- `exchanges/hyperliquid_exchange.py` - Hyperliquid perps (173 contracts)
- `exchanges/kraken_exchange.py` - Kraken futures (353 contracts - disabled)
- `exchanges/deribit_exchange.py` - Deribit futures (20 contracts - disabled)
- `config/sequential_config.py` - Collection timing with staggered delays
- `config/settings.py` - Main configuration (enable/disable exchanges)

### Z-Score System
- `utils/zscore_calculator.py` - Parallel Z-score engine (<1s for 1,260 contracts)
- `utils/zscore_calculator_optimized.py` - Performance optimized version
- `utils/contract_metadata_manager.py` - Tracks funding intervals
- `scripts/test_performance.py` - Performance validation suite
- `utils/redis_cache.py` - Redis caching layer with fallback

### Arbitrage System
- `utils/arbitrage_scanner.py` - Cross-exchange funding rate arbitrage detection
- `utils/arbitrage_spread_statistics.py` - Statistical analysis of spreads
- `scripts/collect_spread_history.py` - Historical spread collection

### Dashboard
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main 600+ asset grid
- `dashboard/src/components/Grid/HistoricalFundingViewContract.tsx` - Historical charts (table-only display)
- `dashboard/src/components/ArbitrageOpportunities.tsx` - Arbitrage opportunities table
- `dashboard/src/pages/ArbitragePage.tsx` - Arbitrage dashboard page
- `dashboard/src/services/api.ts` - API client with all endpoints
- `dashboard/src/services/arbitrage.ts` - Arbitrage-specific API client
- `dashboard/src/App.tsx` - Main router and layout (includes /arbitrage route)
- `dashboard/package.json` - Frontend dependencies (React 19, TypeScript, Tailwind)

### Database & Utilities
- `database/postgres_manager.py` - Database operations and connection pooling
- `database_tools.py` - Database management CLI
- `scripts/unified_historical_backfill.py` - Parallel 30-day backfill
- `scripts/fill_recent_gaps.py` - Fill gaps in historical data
- `scripts/cleanup_delisted_contracts.py` - Remove stale contracts
- `utils/health_tracker.py` - System health monitoring
- `utils/rate_limiter.py` - API rate limiting for exchanges

## Common Issues & Solutions

### Docker Desktop Not Running
- **Problem**: PostgreSQL/Redis containers fail to start
- **Solution**: Start Docker Desktop first, wait for it to fully initialize
- **Verification**: Run `docker ps` to confirm Docker is running
- **Note**: Docker Desktop is REQUIRED for this system to work

### Port Already in Use
```bash
# Windows: Find and kill process using a port
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Alternative: Use different ports
python api.py --port 8001
cd dashboard && PORT=3001 npm start
```

### Symbol Normalization
- **Test**: `python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(len(e.fetch_data()))"`
- Issues with duplicate assets (e.g., "1000BONK" and "BONK") are handled by normalization in each exchange's `normalize_data()` method

### Data Collector Issues
- Check `data_collector.log` for errors
- Manual start: `python main.py --loop --interval 30`
- If not starting: Check if `start.py` process is running
- Verify all exchanges are reachable (network/firewall issues)
- If funding rates not updating: Look for "batch_id" SQL errors in logs (fixed by column whitelisting)

### Dashboard Issues
- Delete `.backfill.status` and `.unified_backfill.status` if backfill stuck at 100%
- TypeScript errors: `cd dashboard && npx tsc --noEmit`
- If not loading: Check API at http://localhost:8000/api/health
- Clear browser cache if UI seems outdated

### Database Connection Issues
- Ensure Docker is running: `docker ps`
- Check PostgreSQL: `docker-compose ps`
- Restart if needed: `docker-compose restart postgres`
- Connection test: `python database_tools.py check`

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn psutil scipy redis     # Additional packages often needed
cd dashboard && npm install                        # Frontend dependencies
```

### Database Password Mismatch
- **Problem**: Connection error with "authentication failed"
- **Solution**: Ensure `.env` file has `POSTGRES_PASSWORD=postgres123`
- **Alternative**: Update `config/settings.py` default password to `postgres123`

### Redis Connection Issues
- **Problem**: "Redis connection failed, using in-memory cache"
- **Solution**: Ensure Docker is running: `docker-compose up -d redis`
- **Note**: System will work without Redis but with reduced performance

## Z-Score Statistical Monitoring System

### Overview
The Z-score system provides statistical analysis of funding rates to identify extreme deviations and trading opportunities.

### Backend Implementation (Completed)
- **Calculator**: `utils/zscore_calculator.py` - Main calculation engine
- **Performance**: <1s for 1,260 contracts using parallel processing (8 workers)
- **Zone-Based Updates**:
  - Active contracts (|Z| > 2): Update every 30 seconds
  - Stable contracts (|Z| ≤ 2): Update every 2 minutes
- **Redis Caching**: 5s TTL for contracts, 10s for summary
- **Database Tables**:
  - `funding_statistics` - Z-scores and 30-day statistics
  - `contract_metadata` - Funding intervals for accurate calculations

### API Endpoints
```bash
# Get all contracts with Z-scores
GET /api/contracts-with-zscores?limit=100&offset=0

# Get Z-score summary statistics
GET /api/zscore-summary

# Get performance metrics
GET /api/health/performance
```

### Testing Z-Score System
```bash
# Run Z-score calculator manually
python utils/zscore_calculator.py

# Test performance
python scripts/test_performance.py

# Check Z-score API response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/contracts-with-zscores
```

### Frontend Implementation Requirements (Not Yet Completed)
When implementing `ContractZScoreGrid.tsx`:
1. **Component Location**: `dashboard/src/components/Grid/ContractZScoreGrid.tsx`
2. **Display Format**: Flat list of 1,260+ contracts (NO asset grouping)
3. **Performance**: Must use `react-window` for virtual scrolling (already installed)
4. **Color Scheme**: Blue-to-orange gradient (NO red/green)
   - Blue: Negative Z-scores (funding below mean)
   - Orange: Positive Z-scores (funding above mean)
   - Intensity: Based on |Z-score| magnitude
5. **Sorting**: By absolute Z-score (|Z|) descending by default
6. **Row Heights**:
   - Standard: 40px for |Z| < 2.0
   - Expanded: 120px for |Z| ≥ 2.0 (shows additional metrics)
7. **Update Frequency**: 30-second polling for live updates

## Files Never to Commit
- `.backfill.status`, `.unified_backfill.status` - Progress tracking files
- `data_collector.log` - Can grow very large (>100MB)
- `.env` - Contains database credentials
- `node_modules/` - NPM packages (use npm install)
- `__pycache__/` - Python bytecode
- `.venv/`, `venv/` - Python virtual environment
- `*.pyc` - Compiled Python files
- `.claude/settings.local.json` - Local Claude settings

## Working with the Arbitrage System

The arbitrage system identifies funding rate spreads across exchanges:

```python
# Example: Testing arbitrage detection
from utils.arbitrage_scanner import ArbitrageScanner
scanner = ArbitrageScanner()
opportunities = scanner.scan_opportunities(min_spread=0.001)  # 0.1% minimum spread

# To save arbitrage spreads to database
from scripts.collect_spread_history import collect_spreads
collect_spreads(min_spread=0.001)
```

### Key Arbitrage Files
- `utils/arbitrage_scanner.py` - Core scanner logic
- `utils/arbitrage_spread_statistics.py` - Statistical analysis of spreads
- `dashboard/src/pages/ArbitragePage.tsx` - Arbitrage dashboard page
- `dashboard/src/components/ArbitrageOpportunities.tsx` - Opportunities table
- `dashboard/src/services/arbitrage.ts` - Frontend API client
- `scripts/collect_spread_history.py` - Historical spread collection

### Arbitrage Dashboard Route
- Available at http://localhost:3000/arbitrage
- Shows real-time funding rate arbitrage opportunities
- Sortable by APR spread, asset, or exchanges

### Arbitrage Database Table
```sql
arbitrage_spreads (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(50) NOT NULL,
    exchange_a VARCHAR(50) NOT NULL,
    exchange_b VARCHAR(50) NOT NULL,
    funding_rate_a NUMERIC(20, 10),
    funding_rate_b NUMERIC(20, 10),
    apr_spread NUMERIC(20, 10),
    timestamp TIMESTAMP WITH TIME ZONE,
    UNIQUE(asset, exchange_a, exchange_b, timestamp)
)
```

## Recent Improvements & Known Issues

### Recent Improvements (2025)
- **Arbitrage System**: Cross-exchange funding rate spread detection with APR calculation
- **Z-Score System**: Full backend implementation with parallel processing
- **Performance**: Optimized dashboard to reduce API calls by 83%
- **Symbol Normalization**: Fixed duplicate assets (1000BONK → BONK, kPEPE → PEPE)
- **Historical Data**: Table-only display for better performance
- **Database Schema**: Added `funding_statistics` and `contract_metadata` tables
- **Redis Caching**: Added Redis for API response caching (5s TTL contracts, 10s summary)
- **Docker Compose**: Full containerization with PostgreSQL, Redis, and pgAdmin
- **Background Processing**: Z-score calculator runs separately with zone-based updates
- **Funding Interval Tracking**: Proper APR calculations based on actual exchange intervals (1h, 4h, 8h)

### Known Issues & Solutions
- **Batch_id Column Error**: Fixed in `postgres_manager.py` - columns are now whitelisted before insertion
- **Backfill Stuck at 100%**: Delete `.backfill.status` and `.unified_backfill.status`
- **High API Load**: Dashboard was pre-fetching 600+ assets - now uses on-demand loading
- **Data Collector Not Starting**: Check `data_collector.log` for errors
- **TypeScript Errors**: Always run `cd dashboard && npx tsc --noEmit` before commits
- **Redis Connection Failed**: System falls back to in-memory cache automatically
- **Port Conflicts**: Use `netstat -ano | findstr :PORT` on Windows to find process
- **Unicode Errors in Logs**: Z-score calculator uses Unicode symbols that may fail on Windows console
- **Dashboard Refresh**: Clear browser cache if UI seems stuck on old data
- **Exchange API Errors**: Check rate limits in `config/settings.py` and adjust delays if needed
- **Parallel Backfill Fails**: Use sequential mode instead: remove `--parallel` flag
- **Docker Desktop Required**: Must have Docker running for PostgreSQL/Redis containers

## Current Development Features (In Progress)

### Kraken Exchange Integration
- Module ready at `exchanges/kraken_exchange.py` (353 contracts)
- Currently disabled in `config/settings.py`
- To enable: Set `'kraken': True` in EXCHANGES dict
- Add to sequential schedule in `config/sequential_config.py`

### Deribit Exchange Integration
- Module ready at `exchanges/deribit_exchange.py` (20 contracts)
- Currently disabled in `config/settings.py`
- To enable: Set `'deribit': True` in EXCHANGES dict
- Add to sequential schedule in `config/sequential_config.py`

### Additional Monitoring Scripts
- `scripts/collect_spread_history.py` - Collects and stores arbitrage spread data
- `scripts/fill_recent_gaps.py` - Fills gaps in historical data
- `scripts/test_performance.py` - Tests Z-score calculation performance

## Test Commands for Debugging

### Testing Individual Exchange Data Collection
```bash
# Test each exchange separately
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); data=e.fetch_data(); print(f'Binance: {len(data)} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); data=e.fetch_data(); print(f'KuCoin: {len(data)} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); data=e.fetch_data(); print(f'Backpack: {len(data)} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); data=e.fetch_data(); print(f'Hyperliquid: {len(data)} contracts')"

# Test all exchanges via factory
python -c "from exchanges.exchange_factory import ExchangeFactory; exchanges=ExchangeFactory.create_all(); print(f'Total exchanges: {len(exchanges)}')"
```

### Testing Database Operations
```bash
# Test table creation
python -c "from database.postgres_manager import PostgresManager; db=PostgresManager(); db.create_tables(); print('Tables created')"

# Check row counts
python -c "from database.postgres_manager import PostgresManager; import psycopg2; db=PostgresManager(); conn=db.get_connection(); cur=conn.cursor(); cur.execute('SELECT COUNT(*) FROM exchange_data'); print(f'Real-time rows: {cur.fetchone()[0]}'); cur.execute('SELECT COUNT(*) FROM funding_rates_historical'); print(f'Historical rows: {cur.fetchone()[0]}'); conn.close()"
```

### Testing API Endpoints
```bash
# Test each major endpoint
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/statistics | python -m json.tool
curl -s http://localhost:8000/api/exchanges | python -m json.tool
curl -s http://localhost:8000/api/unique-assets | python -m json.tool | head -20
curl -s "http://localhost:8000/api/funding-rates?limit=5" | python -m json.tool
curl -s "http://localhost:8000/api/contracts-with-zscores?limit=5" | python -m json.tool
curl -s "http://localhost:8000/api/arbitrage/opportunities?min_spread=0.005" | python -m json.tool
```

### Testing Background Processes
```bash
# Check if data collector is running
tasklist | findstr python  # Windows
ps aux | grep python       # Linux/Mac

# Monitor data collector output
type data_collector.log | findstr "OK"  # Windows
tail -f data_collector.log | grep "OK"   # Linux/Mac

# Check Redis connection
python -c "import redis; r=redis.Redis(host='localhost', port=6379); r.ping(); print('Redis connected')"

# Check Z-score calculator
python utils/zscore_calculator.py
```

## Managing Long-Running Processes in Claude Code

### Monitoring Background Processes
Claude Code runs long-running processes in the background. Use these commands to manage them:

```bash
# List all running background processes
/bashes

# Check output of a specific process
# Use BashOutput tool with the bash_id from /bashes
# Example: BashOutput tool with bash_id="abc123"

# Kill a specific background process
# Use KillShell tool with shell_id from /bashes
# Example: KillShell tool with shell_id="abc123"
```

### Common Background Processes
1. **Data Collector**: `python main.py --loop --interval 30`
   - Runs continuously, collecting data every 30 seconds
   - Output in `data_collector.log`

2. **Historical Backfill**: `python scripts/unified_historical_backfill.py --days 30 --parallel`
   - Can take 10-30 minutes for full backfill
   - Monitor progress with BashOutput tool

3. **Z-Score Calculator**: `python utils/zscore_calculator.py`
   - Runs continuously with zone-based updates
   - Updates active contracts every 30s, stable every 2min

### Process Health Checks
```bash
# Check if critical processes are running
python -c "import requests; r=requests.get('http://localhost:8000/api/health'); print(r.json())"

# Check last data collection time
python -c "from database.postgres_manager import PostgresManager; import psycopg2; db=PostgresManager(); conn=db.get_connection(); cur=conn.cursor(); cur.execute('SELECT MAX(last_updated) FROM exchange_data'); print(f\"Last update: {cur.fetchone()[0]}\"); conn.close()"

# Monitor error rate in data collector
type data_collector.log | findstr ERROR | find /c /v ""  # Windows - count errors
grep -c ERROR data_collector.log  # Linux/Mac - count errors
```

## Summary of Key Improvements in CLAUDE.md

### Critical Rules Enhanced
- Added "NO COMMENTS" rule - do not add code comments unless explicitly requested
- Added "NEVER update git config" rule for git operations
- Added "ALWAYS use HEREDOC for multi-line commit messages" for proper formatting
- Enhanced Windows-specific notes with port finding command

### Core Files Updated
- Updated API endpoint count (28+ instead of 27+)
- Added contract counts for each exchange
- Added missing files for arbitrage system (`arbitrage_spread_statistics.py`, `ArbitragePage.tsx`)
- Added missing utility scripts (`fill_recent_gaps.py`, `cleanup_delisted_contracts.py`)
- Marked disabled exchanges (Kraken, Deribit) clearly

### Better Organization
- Consolidated duplicate sections
- Improved readability with consistent formatting
- Added missing details from README.md discoveries