# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Multi-exchange cryptocurrency funding rate aggregation system tracking 3,642 contracts across 15 exchanges with real-time updates, 30-day historical data, Z-score analysis, and arbitrage detection.

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
- **Critical**: API server creates database schema on first run (api.py:172-181)
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
Cross-exchange arbitrage scanning with statistical analysis and enhanced filtering:
- **ArbitrageScanner** (`utils/arbitrage_scanner.py`): Identifies funding rate spreads across exchanges
- **Statistical Significance**: Z-score and percentile calculations for spread opportunities
- **Spread Tracking**: Historical spread statistics in `arbitrage_spreads` table
- **Real-time Detection**: Calculates APR spreads, hourly rates, sync periods, and daily spreads
- **Cache Integration**: Redis caching with 30s TTL for arbitrage opportunities
- **API Endpoints**:
  - `/api/arbitrage/opportunities`: Legacy endpoint with basic pagination
  - `/api/arbitrage/opportunities-v2`: Enhanced endpoint with multi-parameter filtering
    - Exchange filtering (multi-select with AND logic)
    - Funding interval filtering (1h, 2h, 4h, 8h, variable)
    - APR spread range filtering (min/max)
    - Asset filtering (specific asset search)
    - Pagination (page size, current page)
    - Sort options (spread, asset, exchanges)
  - `/api/arbitrage/assets/search`: Search for assets in arbitrage opportunities
  - `/api/arbitrage/opportunity-detail/{asset}/{long_exchange}/{short_exchange}`: Detailed arbitrage opportunity data

## API Endpoints Reference

### Data Retrieval Endpoints
```bash
GET /api/funding-rates                      # Current funding rates with filters
GET /api/funding-rates-grid                 # Asset-based grid view
GET /api/historical/{symbol}                # Historical rates for specific symbol
GET /api/historical-funding/{symbol}        # Historical funding data with intervals
GET /api/historical-funding-by-asset/{asset}  # All contracts for an asset
GET /api/historical-funding-by-contract/{exchange}/{symbol}  # Contract-specific history
GET /api/current-funding/{asset}            # Current rate with countdown timer
GET /api/funding-sparkline/{symbol}         # Sparkline data for mini-charts
GET /api/contracts-by-asset/{asset}         # List all contracts for an asset
```

### Statistics & Analytics Endpoints
```bash
GET /api/statistics                         # Dashboard statistics
GET /api/statistics/summary                 # Overall system statistics
GET /api/statistics/extreme-values          # Statistical outliers and extremes
GET /api/top-apr/{limit}                    # Top APR contracts
GET /api/group-by-asset                     # Grouped by base asset
GET /api/contracts-with-zscores             # All contracts with Z-score data
GET /api/zscore-summary                     # Z-score summary statistics
```

### Arbitrage Endpoints
```bash
GET /api/arbitrage/opportunities            # Legacy arbitrage endpoint with basic pagination
GET /api/arbitrage/opportunities-v2         # Enhanced endpoint with multi-parameter filtering
GET /api/arbitrage/assets/search            # Search for assets in arbitrage opportunities
GET /api/arbitrage/opportunity-detail/{asset}/{long_exchange}/{short_exchange}  # Detailed opportunity data
```

### System Health & Performance
```bash
GET /api/health                             # Basic health check
GET /api/health/performance                 # System performance metrics
GET /api/health/cache                       # Cache health monitoring (Redis)
```

### Backfill Management
```bash
GET /api/backfill-status                    # Current backfill progress
GET /api/backfill/status                    # Detailed backfill status
GET /api/backfill/verify                    # Verify backfill completeness
POST /api/backfill/start                    # Start historical backfill
POST /api/backfill/stop                     # Stop running backfill
POST /api/backfill/retry                    # Retry failed backfills
```

### Settings Management
```bash
GET /api/settings                           # Retrieve current settings
PUT /api/settings                           # Update settings
POST /api/settings/validate                 # Validate settings without saving
GET /api/settings/backups                   # List available backups
POST /api/settings/restore                  # Restore from backup
GET /api/settings/export                    # Export settings as JSON
POST /api/settings/import                   # Import settings from JSON
POST /api/settings/reset                    # Reset to default settings
```

### Metadata & Discovery
```bash
GET /api/exchanges                          # List all exchanges
GET /api/assets                             # List all unique assets
GET /                                       # Root endpoint with system info
GET /api/test                               # Test endpoint for debugging
```

### System Control
```bash
POST /api/shutdown                          # Clean shutdown of services
```

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

# Frontend testing
cd dashboard && npm test                    # Run all React tests
cd dashboard && npm test -- --watch         # Run tests in watch mode
cd dashboard && npm test -- --coverage      # Run tests with coverage report

# Frontend builds
cd dashboard && npm run build               # Production build
cd dashboard && npx serve -s build          # Serve production build locally

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

# Linux/Mac: Find and kill process on port
lsof -i :8000
kill -9 <pid>

# Check logs for errors
tail -f data_collector.log | grep ERROR       # Linux/Mac
type data_collector.log | findstr "ERROR"     # Windows

# Test database connection
python database_tools.py check

# Monitor background processes
ps aux | grep -E "zscore|arbitrage|spread"    # Linux/Mac
tasklist | findstr "python"                   # Windows

# Redis cache monitoring
curl http://localhost:8000/api/health/cache   # Check cache health
docker exec -it exchange_redis redis-cli INFO stats  # Redis statistics
docker exec -it exchange_redis redis-cli DBSIZE      # Number of cached keys
docker exec -it exchange_redis redis-cli INFO memory # Memory usage

# Check specific cache keys
docker exec -it exchange_redis redis-cli KEYS "*funding-rates*"
docker exec -it exchange_redis redis-cli GET "cache_key_name"
docker exec -it exchange_redis redis-cli TTL "cache_key_name"  # Time to live

# Monitor cache performance
curl http://localhost:8000/api/health/performance | python -m json.tool

# Check arbitrage filter performance
curl "http://localhost:8000/api/arbitrage/opportunities-v2?exchanges=binance&exchanges=kucoin" -w "\nTime: %{time_total}s\n"

# View Z-score calculation status
curl http://localhost:8000/api/contracts-with-zscores | python -m json.tool | head -50

# Check backfill status
curl http://localhost:8000/api/backfill-status | python -m json.tool

# Monitor API response times
time curl -s http://localhost:8000/api/funding-rates-grid > /dev/null

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

# Data maintenance scripts (added in recent updates)
python scripts/cleanup_historical_data.py          # Remove old/invalid historical records
python scripts/fix_duplicate_funding_data.py       # Resolve duplicate entries
python scripts/retry_incomplete_contracts.py       # Retry failed contract fetches
python scripts/collect_spread_history.py           # Collect arbitrage spread history
```

### Database Maintenance Scripts

**cleanup_historical_data.py**
- Removes old, invalid, or corrupted historical funding rate records
- Identifies and deletes records with null/invalid funding rates
- Cleans up records outside the configured retention window
- Optimizes database storage and query performance

**fix_duplicate_funding_data.py**
- Detects and resolves duplicate funding rate entries
- Uses UNIQUE constraint (exchange, symbol, funding_time) to identify duplicates
- Keeps the most recent record when duplicates exist
- Prevents data inconsistencies in historical views

**retry_incomplete_contracts.py**
- Identifies contracts with missing or incomplete historical data
- Retries fetching data for contracts that failed during initial collection
- Particularly useful after network issues or API rate limit errors
- Ensures complete 30-day historical coverage

**collect_spread_history.py**
- Populates the `arbitrage_spreads` table with historical spread data
- Calculates cross-exchange funding rate spreads over time
- Essential for arbitrage opportunity analysis and historical tracking
- Should be run after backfilling historical funding rates
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

## Exchange Coverage

### System Statistics (Current)
- **Total Contracts**: 3,642 perpetual futures
- **Active Exchanges**: 15 (6 CEX, 9 DEX)
  - **CEX Contracts**: 2,690 (73.9%)
  - **DEX Contracts**: 952 (26.1%)
- **Unique Assets**: ~800+ consolidated across all exchanges
- **Update Frequency**: 30-second real-time refresh (parallel mode)
- **Historical Coverage**: 30-day rolling window
- **Funding Intervals Supported**: 1h, 2h, 4h, 8h, variable
- **Recent Expansion**: Added 8 new exchanges (+1,367 contracts, +60% growth)

### Supported Exchanges

The system now supports 15 exchanges (6 CEX, 9 DEX, 2 disabled):

### Centralized Exchanges (CEX)

#### Binance (592 contracts)
- **Funding Intervals**: 1h, 4h, 8h
- **Market Types**: USD-M (USDT-margined) and COIN-M (coin-margined)
- **Base Asset Normalization**: Handles `1000`, `1000000`, and `1MBABYDOGE` prefixes
- **API**: Separate endpoints for USD-M and COIN-M futures
- **Rate Limit**: 40 requests/second
- **Historical Data**: Unlimited time range available

#### KuCoin (522 contracts)
- **Funding Intervals**: 1h, 2h, 4h, 8h
- **Base Asset Normalization**: Handles `1000000`, `10000`, `1000` prefixes (checked in order)
- **Special Cases**: `1000X` → `X` (X token), `XBT` → `BTC`
- **Rate Limit**: 30 requests/second
- **Historical Data**: Recent data only from API

#### ByBit (667 contracts)
- **Funding Intervals**: 1h, 2h, 4h, 8h
- **Market Types**: Linear (USDT/USDC-margined) and Inverse (USD-margined)
- **Base Asset Normalization**: Handles up to 8-digit multiplier prefixes
- **API**: V5 API with cursor-based pagination
- **Rate Limit**: 50 requests/second
- **Historical Data**: 200 records per request with pagination

#### MEXC (826 contracts)
- **Funding Intervals**: 8h (standard)
- **Features**: Bulk fetching optimization with fallback to batch processing
- **Base Asset Normalization**: Handles numerical prefixes (`1000`, `10000`, `1000000`) and `k` prefix
- **API**: REST API with contract details endpoint
- **Rate Limit**: Standard rate limiting with batch optimization
- **Historical Data**: Available via API

#### Backpack (63 contracts)
- **Funding Intervals**: 1h (all contracts)
- **Market Type**: USDC-margined contracts
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kBONK_USDC_PERP` → `BONK`)
- **Historical Data**: 7+ months available
- **Rate Limit**: ~20 requests/second

#### Deribit (20 contracts)
- **Funding Intervals**: 8h
- **Market Type**: Options-focused exchange with perpetuals
- **API**: JSON-RPC API integration
- **Features**: Comprehensive options and perpetuals support
- **Base Asset Normalization**: Standard format from API

### Decentralized Exchanges (DEX)

#### Hyperliquid (182 contracts)
- **Funding Intervals**: 1h (all contracts)
- **Platform**: DEX with 1-hour funding intervals
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kPEPE` → `PEPE`)
- **Special Notations**: `k` prefix, `@` prefix for some contracts
- **Open Interest**: Reported in base asset units
- **Authentication**: No authentication required

#### Drift (51 contracts)
- **Funding Intervals**: 1h
- **Platform**: Solana-based DEX
- **Base Asset Normalization**: Handles `1M` (millions) and `1K` (thousands) prefixes, removes `-PERP` suffix
- **Symbol Format**: XXX-PERP format
- **Features**: Excludes betting markets (perpetuals only)
- **Rate Limit**: No strict limits

#### Aster (123 contracts)
- **Funding Intervals**: 4h
- **Platform**: DEX with async/parallel fetching
- **Base Asset Normalization**: Handles `1000`, `k` prefixes
- **Market Type**: USDT-margined perpetual contracts
- **Rate Limit**: 40 requests/second maximum
- **Features**: Optimized for performance

#### Lighter (91 contracts)
- **Funding Intervals**: 8h (CEX-standard equivalent)
- **Platform**: DEX aggregator combining rates from Binance, OKX, ByBit
- **Base Asset Normalization**: Handles standard multiplier prefixes (`1000000`, `100000`, `10000`, `1000`, `100`, `k`, `1M`)
- **Rate Conversion**: Divides API rate by 8 for CEX-standard alignment
- **Market ID**: Unique numeric market_id for each contract
- **Historical Data**: 1-hour resolution (up to 1000 records per request)

#### Paradex (122 contracts)
- **Funding Intervals**: 1h, 2h, 4h, 8h (variable)
- **Platform**: Starknet-based DEX
- **Features**: Real-time funding rates and prices
- **API**: REST API with markets endpoint
- **Asset Kind**: Filters for PERP (perpetual) contracts

#### Orderly (139 contracts)
- **Funding Intervals**: 8h
- **Platform**: Orderly Network DEX
- **Features**: Perpetual contracts with funding rates and open interest
- **Base Asset Normalization**: Uses symbol parsing to extract base and quote assets
- **API**: REST API with instruments endpoint

#### Pacifica (25 contracts)
- **Funding Intervals**: 1h
- **Platform**: Pacifica Finance DEX
- **Features**: Rich data including funding rates, prices, and open interest
- **API**: REST API with prices endpoint
- **Base Asset Normalization**: Standard format from API

#### Hibachi (20 contracts)
- **Funding Intervals**: 8h
- **Platform**: High-performance, privacy-focused DEX
- **Features**: Combines speed of centralized platforms with cryptographic integrity
- **Known Markets**: BTC, ETH, SOL with up to 5x leverage
- **API**: REST API with market data endpoints

#### dYdX (199 contracts)
- **Funding Intervals**: 8h
- **Platform**: dYdX v4 DEX
- **API**: Indexer API for perpetual market data
- **Features**: Active market filtering, comprehensive perpetual support
- **Base Asset Normalization**: Extracts from ticker format (e.g., "BTC-USD" → "BTC")

### Disabled Exchanges

#### EdgeX and ApeX
- **Status**: Disabled - API not accessible
- **Reason**: API endpoints unavailable or authentication issues

#### Kraken
- **Status**: Ready but disabled
- **Contracts**: Implementation available for 353 contracts
- **Reason**: Can be enabled when needed

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
- `Arbitrage/` - Enhanced arbitrage filtering components
  - ArbitrageFilterPanel: Main filter orchestration with exchange, interval, APR, and liquidity filters
  - APRRangeFilter: Min/max APR spread filtering with real-time validation
  - IntervalSelector: Funding interval selection (1h, 2h, 4h, 8h, variable)
  - LiquidityFilter: Asset liquidity filtering with autocomplete
  - AssetAutocomplete: Smart asset search with debouncing and suggestions
  - ArbitrageFilter.module.css: Comprehensive styling for filter components
  - __tests__/ArbitrageFilter.test.tsx: Full test coverage for filter logic

### React Hook Orchestration
The filter system uses a hierarchy of custom hooks:
```
useExchangeFilter()                    # Main orchestrator for exchange grid
  ├── useFilterPersistence()          # localStorage sync
  └── useFilterURL()                  # URL parameter sync

useArbitrageFilter()                   # Enhanced arbitrage opportunities filter
  ├── Exchange filtering              # Multi-select exchange filter with persistence
  ├── Interval filtering              # 1h, 2h, 4h, 8h, variable intervals
  ├── APR range filtering             # Min/max APR spread with validation
  ├── Asset filtering                 # Autocomplete asset search
  ├── Liquidity filtering             # Filter by asset liquidity
  ├── Pagination state                # Page size and current page
  └── localStorage persistence        # Maintains filter state across sessions
```

**Filter Priority**: URL parameters > localStorage > default state

**Performance Optimizations**:
- `useMemo` for expensive filtering/sorting operations
- 300ms debounced search for asset autocomplete
- Virtual scrolling for large datasets (react-window, react-window-infinite-loader)
- Pre-fetched contract data for instant search
- Real-time validation for APR range inputs
- Efficient re-rendering with React.memo

## Non-Obvious Implementation Details

### Parallel vs Sequential Collection
- **Parallel** (default): ThreadPoolExecutor with 10 workers, 120s timeout per exchange
- **Sequential** (disabled by default): Staggers API calls (0s, 30s, 90s delays) to reduce load
- Configured in `config/settings.py`: `ENABLE_SEQUENTIAL_COLLECTION = False`

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

### CRITICAL: Missing Python Dependencies
**IMPORTANT**: The following packages are used by the system but are NOT in requirements.txt. Install them manually:
```bash
pip install fastapi uvicorn psutil scipy websockets
```

**Why this matters**: Without these packages, the system will fail to start:
- `fastapi` + `uvicorn`: Required for API server (api.py)
- `psutil`: Required for system monitoring and process management
- `scipy`: Required for statistical calculations (Z-scores)
- `websockets`: Required for real-time updates

**Current requirements.txt only includes**: pandas, requests, psycopg2-binary, numpy, python-dotenv, aiohttp, asyncio-throttle, redis

**Recommended action**: Add these packages to requirements.txt for future installations.

### Required Services
- **Python 3.8+**: Core language runtime
- **PostgreSQL 15+**: Primary database (port 5432)
- **Redis 7+**: Caching layer (port 6379, optional with fallback to in-memory cache)
- **Node.js 18+**: Frontend runtime for React dashboard (port 3000)
- **Docker Desktop**: Container runtime for PostgreSQL/Redis

## File Management Rules
- **Never commit**: `*.log`, `.*.status`, `.*.lock`, `test*.json`, `.env`
- **Cross-platform paths**: Use `Path("config") / "settings.py"` not `"config/settings.py"`
- **Test artifacts**: Delete immediately after testing