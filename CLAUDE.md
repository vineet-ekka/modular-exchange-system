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

## Quick Start

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
# - Arbitrage scanner (cross-exchange opportunities)

# Verify everything is running
curl http://localhost:8000/api/health         # Should return {"status":"healthy"}
curl http://localhost:3000                    # Should load dashboard

# Shutdown
python shutdown_dashboard.py
```

## Essential Commands

### Pre-commit Checks (MUST run before any commit)
```bash
cd dashboard && npx tsc --noEmit              # TypeScript check (REQUIRED)
python database_tools.py check                # Database connectivity
python -m py_compile api.py main.py          # Python syntax check
```

### Development Commands
```bash
# Build & Test
cd dashboard && npm run build                 # Production build
cd dashboard && npx tsc --noEmit              # TypeScript check only

# Individual Components
python api.py                                 # API server only (port 8000)
cd dashboard && npm start                     # Dashboard only (port 3000)
python main.py --loop --interval 30           # Data collector only
python utils/zscore_calculator.py             # Z-score calculator only

# Database Operations
python database_tools.py check                # Test connection
python database_tools.py clear --quick        # Clear all data (CAUTION)
python database_tools.py status               # Show detailed table stats
python scripts/unified_historical_backfill.py --days 30 --parallel  # Backfill all exchanges
python scripts/fill_recent_gaps.py            # Fill any gaps in recent data

# Performance Testing
python scripts/test_performance.py            # Z-score performance
curl -s http://localhost:8000/api/health/performance | python -m json.tool

# Monitor Running Processes
tasklist | findstr "python"                   # Check Python processes
netstat -ano | findstr ":8000"                # Check API server port
netstat -ano | findstr ":3000"                # Check dashboard port
```


## High-Level Architecture

### System Overview
- **Scale**: 1,240+ contracts across 600+ unique assets from 4 exchanges (Binance, KuCoin, Backpack, Hyperliquid)
- **Update Cycle**: 30-second real-time refresh with sequential API calls
- **Database**: PostgreSQL with 5 tables (real-time, historical, statistics, metadata, arbitrage)
- **Backend**: FastAPI (port 8000) with 35+ endpoints including arbitrage detection and WebSocket support
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
                                             Z-Score Calc   Redis   Arbitrage
                                                    ↓         Cache   Detection
                                         funding_statistics        ↓
                                                    ↓          arbitrage_spreads
                                            contract_metadata
```

### Key Patterns

1. **Exchange Factory Pattern** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange`
   - Implement `fetch_data()` and `normalize_data()`
   - Factory creates instances: `ExchangeFactory.create_exchange(name)`

2. **Sequential Collection** (`config/sequential_config.py`)
   - Staggered delays: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s)
   - Prevents API rate limiting across exchanges

3. **Symbol Normalization** (Critical for consistency)
   - Handles prefixes: `1000SHIB` → `SHIB`, `kPEPE` → `PEPE`, `1MBABYDOGE` → `BABYDOGE`
   - Each exchange implements in `normalize_data()` method

4. **Z-Score System** (`utils/zscore_calculator.py`)
   - Zone-based updates: Active (|Z|>2) every 30s, Stable every 2min
   - Performance: <1s calculation, <100ms API response
   - Parallel processing with ThreadPoolExecutor

5. **Arbitrage Detection** (`utils/arbitrage_scanner.py`, `utils/arbitrage_spread_statistics.py`)
   - Real-time cross-exchange opportunity scanning
   - APR spread calculation and ranking
   - Historical spread tracking and statistics

## Critical Business Logic

### Symbol Normalization Rules
- **Binance prefixes**: `1000SHIB` → `SHIB`, `1000PEPE` → `PEPE`, `1000BONK` → `BONK`
- **KuCoin prefixes**: `kPEPE` → `PEPE`, `kBONK` → `BONK`
- **Special cases**: `1MBABYDOGE` → `BABYDOGE`, `10000LADYS` → `LADYS`
- **Implementation**: Each exchange's `normalize_data()` method handles its specific rules

### Funding Interval Standards
- **Binance**: 8-hour intervals (3 times daily)
- **KuCoin**: Mixed 4-hour and 8-hour intervals (contract-specific)
- **Backpack**: 1-hour intervals (24 times daily)
- **Hyperliquid**: 1-hour intervals (24 times daily)
- **APR Calculation**: `funding_rate * (365 * 24 / interval_hours) * 100`

### Data Collection Sequencing
- **Purpose**: Prevent API rate limits and server overload
- **Schedule**: Binance (0s) → KuCoin (30s) → Backpack (120s) → Hyperliquid (180s)
- **Configuration**: `config/sequential_config.py` defines exact timing
- **Error Handling**: Failed collections retry after full cycle completes

## Database Schema

```sql
-- Real-time data (current funding rates)
exchange_data (
    exchange, symbol, base_asset, quote_asset,
    funding_rate, funding_interval_hours, apr,
    index_price, mark_price, open_interest,
    timestamp, last_updated,
    volume_24h_quote, index_mark_spread,
    UNIQUE(exchange, symbol)
)

-- Historical data (30-day rolling window)
funding_rates_historical (
    exchange, symbol, funding_rate, funding_time,
    mark_price, funding_interval_hours, created_at,
    UNIQUE(exchange, symbol, funding_time)
)

-- Statistical metrics (Z-scores, percentiles)
funding_statistics (
    exchange, symbol, current_z_score, current_percentile,
    mean_30d, std_dev_30d, median_30d, min_30d, max_30d,
    data_points, last_updated,
    UNIQUE(exchange, symbol)
)

-- Contract metadata (funding intervals, creation time)
contract_metadata (
    exchange, symbol, funding_interval_hours,
    created_at, last_seen,
    UNIQUE(exchange, symbol)
)

-- Arbitrage spreads (cross-exchange opportunities)
arbitrage_spreads (
    asset, exchange_a, exchange_b,
    funding_rate_a, funding_rate_b, apr_spread,
    timestamp,
    UNIQUE(asset, exchange_a, exchange_b, timestamp)
)

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

## Core Files for Understanding

### System Entry Points
- `start.py` - One-command orchestrator (starts everything)
- `api.py` - FastAPI backend with 35+ endpoints
- `main.py` - Data collection coordinator with health tracking
- `shutdown_dashboard.py` - Clean shutdown utility
- `database_tools.py` - Database management CLI

### Exchange Integration
- `exchanges/base_exchange.py` - Abstract base class
- `exchanges/exchange_factory.py` - Factory pattern for exchanges
- `exchanges/binance_exchange.py` - Binance futures (547 contracts)
- `exchanges/kucoin_exchange.py` - KuCoin futures (477 contracts)
- `exchanges/backpack_exchange.py` - Backpack futures (43 contracts)
- `exchanges/hyperliquid_exchange.py` - Hyperliquid perps (173 contracts)

### Z-Score System
- `utils/zscore_calculator.py` - Parallel Z-score engine
- `utils/zscore_calculator_optimized.py` - Performance optimized version
- `utils/contract_metadata_manager.py` - Tracks funding intervals
- `scripts/test_performance.py` - Performance validation suite
- `utils/redis_cache.py` - Redis caching layer

### Arbitrage System
- `utils/arbitrage_scanner.py` - Cross-exchange arbitrage detection
- `utils/arbitrage_spread_statistics.py` - Statistical analysis
- `scripts/collect_spread_history.py` - Historical spread collection

### Dashboard
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main 600+ asset grid
- `dashboard/src/components/Grid/HistoricalFundingViewContract.tsx` - Historical charts
- `dashboard/src/components/ArbitrageOpportunities.tsx` - Arbitrage table
- `dashboard/src/components/Neumorphic/` - Neumorphic UI components (cards, buttons, inputs)
- `dashboard/src/components/LiveTicker.tsx` - Real-time funding rate ticker
- `dashboard/src/components/WebSocketStatus.tsx` - WebSocket connection indicator
- `dashboard/src/services/api.ts` - API client with all endpoints
- `dashboard/src/services/websocket.ts` - WebSocket service implementation
- `dashboard/src/contexts/WebSocketContext.tsx` - WebSocket React context provider
- `dashboard/src/hooks/` - Custom React hooks for data fetching and state management
- `dashboard/src/App.tsx` - Main router and layout

### Database & Utilities
- `database/postgres_manager.py` - Database operations and connection pooling
- `scripts/unified_historical_backfill.py` - Parallel 30-day backfill for all exchanges
- `scripts/fill_recent_gaps.py` - Fill gaps in historical data
- `scripts/test_performance.py` - Z-score and API performance testing
- `scripts/collect_spread_history.py` - Collect arbitrage spread history
- `utils/health_tracker.py` - System health monitoring
- `utils/rate_limiter.py` - API rate limiting
- `utils/redis_cache.py` - Redis caching with TTL management
- `utils/contract_metadata_manager.py` - Tracks funding intervals and contract info

## Debugging & Monitoring

### Real-time Monitoring Commands
```bash
# Monitor data collection logs
type data_collector.log | findstr /C:"ERROR"   # Show only errors
type data_collector.log | findstr /C:"OK"       # Show successful collections

# Check system resource usage
tasklist | findstr python                       # List all Python processes
wmic process where "name='python.exe'" get ProcessId,WorkingSetSize,CommandLine

# Monitor API endpoints
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/statistics | python -m json.tool

# Database connection count
python -c "from database.postgres_manager import PostgresManager; pm=PostgresManager(); print(f'Active connections: {pm.get_connection_count()}')"
```

### Debug Mode Execution
```bash
# Run components with verbose logging
python api.py --debug                          # API with debug logs
python main.py --loop --interval 30 --verbose  # Collector with verbose output
python utils/zscore_calculator.py --debug      # Z-score calculator with debug

# Test individual exchange connections
python -c "from exchanges.exchange_factory import ExchangeFactory; e=ExchangeFactory.create_exchange('binance'); print(e.test_connection())"
```

## Common Issues & Solutions

### Docker Desktop Not Running
- **Problem**: PostgreSQL/Redis containers fail to start
- **Solution**: Start Docker Desktop first, wait for it to fully initialize
- **Verification**: Run `docker ps` to confirm Docker is running

### Port Already in Use
```bash
# Windows: Find and kill process using a port
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### Database Connection Issues
- Ensure Docker is running: `docker ps`
- Check PostgreSQL: `docker-compose ps`
- Restart if needed: `docker-compose restart postgres`
- Connection test: `python database_tools.py check`

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn psutil scipy redis  # Additional packages often needed
cd dashboard && npm install                     # Frontend dependencies
```

### Data Collector Issues
- Check `data_collector.log` for errors
- Manual start: `python main.py --loop --interval 30`
- Verify all exchanges are reachable

### Dashboard Issues
- TypeScript errors: `cd dashboard && npx tsc --noEmit`
- If not loading: Check API at http://localhost:8000/api/health
- Clear browser cache if UI seems outdated

## Files Never to Commit
- `.backfill.status`, `.unified_backfill.status` - Progress tracking files
- `data_collector.log` - Can grow very large (>100MB)
- `.env` - Contains database credentials
- `node_modules/` - NPM packages
- `__pycache__/` - Python bytecode
- `.venv/`, `venv/` - Python virtual environment
- `*.pyc` - Compiled Python files
- `.claude/settings.local.json` - Local Claude settings

## Testing Individual Components

```bash
# Test each exchange separately
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); print(f'Backpack: {len(e.fetch_data())} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); print(f'Hyperliquid: {len(e.fetch_data())} contracts')"

# Test Z-score calculator
python utils/zscore_calculator.py                   # Run calculator
python scripts/test_performance.py                  # Performance test

# Test arbitrage scanner
python -c "from utils.arbitrage_scanner import ArbitrageScanner; s=ArbitrageScanner(); print(f'Found {len(s.scan_opportunities(0.001))} opportunities')"

# Check Redis connection and cache
python -c "import redis; r=redis.Redis(host='localhost', port=6379); r.ping(); print('Redis connected')"
python -c "from utils.redis_cache import RedisCache; c=RedisCache(); c.test_connection()"
```

## APR Calculation Formula

```python
# APR = funding_rate × periods_per_year × 100
periods_per_year = (365 × 24) / funding_interval_hours

# Exchange-specific intervals:
# Binance: 8-hour (1,095 periods/year)
# KuCoin: 4 or 8-hour (2,190 or 1,095 periods/year)
# Backpack: 1-hour (8,760 periods/year)
# Hyperliquid: 1-hour (8,760 periods/year)
```

## WebSocket Support

### Real-time Updates
- **WebSocket Server**: FastAPI WebSocket endpoint at `/ws`
- **Live Updates**: Real-time funding rate broadcasts every 30 seconds
- **React Integration**: WebSocketContext for managing connections (`dashboard/src/contexts/WebSocketContext.tsx`)
- **Components**: LiveTicker (`dashboard/src/components/LiveTicker.tsx`), WebSocketStatus (`dashboard/src/components/WebSocketStatus.tsx`)
- **Auto-reconnect**: Automatic reconnection with exponential backoff
- **Message Broadcasting**: Server broadcasts updates to all connected clients simultaneously

### WebSocket Usage
```typescript
// Frontend WebSocket connection managed via context
const ws = new WebSocket('ws://localhost:8000/ws');
```

### WebSocket Message Types
- `funding_update`: Real-time funding rate updates
- `health_status`: System health notifications
- `error`: Error messages from the server

## Docker Container Management

### Container Stack
```bash
# Start all containers
docker-compose up -d

# Check container status
docker ps

# View logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs pgadmin

# Restart containers
docker-compose restart postgres redis

# Stop containers (preserves data)
docker-compose down

# Stop and remove volumes (CAUTION: deletes all data)
docker-compose down -v
```

### pgAdmin Access
- URL: http://localhost:5050
- Email: admin@exchange.local
- Password: admin123
- Add Server: Host=postgres, Port=5432, Database=exchange_data, Username=postgres, Password=postgres123

## Package Dependencies

### Python Requirements
```bash
pip install pandas requests psycopg2-binary numpy python-dotenv aiohttp asyncio-throttle redis
pip install fastapi uvicorn psutil scipy  # API server dependencies
```

### React Dependencies
```bash
cd dashboard && npm install  # Installs all package.json dependencies including:
# - React 19 + TypeScript
# - TailwindCSS for styling
# - Recharts for visualization
# - React Router for navigation
# - Axios for API calls
# - React Window for virtualization
```

## Summary

This codebase implements a comprehensive cryptocurrency funding rate tracking system with:
- Real-time data collection from 4 exchanges (1,240+ contracts)
- Historical data management with 30-day rolling window
- Z-score statistical analysis for identifying extreme deviations
- Cross-exchange arbitrage opportunity detection
- Redis caching for performance optimization
- WebSocket support for real-time updates
- Professional React dashboard with advanced filtering and search

The system is designed for production use with automatic error recovery, health monitoring, and comprehensive logging. All components can be started with a single `python start.py` command.

## Performance Requirements

- **API Response Time**: <100ms for most endpoints, <1s for complex aggregations
- **Z-Score Calculation**: <1s for all 1,240 contracts
- **Dashboard Load**: <2s initial load, 30s polling cycle
- **Database Queries**: Optimized with indexes for <50ms response
- **Memory Usage**: API server <500MB, Redis <512MB
- **Historical Backfill**: ~5-7 minutes for 30 days across all exchanges
- **WebSocket Latency**: <50ms for real-time updates
- **Data Collector Memory**: <200MB during normal operation
- **Concurrent Connections**: Support for 100+ WebSocket clients

## Development Workflow

### Before Making Changes
1. Check if component is running: `netstat -ano | findstr :PORT`
2. Stop component if needed: `taskkill /PID <pid> /F`
3. Read relevant files with Read tool before editing
4. For new features, check existing patterns in similar files

### Making Changes
1. Edit existing files rather than creating new ones
2. Verify imports exist in requirements.txt or package.json
3. Follow existing code patterns and conventions
4. Run type checking after React changes: `cd dashboard && npx tsc --noEmit`
5. Test Python syntax: `python -m py_compile <file.py>`

### Testing Changes
1. Test individual components before full system test
2. Check API endpoints: `curl http://localhost:8000/api/health`
3. Monitor logs: `type data_collector.log | findstr "ERROR"`
4. Verify database operations: `python database_tools.py check`
5. For UI changes, verify responsive behavior at different screen widths
6. Test expanded table views for proper scrolling and alignment

## Required Python Packages

### Core Dependencies (requirements.txt)
- pandas>=1.5.0
- requests>=2.28.0
- psycopg2-binary>=2.9.0
- numpy>=1.21.0
- python-dotenv>=1.0.0
- aiohttp>=3.8.0
- asyncio-throttle>=1.0.0
- redis==5.0.1

### Additional API Server Dependencies
- fastapi
- uvicorn
- psutil
- scipy

## React Dashboard Commands

```bash
# Development
cd dashboard && npm start                     # Start dev server (port 3000)
cd dashboard && npm run build                 # Production build
cd dashboard && npx tsc --noEmit             # TypeScript check (REQUIRED before commit)
cd dashboard && npm test                      # Run React tests

# Package Management
cd dashboard && npm install                   # Install all dependencies
```

## Dashboard Layout Patterns

### Full-Width Components
When creating full-width dashboard components:
- Use `<div className="w-full px-2">` wrapper for edge-to-edge layout
- Remove rounded corners (`rounded-xl`) and use `border-y` for horizontal borders
- For expanded tables within cards, remove container padding to maximize width
- Use `min-w-full` on tables instead of `w-full` to ensure proper width usage

### Grid Table Optimization
- Main grid uses `overflow-x-auto` for horizontal scrolling
- Expanded contract tables should have column minimum widths (`min-w-[...]`)
- Sticky columns use `sticky left-0 z-10` for fixed positioning during scroll