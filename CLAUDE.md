# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Multi-exchange cryptocurrency funding rate aggregation system tracking 2,275 contracts across 8 exchanges with real-time updates, 30-day historical data, Z-score analysis, and arbitrage detection.

## CRITICAL RULES
- **NEVER delete files without DOUBLE CONFIRMATION**
- **ALWAYS prefer editing existing files** over creating new ones
- **NEVER create documentation files** unless explicitly requested
- **ALWAYS read files before editing** - never assume contents
- **NEVER commit unless explicitly asked**
- **NO COMMENTS** unless explicitly requested
- **NO EMOJIS** unless explicitly requested

## Key Architectural Patterns

### Service Dependency Chain
The system MUST start services in this exact order:
```
PostgreSQL (5432) → Redis (6379) → API Server (8000) → Dashboard (3000) → Data Collector
```
- **Critical**: API server creates database schema on first run (api.py:171-181)
- **Critical**: Data collector requires schema to exist - will fail if started before API
- **Cache invalidation**: Always happens AFTER database updates (main.py:395-414)

### Exchange Factory Pattern
All exchanges inherit from `BaseExchange` with standard interface:
```python
factory = ExchangeFactory(settings)
exchange = factory.get_exchange("binance")  # Returns BinanceExchange instance
data = exchange.fetch_data()                # Raw API data
normalized = exchange.normalize_data(data)  # Standard 12-column format
```

### Z-Score Zone Optimization
Reduces database load by 60% through intelligent update scheduling:
- Active zones (|Z-score| > 2): Update every 30 seconds
- Stable zones (|Z-score| < 2): Update every 2 minutes
- Each contract analyzed independently in `utils/zscore_calculator.py`

### Dual-Cache Architecture
Automatic fallback ensures system resilience:
- Primary: Redis (512MB, LRU eviction, distributed)
- Fallback: SimpleCache (in-memory if Redis unavailable)
- TTL: 5s contracts, 10s summaries, 30s arbitrage opportunities, 25s Z-score data

### Arbitrage Detection System
Cross-exchange arbitrage scanning with statistical analysis:
- **ArbitrageScanner** (`utils/arbitrage_scanner.py`): Identifies funding rate spreads across exchanges
- **Statistical Significance**: Z-score and percentile calculations for spread opportunities
- **Spread Tracking**: Historical spread statistics in `arbitrage_spreads` table
- **Real-time Detection**: Calculates APR spreads, hourly rates, sync periods, and daily spreads
- **Cache Integration**: Redis caching with 30s TTL for arbitrage opportunities
- **API Endpoint**: `/api/arbitrage/opportunities` with pagination and filtering

## Common Commands

### Startup & Shutdown
```bash
python start.py                    # One-command startup (handles all dependencies)
python shutdown_dashboard.py        # Clean shutdown of all services
```

### Development Workflow
```bash
# Pre-commit checks (REQUIRED before any git operations)
cd dashboard && npx tsc --noEmit
python -m py_compile api.py main.py utils/*.py exchanges/*.py scripts/*.py

# Testing a new exchange implementation
python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"

# Test arbitrage filter with specific exchanges
curl "http://localhost:8000/api/arbitrage/opportunities-v2?exchanges=binance&exchanges=kucoin" | python -m json.tool

# Verify Python syntax after edits
python -m py_compile utils/arbitrage_scanner.py

# Check system health
curl http://localhost:8000/api/health/performance | python -m json.tool

# Database inspection
python database_tools.py status    # Show table statistics
psql -U postgres -d exchange_data -c "SELECT exchange, COUNT(*) FROM exchange_data GROUP BY exchange;"
```

### Debugging Issues
```bash
# Windows: Find and kill process on port
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Check logs for errors
tail -f data_collector.log | grep ERROR       # Linux/Mac
type data_collector.log | findstr "ERROR"     # Windows

# Test database connection
python database_tools.py check

# Monitor background processes
ps aux | grep -E "zscore|arbitrage|spread"    # Linux/Mac
tasklist | findstr "python"                   # Windows

# Clear all data (CAUTION - cannot be undone)
python database_tools.py clear --quick
```

### Historical Data Management
```bash
# Full 30-day backfill (runs automatically on startup)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Fill recent gaps
python scripts/fill_recent_gaps.py

# Rebuild arbitrage spreads
python scripts/backfill_arbitrage_spreads_v2.py

# Data maintenance scripts
python scripts/cleanup_historical_data.py          # Remove old/invalid historical records
python scripts/fix_duplicate_funding_data.py       # Resolve duplicate entries
python scripts/retry_incomplete_contracts.py       # Retry failed contract fetches
python scripts/collect_spread_history.py           # Collect arbitrage spread history
```

## Critical Business Logic

### APR Calculation
APR calculation depends on funding interval - rates with different intervals are NOT directly comparable:
```python
periods_per_year = (365 * 24) / funding_interval_hours
apr = funding_rate * periods_per_year * 100
# 8h interval, 0.01% rate = 10.95% APR
# 4h interval, 0.01% rate = 21.9% APR (2x higher!)
```

### Symbol Normalization Patterns
Each exchange uses different multiplier conventions that must be handled:
- **Numerical prefixes**: `1000SHIB` → `SHIB`, `10000CAT` → `CAT`
- **Million denomination**: `1MBABYDOGE` → `BABYDOGE`
- **KuCoin special case**: `1000X` → `X` (this is the X token, not a multiplier)
- **Exchange-specific**: Hyperliquid's `kPEPE` → `PEPE`, KuCoin's `XBT` → `BTC`

### Data Processing Pipeline
```
Raw API → fetch_data() → normalize_data() → DataProcessor → PostgreSQL
             ↓                ↓                  ↓             ↓
        Rate limiting    Symbol mapping    APR calculation   UPSERT
```

## Adding a New Exchange

1. Create `exchanges/new_exchange.py`:
```python
from exchanges.base_exchange import BaseExchange

class NewExchange(BaseExchange):
    def fetch_data(self):
        # Implement API call with rate limiting
        pass

    def normalize_data(self, raw_data):
        # Convert to standard 12-column format
        pass
```

2. Register in `exchanges/exchange_factory.py`:
```python
from exchanges.new_exchange import NewExchange
# Add to imports and exchange_classes dict
```

3. Enable in `config/settings.py`:
```python
EXCHANGES = {
    'new_exchange': {'enabled': True, 'rate_limit': 30}
}
```

4. Test the implementation:
```bash
python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"
```

## Database Schema

**Core Tables** (all use UPSERT for atomic updates):
- `exchange_data`: Real-time rates (UNIQUE: exchange, symbol)
- `funding_rates_historical`: 30-day history (UNIQUE: exchange, symbol, funding_time)
- `funding_statistics`: Z-scores and percentiles
- `contract_metadata`: Lifecycle tracking (NEW→ACTIVE→STALE→INACTIVE)
- `arbitrage_spreads`: Cross-exchange opportunities

**Key Index**: Composite on (exchange, symbol, funding_time DESC) for time-series queries

## Frontend Architecture

### Component Design Systems
The dashboard uses **two parallel component libraries**:

**Modern Components** (`dashboard/src/components/Modern/`)
- Primary UI system used throughout the application
- ModernCard, ModernButton, ModernSelect, ModernInput, ModernToggle
- ModernTable (sortable, striped, hover states)
- ModernMultiSelect, ModernPagination, ModernTooltip, ModernBadge
- Clean, minimal design with consistent spacing and colors

**Neumorphic Components** (`dashboard/src/components/Neumorphic/`)
- Alternative design system with soft shadows
- NeumorphicCard, NeumorphicButton, NeumorphicSelect, NeumorphicToggle, NeumorphicTable
- Not actively used but available for alternative styling

**Component Organization**:
- `Cards/` - Metric display cards (StatCard, APRExtremeCard, DashboardStatsCard, SystemOverviewCard)
- `Charts/` - Data visualization (Sparkline, FundingChartTooltip, ArbitrageHistoricalChart)
- `Grid/` - Main data tables (AssetFundingGrid, HistoricalFundingView, ExchangeFilter)
- `Layout/` - Page structure (Header, navigation)
- `Ticker/` - Real-time updates (LiveFundingTicker, FundingCountdown)
- `Arbitrage/` - Arbitrage filtering components (ArbitrageFilterPanel, filter controls)

### React Hook Orchestration
The filter system uses a hierarchy of custom hooks:
```
useExchangeFilter()                    # Main orchestrator for exchange grid
  ├── useFilterPersistence()          # localStorage sync
  └── useFilterURL()                  # URL parameter sync

useArbitrageFilter()                   # Arbitrage opportunities filter
  └── localStorage persistence        # Maintains filter state across sessions
```

**Filter Priority**: URL parameters > localStorage > default state

**Performance Optimizations**:
- `useMemo` for expensive filtering/sorting operations
- 300ms debounced search
- Virtual scrolling for large datasets (react-window, react-window-infinite-loader)
- Pre-fetched contract data for instant search

## Non-Obvious Implementation Details

### Parallel vs Sequential Collection
- **Parallel** (default): ThreadPoolExecutor with 10 workers, 120s timeout per exchange
- **Sequential**: Staggers API calls (0s, 30s, 90s delays) to reduce load
- Configured in `config/settings.py`: `COLLECTION_MODE`

### Contract Lifecycle Management
Contracts automatically transition through states based on last_updated time:
- **STALE**: No updates for 24 hours
- **INACTIVE**: No updates for 48 hours
- Managed by `utils/contract_monitor.py`

### Background Process Coordination
`start.py` launches 4 background processes with specific dependencies:
1. Data collector (main.py --loop)
2. Z-score calculator (independent per contract)
3. Spread collector (requires arbitrage backfill)
4. Historical backfill (7-day refresh on startup)

### Cache Invalidation Timing
Cache is cleared AFTER database updates complete, not before. This prevents:
- Race conditions during collection
- Serving stale data mid-update
- Double-update scenarios

### Arbitrage Filter Logic
The exchange filter in `utils/arbitrage_scanner.py` (line 721) uses AND logic for multiple selections:
- **No exchanges selected**: Shows all arbitrage opportunities
- **1 exchange selected**: Shows all opportunities involving that exchange (either long or short)
- **2+ exchanges selected**: Shows ONLY opportunities BETWEEN the selected exchanges (both long AND short must be in selection)

This ensures the filter narrows results as more exchanges are selected, matching user expectations for multi-select filtering.

## Environment Requirements

### Python Packages NOT in requirements.txt
The following packages are used by the system but missing from requirements.txt:
```bash
pip install fastapi uvicorn psutil scipy websockets
```
**Note**: These should be added to requirements.txt. Current requirements.txt only includes: pandas, requests, psycopg2-binary, numpy, python-dotenv, aiohttp, asyncio-throttle, redis.

### Required Services
- PostgreSQL 15+ (port 5432)
- Redis 7+ (port 6379, optional with fallback)
- Node.js 18+ (for React dashboard)
- Docker (for PostgreSQL/Redis containers)

## File Management Rules
- **Never commit**: `*.log`, `.*.status`, `.*.lock`, `test*.json`, `.env`
- **Cross-platform paths**: Use `Path("config") / "settings.py"` not `"config/settings.py"`
- **Test artifacts**: Delete immediately after testing