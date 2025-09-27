# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a multi-exchange cryptocurrency funding rate dashboard that tracks 1,403+ perpetual contracts across 6 exchanges (Binance, KuCoin, Backpack, Hyperliquid, Aster, Drift). The system collects real-time funding rates every 30 seconds, maintains 30-day historical data, calculates Z-scores for statistical analysis, and identifies cross-exchange arbitrage opportunities.

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
- **Imports**: Check if packages exist in requirements.txt or package.json before using
- **NO COMMENTS**: Do not add code comments unless explicitly requested

### Windows-Specific Notes
- Use `type` instead of `cat` for viewing files
- Use `dir` instead of `ls` if needed
- Use `taskkill /PID <pid> /F` instead of `kill -9`
- Python commands use `python` prefix (not `python3`)
- Use `netstat -ano | findstr :PORT` to find processes on ports

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
# - Runs background processes (historical backfill, Z-score calculator, arbitrage scanner)

# Shutdown everything
python shutdown_dashboard.py

# Clean shutdown of specific services
taskkill /PID <pid> /F       # Windows: Kill specific process
docker-compose down           # Stop all Docker containers
```

### Pre-commit Checks (MUST run before any commit)
```bash
cd dashboard && npx tsc --noEmit              # TypeScript check (REQUIRED)
python database_tools.py check                # Database connectivity
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
cd dashboard && npm test                     # React tests (if any)
cd dashboard && npx tsc --noEmit            # TypeScript type checking

# Database Operations
python database_tools.py check               # Test connection
python database_tools.py clear --quick       # Clear all data (CAUTION)
python database_tools.py status              # Show detailed table stats
python scripts/unified_historical_backfill.py --days 30 --parallel  # Backfill all exchanges
python scripts/collect_spread_history.py     # Collect arbitrage spread history
python scripts/backfill_arbitrage_spreads_v2.py  # V2 backfill (more efficient)

# Performance Testing
python scripts/test_performance.py           # Z-score performance
curl -s http://localhost:8000/api/health/performance | python -m json.tool

# Contract Health Monitoring
python utils/contract_monitor.py --report-only  # Check for stale/delisted contracts
python utils/contract_monitor.py --dry-run     # Preview changes without applying

# Monitor Processes (Windows)
tasklist | findstr "python"                  # Check Python processes
netstat -ano | findstr ":8000"              # Check API server port
netstat -ano | findstr ":3000"              # Check dashboard port
netstat -ano | findstr ":5432"              # Check PostgreSQL port
netstat -ano | findstr ":6379"              # Check Redis port
netstat -ano | findstr ":5050"              # Check pgAdmin port
type data_collector.log | findstr "ERROR"    # Check for errors

# Check Background Process Output
python -c "print('Check background process IDs with: tasklist | findstr python')"
```

## High-Level Architecture

### System Overview
- **Scale**: 1,403+ contracts across 600+ unique assets from 6 exchanges
- **Update Cycle**: 30-second real-time refresh with sequential API calls
- **Database**: PostgreSQL with 6 tables (real-time, historical, statistics, metadata, arbitrage, funding_statistics)
- **Backend**: FastAPI (port 8000) with 35+ endpoints, WebSocket support, Redis caching
- **Frontend**: React 19/TypeScript with 30-second polling and WebSocket integration
- **Performance**: Z-scores <1s for all contracts, API responses <100ms, WebSocket latency <50ms

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

### Core Architectural Patterns

1. **Exchange Factory Pattern** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange`
   - Must implement `fetch_data()` and `normalize_data()` methods
   - Factory creates instances: `ExchangeFactory.create_exchange(name)`
   - Handles rate limiting and error recovery

2. **Sequential Collection Strategy** (`config/sequential_config.py`)
   - Staggered delays prevent API rate limiting: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s)
   - Each exchange has configurable collection schedules
   - Failed collections retry after full cycle completes
   - Rate limits: Binance (40 req/s), KuCoin (30 req/s), Backpack (~20 req/s), Hyperliquid (10 req/s enforced), Aster (40 req/s max), Drift (no strict limit)

3. **Symbol Normalization** (Critical for cross-exchange consistency)
   - Each exchange's `normalize_data()` method implements specific rules
   - See "Exchange-Specific Information" section for detailed normalization rules
   - Ensures unified asset display across all exchanges

4. **Z-Score System** (`utils/zscore_calculator.py`)
   - Zone-based updates: Active zones (|Z|>2) every 30s, Stable zones every 2min
   - Parallel processing with ThreadPoolExecutor for <1s calculation
   - Percentile rankings for distribution-independent analysis

5. **Real-time Updates & Caching**
   - Polling-based updates (30-second intervals)
   - WebSocket real-time broadcasting at `/ws` endpoint
   - Redis caching with TTL: 5s for contracts, 10s for summary data
   - Performance monitoring via `/api/health/performance` endpoint
   - Automatic cache invalidation on data updates
   - WebSocket auto-reconnect with exponential backoff

## Critical Business Logic

### APR Calculation Formula
```python
# Based on funding interval - NEVER modify without understanding impact
periods_per_year = (365 * 24) / funding_interval_hours
apr = funding_rate * periods_per_year * 100

# Exchange intervals:
# Binance: 8 hours (1,095 periods/year)
# KuCoin: 4 or 8 hours (2,190 or 1,095 periods/year)
# Backpack: 1 hour (8,760 periods/year)
# Hyperliquid: 1 hour (8,760 periods/year)
# Aster: 4 hours (2,190 periods/year)
# Drift: 1 hour (8,760 periods/year)
```

### Database Schema (Key Tables)
```sql
-- Real-time funding rates
exchange_data (exchange, symbol, funding_rate, apr, timestamp, UNIQUE(exchange, symbol))

-- Historical data with 30-day rolling window
funding_rates_historical (exchange, symbol, funding_rate, funding_time, UNIQUE(exchange, symbol, funding_time))

-- Z-score statistics
funding_statistics (exchange, symbol, current_z_score, mean_30d, std_dev_30d, UNIQUE(exchange, symbol))

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
- **PostgreSQL**: Port 5432, database `exchange_data`
- **Redis**: Port 6379, 512MB memory limit, LRU eviction policy
- **pgAdmin**: Port 5050, web interface at http://localhost:5050
  - Login: admin@example.com / admin123
  - Pre-configured server: exchange_postgres

## Exchange-Specific Information

### Exchange Summary
| Exchange | Contracts | Funding Intervals | Rate Limit | Special Notes |
|----------|-----------|-------------------|------------|---------------|
| Binance | 547 | 8h (38%), 4h (61.6%), 1h (0.4%) | 40 req/s | USD-M and COIN-M markets |
| KuCoin | 477 | 8h (39.4%), 4h (59.5%), 2h (0.2%), 1h (0.8%) | 30 req/s | XBT prefix for Bitcoin |
| Backpack | 43 | 1h (100%) | ~20 req/s | Recently changed to all 1-hour |
| Hyperliquid | 173 | 1h (100%) | 10 req/s | DEX with simple naming |
| Aster | 102 | 4h (default) | 40 req/s max | DEX with async/parallel fetching |
| Drift | 61 | 1h (100%) | No strict limit | Solana-based DEX |

### Symbol Normalization Rules
- **Binance**: `1000SHIB` → `SHIB`, `1MBABYDOGE` → `BABYDOGE`, `1000000MOG` → `MOG`
- **KuCoin**: `1000X` → `X`, `kPEPE` → `PEPE`, `10000CAT` → `CAT`, `1MBABYDOGE` → `BABYDOGE`
- **Backpack**: `kBONK_USDC_PERP` → `BONK`
- **Hyperliquid**: `kPEPE` → `PEPE`
- **Aster**: `1000FLOKI` → `FLOKI`, `kX` → `X`, numerical prefixes removed
- **Drift**: `XXX-PERP` → `XXX`, `1MBONK` → `BONK`, `1MPEPE` → `PEPE`

## Recent Additions

### Arbitrage Detection System
- **Real-time scanning**: Cross-exchange arbitrage opportunities every 30s
- **Database table**: `arbitrage_spreads` tracks opportunities over time
- **API endpoints**: Both v1 (simple) and v2 (paginated) versions available
- **Dashboard page**: `/arbitrage` shows real-time opportunities
- **Spread statistics**: Historical tracking via `utils/arbitrage_spread_statistics.py`

### Modern UI Components
- **Component library**: Comprehensive reusable components in `dashboard/src/components/Modern/`
- **ModernTable**: Advanced table with sorting, pagination, selection, and virtualization
- **ModernCard**: Consistent card styling across the dashboard
- **ModernInput/Select**: Form controls with unified styling
- **ModernButton**: Unified button components with consistent styling
- **ModernBadge**: Status indicators and labels
- **ModernToggle**: Toggle switches for settings
- **ModernTooltip**: Tooltip components for contextual help
- **ModernPagination**: Advanced pagination controls for large datasets

### Enhanced Dashboard Pages
- **ArbitrageDetailPage** (`dashboard/src/pages/ArbitrageDetailPage.tsx`)
  - Detailed view for individual arbitrage opportunities
  - Historical charts with spread analysis
  - Z-score analysis for funding rates
  - Open interest and volume metrics
- **ArbitrageHistoricalChart** (`dashboard/src/components/Charts/ArbitrageHistoricalChart.tsx`)
  - Time-series visualization of cross-exchange opportunities

## Common Workflows

### Adding New Exchange
1. Create module in `exchanges/` inheriting from `BaseExchange`
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to `exchanges/exchange_factory.py`
4. Update `config/settings.py` EXCHANGES dict
5. Add to `config/sequential_config.py` schedule
6. Test: `python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"`

### Debugging Data Issues
```bash
# Check data collection
type data_collector.log | findstr "ERROR"    # Windows
tail -f data_collector.log | grep "ERROR"    # Linux/Mac

# Test individual exchanges
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"

# Check database status
python database_tools.py status

# Test Redis cache
python -c "from utils.redis_cache import RedisCache; c=RedisCache(); c.test_connection()"

# Test WebSocket connection
python -c "import asyncio, websockets; asyncio.run(websockets.connect('ws://localhost:8000/ws'))"

# Fix data issues
python scripts/fix_funding_intervals.py      # Fix incorrect funding intervals
python scripts/fix_data_pipeline.py          # Repair data pipeline issues
python scripts/retry_incomplete_contracts.py # Retry failed contract fetches
python scripts/cleanup_delisted_contracts.py # Remove delisted contracts

# Contract Health Management
python utils/contract_monitor.py             # Monitor and mark stale contracts
python utils/contract_monitor.py --dry-run   # Preview without making changes
python utils/contract_monitor.py --report-only  # Generate health report
```

## Performance Optimizations

### Database
- Indexes on (exchange, symbol) for <50ms queries
- Materialized views for analytics
- Connection pooling with 20 max connections
- UPSERT operations to prevent duplicates

### Caching
- Redis with TTL: 5s for contracts, 10s for summary data
- Zone-based Z-score updates to reduce calculations
- Pre-computed APR values stored in database

### Frontend
- React Window virtualization for 600+ assets
- Debounced search with on-demand contract fetching
- Memoized components with React.memo
- Modern UI components library in `dashboard/src/components/Modern/`
- 30-second polling for real-time updates

## Package Dependencies

### Python (requirements.txt)
```bash
pip install -r requirements.txt
# All required packages including fastapi, uvicorn, psutil, scipy, websockets, and redis are included
```

### React (dashboard/package.json)
- React 19 with TypeScript 4.9
- TailwindCSS for styling
- Recharts for visualization
- React Window for virtualization
- Axios for API calls

## Files Never to Commit
- `.backfill.status`, `.unified_backfill.status`, `.backfill.lock` - Progress tracking
- `.unified_backfill.lock` - Backfill lock file
- `data_collector.log` - Can grow >100MB
- `.env` - Contains credentials
- `node_modules/`, `__pycache__/`, `.venv/` - Dependencies
- `.claude/settings.local.json` - Local Claude settings
- `test*.json`, `grid_response.json` - Test/debug files

## Managing Background Processes

### Identifying Running Processes
```bash
# List all Python processes with PIDs
tasklist | findstr "python"

# Find processes on specific ports
netstat -ano | findstr ":8000"   # API server
netstat -ano | findstr ":3000"   # Dashboard
netstat -ano | findstr ":5432"   # PostgreSQL
netstat -ano | findstr ":6379"   # Redis
netstat -ano | findstr ":5050"   # pgAdmin

# Kill specific process
taskkill /PID <pid> /F
```

### Common Process Issues
- Multiple API instances running on port 8000: Kill duplicate processes
- Data collector not updating: Check `data_collector.log` for errors
- Redis connection failures: Ensure Redis container is running
- Dashboard not refreshing: Check network tab for API errors

## Critical Utilities

### Contract Monitor (`utils/contract_monitor.py`)
- **Purpose**: Maintains data quality by detecting and marking inactive contracts
- **Features**:
  - Detects stale contracts (24/48 hour thresholds)
  - Auto-marks inactive/delisted contracts
  - Checks for contract reactivations
  - Generates comprehensive health reports
- **Usage**: Run hourly for optimal data quality
  ```bash
  python utils/contract_monitor.py             # Apply changes
  python utils/contract_monitor.py --dry-run   # Preview changes
  python utils/contract_monitor.py --report-only  # Health report only
  ```

## Known Limitations (MVP Status)

### Current System Status
- **MVP Implementation**: This is a minimum viable product, not production-ready
- **WebSocket Support**: Basic WebSocket at `/ws` endpoint with 30-second broadcasts
- **No Authentication**: API and dashboard have no authentication/authorization
- **Basic Error Recovery**: Limited retry mechanisms for failed API calls
- **No Tests**: Python code lacks unit tests, React has minimal tests
- **Manual Scaling**: No auto-scaling or distributed processing

### Data Limitations
- **30-day Window**: Historical data limited to 30-day rolling window
- **Rate Limiting**: Sequential collection to avoid API throttling adds delays
- **Gap Handling**: Some exchanges may have gaps in historical data
- **Symbol Normalization**: Edge cases may exist in cross-exchange asset mapping
- **Testing**: No formal unit test framework, TypeScript checking only