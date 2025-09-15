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

### Code Standards
- **TypeScript**: Always run `cd dashboard && npx tsc --noEmit` before commits
- **Python**: Verify imports exist, format with black, lint with ruff
- **Testing**: No formal test framework for Python. React uses type checking only.

## Quick Start

```bash
# Start everything with one command
python start.py

# This automatically handles:
# - Prerequisites check (Python, Node, Docker)
# - PostgreSQL database startup
# - API server (port 8000)
# - React dashboard (port 3000)  
# - Data collector (30-second updates)
# - Historical backfill (30-day)
# - Z-score calculator (zone-based updates)

# Shutdown
python shutdown_dashboard.py
```

## Essential Commands

### Pre-commit Checks (MUST run before any commit)
```bash
cd dashboard && npx tsc --noEmit              # TypeScript check
python database_tools.py check                # Database connectivity
black . --line-length=120 --exclude=".venv"   # Python formatting
ruff check .                                  # Python linting
```

### Development Commands
```bash
# Build & Test
cd dashboard && npm run build                 # Production build
cd dashboard && CI=true npm test              # Run tests

# Individual Components
python api.py                                 # API server only
cd dashboard && npm start                     # Dashboard only
python main.py --loop --interval 30           # Data collector only

# Database Operations
python database_tools.py check                # Test connection
python database_tools.py clear --quick        # Clear all data
python scripts/unified_historical_backfill.py --days 30 --parallel

# Performance Testing
python scripts/test_performance.py            # Z-score performance
curl -s http://localhost:8000/api/health/performance | python -m json.tool
```

### Troubleshooting Commands
```bash
# Check services
curl http://localhost:8000/api/health
curl http://localhost:3000

# Port conflicts (Windows)
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Check logs
type data_collector.log                       # Windows
cat data_collector.log                        # Linux/Mac

# Background processes (Claude Code specific)
/bashes                                       # List processes
BashOutput tool with bash_id="<id>"          # Monitor output
KillBash tool with shell_id="<id>"           # Kill process
```

## High-Level Architecture

### System Overview
- **Scale**: 1,260+ contracts across 600+ unique assets from 4 exchanges
- **Update Cycle**: 30-second real-time refresh with sequential API calls
- **Database**: PostgreSQL with 3 tables (real-time, historical, statistics)
- **Backend**: FastAPI (port 8000) with 27+ endpoints
- **Frontend**: React/TypeScript (port 3000) with 30-second polling
- **Z-Score System**: Parallel processing <1s for all contracts, zone-based updates

### Data Flow
```
Exchange APIs → Rate Limiter → Normalization → PostgreSQL → FastAPI → React Dashboard
                                                    ↓
                                            Z-Score Calculator
```

### Key Patterns

1. **Exchange Factory Pattern** (`exchanges/exchange_factory.py`)
   - All exchanges inherit from `BaseExchange`
   - Implement `fetch_data()` and `normalize_data()`

2. **Sequential Collection** (`config/sequential_config.py`)
   - Staggered delays: Binance (0s), KuCoin (30s), Backpack (120s), Hyperliquid (180s)

3. **Symbol Normalization** (Critical for consistency)
   - Handles prefixes: `1000SHIB` → `SHIB`, `kPEPE` → `PEPE`, `1MBABYDOGE` → `BABYDOGE`
   - Each exchange implements in `normalize_data()` method

4. **Z-Score System** (`utils/zscore_calculator.py`)
   - Zone-based updates: Active (|Z|>2) every 30s, Stable every 2min
   - Performance: <1s calculation, <100ms API response
   - Caching: 5s TTL for contracts, 10s for summary
   - Parallel processing with 8 workers

## Database Schema

```sql
-- Real-time data (current funding rates)
exchange_data (
    exchange, symbol, base_asset, quote_asset, 
    funding_rate, funding_interval_hours, apr,
    index_price, mark_price, open_interest,
    contract_type, market_type, timestamp, last_updated
)

-- Historical data (30-day rolling window)
funding_rates_historical (
    exchange, symbol, funding_rate, funding_time,
    mark_price, funding_interval_hours, created_at
)

-- Statistical metrics (Z-scores, percentiles)
funding_statistics (
    exchange, symbol, current_z_score, current_percentile,
    mean_30d, std_dev_30d, median_30d, 
    min_30d, max_30d, data_points, last_updated
)

-- Contract metadata (funding intervals, creation time)
contract_metadata (
    exchange, symbol, funding_interval_hours, 
    created_at, last_seen
)
```

## APR Calculation

```python
# Based on funding interval hours
if hours == 1: apr = rate * 8760 * 100
elif hours == 4: apr = rate * 2190 * 100
elif hours == 8: apr = rate * 1095 * 100
```

## Common Issues & Solutions

### Symbol Normalization
- **Test**: `python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(len(e.fetch_data()))"`

### Data Collector Issues
- Check `data_collector.log` for errors
- Manual start: `python main.py --loop --interval 30`

### Dashboard Issues
- Delete `.backfill.status` and `.unified_backfill.status` if stuck
- TypeScript errors: `cd dashboard && npx tsc --noEmit`

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn psutil scipy black ruff
```

## Z-Score Implementation Status

### Completed
- **Backend**: Full Z-score calculation with parallel processing (<1s for 1,260 contracts)
- **Database**: `funding_statistics` table with all statistical metrics
- **API Endpoints**: `/api/contracts-with-zscores`, `/api/zscore-summary`, `/api/health/performance`
- **Performance**: Batch operations, caching (5s contracts, 10s summary), zone-based updates
- **Metadata Tracking**: `contract_metadata` table for funding intervals

### UI Requirements (Not Yet Implemented)
When implementing `ContractZScoreGrid.tsx`:
1. **FLAT LIST** - 1,260 contracts, NO grouping
2. **Virtual Scrolling** - Must use react-window
3. **Blue-Orange Colors** - NO red/green
4. **Sort by |Z-score|** - Descending absolute value
5. **Dynamic Heights** - 40px standard, 120px for |Z| ≥ 2.0

## Environment Variables

Create `.env` file:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

## Common Workflows

### Adding New Exchange
1. Create new exchange module in `exchanges/` inheriting from `BaseExchange`
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to `exchanges/exchange_factory.py`
4. Update `config/settings.py` EXCHANGES dict
5. Add to `config/sequential_config.py` schedule
6. Test: `python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"`

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

## Files Never to Commit
- `.backfill.status`, `.unified_backfill.status` - Progress tracking
- `data_collector.log` - Can grow large
- `.env` - Contains secrets
- `node_modules/`, `__pycache__/`, `.venv/`

## Core Files for Understanding

### System Entry Points
- `start.py` - One-command orchestrator
- `api.py` - FastAPI backend with Z-score endpoints
- `main.py` - Data collection coordinator

### Exchange Integration
- `exchanges/base_exchange.py` - Abstract base class
- `exchanges/exchange_factory.py` - Instance management
- `config/sequential_config.py` - Collection timing

### Z-Score System
- `utils/zscore_calculator.py` - Parallel Z-score engine
- `scripts/test_performance.py` - Performance validation
- `utils/contract_metadata_manager.py` - Metadata tracking

### Dashboard
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main grid
- `dashboard/src/services/api.ts` - API client (needs Z-score methods)

### Utilities
- `scripts/unified_historical_backfill.py` - 30-day backfill
- `database_tools.py` - Database management
- `scripts/test_performance.py` - Z-score performance testing