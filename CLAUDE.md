# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a multi-exchange cryptocurrency funding rate aggregation and arbitrage detection system that tracks 2,275 perpetual contracts across 8 exchanges (Binance, KuCoin, Backpack, Hyperliquid, Aster, Drift, Lighter, ByBit). The system collects real-time funding rates every 30 seconds, maintains 30-day historical data, calculates Z-scores for statistical analysis, and identifies cross-exchange arbitrage opportunities.

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
- **Testing**: No formal unit test framework. Use manual testing and type checking:
  - Python: `python -m py_compile <file.py>` for syntax checking
  - React: `npx tsc --noEmit` for TypeScript checking
  - API: Use curl or http://localhost:8000/docs for endpoint testing
  - **ALWAYS delete test files after tests complete** - No test artifacts should remain
- **Imports**: Check if packages exist in requirements.txt or package.json before using
- **NO COMMENTS**: Do not add code comments unless explicitly requested
- **NO EMOJIS**: Never use emojis in code, commits, or documentation unless explicitly requested
- **EVIDENCE-BASED DOCUMENTATION**: All numbers and statistics in documentation must be backed by verifiable evidence (API responses, database queries, or code inspection)
- **ASK BEFORE FINALIZING**: Always ask for confirmation before presenting the final plan for any multi-step task

### Required Python Packages
**Core packages** in `requirements.txt` (required for data collection):
- pandas, requests, psycopg2-binary, numpy, python-dotenv
- aiohttp, asyncio-throttle, redis

**Additional packages** needed for full system functionality (NOT in requirements.txt):
```bash
pip install fastapi uvicorn psutil scipy websockets
```

**Note**: These additional packages are REQUIRED to run the API server (`api.py`), Z-score calculator (`utils/zscore_calculator.py`), and WebSocket features. If you only need data collection (`main.py`), the core packages are sufficient.

### Windows-Specific Notes (CRITICAL for Windows Development)

**Command Equivalents:**
```bash
# File Operations
cat file.txt        →  type file.txt
ls -la              →  dir
rm -rf folder       →  rmdir /s /q folder
cp file dest        →  copy file dest
mv file dest        →  move file dest

# Process Management
kill -9 <pid>       →  taskkill /PID <pid> /F
kill -9 $(lsof -t -i:8000)  →  netstat -ano | findstr :8000 (get PID) → taskkill /PID <pid> /F
ps aux | grep python →  tasklist | findstr "python"

# Python
python3             →  python
pip3                →  pip

# Port Checking
lsof -i :8000       →  netstat -ano | findstr ":8000"
```

**Background Process Management:**
start.py uses `CREATE_NEW_PROCESS_GROUP` flag for Windows compatibility (line 354). Processes write to dedicated log files in project root.

**Log Files (Essential for Debugging):**
```bash
# View logs
type data_collector.log | findstr "ERROR"     # Check for errors
type spread_collector.log | findstr "WARNING" # Check warnings
Get-Content data_collector.log -Tail 20 -Wait # Real-time (PowerShell)

# Clear logs when too large
type nul > data_collector.log
type nul > spread_collector.log
type nul > zscore_calculator.log
```

**Process Monitoring:**
```bash
# Find all Python processes
tasklist | findstr "python"

# Find specific service ports
netstat -ano | findstr ":8000"   # API server
netstat -ano | findstr ":3000"   # React dashboard
netstat -ano | findstr ":5432"   # PostgreSQL
netstat -ano | findstr ":6379"   # Redis

# Kill specific process
taskkill /PID 12345 /F

# Kill all Python processes (CAUTION!)
taskkill /F /IM python.exe

# Kill process on specific port
FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr ":8000"') DO taskkill /PID %P /F
```

**Docker Desktop on Windows:**
```bash
# Start Docker Desktop programmatically
start "Docker Desktop" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Check if Docker is running
docker info

# Common Docker Desktop issues
# 1. WSL 2 not enabled: Enable in Windows Features
# 2. Hyper-V conflicts: Disable Hyper-V if using VirtualBox
# 3. File sharing: Add project directory to Docker Desktop shared folders
```

**Path Handling (CRITICAL for Cross-Platform Code):**
```python
# ALWAYS use Path objects for file paths
from pathlib import Path

# Good (works on both Windows and Linux)
log_file = Path("data_collector.log")
config_file = Path("config") / "settings.py"

# Bad (breaks on Windows)
log_file = "logs/data_collector.log"  # Should be: logs\data_collector.log on Windows
```

**Common Windows Pitfalls:**
1. **Encoding Issues**: start.py sets UTF-8 encoding (line 34-39) to prevent codec errors
2. **Path Separators**: See "Path Handling" section above for proper cross-platform path usage
3. **Process Cleanup**: Windows doesn't auto-kill child processes; use `taskkill` manually
4. **Port Binding**: Windows holds ports longer than Linux; wait 30s before restarting services
5. **File Locks**: Windows locks open files; close log files before clearing them
6. **Line Endings**: Git auto-converts CRLF↔LF; ensure `.gitattributes` is configured correctly

## Essential Commands

### Quick Start
```bash
# Start everything with one command (orchestrates all services)
python start.py

# This automatically:
# - Checks prerequisites (Python, Node, Docker)
# - Starts PostgreSQL, Redis, pgAdmin containers
# - Starts API server (port 8000), React dashboard (port 3000)
# - Starts data collector (30-second updates to data_collector.log)
# - Backfills 30-day arbitrage spread history (one-time, ~60s)
# - Starts spread collector (ongoing arbitrage tracking → spread_collector.log)
# - Starts Z-score calculator (funding statistics → zscore_calculator.log)
# - Starts background historical refresh (30-day window)

# Shutdown everything
python shutdown_dashboard.py

# Clean shutdown of specific services
taskkill /PID <pid> /F       # Windows: Kill specific process
docker-compose down           # Stop all Docker containers
```

### Pre-commit Checks (MUST run before any commit)
```bash
cd dashboard && npx tsc --noEmit              # TypeScript check (REQUIRED)
python database_tools.py check                # Database connectivity (optional)
python -m py_compile api.py main.py          # Python syntax check
python -m py_compile utils/*.py exchanges/*.py scripts/*.py  # Check all Python modules
```

### Development & Testing
```bash
# Individual component startup
python api.py                                 # API server only (port 8000)
cd dashboard && npm start                     # Dashboard only (port 3000)
python main.py --loop --interval 30          # Data collector only
python utils/zscore_calculator.py            # Z-score calculator only
python utils/arbitrage_scanner.py            # Arbitrage scanner only

# Build & Test
cd dashboard && npm run build                # Production build
cd dashboard && npx tsc --noEmit            # TypeScript type checking

# Database Operations
python database_tools.py check               # Test connection
python database_tools.py clear --quick       # Clear all data (CAUTION)
python database_tools.py status              # Show detailed table stats
python scripts/unified_historical_backfill.py --days 30 --parallel  # Backfill all exchanges
python scripts/collect_spread_history.py     # Collect arbitrage spread history
python scripts/backfill_arbitrage_spreads_v2.py  # V2 backfill (more efficient)
python scripts/retry_incomplete_contracts.py # Retry failed contract fetches
python scripts/fill_recent_gaps.py           # Fill gaps in historical data

# Contract Health Monitoring
python utils/contract_monitor.py --report-only  # Check for stale/delisted contracts
python utils/contract_monitor.py --dry-run     # Preview changes without applying
python utils/contract_monitor.py             # Apply changes (marks stale contracts)
```

For process monitoring commands (tasklist, netstat), see "Process Monitoring" in Windows-Specific Notes.

## High-Level Architecture

### System Overview
- **Scale**: 2,275 contracts across 660+ unique assets from 8 exchanges
  - Binance: 589 contracts (379 4h, 167 8h, 7 1h) + 36 COIN-M (8h)
  - KuCoin: 519 contracts (mixed 1h, 2h, 4h, 8h intervals)
  - ByBit: 663 contracts (639 linear USDT + 24 inverse perpetuals)
  - Hyperliquid: 182 contracts (100% 1h DEX funding)
  - Aster: 120 contracts (4h DEX funding)
  - Lighter: 91 contracts (8h CEX-standard equivalent)
  - Backpack: 63 contracts (100% 1h funding)
  - Drift: 48 contracts (1h Solana DEX)
- **Update Cycle**: 30-second real-time refresh with parallel collection (default) or sequential mode (optional)
- **Database**: PostgreSQL with 6 tables (real-time, historical, statistics, metadata, arbitrage, funding_statistics)
- **Backend**: FastAPI (port 8000) with 35+ endpoints, WebSocket support, Redis caching
- **Frontend**: React 19/TypeScript with 30-second polling and WebSocket integration
- **Performance**: Z-scores <1s for all contracts, API responses <100ms, WebSocket latency <50ms

### Critical Dependency Chain (MUST READ FIRST!)

**Process Startup Order (CRITICAL - Breaking this causes failures!):**

```
Phase 1: Infrastructure Layer
├── PostgreSQL (localhost:5432) ────────────────┐
│   - MUST start first                          │
│   - Database: exchange_data                   │
│   - Auto-creates schema on first API startup  │
│                                                ▼
└── Redis (localhost:6379) ─────────────────────┤ [Optional but recommended]
    - 512MB memory, LRU eviction                │
    - Fallback: SimpleCache (in-memory)         │
                                                 │
Phase 2: Application Layer                      │
├── npm install (if node_modules missing) ◄─────┤
│                                                │
├── API Server (api.py:178) ◄──────────────────┘
│   - Port 8000
│   - Creates database schema automatically
│   - Initializes connection pool (5-20 connections)
│   - BLOCKS until PostgreSQL ready
│
├── React Dashboard (npm start)
│   - Port 3000
│   - REQUIRES API server running
│   - Opens browser automatically
│
└── Data Collector (main.py --loop --interval 30)
    - REQUIRES schema to exist
    - Logs to: data_collector.log
    - Updates database every 30s
    - Cache invalidation AFTER DB write

Phase 3: Background Analysis (start.py orchestrates all)
├── Arbitrage Backfill (one-time) ──────────────┐
│   - Populates 30-day spread history           │
│   - MUST complete before spread collector     │
│   - Duration: ~60 seconds                     │
│                                                ▼
├── Spread Collector (continuous) ◄─────────────┘
│   - Logs to: spread_collector.log
│   - REQUIRES backfill data to exist
│   - Updates arbitrage_spreads table
│
├── Z-Score Calculator (continuous)
│   - Logs to: zscore_calculator.log
│   - Updates funding_statistics table
│   - Zone-based: active (30s), stable (2min)
│
└── Historical Refresh (background thread)
    - 30-day rolling window maintenance
    - Non-blocking background operation
```

**Critical Implementation Details:**
1. **Schema Creation**: api.py line 171-181 creates connection pool, triggers schema auto-creation
2. **Background Processes**: start.py uses CREATE_NEW_PROCESS_GROUP (line 354) for Windows compatibility
3. **Cache Invalidation**: main.py line 395-414 clears cache AFTER database updates, not before
4. **Log Files**: Each background process has its own log file for debugging
5. **Process Dependencies**: Data collector depends on schema; spread collector depends on backfill

**Why this exact order matters:**
- PostgreSQL must start first (everything depends on database)
- Schema creation by API is prerequisite for data collector
- Arbitrage backfill must complete before spread collector starts
- Cache invalidation happens after DB writes to prevent stale data
- Background processes are independent and can be restarted individually
- Database schema is created on first API startup (api.py:171-181)
- Data collector requires existing schema to insert data (main.py:168-178)
- Spread collector needs historical arbitrage_spreads data from backfill
- Background processes run independently with their own log files
- Cache invalidation occurs AFTER database updates (main.py:395-414)

### Data Flow Architecture
```
Exchange APIs → Rate Limiter → Normalization → PostgreSQL → FastAPI → React Dashboard
                                                    ↓            ↓         ↓
                                             Z-Score Calc   Redis     WebSocket (/ws)
                                                    ↓      (5s/10s)   Broadcasting
                                         funding_statistics  TTL         ↓
                                                    ↓                Real-time
                                            contract_metadata      Updates
                                                    ↓
                                            arbitrage_spreads
```

### Module Dependency Map

**Core Module Dependencies (Understanding the Import Chain):**

```
main.py (Data Collection Orchestrator)
├── config/settings.py ──────────────────── System configuration
├── config/validator.py ─────────────────── Config validation
├── exchanges/exchange_factory.py ───────┐
│   ├── exchanges/base_exchange.py       │ Factory Pattern
│   ├── exchanges/binance_exchange.py    │ All exchange modules
│   ├── exchanges/kucoin_exchange.py     │ inherit from BaseExchange
│   ├── exchanges/backpack_exchange.py   │
│   ├── exchanges/hyperliquid_exchange.py│
│   ├── exchanges/aster_exchange.py      │
│   ├── exchanges/drift_exchange.py      │
│   ├── exchanges/lighter_exchange.py    │
│   └── exchanges/bybit_exchange.py ─────┘
├── data_processing/data_processor.py ───── APR calculation, normalization
├── database/postgres_manager.py ────────── Database CRUD operations
├── utils/contract_metadata_manager.py ──── Contract lifecycle tracking
├── utils/zscore_calculator.py ──────────── Statistical analysis
├── utils/redis_cache.py ────────────────── Cache invalidation
├── utils/backfill_completeness.py ──────── Data quality validation
└── utils/logger.py ─────────────────────── Logging configuration

api.py (FastAPI Backend)
├── database/postgres_manager.py ────────── Database connection pool
├── config/settings_manager.py ──────────── Dynamic settings management
├── config/settings.py ──────────────────── Current configuration
├── utils/redis_cache.py ────────────────── API response caching
├── utils/arbitrage_scanner.py ──────────── Cross-exchange opportunities
└── psycopg2.pool.ThreadedConnectionPool ─ 5-20 concurrent connections

start.py (Startup Orchestrator)
├── subprocess (Popen) ──────────────────── Background process management
│   ├── api.py (port 8000)
│   ├── dashboard/npm start (port 3000)
│   ├── main.py --loop --interval 30
│   ├── scripts/backfill_arbitrage_spreads_v2.py
│   ├── scripts/collect_spread_history.py
│   ├── utils/zscore_calculator.py
│   └── scripts/unified_historical_backfill.py
└── threading.Thread ────────────────────── Background historical refresh

utils/zscore_calculator.py
├── database connection ─────────────────── Direct psycopg2 connection
├── funding_statistics table ───────────── Updates Z-scores
└── Zone-based processing ───────────────── Active (|Z|>2): 30s, Stable: 2min

utils/arbitrage_scanner.py
├── database/postgres_manager.py ────────── Funding rate queries
├── arbitrage_spreads table ─────────────── Historical opportunity tracking
└── utils/redis_cache.py ────────────────── 30s TTL for opportunities

exchanges/exchange_factory.py
├── config/settings.EXCHANGES ───────────── Enabled/disabled exchanges
├── utils/rate_limiter.py ───────────────── API throttling
└── BaseExchange implementations ────────── Dynamic exchange loading
```

**Import Rules**:
1. **No Circular Imports**: Factory pattern prevents circular dependencies
2. **Config First**: settings.py loaded before any exchange modules
3. **Database Pooling**: api.py creates pool, other modules use direct connections
4. **Cache Independence**: RedisCache has automatic fallback, no hard dependency
5. **Process Isolation**: Background processes don't share Python instances

**Common Import Errors**:
- `ModuleNotFoundError: config.settings` → Run from project root, not subdirectory
- `psycopg2.OperationalError` → PostgreSQL not running or wrong credentials
- `ImportError: fastapi` → Run `pip install fastapi uvicorn psutil scipy`

### Frontend Architecture (React Dashboard)

**Tech Stack**: React 19, TypeScript, TailwindCSS, React Router

**Key Architectural Patterns**:

1. **Custom Hooks for State Management**
   - `useExchangeFilter`: Orchestrates filter state, persistence, and data filtering
   - `useFilterPersistence`: Auto-saves filter state to localStorage
   - `useFilterURL`: Syncs filter state with URL parameters for shareability

2. **Filter Architecture** (`dashboard/src/components/Grid/ExchangeFilter/`)
   ```
   User Action → updateFilterState() → React State Update
       ↓                                        ↓
   Parallel Triggers:                    [Effects Fire]
   ├─→ localStorage.setItem()              ↓         ↓
   ├─→ URL replaceState()         useFilterPersistence  useFilterURL
   └─→ useMemo recomputes                  ↓         ↓
       filteredData                   Auto-save   URL Sync
   ```

3. **Performance Optimizations**
   - **useMemo**: Expensive computations (filtering, sorting) cached between renders
   - **useCallback**: Stable function references prevent unnecessary re-renders
   - **On-demand data fetching**: Contracts fetched only when asset row expanded
   - **Debounced search**: 300ms debounce on search input to reduce API calls

4. **Filter State Priority**
   ```
   URL Parameters > localStorage > DEFAULT_FILTER_STATE

   On component mount:
   1. Check URL query params (?exchanges=binance,kucoin)
   2. If URL empty, load from localStorage
   3. If localStorage empty, use DEFAULT_FILTER_STATE
   ```

5. **Common React Patterns Used**
   - **Inline filtering with useMemo**: Simple filters applied once per state change
   - **Computed maps with useMemo**: Pre-filter data once, render many times (e.g., filteredContractsMap)
   - **State synchronization**: Multiple persistence mechanisms triggered in parallel
   - **Controlled components**: All form inputs controlled by React state

**Critical Frontend Files**:
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` (main grid, line 488: uses filteredContractsMap)
- `dashboard/src/hooks/useExchangeFilter.ts` (filter orchestration hub)
- `dashboard/src/utils/filterAlgorithms.ts` (pure filter functions)
- `dashboard/src/constants/exchangeMetadata.ts` (exchange config: colors, contracts, intervals)
- `dashboard/src/types/exchangeFilter.ts` (TypeScript interfaces for filter state)

**Frontend Development Guidelines**:
- **Adding new filters**: Update `ExchangeFilterState` type AND `DEFAULT_FILTER_STATE`
- **Filter functions**: Must be pure (no side effects) to work correctly with useMemo
- **Adding exchanges**: Update `EXCHANGE_METADATA` with color, contract count, intervals, orderPriority
- **Expanded details**: ALWAYS use filtered data (e.g., `filteredContractsMap`), never raw cache
- **Performance**: Use `useMemo` for expensive computations, `useCallback` for event handlers

**Common Frontend Bugs to Avoid**:
- **Filter not applying to expanded rows**: Expanded contract details must use filtered data, not raw `contractsData`
- **Stale closures in effects**: Include all dependencies in useEffect/useMemo dependency arrays
- **Infinite re-render loops**: Ensure setState calls are properly guarded or in effects
- **Memory leaks**: Always clean up subscriptions, timers, and event listeners in useEffect return

### Cache Invalidation Flow
The system maintains data freshness through automatic cache invalidation:
```
Data Update Cycle (every 30 seconds):
main.py fetches → Updates DB → Clears Cache → Next API Request → Cache Miss → Fresh DB Query → Cache Result
                                     ↓
                            _invalidate_cache()
                            (prevents stale data)
```

**Cache Architecture (Dual-Layer with Automatic Fallback):**
```
API Request → RedisCache.get() ─────────┐
                 ↓                      │
         [Redis Available?]            │
              ↓         ↓               │
            YES        NO               │
             ↓          ↓               │
       Redis Cache  SimpleCache        │
       (Primary)    (Fallback)         │
             ↓          ↓               │
             └─────┬────┘               │
                   ↓                    │
            [Cache Hit?] ───────────────┘
              ↓       ↓
            YES      NO
             ↓        ↓
        Return    Query DB
        Cached    Update Cache
         Data     Return Data
```

**Cache Behavior**:
- **Primary**: Redis cache (distributed, persistent across restarts)
  - Host: localhost:6379
  - Memory: 512MB with LRU eviction
  - Connection pool: Shared across processes
- **Fallback**: SimpleCache (in-memory, process-local)
  - Automatic fallback if Redis unavailable
  - No cross-process sharing
  - Dictionary-based with timestamp tracking
- **Invalidation Strategy**: Cache cleared AFTER database updates (not before) to prevent stale data
  - Triggered by: main.py line 395-414 (_invalidate_cache method)
  - Clears ALL keys to ensure consistency
  - Next request triggers fresh DB query
- **TTL Values**:
  - 5s: Individual contracts (api_cache.get with ttl_seconds=5)
  - 10s: Summary statistics (api_cache.get with ttl_seconds=10)
  - 25s: API endpoint responses (standardized across endpoints)
  - 30s: Arbitrage opportunities (matches data update cycle)

**Cache Implementation Details**:
- **Location**: utils/redis_cache.py defines RedisCache class
- **Initialization**: api.py line 158 creates global `api_cache = RedisCache()`
- **Health Check**: api_cache.is_available() tests Redis connection
- **Metrics**: api_cache.get_metrics() returns hit/miss ratios
- **Manual Clear**: api_cache.clear() removes all cached entries

### Contract Lifecycle Management
```
State Machine:
NEW → ACTIVE → STALE (24h) → INACTIVE (48h) → REMOVED
 ↓       ↓         ↓              ↓               ↓
Added  Normal   No Updates    is_active=false  Deleted from
to DB  Operation  Warning     Hidden in API    exchange_data

Reactivation: INACTIVE → ACTIVE (if contract returns)
```

### Core Architectural Patterns

1. **Exchange Factory Pattern** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange`
   - Must implement `fetch_data()` and `normalize_data()` methods
   - Factory creates instances: `factory = ExchangeFactory(settings)` then `factory.get_exchange(name)`
   - Handles rate limiting and error recovery

2. **Collection Strategy** (`config/sequential_config.py`)
   - **Default Mode**: Parallel collection using ThreadPoolExecutor (faster, higher API load)
   - **Optional Mode**: Sequential collection with staggered delays (rate-limit friendly)
   - Rate limits: Binance (40 req/s), KuCoin (30 req/s), Backpack (~20 req/s), Hyperliquid (10 req/s enforced)
   - Toggle via `ENABLE_SEQUENTIAL_COLLECTION` in `config/settings.py` (default: False)

3. **Symbol Normalization** - Exchanges use different conventions for leveraged tokens (see "Symbol Normalization Rules" below)

4. **Z-Score System** (`utils/zscore_calculator.py`)
   - **Zone-based updates**: Performance optimization strategy
   - Active zones (|Z|>2): Update every 30s (volatile, needs monitoring)
   - Stable zones (|Z|<2): Update every 2min (stable, less frequent updates)
   - **WHY**: Reduces database load by 60% while maintaining accuracy for important contracts

5. **Real-time Updates & Caching**
   - Polling-based updates (30-second intervals)
   - WebSocket real-time broadcasting at `/ws` endpoint
   - Performance monitoring via `/api/health/performance` endpoint
   - WebSocket auto-reconnect with exponential backoff

## Critical Business Logic

### APR Calculation Formula
```python
# Based on funding interval - NEVER modify without understanding impact
periods_per_year = (365 * 24) / funding_interval_hours
apr = funding_rate * periods_per_year * 100

# Example calculations:
# 8h interval (1,095 periods/year) → 0.01% funding rate = 10.95% APR
# 1h interval (8,760 periods/year) → 0.01% funding rate = 87.6% APR

# IMPORTANT: APRs are NOT directly comparable across different intervals!
# See "Exchange Summary" table below for specific intervals by exchange.
```

### Database Schema (Key Tables)
```sql
-- Real-time funding rates
exchange_data (exchange, symbol, funding_rate, apr, timestamp, UNIQUE(exchange, symbol))

-- Historical data with 30-day rolling window
funding_rates_historical (exchange, symbol, funding_rate, funding_time, UNIQUE(exchange, symbol, funding_time))

-- Z-score statistics
funding_statistics (exchange, symbol, current_z_score, mean_30d, std_dev_30d, UNIQUE(exchange, symbol))

-- Contract lifecycle tracking
contract_metadata (exchange, symbol, is_active, last_seen, first_seen, UNIQUE(exchange, symbol))

-- Cross-exchange arbitrage opportunities
arbitrage_spreads (asset, exchange_a, exchange_b, apr_spread, timestamp)
```

## Key API Endpoints

### Core Data
- `/api/funding-rates` - All contracts with pagination
- `/api/funding-rates-grid` - Asset-grouped cross-exchange view
- `/api/historical-funding-by-asset/{asset}?days=7` - Historical rates

### Analytics
- `/api/contracts-with-zscores` - Z-score data for all contracts
- `/api/arbitrage/opportunities?min_spread=0.001` - Arbitrage opportunities (v1)
- `/api/arbitrage/opportunities-v2?page=1&page_size=20` - Paginated arbitrage opportunities
- `/api/health/performance` - System performance metrics
- `/api/statistics/extreme-values` - Statistical outliers and extremes
- `/api/statistics/summary` - Overall system statistics

## Environment Configuration

### Required .env file
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123  # Must match docker-compose.yml
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Docker Services (docker-compose.yml)
For Windows-specific Docker Desktop startup commands and troubleshooting, see "Docker Desktop on Windows" in Windows-Specific Notes.

- **PostgreSQL**: Port 5432, database `exchange_data`
- **Redis**: Port 6379, 512MB memory limit, LRU eviction policy
- **pgAdmin**: Port 5050, web interface at http://localhost:5050
  - Login: admin@example.com / admin123
  - Pre-configured server: exchange_postgres

## Exchange-Specific Information

### Exchange Summary
| Exchange | Contracts | Funding Intervals | Rate Limit | Special Notes |
|----------|-----------|-------------------|------------|---------------|
| Binance | 589 | 8h (28.3%), 4h (64.4%), 1h (1.2%) + 36 COIN-M (8h) | 40 req/s | USD-M and COIN-M markets |
| KuCoin | 519 | 8h (39.4%), 4h (59.5%), 2h (0.2%), 1h (0.8%) | 30 req/s | XBT prefix for Bitcoin |
| ByBit | 663 | Mixed (1h, 2h, 4h, 8h) | 50 req/s | 639 linear USDT + 24 inverse perpetuals |
| Hyperliquid | 182 | 1h (100%) | 10 req/s | DEX with simple naming |
| Aster | 120 | 4h (default) | 40 req/s max | DEX with async/parallel fetching |
| Lighter | 91 | 8h (CEX-standard equivalent) | No published limit | Aggregator DEX with multi-exchange data |
| Backpack | 63 | 1h (100%) | ~20 req/s | Recently changed to all 1-hour |
| Drift | 48 | 1h (100%) | No strict limit | Solana-based DEX |

### Symbol Normalization Rules (Critical for Asset Grouping)

**Why these rules exist**: Exchanges use different conventions for leveraged/multiplier tokens. Without normalization, the same asset appears as multiple different assets in the dashboard.

- **Binance**:
  - `1000SHIB` → `SHIB` (price per 1000 tokens)
  - `1MBABYDOGE` → `BABYDOGE` (1M = 1 million multiplier)
  - `1000000MOG` → `MOG` (price per million)

- **KuCoin**:
  - `1000X` → `X` (careful: could be X token OR 1000x multiplier)
  - `kPEPE` → `PEPE` (k = thousand multiplier)
  - `10000CAT` → `CAT`
  - `1MBABYDOGE` → `BABYDOGE`

- **Backpack**: `kBONK_USDC_PERP` → `BONK`
- **Hyperliquid**: `kPEPE` → `PEPE`
- **Aster**: `1000FLOKI` → `FLOKI`, `kX` → `X`
- **Drift**: `XXX-PERP` → `XXX`, `1MBONK` → `BONK`
- **ByBit**: Uses baseCoin from API response with normalization:
  - `10000000SHIB` → `SHIB` (10 million multiplier)
  - `1000000BABYDOGE` → `BABYDOGE` (1 million multiplier)
  - `100000MOG` → `MOG` (100k multiplier)
  - `10000LADYS` → `LADYS` (10k multiplier)
  - `1000FLOKI` → `FLOKI` (1k multiplier)
- **Lighter**: Aggregates rates from multiple exchanges, normalizes with standard prefixes:
  - `1000000XXX` → `XXX`, `100000XXX` → `XXX`, `10000XXX` → `XXX`, `1000XXX` → `XXX`
  - `1MXXX` → `XXX` (1 million multiplier)
  - `100XXXX` → `XXX`, `kXXX` → `XXX`
  - Uses 8-hour CEX-standard equivalent rate format

### Exchange-Specific Implementation Details

#### ByBit (663 contracts)
**API Structure**:
- **V5 API**: Uses versioned V5 endpoints (`/v5/market/instruments-info`, `/v5/market/tickers`)
- **Dual Markets**: Separate linear (USDT) and inverse (USD) perpetual markets
- **Pagination**: Instruments API paginates with cursor-based system (limit: 1000 per page)
- **Rate Limit**: 50 requests/second

**Key Features**:
- **Linear Perpetuals (639 contracts)**: USDT and USDC-margined contracts
  - Funding intervals: 1h, 2h, 4h, 8h (mixed across different contracts)
  - Open Interest provided in USD value (`openInterestValue`)
  - Contract types: `LinearPerpetual`
- **Inverse Perpetuals (24 contracts)**: USD-margined contracts
  - Standard 8-hour funding intervals
  - Contract types: `InversePerpetual`
  - Coin-margined settlement

**Normalization Logic** (`exchanges/bybit_exchange.py` lines 190-209):
- Uses `baseCoin` field from API (not derived from symbol)
- Handles up to 8-digit multiplier prefixes (`10000000SHIB` → `SHIB`)
- APR calculation accounts for funding interval in minutes (converted to hours)

**Historical Data**:
- Endpoint: `/v5/market/funding/history`
- Limit: 200 records per request (requires pagination for 30-day backfill)
- Auto-detects category (linear vs inverse) based on symbol suffix

**Cache Strategy**:
- Instrument metadata cached during fetch for quick lookups
- Stores `fundingInterval`, `contractType`, `baseCoin`, `quoteCoin`

#### Lighter (91 contracts)
**Platform Type**: DEX Aggregator (aggregates funding from multiple CEXs)

**API Structure**:
- **Current Rates**: `/api/v1/funding-rates` returns all markets
- **Historical Data**: `/api/v1/fundings` with market_id-based queries
- **No Authentication**: Public REST API access
- **Base URL**: `https://mainnet.zklighter.elliot.ai`

**Key Features**:
- **Aggregated Rates**: Collects funding from Binance, OKX, Bybit, others
- **Filtered Output**: System filters to only use `'lighter'` exchange rates (not upstream sources)
- **Market IDs**: Each contract has unique numeric market_id (e.g., BTC=1, ARB=50)
- **Rate Format**: API returns rates already divided by 8 for CEX-standard alignment

**Normalization Logic** (`exchanges/lighter_exchange.py` lines 114-139):
- **Rate Conversion**: Divides API rate by 8 for CEX-standard 8-hour equivalent
  - Formula: `APR = (rate / 8) * 3 * 365 * 100` (3 payments per day)
- **Historical Rates**: Divides by 100 (API returns percentage, need decimal)
- Handles all standard multiplier prefixes (1000000, 100000, 10000, 1000, 1M, k)

**Historical Data**:
- **Resolution**: 1-hour granularity
- **Timestamp Format**: Unix timestamps (seconds)
- **Count Limit**: Up to 1000 records per request
- **API Response**: Returns `fundings` array with market_id, rate, timestamp

**Special Considerations**:
- **Market Metadata**: Must fetch current rates first to map market_ids to symbols
- **Symbol Format**: Returns without USDT suffix (adds `USDT` during normalization)
- **Delay**: 0.5s between API calls to avoid overwhelming the API

## Common Workflows

### Adding New Exchange
1. Create module in `exchanges/` inheriting from `BaseExchange`
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to `exchanges/exchange_factory.py`
4. Update `config/settings.py` EXCHANGES dict
5. Add to `config/sequential_config.py` schedule (if using sequential mode)
6. Test: `python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"`
7. Verify normalization: Check that assets group correctly in dashboard

### Verifying Exchange Data Collection
```bash
# Check individual exchanges
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"
python -c "from exchanges.bybit_exchange import ByBitExchange; e=ByBitExchange(); print(f'ByBit: {len(e.fetch_data())} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); print(f'Hyperliquid: {len(e.fetch_data())} contracts')"
python -c "from exchanges.aster_exchange import AsterExchange; e=AsterExchange(); print(f'Aster: {len(e.fetch_data())} contracts')"
python -c "from exchanges.lighter_exchange import LighterExchange; e=LighterExchange(); print(f'Lighter: {len(e.fetch_data())} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); print(f'Backpack: {len(e.fetch_data())} contracts')"
python -c "from exchanges.drift_exchange import DriftExchange; e=DriftExchange(); print(f'Drift: {len(e.fetch_data())} contracts')"

# Check all exchanges at once
python -c "from exchanges.exchange_factory import ExchangeFactory; from config.settings import EXCHANGES; factory=ExchangeFactory(EXCHANGES); [print(f'{ex}: {len(factory.get_exchange(ex).fetch_data())} contracts') for ex in ['binance','kucoin','bybit','hyperliquid','aster','lighter','backpack','drift']]"
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Dashboard Issues
- **"Dashboard stuck at loading"**:
  - Check if API server is running: `netstat -ano | findstr :8000`
  - Open browser network tab, look for failed API calls
  - Verify database is running: `docker ps | findstr postgres`

- **"Data not updating"**:
  - Check data collector: `type data_collector.log | findstr ERROR`
  - Verify main.py is running: `tasklist | findstr python`
  - Check last update time in dashboard header

#### Data Collection Issues
- **"Wrong funding rates displayed"**:
  - Symbol normalization issue - check exchange-specific rules
  - Verify funding interval calculations in exchange module
  - Check APR calculation (different intervals = different APRs)

- **"Missing contracts"**:
  - Check if marked inactive: `python utils/contract_monitor.py --report-only`
  - Verify exchange is enabled in `config/settings.py`
  - Test exchange directly (see verification commands above)

#### Performance Issues
- **"High memory usage"**:
  - Redis exceeding 512MB limit (check: `docker stats redis`)
  - Too many log files (clear with: `type nul > data_collector.log`)
  - Z-score calculator memory leak (restart: `python utils/zscore_calculator.py`)

- **"Slow API responses"**: See "Performance Monitoring" section below for detailed diagnostics and thresholds

#### Process Management Issues
- **"Multiple API instances on port 8000"**:
  ```bash
  netstat -ano | findstr :8000    # Find PIDs
  taskkill /PID <pid> /F          # Kill duplicates
  ```

- **"Background processes not starting"**:
  - Check CREATE_NEW_PROCESS_GROUP flag in start.py
  - Verify Python path is correct
  - Check individual log files for errors

### Log Files and Monitoring

For log file locations and viewing commands, see "Log File Locations" in the Windows-Specific Notes section above.

#### Background Process Logs - What to Look For
| Log File | Purpose | Key Indicators |
|----------|---------|----------------|
| `data_collector.log` | Real-time collection | ERROR, "Failed to fetch", rate limit messages |
| `spread_collector.log` | Arbitrage tracking | WARNING, "No opportunities", database errors |
| `zscore_calculator.log` | Statistics | "Zone update", calculation times, memory usage |

#### Monitoring Commands
```bash
# Check for stale data
python -c "import requests; r=requests.get('http://localhost:8000/api/statistics/summary'); print(r.json()['last_update'])"

# Monitor cache performance
curl http://localhost:8000/api/health/performance | python -m json.tool | findstr "hit_rate"
```

## Performance Monitoring

### Performance Thresholds
| Metric | Target | Warning | Critical | Action if Exceeded |
|--------|--------|---------|----------|-------------------|
| API Response Time | <100ms | 100-200ms | >200ms | Check cache, database indexes |
| Database Query Time | <50ms | 50-100ms | >100ms | Verify indexes, connection pool |
| Z-score Calculation | <1000ms | 1-2s | >2s | Reduce zone update frequency |
| Cache Hit Rate | >50% | 30-50% | <30% | Increase TTL, check invalidation |
| WebSocket Latency | <50ms | 50-100ms | >100ms | Check network, reduce broadcast size |

### Performance Monitoring Tools
```bash
# System performance overview
curl http://localhost:8000/api/health/performance | python -m json.tool

# Monitor API latency
python -c "import requests, time; start=time.time(); requests.get('http://localhost:8000/api/funding-rates'); print(f'Response time: {(time.time()-start)*1000:.2f}ms')"

# Database query performance
python database_tools.py check

# Redis cache metrics
python -c "from utils.redis_cache import RedisCache; c=RedisCache(); print(c.get_metrics())"

# Z-score performance
python -c "import requests; r=requests.get('http://localhost:8000/api/health/performance'); print(f\"Z-score calc: {r.json()['zscore_calculation_ms']}ms\")"
```

### Performance Optimization Tips
1. **Database**: Create indexes on (exchange, symbol, funding_time) if missing
2. **Redis**: Monitor memory (`docker stats redis`), increase limit if needed
3. **Z-scores**: Adjust zone thresholds in `zscore_calculator.py`
4. **API**: Enable response compression in FastAPI
5. **Frontend**: Use React.memo for expensive components

## Files Never to Commit
- **Log Files** (can exceed 100MB):
  - `data_collector.log`, `spread_collector.log`, `zscore_calculator.log`
- **Status/Lock Files**:
  - `.backfill.status`, `.unified_backfill.status`
  - `.backfill.lock`, `.unified_backfill.lock`
  - `.hyperliquid_backfill.status`
- **Configuration**:
  - `.env` (contains credentials)
  - `.claude/settings.local.json` (local Claude settings)
- **Test/Debug Files**:
  - `test*.json`, `grid_response.json`, `*_test.json`
  - `aave_data.json`, `okx_swap_test.json`
- **Dependencies**:
  - `node_modules/`, `__pycache__/`, `.venv/`

## Key System Features

### Arbitrage Detection System
- **Real-time scanning**: Cross-exchange arbitrage opportunities every 30s
- **Database table**: `arbitrage_spreads` tracks opportunities over time
- **API endpoints**: `/api/arbitrage/opportunities` (v1) and `/api/arbitrage/opportunities-v2` (paginated)
- **Dashboard page**: `/arbitrage` shows real-time opportunities
- **Spread statistics**: Historical tracking via `utils/arbitrage_spread_statistics.py`
- **Implementation**: `utils/arbitrage_scanner.py` with 30s cache TTL

### Z-Score Statistical Analysis
- **Zone-based updates**: Active zones (|Z|>2) update every 30s, stable zones every 2min
- **Performance**: <1s calculation for all 2,275 contracts using parallel processing
- **Database table**: `funding_statistics` stores Z-scores and statistical measures
- **API endpoints**: `/api/contracts-with-zscores`, `/api/zscore-summary`
- **Implementation**: `utils/zscore_calculator.py` with percentile rankings

### Modern UI Components
Complete component library in `dashboard/src/components/Modern/`:
- **ModernTable**: Virtualized tables for large datasets
- **ModernCard**: Consistent card styling
- **ModernButton/Badge**: Unified UI elements
- **ModernTooltip/Pagination**: Enhanced UX components
- **ModernMultiSelect**: Multi-select dropdowns for filtering

Usage: Always prefer Modern components for consistency across the dashboard

### Contract Health Management
The `contract_monitor.py` utility maintains data quality:
- **Stale Detection**: Marks contracts with no updates for 24h
- **Inactive Marking**: Sets is_active=false after 48h without updates
- **Delisted Cleanup**: Removes data for permanently delisted contracts
- **Reactivation**: Automatically reactivates contracts that return
- **Modes**: `--report-only` (view only), `--dry-run` (preview), normal (apply changes)
- **Recommendation**: Run hourly via cron for optimal data quality

## Known Limitations (MVP Status)

### Current System Status
- **MVP Implementation**: Not production-ready, requires hardening
- **No Authentication**: API and dashboard lack auth/authorization
- **Basic Error Recovery**: Limited retry mechanisms
- **No Unit Tests**: Manual testing only
- **Manual Scaling**: No auto-scaling or distributed processing

### Data Limitations
- **30-day Window**: Historical data rolling window limitation
- **Rate Limiting**: May hit exchange API limits during peak usage
- **Symbol Edge Cases**: Some normalization edge cases may exist
- **Gap Handling**: Historical data may have gaps during outages