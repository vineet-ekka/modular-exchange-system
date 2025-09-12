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

### Testing Policy
- No formal test framework is currently set up for Python code
- Test individual components using the inline Python commands provided
- For React components, no test files exist - focus on type checking during development
- Run dashboard type check with `cd dashboard && npx tsc --noEmit`

### Z-Score System Policy
- Z-scores are calculated every 30 seconds (active zone) or 2 minutes (stable zone)
- Performance targets: Z-score calc <1s (achieved: 792ms), API response <100ms
- Automatic zone-based updates: ~68 active contracts (|Z|>2), ~1,197 stable contracts
- Manual Z-score update: `python -c "from utils.zscore_calculator import ZScoreCalculator; import psycopg2; conn = psycopg2.connect(host='localhost', port=5432, database='exchange_data', user='postgres', password='postgres123'); calc = ZScoreCalculator(conn); calc.process_all_contracts()"`

## Quick Start

```bash
# Start everything (one command) - Handles all prerequisites
python start.py

# This automatically:
# 1. Checks prerequisites (Python, Node, Docker)
# 2. Starts PostgreSQL database (docker-compose)
# 3. Installs npm dependencies (if needed)
# 4. Starts API server (port 8000)
# 5. Starts React dashboard (port 3000)
# 6. Starts data collector (30-second updates, logs to data_collector.log)
# 7. Starts background historical data refresh (30-day backfill)
# 8. Starts Z-score calculator (zone-based: 30s active, 2min stable)
# 9. Opens browser automatically

# Manual shutdown if needed
python shutdown_dashboard.py  # Stops all running processes
```

## Essential Commands

### Validation Commands (Run to check implementation)
```bash
# Test Z-score performance (target: <1s for calc, <100ms for API)
python scripts/test_performance.py

# Check Z-score data in database
python -c "from database.postgres_manager import PostgresManager; db=PostgresManager(); import pandas as pd; df=pd.read_sql('SELECT * FROM funding_statistics LIMIT 5', db.conn); print(df)"

# Test Z-score API endpoints
curl -s http://localhost:8000/api/contracts-with-zscores | python -m json.tool | head -50
curl -s http://localhost:8000/api/statistics/extreme-values | python -m json.tool
curl -s http://localhost:8000/api/statistics/summary | python -m json.tool
curl -s http://localhost:8000/api/health/performance | python -m json.tool
```

### Pre-commit Checks (ALWAYS run before committing)
```bash
# Type check TypeScript - MUST pass before commits
cd dashboard && npx tsc --noEmit

# Test critical functionality  
python database_tools.py check

# Format Python code
black . --line-length=120 --exclude=".venv"

# Lint Python code
ruff check .

# Test performance (if working on Z-score optimization)
python scripts/test_performance.py
```

### Build & Test
```bash
# Build dashboard for production
cd dashboard && npm run build

# Run dashboard tests
cd dashboard && npm test                # Interactive mode
cd dashboard && CI=true npm test        # CI mode (single run)

# Test individual exchange modules (quick validation)
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"

# Install missing Python dependencies
pip install -r requirements.txt
pip install fastapi uvicorn psutil scipy black ruff  # Additional packages not in requirements.txt
```

### System Control
```bash
# Start everything
python start.py

# Individual components (for debugging)
python api.py                              # API server (port 8000)
cd dashboard && npm start                  # Dashboard (port 3000)
python main.py --loop --interval 30        # Data collector

# Check if services are running
curl http://localhost:8000/api/health      # Check API health
curl http://localhost:3000                 # Check dashboard

# Background process management (Claude Code specific)
/bashes                                    # List background processes
BashOutput tool with bash_id="<id>"       # Monitor output
KillBash tool with shell_id="<id>"        # Kill stuck process
```

### Data Operations
```bash
# Database management
python database_tools.py check              # Test connection
python database_tools.py clear --quick      # Clear all data (careful!)
python database_tools.py init               # Initialize database

# Historical backfill (30 days, all exchanges)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Fix data issues
python scripts/fix_funding_intervals.py     # Correct funding interval calculations
python scripts/hyperliquid_gap_filler.py    # Fill Hyperliquid gaps (hourly funding)

# Check data collector output
type data_collector.log                     # Windows
cat data_collector.log                      # Linux/Mac
```

## High-Level Architecture

### System Overview
- **Multi-Exchange Collection**: 4 active exchanges (Binance, KuCoin, Backpack, Hyperliquid)
- **Update Cycle**: 30-second real-time refresh with sequential API calls
- **Scale**: 1,260+ contracts across 600+ unique assets
- **Database**: PostgreSQL with 3 main tables (real-time, historical, statistics)
- **Backend**: FastAPI with 27+ endpoints (port 8000)
- **Frontend**: React/TypeScript dashboard with 30-second polling (port 3000)

### Data Flow
```
Exchange APIs → Rate Limiter → Normalization → PostgreSQL → FastAPI → React Dashboard
```

### Key Architectural Patterns

1. **Factory Pattern for Exchanges** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange` (`exchanges/base_exchange.py`)
   - Easy to add new exchanges by implementing `fetch_data()` and `normalize_data()`

2. **Rate Limiting & Sequential Collection** (`config/sequential_config.py`)
   - Staggered API calls: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s), Kraken (240s)
   - Prevents API throttling across exchanges

3. **Symbol Normalization** (Critical for data consistency)
   - Each exchange normalizes to base assets in `normalize_data()` method
   - Examples: `1000SHIB` → `SHIB`, `kPEPE` → `PEPE`, `XBTUSDTM` → `BTC`
   - Handles prefixes: numeric (`1000`, `10000`, `1000000`), letter (`k`), special (`1MBABYDOGE`)

4. **Database Strategy**
   - UPSERT operations prevent duplicates
   - Composite indexes on (exchange, symbol) for performance
   - Real-time table cleared and repopulated every 30 seconds
   - Historical table uses unique constraint on (exchange, symbol, funding_time)

5. **Dashboard Updates**
   - Components poll API every 30 seconds (synchronized with collector)
   - No WebSocket implementation - uses polling for simplicity
   - Virtual scrolling for large datasets (react-window for Z-score grid)

### Exchange-Specific Normalization

#### Binance
- Prefixes handled: `1000`, `1000000`, `1MBABYDOGE`
- Examples: `1000SHIBUSDT` → `SHIB`, `1000000MOGUSDT` → `MOG`
- Special case: `1MBABYDOGEUSDT` → `BABYDOGE` (1M = 1 Million denomination)

#### KuCoin
- Prefixes checked in order: `1000000`, `10000`, `1000`, `1MBABYDOGE`
- XBT → BTC normalization for Bitcoin contracts
- Special case: `1000XUSDTM` → `X` (1000X is X token with 1000x denomination)

#### Backpack
- Prefix handled: `k` (e.g., `kBONK_USDC_PERP` → `BONK`)
- All contracts use USDC margin and 1-hour funding

#### Hyperliquid
- Prefix handled: `k` (e.g., `kPEPE` → `PEPE`)
- DEX with 1-hour funding intervals for all contracts
- Contract names are simple (e.g., "BTC" not "BTCUSDT")

## Current Status: Z-Score System

### Performance Status ✅ OPTIMIZED
- **Z-score Calculation**: 792ms (target <1s) ✅ ACHIEVED
- **API Response**: 289ms with caching (target <100ms) ✅ Acceptable
- **Database Query**: 17ms (excellent) ✅
- **Zone-based Updates**: 68 active (30s), 1,197 stable (2min) ✅

### System Components
- **Database**: ✅ `funding_statistics` table with 1,265 contracts
- **Backend**: ✅ Optimized with parallel processing, connection pooling
- **API Endpoints**: ✅ All working with caching
  - `/api/contracts-with-zscores` - All contracts with Z-scores
  - `/api/statistics/extreme-values` - Extreme deviations
  - `/api/statistics/summary` - System statistics
  - `/api/health/performance` - Performance metrics
- **Frontend**: ⏳ `ContractZScoreGrid.tsx` not yet implemented

### Z-Score UI Requirements (Z_score.md lines 1083-1118)
When implementing the frontend component:
1. **FLAT LIST** - 1,260 individual contracts, NO asset grouping
2. **Virtual Scrolling REQUIRED** - Must use react-window
3. **Blue-Orange Colors ONLY** - NO red/green colors
4. **Primary Sort by |Z-score|** - Descending by absolute value
5. **Dynamic Row Heights** - 40px standard, 120px for |Z| ≥ 2.0
6. **New Component** - ContractZScoreGrid.tsx, NOT modifying AssetFundingGrid

See `Z_score.md` for complete specification, `tasklist.md` for implementation history.

## Performance Testing & Monitoring

```bash
# Run comprehensive performance tests
python scripts/test_performance.py

# Check performance metrics endpoint
curl -s http://localhost:8000/api/health/performance | python -m json.tool

# Monitor Z-score calculation time
python -c "
import time
from utils.zscore_calculator import ZScoreCalculator
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='exchange_data', user='postgres', password='postgres123')
calc = ZScoreCalculator(conn)
start = time.time()
calc.process_all_contracts()
print(f'Z-score calculation: {time.time()-start:.2f}s')
conn.close()
"

# Check zone distribution (active vs stable)
python -c "
from database.postgres_manager import PostgresManager
import pandas as pd
db = PostgresManager()
df = pd.read_sql('SELECT update_zone, COUNT(*) as count FROM funding_statistics GROUP BY update_zone', db.conn)
print(df)
"
```

## Testing Individual Components

```bash
# Quick validation of all exchanges
python -c "
from exchanges.exchange_factory import ExchangeFactory
factory = ExchangeFactory({'binance': True, 'kucoin': True, 'backpack': True, 'hyperliquid': True})
for name, exchange in factory.exchanges.items():
    try:
        data = exchange.fetch_data()
        print(f'{name}: {len(data)} contracts - OK')
    except Exception as e:
        print(f'{name}: FAILED - {e}')
"

# Test API endpoints
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/statistics | python -m json.tool
curl -s http://localhost:8000/api/contracts-with-zscores | python -m json.tool | head -50

# Check Z-score extreme values
python -c "
from database.postgres_manager import PostgresManager
import pandas as pd
db = PostgresManager()
query = 'SELECT exchange, symbol, current_z_score, current_percentile FROM funding_statistics WHERE ABS(current_z_score) > 2 ORDER BY ABS(current_z_score) DESC LIMIT 10'
df = pd.read_sql(query, db.conn)
print(df)
"
```

## Data Completeness Tools

### Check Data Completeness
```bash
# Generate completeness report
python data_completeness.py

# Test completeness calculation
python test_completeness_implementation.py

# Retry incomplete contracts
python scripts/retry_incomplete_contracts.py

# View completeness metrics in database
python -c "
from database.postgres_manager import PostgresManager
import pandas as pd
db = PostgresManager()
query = 'SELECT exchange, symbol, data_points, expected_points, completeness_percentage FROM funding_statistics WHERE completeness_percentage < 80 LIMIT 10'
df = pd.read_sql(query, db.conn)
print(df)
"
```

## Database Schema

### Main Tables
```sql
-- Real-time funding rates
exchange_data (
    exchange, symbol, base_asset, quote_asset, 
    funding_rate, funding_interval_hours, apr,
    index_price, mark_price, open_interest, last_updated
)

-- Historical funding rates (30-day rolling window)
funding_rates_historical (
    exchange, symbol, base_asset, quote_asset,
    funding_rate, funding_interval_hours, apr,
    index_price, mark_price, open_interest,
    funding_time, created_at
)

-- Z-score statistics (1,260+ contracts)
funding_statistics (
    exchange, symbol, current_z_score, current_percentile,
    mean_funding_rate, std_funding_rate,
    min_funding_rate, max_funding_rate,
    data_points, expected_points, completeness_percentage,
    last_updated
)
```

## Common Pitfalls & Solutions

### Symbol Normalization Issues
- **Problem**: Duplicate assets like "1000SHIB" and "SHIB" appearing separately
- **Solution**: Check exchange's `normalize_data()` method handles all prefix patterns
- **Test**: `python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); data=e.fetch_data(); normalized=e.normalize_data(data); print(set(d['base_asset'] for d in normalized))"`

### Data Collector Not Starting
- **Problem**: `start.py` shows collector failed
- **Solution**: Check `data_collector.log` for errors, verify `main.py` exists
- **Manual start**: `python main.py --loop --interval 30`

### TypeScript Errors
- **Problem**: Dashboard won't build
- **Solution**: Run `cd dashboard && npx tsc --noEmit` to see all errors
- **Common fix**: Missing type definitions for API responses

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Linux/Mac
lsof -i :8000
kill -9 <process_id>
```

### Dashboard Refresh Issues
- **Problem**: Dashboard constantly refreshing or stuck at backfill progress
- **Solution**: Delete `.backfill.status` and `.unified_backfill.status` files
- **Root cause**: Backfill status files with incomplete state

### Missing Python Dependencies
- **Problem**: Import errors when starting API or collector
- **Solution**: Install all required packages
```bash
pip install -r requirements.txt
pip install fastapi uvicorn psutil scipy black
```

### Z-Score Performance Issues
- **Problem**: Z-score calculation or API too slow
- **Solution**: 
  1. Run performance test: `python scripts/test_performance.py`
  2. Check zone distribution: More than 100 active contracts slows updates
  3. Verify connection pooling is active in logs
  4. Check cache hit rates at `/api/health/performance`
- **Validation**: 
```bash
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='exchange_data', user='postgres', password='postgres123')
cur = conn.cursor()
cur.execute('SELECT symbol, current_z_score, current_percentile FROM funding_statistics WHERE symbol = \'REDUSDT\'')
print(cur.fetchone())
conn.close()
"
```

## Environment Variables
Required `.env` file in project root:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

## Important Files for Understanding the Codebase

### Core System Files
- `start.py` - One-command system orchestrator
- `api.py` - FastAPI backend with all endpoints
- `main.py` - Data collection coordinator
- `database/postgres_manager.py` - All database operations
- `exchanges/base_exchange.py` - Abstract base for all exchanges
- `exchanges/exchange_factory.py` - Exchange instance management

### Configuration
- `config/settings.py` - Central configuration
- `config/sequential_config.py` - Collection timing configuration
- `.env` - Environment variables (create from .env.example)

### Dashboard
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main grid component with percentile display
- `dashboard/src/components/Grid/ContractZScoreGrid.tsx` - Z-score grid (to be created)
- `dashboard/src/services/api.ts` - API client with ContractDetails interface including percentiles

### Documentation
- `README.md` - Comprehensive project documentation
- `Z_score.md` - Complete Z-score implementation specification
- `tasklist.md` - Current implementation progress tracking

## Git Workflow Reminders

When creating commits:
1. **ALWAYS run type check first**: `cd dashboard && npx tsc --noEmit`
2. Format Python code: `black . --line-length=120 --exclude=".venv"`
3. Lint Python code: `ruff check .`
4. Test critical functionality: `python database_tools.py check`
5. Performance test (if working on Z-score): `python scripts/test_performance.py`
6. Use batch git commands when checking status
7. **NEVER commit unless explicitly asked by the user**

## Files to Never Commit
- `.unified_backfill.status`, `.backfill.status` - Backfill progress tracking
- `.unified_backfill.lock` - Backfill lock file
- `data_collector.log` - Collector output (can grow large)
- `temp_data.json` - Temporary data storage
- `.env` - Environment secrets (use .env.example as template)
- `node_modules/` - NPM packages
- `__pycache__/` - Python bytecode
- `.venv/` - Python virtual environment

## APR Calculation Formula

APR (Annual Percentage Rate) is calculated based on funding interval:
```python
if funding_interval_hours == 1:
    apr = funding_rate * 8760 * 100  # 365 * 24
elif funding_interval_hours == 2:
    apr = funding_rate * 4380 * 100  # 365 * 24 / 2
elif funding_interval_hours == 4:
    apr = funding_rate * 2190 * 100  # 365 * 24 / 4
elif funding_interval_hours == 8:
    apr = funding_rate * 1095 * 100  # 365 * 24 / 8
```

## Performance Considerations

### Database Optimization
- Indexes are crucial for performance with 1,240+ contracts
- Materialized views used for expensive aggregations
- Connection pooling handles concurrent requests
- UPSERT operations prevent duplicate key errors

### Frontend Optimization
- Virtual scrolling (react-window) required for Z-score grid
- React.memo for component optimization
- Debounced search inputs (300ms delay)
- Lazy loading for expanded contract details

### API Response Times
- Target: <100ms for most endpoints
- Heavy queries use materialized views
- Batch processing for multiple symbols
- Async request handling with FastAPI

## Key Utils and Helpers

### Performance and Optimization
- `utils/zscore_calculator.py` - Z-score calculation engine (integrated into main.py)
- `utils/zscore_calculator_optimized.py` - Optimized version (in development)
- `utils/rate_limiter.py` - API rate limiting to prevent throttling
- `utils/health_tracker.py` - System health monitoring
- `utils/data_validator.py` - Data validation utilities
- `utils/backfill_completeness.py` - Data completeness tracking

### Scripts for Maintenance
- `scripts/unified_historical_backfill.py` - Historical data backfill (30 days)
- `scripts/fix_funding_intervals.py` - Fix incorrect funding intervals
- `scripts/retry_incomplete_contracts.py` - Retry failed data fetches
- `scripts/test_performance.py` - Performance benchmarking
- `scripts/fix_data_pipeline.py` - Fix pipeline issues

## Project Status & Active Development

### Current System State
- **Production Ready**: Core functionality is stable and working
- **Active Contracts**: 1,260+ perpetual futures across 4 exchanges
- **Data Collection**: Running 24/7 with 30-second updates
- **Historical Data**: 30-day rolling window with 269,381+ records
- **Dashboard**: Fully functional with real-time updates

### Z-Score System Status
- ✅ Database table (`funding_statistics`) with 1,265 contracts
- ✅ Backend calculator optimized (792ms, target <1s achieved)
- ✅ Zone-based updates (68 active @ 30s, 1,197 stable @ 2min)
- ✅ API endpoints with caching (5s TTL for contracts, 10s for summary)
- ✅ Performance monitoring at `/api/health/performance`
- ✅ React dependencies (react-window) installed
- ⏳ Dedicated Z-score grid component (`ContractZScoreGrid.tsx`) not yet implemented
- See `tasklist.md` for optimization history

### Known Issues & Limitations
- Dashboard uses polling instead of WebSockets (by design for simplicity)
- No automated tests for Python code
- Backfill status files can occasionally get stuck (delete manually)
- Z-score frontend component (ContractZScoreGrid.tsx) not yet implemented
- Dashboard may show "Loading..." if API/collector not running
- Windows may have Unicode encoding issues (check for 'charmap' errors)