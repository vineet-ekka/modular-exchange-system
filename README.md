# Multi-Exchange Cryptocurrency Funding Rate Dashboard (MVP)

An MVP cryptocurrency funding rate tracking system supporting 8 exchanges with real-time updates, historical data analysis, and cross-exchange arbitrage detection.

**Note: This is a minimum viable product (MVP) for demonstration and development purposes only. Not intended for production use.**

## Table of Contents

- [Quick Start](#quick-start)
- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Features](#features)
- [Exchange Coverage](#exchange-coverage)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Dashboard Features](#dashboard-features)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Technical Implementation](#technical-implementation)
- [Development History](#development-history)
- [Performance Metrics](#performance-metrics)
- [Troubleshooting](#troubleshooting)
- [Scripts & Utilities](#scripts--utilities)

## Quick Start

### One-Command Launch
```bash
# Starts everything automatically
python start.py

# On Windows, can also use:
python start.py
```

This automatically:
1. Checks prerequisites (Python, Node, Docker)
2. Starts PostgreSQL database
3. Installs npm dependencies (if needed)
4. Starts API server
5. Starts React dashboard  
6. Starts data collector with 30-second updates (logs to `data_collector.log`)
7. Starts background historical data refresh (30-day backfill)
8. Opens browser automatically

### Access Points
- **Dashboard**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## System Overview

### Core Capabilities
- **Multi-Exchange Collection**: Real-time funding rates from Binance, KuCoin, ByBit, Hyperliquid, Aster, Lighter, Backpack, and Drift
- **Sequential Collection**: Staggered API calls to manage rate limits (0s, 30s, 120s, 180s delays)
- **Asset Aggregation**: 656 unique assets consolidated from 2,275 individual contracts
- **Historical Analysis**: 30-day rolling window with automated backfill and gap detection
- **Dashboard**: React-based interface with real-time updates and charts
- **APR Calculations**: Automatic annualized percentage rate computation
- **Data Export**: CSV export functionality for historical data
- **Redis Caching**: High-performance caching with 5s TTL for contracts, 10s for summaries

### System Statistics
- **Total Contracts**: 2,275 perpetual futures
- **Active Exchanges**: 8 (Binance, KuCoin, ByBit, Hyperliquid, Aster, Lighter, Backpack, Drift)
- **Unique Assets**: 656 with cross-exchange comparison
- **Update Frequency**: 30-second real-time refresh
- **Historical Coverage**: 30-day rolling window
- **API Endpoints**: 25+ RESTful endpoints
- **Database Tables**: 6 (real-time, historical, statistics, metadata, arbitrage, funding_statistics)
- **Infrastructure**: PostgreSQL database, Redis cache, pgAdmin web interface

## Architecture

### System Architecture Diagram
```
┌─────────────────────────────────────────────┐
│          Exchange APIs                      │
│  (Binance, KuCoin, ByBit, Hyperliquid,     │
│   Aster, Lighter, Backpack, Drift)         │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Data Collection Layer                  │
│  (Rate-limited, Sequential/Parallel modes)  │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         Data Processing                     │
│  (Normalization, APR calc, Z-scores)        │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         PostgreSQL Database                 │
│  (6 tables: real-time, historical, statistics,│
│   metadata, arbitrage, funding_statistics)    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         FastAPI Backend                     │
│  (RESTful API, Redis Cache, Arbitrage,      │
│   WebSocket)                                │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      React Dashboard                        │
│  (Real-time updates, Charts, Export)        │
└─────────────────────────────────────────────┘
```

### Component Overview

#### 1. Data Collection Layer
- **main.py**: Orchestrates data collection with health tracking
- **Exchange modules**: Factory pattern with base class inheritance
- **Rate limiting**: Prevents API throttling with configurable delays
- **Sequential collection**: Staggers API calls across exchanges

#### 2. Data Processing
- **DataProcessor**: Normalizes exchange-specific data formats
- **APR calculation**: Accounts for different funding intervals
- **Validation**: Ensures data integrity and completeness
- **Symbol mapping**: Handles exchange-specific naming conventions

#### 3. Data Storage
- **PostgreSQL**: Primary database via Docker container
- **UPSERT operations**: Prevents duplicate entries
- **Historical retention**: 30-day rolling window
- **Indexes**: Optimized for time-series queries

#### 4. API Backend
- **FastAPI**: High-performance async Python framework
- **CORS enabled**: Supports React frontend
- **Settings management**: Hot-reload configuration
- **Error handling**: Comprehensive error responses

#### 5. Frontend Dashboard
- **React 19**: Modern JavaScript framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **Recharts**: Interactive data visualization

## Features

### Real-time Data Collection
- 30-second update cycle for all exchanges
- Sequential collection mode to manage API rate limits
- Parallel collection mode for development
- Automatic retry with exponential backoff
- Health monitoring and status reporting

### Historical Data Management
- 30-day rolling window of funding rates
- Synchronized data windows across exchanges
- Gap filling for missing data points
- Materialized views for performance
- Automated backfill scripts

### Dashboard Features
- Asset-based grid view (656 assets)
- Expandable rows showing individual contracts
- **Funding Interval Display**: Shows funding frequency (1h, 2h, 4h, 8h) for each contract
- **Enhanced Search**: Search both assets AND contracts simultaneously
- **Auto-expansion**: Automatically expands assets when contracts match search
- **Search Highlighting**: Matching contracts highlighted in blue
- Multi-contract historical charts
- Live funding rate ticker
- Countdown timer to next funding
- Color-coded rates (green positive, red negative)
- Advanced sorting and filtering
- CSV export functionality
- Settings management interface
- Backfill progress indicator
- Z-score statistical analysis
- Cross-exchange arbitrage detection
- WebSocket real-time updates

### API Capabilities
- RESTful endpoints for all data
- Real-time and historical data access
- Aggregated statistics with Z-scores
- Asset-based queries
- Cross-exchange arbitrage opportunities
- Settings management endpoints
- Health and performance monitoring
- WebSocket endpoint for real-time updates

## Exchange Coverage

### Active Exchanges

#### Binance (589 contracts)
| Market Type | Contracts | Funding Intervals | Features |
|------------|-----------|-------------------|----------|
| USD-M | 553 | 4h (64.3%), 8h (34.6%), 1h (1.0%) | USDT-margined perpetuals |
| COIN-M | 36 | 8 hours | Coin-margined perpetuals |

#### KuCoin (519 contracts)
| Funding Interval | Contracts | Percentage | Notable Examples |
|-----------------|-----------|------------|------------------|
| 4 hours | 324 | 62.8% | Higher frequency |
| 8 hours | 178 | 34.5% | Standard perpetuals |
| 1 hour | 14 | 2.7% | CARVUSDTM, XEMUSDTM |
| 2 hours | 3 | 0.6% | MAGICUSDTM |

#### ByBit (663 contracts)
| Market Type | Contracts | Funding Intervals | Features |
|------------|-----------|-------------------|----------|
| Linear | 639 | 4h (52.3%), 8h (38.8%), 1h (5.9%), 2h (3.0%) | USDT/USDC-margined |
| Inverse | 24 | 8h (100%) | USD-margined perpetuals |

#### Backpack (63 contracts)
| Funding Interval | Contracts | Percentage | Features |
|-----------------|-----------|------------|----------|
| 1 hour | 63 | 100% | All contracts now 1-hour funding |

#### Hyperliquid (182 contracts)
| Funding Interval | Contracts | Percentage | Features |
|-----------------|-----------|------------|----------|
| 1 hour | 182 | 100% | Unique DEX with hourly funding |

#### Aster (120 contracts)
| Funding Interval | Contracts | Rate Limit | Features |
|-----------------|-----------|------------|----------|
| 4 hours | 120 | 40 req/s | DEX with async/parallel fetching, USDT pairs |

#### Lighter (91 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 8 hours | 91 | DEX Aggregator | CEX-standard equivalent, aggregates from Binance/OKX/ByBit |

#### Drift (48 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 1 hour | 48 | Solana | Solana-based DEX, excludes betting markets |

### Ready for Integration
- **Kraken**: 353 contracts (module available)
- **Deribit**: 20 contracts (module available)

**Total Active**: 2,275 perpetual contracts across 656 unique assets

## Installation & Setup

### Prerequisites
- **Python 3.8+** - [Download](https://python.org)
- **Node.js 16+** - [Download](https://nodejs.org)  
- **Docker Desktop** - [Download](https://docker.com)

### Manual Setup

#### 1. Clone Repository
```bash
git clone https://github.com/yourusername/modular-exchange-system.git
cd modular-exchange-system
```

#### 2. Install Dependencies
```bash
# Python dependencies from requirements.txt
pip install -r requirements.txt

# CRITICAL: Install missing dependencies not in requirements.txt
pip install fastapi uvicorn psutil scipy websockets

# Dashboard dependencies
cd dashboard && npm install && cd ..

# For Z-Score implementation (in progress)
cd dashboard && npm install react-window react-window-infinite-loader @types/react-window && cd ..
```

#### 3. Start PostgreSQL
```bash
docker-compose up -d

# Verify services are running
docker ps  # Should show exchange_postgres, redis, and pgAdmin
```

#### 4. Configure Environment
Create `.env` file:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

#### 5. Start Services
```bash
# API Server (Terminal 1)
python api.py

# Dashboard (Terminal 2)
cd dashboard && npm start

# Data Collector (Terminal 3)
python main.py --loop --interval 30 --quiet
```

## Configuration

### Main Settings (`config/settings.py`)
```python
# Exchange Configuration
EXCHANGES = {
    'binance': True,      # 589 contracts
    'kucoin': True,       # 519 contracts
    'bybit': True,        # 663 contracts (linear + inverse)
    'hyperliquid': True,  # 182 contracts (1-hour funding)
    'aster': True,        # 120 contracts (4-hour funding)
    'lighter': True,      # 91 contracts (8-hour DEX aggregator)
    'backpack': True,     # 63 contracts (1-hour funding)
    'drift': True,        # 48 contracts (1-hour funding)
    'deribit': False,     # Ready but disabled
    'kraken': False       # Ready but disabled
}

# Data Collection Settings
ENABLE_SEQUENTIAL_COLLECTION = True  # Stagger API calls
EXCHANGE_COLLECTION_DELAY = 30      # Seconds between exchanges
ENABLE_OPEN_INTEREST_FETCH = True   # Fetch OI data
ENABLE_FUNDING_RATE_FETCH = True    # Fetch funding rates

# Display Settings
DISPLAY_LIMIT = 100                 # Results per page
DEFAULT_SORT_COLUMN = "apr"         # Default sort field
DEFAULT_SORT_ASCENDING = True       # Sort order

# Historical Data Settings
ENABLE_HISTORICAL_COLLECTION = True
HISTORICAL_FETCH_INTERVAL = 300     # 5 minutes
HISTORICAL_SYNC_ENABLED = True      # Synchronized windows
HISTORICAL_ALIGN_TO_MIDNIGHT = True # Clean boundaries
HISTORICAL_WINDOW_DAYS = 30         # Default window size
```

### Sequential Collection (`config/sequential_config.py`)
```python
# Custom collection schedules
EXCHANGE_SCHEDULE = [
    ("binance", 0),       # Starts immediately
    ("kucoin", 30),       # 30s delay
    ("bybit", 60),        # 60s delay
    ("hyperliquid", 120), # 120s delay
    ("aster", 150),       # 150s delay
    ("lighter", 180),     # 180s delay
    ("backpack", 210),    # 210s delay
    ("drift", 240)        # 240s delay
]

# Schedule presets: "default", "fast", "conservative", "priority"
ACTIVE_SCHEDULE = "default"
```

## API Documentation

### Complete API Endpoints (39 Total)

#### Data Retrieval Endpoints
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

#### Statistics & Analytics Endpoints
```bash
GET /api/statistics                         # Dashboard statistics
GET /api/statistics/summary                 # Overall system statistics
GET /api/statistics/extreme-values          # Statistical outliers and extremes
GET /api/top-apr/{limit}                    # Top APR contracts
GET /api/group-by-asset                     # Grouped by base asset
GET /api/contracts-with-zscores             # All contracts with Z-score data
GET /api/zscore-summary                     # Z-score summary statistics
```

#### Arbitrage Endpoints
```bash
GET /api/arbitrage/opportunities            # Legacy arbitrage endpoint with basic pagination
GET /api/arbitrage/opportunities-v2         # Enhanced endpoint with multi-parameter filtering
GET /api/arbitrage/assets/search            # Search for assets in arbitrage opportunities
GET /api/arbitrage/opportunity-detail/{asset}/{long_exchange}/{short_exchange}  # Detailed opportunity data
```

#### System Health & Performance
```bash
GET /api/health                             # Basic health check
GET /api/health/performance                 # System performance metrics
GET /api/health/cache                       # Cache health monitoring (Redis)
```

#### Backfill Management
```bash
GET /api/backfill-status                    # Current backfill progress
GET /api/backfill/status                    # Detailed backfill status
GET /api/backfill/verify                    # Verify backfill completeness
POST /api/backfill/start                    # Start historical backfill
POST /api/backfill/stop                     # Stop running backfill
POST /api/backfill/retry                    # Retry failed backfills
```

#### Settings Management
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

#### Metadata & Discovery
```bash
GET /api/exchanges                          # List all exchanges
GET /api/assets                             # List all unique assets
GET /                                       # Root endpoint with system info
GET /api/test                               # Test endpoint for debugging
```

#### System Control
```bash
POST /api/shutdown                          # Clean shutdown of services
```

### Request/Response Examples

#### Get Funding Rates Grid
```bash
GET /api/funding-rates-grid

Response:
{
  "BTC": {
    "exchanges": {
      "Binance": {
        "funding_rate": 0.0001,
        "apr": 10.95,
        "contracts": ["BTCUSDT", "BTCUSDC"]
      },
      "KuCoin": {
        "funding_rate": 0.00009,
        "apr": 9.86,
        "contracts": ["XBTUSDTM"]
      }
    }
  }
}
```

#### Get Historical Funding
```bash
GET /api/historical-funding-by-asset/BTC?timeRange=7D

Response:
{
  "asset": "BTC",
  "data": [
    {
      "timestamp": "2025-08-20 00:00",
      "BTCUSDT": {
        "funding_rate": 0.0001,
        "apr": 10.95
      },
      "XBTUSDTM": {
        "funding_rate": 0.00009,
        "apr": 9.86
      }
    }
  ]
}
```

## Dashboard Features

### Asset Grid View
- **Consolidated Display**: 656 assets across all exchanges
- **Multi-Exchange Columns**: Side-by-side comparison
- **Expandable Details**: Click to see individual contracts
- **Color Coding**: Visual indicators for rate direction
- **Advanced Search**: 
  - Search assets by name (e.g., "BTC", "ETH")
  - Search contracts by symbol (e.g., "BTCUSDT", "XBTUSDTM")
  - Search by partial match (e.g., "USDT" finds all USDT pairs)
  - Search by exchange name (e.g., "Binance", "KuCoin")
  - Auto-expands assets when contracts match
  - Highlights matching contracts in blue
- **Sorting**: Multi-column sorting with indicators

### Historical Data View
- **Table Display**: Clean tabular presentation of funding rate history
- **Latest First**: Historical data ordered from most recent to oldest
- **Multi-Contract**: View data for multiple contracts per asset
- **APR Display**: Annualized rates for comparison
- **Contract Selection**: Dropdown selector for specific contract views
- **Live Updates**: Real-time ticker showing current rates
- **Export**: Download data as CSV

### Real-time Monitoring
- **Live Ticker**: Current funding rates
- **Countdown Timer**: Time to next funding
- **Auto-refresh**: 30-second updates
- **Progress Indicator**: Backfill status

### Settings Management
- **Hot Reload**: Change settings without restart
- **Validation**: Real-time configuration checking
- **Backup/Restore**: Configuration management
- **Import/Export**: JSON configuration files

## Project Structure

```
modular_exchange_system/
├── main.py                         # Main data collector orchestrator
├── api.py                          # FastAPI backend server
├── start.py                        # One-command startup script
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # PostgreSQL container setup
├── .env.example                    # Environment variables template
│
├── config/                         # Configuration files
│   ├── settings.py                 # Main system settings
│   ├── sequential_config.py        # Sequential collection config
│   ├── settings_manager.py         # Dynamic settings management
│   └── validator.py                # Configuration validator
│
├── dashboard/                      # React frontend application
│   ├── public/                     # Static assets
│   ├── src/                        # Source code
│   │   ├── components/             # React components
│   │   │   ├── BackfillProgress.tsx
│   │   │   ├── Cards/              # Metric display cards
│   │   │   ├── Grid/               # Asset grid components
│   │   │   │   ├── AssetFundingGrid.tsx
│   │   │   │   └── HistoricalFundingView.tsx
│   │   │   ├── Layout/             # Layout components
│   │   │   ├── Settings/           # Settings management
│   │   │   └── Ticker/             # Live ticker components
│   │   ├── pages/                 # Page components
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── HistoricalFundingPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── services/               # API services
│   │   │   └── api.ts
│   │   └── App.tsx                # Main app component
│   ├── package.json               # Node dependencies
│   └── tsconfig.json              # TypeScript configuration
│
├── database/                      # Database management
│   └── postgres_manager.py        # PostgreSQL operations
│
├── data_processing/               # Data processing modules
│   └── data_processor.py          # Transformation & APR calculation
│
├── exchanges/                     # Exchange integrations
│   ├── base_exchange.py           # Abstract base class
│   ├── binance_exchange.py        # Binance integration
│   ├── kucoin_exchange.py         # KuCoin integration
│   ├── bybit_exchange.py          # ByBit integration
│   ├── backpack_exchange.py       # Backpack integration
│   ├── hyperliquid_exchange.py    # Hyperliquid integration
│   ├── aster_exchange.py          # Aster DEX integration
│   ├── lighter_exchange.py        # Lighter DEX aggregator integration
│   ├── drift_exchange.py          # Drift Solana DEX integration
│   ├── kraken_exchange.py         # Kraken (ready but disabled)
│   ├── deribit_exchange.py        # Deribit (ready but disabled)
│   └── exchange_factory.py        # Factory pattern manager
│
├── scripts/                       # Utility scripts
│   ├── unified_historical_backfill.py    # Multi-exchange backfill
│   ├── fix_funding_intervals.py          # Data maintenance
│   └── hyperliquid_gap_filler.py         # Specific gap filling
│
├── sql/                           # Database schemas
│   ├── init/                      # Initial table creation
│   └── performance/               # Indexes and optimization
│
├── utils/                         # Utility modules
│   ├── logger.py                  # Logging configuration
│   ├── rate_limiter.py            # API rate limiting
│   ├── health_tracker.py          # System health monitoring
│   ├── health_check.py            # Health status reporting
│   ├── data_validator.py          # Data validation
│   ├── contract_monitor.py        # Contract health monitoring
│   ├── zscore_calculator.py       # Z-score statistical analysis
│   ├── arbitrage_scanner.py       # Cross-exchange arbitrage detection
│   └── redis_cache.py             # Redis caching layer
│
├── database_tools.py              # Consolidated database utilities
└── shutdown_dashboard.py          # Clean shutdown utility
```

## Database Schema

### Main Table: exchange_data
```sql
CREATE TABLE exchange_data (
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
    UNIQUE(exchange, symbol)
);
```

### Historical Table: funding_rates_historical
```sql
CREATE TABLE funding_rates_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_rate NUMERIC(20, 10) NOT NULL,
    funding_time TIMESTAMP WITH TIME ZONE NOT NULL,
    mark_price NUMERIC(20, 10),
    funding_interval_hours INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, funding_time)
);

-- Performance index
CREATE INDEX idx_funding_historical_composite 
ON funding_rates_historical(exchange, symbol, funding_time DESC);
```

### Analytics View
```sql
CREATE MATERIALIZED VIEW funding_rate_analytics AS
SELECT 
    exchange,
    symbol,
    DATE(funding_time) as date,
    AVG(funding_rate) as avg_funding_rate,
    STDDEV(funding_rate) as volatility,
    MIN(funding_rate) as min_rate,
    MAX(funding_rate) as max_rate,
    COUNT(*) as data_points
FROM funding_rates_historical
GROUP BY exchange, symbol, DATE(funding_time);
```

### Statistical Tables

```sql
-- Z-score statistics table
CREATE TABLE funding_statistics (
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
);

-- Contract metadata table
CREATE TABLE contract_metadata (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_interval_hours INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE,
    UNIQUE(exchange, symbol)
);

-- Arbitrage spreads table
CREATE TABLE arbitrage_spreads (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(50) NOT NULL,
    exchange_a VARCHAR(50) NOT NULL,
    exchange_b VARCHAR(50) NOT NULL,
    funding_rate_a NUMERIC(20, 10),
    funding_rate_b NUMERIC(20, 10),
    apr_spread NUMERIC(20, 10),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset, exchange_a, exchange_b, timestamp)
);
```

## Technical Implementation

### APR Calculation Formula
```python
# Based on funding interval
if funding_interval_hours == 1:
    apr = funding_rate * 8760 * 100  # 365 * 24
elif funding_interval_hours == 2:
    apr = funding_rate * 4380 * 100  # 365 * 24 / 2
elif funding_interval_hours == 4:
    apr = funding_rate * 2190 * 100  # 365 * 24 / 4
elif funding_interval_hours == 8:
    apr = funding_rate * 1095 * 100  # 365 * 24 / 8
```

### Symbol Mapping
| Asset | Binance | KuCoin | Backpack | Hyperliquid |
|-------|---------|---------|----------|-------------|
| Bitcoin | BTCUSDT | XBTUSDTM | BTC_USDC_PERP | BTCUSD |
| Ethereum | ETHUSDT | ETHUSDTM | ETH_USDC_PERP | ETHUSD |
| Solana | SOLUSDT | SOLUSDTM | SOL_USDC_PERP | SOLUSD |

### Exchange-Specific Features

#### Binance
- Separate endpoints for USD-M and COIN-M futures
- Dynamic funding interval detection
- Historical data unlimited time range
- Rate limit: 40 requests/second
- **Base Asset Normalization**: Handles `1000` prefix (e.g., `1000SHIBUSDT` → `SHIB`), `1000000` prefix (e.g., `1000000MOGUSDT` → `MOG`), and `1MBABYDOGE` (e.g., `1MBABYDOGEUSDT` → `BABYDOGE`)

#### KuCoin
- XBT prefix for Bitcoin (XBT → BTC normalization)
- Multiple funding intervals (1h, 2h, 4h, 8h)
- Recent data only from API
- Rate limit: 30 requests/second
- **Base Asset Normalization**: Handles `1000000`, `10000`, `1000` prefixes (checked in order), and `1MBABYDOGE`
  - `1000000MOGUSDTM` → `MOG`
  - `10000CATUSDTM` → `CAT`
  - `1000BONKUSDTM` → `BONK`
  - `1000XUSDTM` → `X` (special case: 1000X is X token with 1000x denomination)
  - `1MBABYDOGEUSDTM` → `BABYDOGE` (1M = 1 Million denomination)

#### ByBit
- V5 API with versioned endpoints
- Dual markets: Linear (USDT/USDC) and Inverse (USD) perpetuals
- Mixed funding intervals across contracts (1h, 2h, 4h, 8h)
- Cursor-based pagination for instruments (limit: 1000 per page)
- Rate limit: 50 requests/second
- Historical data: 200 records per request with pagination support
- **Base Asset Normalization**: Uses baseCoin field from API, handles up to 8-digit multiplier prefixes
  - `10000000SHIB` → `SHIB` (10 million multiplier)
  - `1000000BABYDOGE` → `BABYDOGE` (1 million multiplier)
  - `100000MOG` → `MOG` (100k multiplier)
  - `10000LADYS` → `LADYS` (10k multiplier)
  - `1000FLOKI` → `FLOKI` (1k multiplier)

#### Backpack
- USDC-margined contracts
- Recently changed to all 1-hour funding
- 7+ months historical data available
- Rate limit: ~20 requests/second
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kBONK_USDC_PERP` → `BONK`)

#### Hyperliquid
- DEX with 1-hour funding intervals
- Open interest in base asset units
- No authentication required
- Special notations (k prefix, @ prefix)
- Contract naming: Simple asset names (e.g., "BTC" not "BTCUSDT")
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kPEPE` → `PEPE`)

#### Aster
- DEX with 4-hour funding intervals
- Async/parallel fetching for improved performance
- USDT-margined perpetual contracts
- Rate limit: 40 requests/second maximum
- **Base Asset Normalization**: Handles multiple prefixes:
  - `1000` prefix (e.g., `1000FLOKI` → `FLOKI`)
  - `k` prefix for thousands (e.g., `kX` → `X`)
  - Numerical prefix removal for clean asset names

#### Lighter
- DEX aggregator combining rates from multiple CEXs (Binance, OKX, ByBit)
- 8-hour CEX-standard equivalent funding rate format
- No authentication required for public REST API
- Unique numeric market_id for each contract
- 1-hour resolution historical data (up to 1000 records per request)
- Rate conversion: Divides API rate by 8 for CEX-standard alignment
- **Base Asset Normalization**: Handles standard multiplier prefixes
  - `1000000XXX` → `XXX`, `100000XXX` → `XXX`, `10000XXX` → `XXX`, `1000XXX` → `XXX`
  - `1MXXX` → `XXX` (1 million multiplier)
  - `100XXX` → `XXX`, `kXXX` → `XXX`

#### Drift
- Solana-based DEX with 1-hour funding intervals
- No strict rate limits
- Excludes betting markets (perpetuals only)
- **Symbol Format**: XXX-PERP format requires suffix removal
- **Base Asset Normalization**: Handles special prefixes:
  - `1M` prefix for millions (e.g., `1MBONK` → `BONK`, `1MPEPE` → `PEPE`)
  - `1K` prefix for thousands (e.g., `1KMEW` → `MEW`, `1KWEN` → `WEN`)
  - `-PERP` suffix removal for all contracts

### Performance Optimizations

#### Database
- Composite indexes on (exchange, symbol, funding_time)
- UPSERT operations prevent duplicates
- Materialized views for analytics
- Connection pooling for concurrent access

#### Frontend
- Lazy loading for contract details
- Memoized calculations
- Virtual scrolling for large tables
- Debounced search inputs
- React.memo for component optimization

#### API
- Batch processing for multiple symbols
- Timestamp normalization for alignment
- Efficient query joins between tables
- Async request handling

## Development History

### Phase Timeline

#### Phase 1-4: Core System (2025-08-07)
- Binance integration with 541 contracts
- PostgreSQL database setup
- FastAPI backend implementation
- React dashboard foundation
- Historical data collection system

#### Phase 5: Asset Grid View (2025-08-08)
- Simplified from 1400+ contracts to 600+ assets
- CoinGlass-inspired interface design
- One-command startup implementation

#### Phase 6: Enhanced Historical Page (2025-08-11)
- Live funding ticker
- Countdown timer to next funding
- Combined chart and table view

#### Phase 7-10: System Improvements (2025-08-12)
- Critical funding interval detection fix
- Multi-contract chart enhancements
- Backfill progress indicator
- Dashboard shutdown button
- APR display implementation
- Dynamic OI units

#### Phase 11-12: Multi-Exchange Support (2025-08-13)
- KuCoin integration (472 contracts)
- Sequential collection implementation
- Symbol normalization (XBT → BTC)
- Unified backfill scripts

#### Phase 13: Settings Management (2025-08-14)
- Web-based settings interface
- Hot-reload configuration
- Backup/restore functionality
- Import/export settings

#### Phase 14: Backpack Integration (2025-08-15)
- 39 perpetual contracts added
- Historical backfill implementation
- Chart and data fixes

#### Phase 15: Hyperliquid Integration (2025-08-18)
- 173 DEX perpetual contracts
- 1-hour funding intervals
- Open interest USD conversion
- API fixes for contract naming (2025-08-27)

#### Phase 21: Base Asset Normalization (2025-08-28)
- Fixed prefix token normalization across all exchanges
- Unified asset display (no more duplicates like "1000BONK" and "BONK")
- Proper handling of all prefix patterns:
  - Binance: `1000` and `1000000` prefixes
  - KuCoin: `1000000`, `10000`, and `1000` prefixes (checked in order)
  - Hyperliquid & Backpack: `k` prefix tokens
- Fixed edge cases like `10000CATUSDTM` → `CAT`, `1000000MOGUSDTM` → `MOG`

#### Phase 22: Dashboard Search Enhancement (2025-08-28)
- **Enhanced Search Functionality**: Can now search both assets and contracts
- **Auto-Expansion**: Assets automatically expand when contracts match search
- **Visual Highlighting**: Matching contracts highlighted with blue border
- **Search Modes**: Search by asset name, contract symbol, exchange, or partial matches
- **Pre-fetching**: All contract data pre-loaded for instant search results

#### Phase 23: Data Collector Reliability (2025-08-28)
- **Improved Startup**: Better error handling in `start.py`
- **Process Monitoring**: Verifies data collector starts successfully
- **Logging Support**: Output redirected to `data_collector.log`
- **Windows Compatibility**: Fixed console window issues on Windows
- **Status Feedback**: Clear indication if collector fails to start

#### Phase 24: Documentation Enhancement (2025-08-28)
- **Enhanced CLAUDE.md**: Improved guidance for Claude Code instances
- **Background Process Monitoring**: Added instructions for managing background processes
- **Windows Support**: Better Windows-specific commands and alternatives
- **Dependency Clarity**: Added missing package installations (fastapi, uvicorn, psutil)
- **Troubleshooting**: Expanded debugging and status checking commands

#### Phase 25: 1000X Token Normalization Fix (2025-08-28)
- **Fixed 1000X token**: Special handling for KuCoin's 1000XUSDTM contract
- **Normalization**: 1000X correctly normalized to "X" (representing X token with 1000x denomination)
- **Unified display**: X token now appears consistently across Binance and KuCoin
- **Edge case handling**: Added explicit check for baseCurrency='1000X' from KuCoin API

#### Phase 26: 1MBABYDOGE Normalization (2025-08-29)
- **Added 1MBABYDOGE normalization**: 1M denomination (1 Million) now properly handled
- **Normalization**: `1MBABYDOGEUSDT` and `1MBABYDOGEUSDTM` → `BABYDOGE`
- **Unified display**: Both Binance and KuCoin 1MBABYDOGE contracts now grouped under BABYDOGE asset
- **Denomination recognition**: System correctly identifies 1M as a denomination prefix like 1000, 10000, etc.

#### Phase 27: Step Function Chart Implementation (2025-08-29)
- **Chart Accuracy**: Replaced smooth curves with step functions for funding rates
- **Interval Detection**: Automatically detects funding intervals (1h, 2h, 4h, 8h)
- **Forward Fill**: Properly handles null values with last known values
- **Enhanced Tooltips**: Shows funding interval, change percentage, and data type
- **Visual Indicators**: Reference lines at actual funding update times
- **Performance**: Disabled animations for better performance with 720+ data points

#### Phase 28: Dashboard Refresh Fix (2025-08-29)
- **Fixed Stuck Backfill**: Corrected backfill status file preventing infinite polling
- **Smart Polling Logic**: BackfillProgress component now stops polling at 100% progress
- **API Auto-fix**: Backfill status endpoint automatically corrects inconsistent states
- **Removed Pre-fetch**: Eliminated automatic fetching of 600+ assets on mount
- **Performance Boost**: Reduced API calls from ~720/hour to ~120/hour (83% reduction)
- **Smart Search**: Added debounced search with on-demand contract fetching

#### Phase 29: Funding Interval Display (2025-08-29)
- **Contract Details Enhancement**: Added funding interval column to expanded contract view
- **Clear Interval Display**: Shows funding frequency (1h, 2h, 4h, 8h) for each contract
- **API Update**: Modified `/api/funding-rates-grid` endpoint to include funding_interval_hours
- **Clean UI**: Interval shown only in contract details table for clarity
- **Essential Information**: Helps traders understand holding costs and funding payment frequency

#### Phase 16-20: Recent Improvements (2025-08-21)
- Synchronized historical windows
- Bug fixes for historical page
- Contract-specific countdown timers
- X-axis improvements for charts
- Performance optimizations

#### Phase 30: Z-Score Statistical Monitoring (2025-09-03 - Completed)
- **Statistical Analysis**: Z-score calculations for all funding rates
- **New Database Tables**: `funding_statistics`, `contract_metadata`
- **Zone-based Updates**: Active zones (|Z|>2) update every 30s, stable every 2min
- **Parallel Processing**: <1s calculation for all 1,297 contracts
- **API Endpoints**: `/api/contracts-with-zscores`, `/api/zscore-summary`
- **Percentile Rankings**: Distribution-independent statistical measures
- **Performance Optimized**: <100ms API response times

#### Phase 31: Arbitrage Detection System (2025-09-15 - Completed)
- **Cross-Exchange Scanning**: Real-time arbitrage opportunity detection
- **APR Spread Calculation**: Automatic spread and profit calculations
- **New Database Table**: `arbitrage_spreads` for opportunity tracking
- **API Endpoint**: `/api/arbitrage/opportunities` with filtering
- **Historical Tracking**: Spread statistics over time
- **Redis Caching**: 5s TTL for performance optimization

#### Phase 32: Aster and Drift Exchange Integration (2025-09-20 - Completed)
- **Aster DEX Integration**: 102 perpetual contracts with 4-hour funding intervals
- **Drift Solana DEX**: 61 perpetual contracts with 1-hour funding intervals
- **Symbol Normalization**: Handle Aster prefixes (1000FLOKI → FLOKI, kX → X)
- **Drift Normalization**: Remove -PERP suffix, handle 1M/1K prefixes (1MBONK → BONK)
- **Rate Limiting**: Aster at 40 req/s max, Drift with no strict limits
- **Parallel Fetching**: Optimized async/await for both exchanges
- **Total Contracts**: System expanded to 1,403 across 6 exchanges

#### Phase 33: Redis Cache Implementation (2025-09-23 - Completed)
- **Redis Integration**: High-performance caching layer
- **TTL Strategy**: 5s for contracts, 10s for summary data
- **Memory Limit**: 512MB with LRU eviction policy
- **Fallback**: Graceful degradation to in-memory cache if Redis unavailable
- **Performance**: <100ms API response times with caching

#### Phase 34: ByBit and Lighter Exchange Integration (2025-10-13 - Completed)
- **ByBit Integration**: 663 perpetual contracts (largest single exchange addition)
  - 639 linear perpetual contracts (USDT/USDC-margined)
  - 24 inverse perpetual contracts (USD-margined)
  - V5 API with cursor-based pagination
  - Mixed funding intervals: 4h (52.3%), 8h (38.8%), 1h (5.9%), 2h (3.0%)
  - Rate limit: 50 req/s with automatic pagination handling
  - Base asset normalization handles up to 8-digit multiplier prefixes
- **Lighter Integration**: 91 contracts from DEX aggregator
  - Aggregates funding rates from Binance, OKX, and ByBit
  - 8-hour CEX-standard equivalent rate format
  - Unique market_id system for contract identification
  - 1-hour resolution historical data support
  - Rate conversion logic for CEX-standard alignment
- **Enhanced Dashboard Features**:
  - Exchange Filter System with multi-select and persistence
  - Custom hooks (useExchangeFilter, useFilterPersistence, useFilterURL)
  - New UI cards (APRExtremeCard, DashboardStatsCard, SystemOverviewCard)
  - Arbitrage Historical Chart component
  - Modern UI components (ModernMultiSelect, ModernPagination, ModernTooltip)
  - Filter state synchronization with URL parameters and localStorage
- **System Expansion**: Total contracts increased from 1,403 to 2,275 (+62%)
- **Asset Coverage**: Unique assets expanded from 600+ to 656

### Critical Fixes Implemented
1. **Funding Interval Detection**: Fixed 333 contracts with incorrect APR
2. **Multi-Contract Chart Alignment**: Timestamp normalization
3. **COIN-M Contract Display**: Base asset extraction
4. **Historical Data Completeness**: Zero value handling
5. **Open Interest Display**: Dynamic unit formatting
6. **Base Asset Normalization**: Fixed duplicate assets in dashboard (e.g., "1000BONK" and "BONK" now unified)
7. **Dashboard Search**: Can now search both assets and contracts with auto-expansion
8. **Data Collector Startup**: Improved reliability with logging and error handling
9. **Documentation Enhancement**: Improved CLAUDE.md for better Claude Code integration
10. **1000X Token Fix**: Correctly normalizes KuCoin's 1000XUSDTM to "X" instead of "1000X"
11. **1MBABYDOGE Normalization**: Added support for 1M (1 Million) denomination prefix
12. **Step Function Charts**: Accurate representation of funding rate changes with proper intervals
13. **Dashboard Refresh Fix**: Eliminated constant refreshing from stuck backfill status
14. **Funding Interval Display**: Added clear display of funding frequency for each contract

## Performance Metrics

### System Performance
- **Total Contracts**: 2,275 across 8 exchanges
- **Unique Assets**: 656 consolidated view
- **Update Cycle**: 30 seconds with parallel collection (default)
- **API Response**: <100ms with Redis caching
- **Dashboard Load**: ~2 seconds initial
- **Chart Rendering**: Smooth with forward-fill normalization
- **Z-Score Calculation**: <1s for all contracts (parallel processing)
- **Cache Performance**: 5s TTL contracts, 10s summaries

### Data Metrics
- **Historical Records**: 354,749+ total (including 85,368 Hyperliquid records)
- **Data Completeness**: 100% (gaps filled)
- **Backfill Speed**: ~5-7 minutes for 30 days
- **Database Size**: ~5GB with full history
- **Memory Usage**: <500MB typical

### Current Status (MVP)
- **Uptime**: System runs continuously when started
- **Error Recovery**: Basic retry mechanisms in place
- **Data Collection**: Functional across 8 exchanges
- **Known Limitations**: This is an MVP with basic functionality

## Troubleshooting

### Common Issues

#### No Data Showing
```bash
# Check PostgreSQL
docker ps  # Should show exchange_postgres

# Test data collection
python main.py

# Verify API
curl http://localhost:8000/api/funding-rates-grid
```

#### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Linux/Mac
lsof -i :8000
kill -9 <process_id>
```

#### Docker Not Running
Start Docker Desktop first, then run:
```bash
docker-compose up -d
```

#### Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose ps

# Restart if needed
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

#### High API Request Volume
Check for asset-specific issues in logs. The system may be retrying failed requests.

#### Configuration Issues
- Check `config/settings.py` for syntax errors
- Verify exchange enable/disable settings
- Ensure sequential collection settings are correct

#### Data Collector Not Starting
- Check `data_collector.log` for error messages
- Verify `main.py` exists in the project root
- Try starting manually: `python main.py --loop --interval 30`
- On Windows, check if Python is in PATH
- Ensure all required dependencies are installed: `pip install -r requirements.txt`

#### Redis Cache Monitoring
```bash
# Check cache health
curl http://localhost:8000/api/health/cache

# Redis statistics
docker exec -it exchange_redis redis-cli INFO stats
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
```

#### System Performance Monitoring
```bash
# View Z-score calculation status
curl http://localhost:8000/api/contracts-with-zscores | python -m json.tool | head -50

# Check backfill status
curl http://localhost:8000/api/backfill-status | python -m json.tool

# Monitor API response times
time curl -s http://localhost:8000/api/funding-rates-grid > /dev/null

# Check system performance metrics
curl http://localhost:8000/api/health/performance | python -m json.tool
```

## Scripts & Utilities

### Contract Health Monitoring
```bash
# Monitor contract health and detect stale/inactive contracts
python utils/contract_monitor.py --report-only

# Preview changes without applying them
python utils/contract_monitor.py --dry-run

# Apply changes to mark inactive contracts
python utils/contract_monitor.py

# Monitor with custom thresholds (default: 24h stale, 48h inactive)
python utils/contract_monitor.py --stale-hours 48 --inactive-hours 72
```

### Data Collection
```bash
# Single run
python main.py

# Continuous mode (30-second intervals)
python main.py --loop --interval 30 --quiet
```

### Historical Backfill
```bash
# All exchanges (parallel) - Recommended
python scripts/unified_historical_backfill.py --days 30 --parallel

# Specific exchanges only
python scripts/unified_historical_backfill.py --days 30 --exchanges binance,kucoin

# Run hourly at every UTC hour (XX:00) - Continuous mode
python scripts/unified_historical_backfill.py --days 30 --parallel --loop-hourly

# Backfill arbitrage spreads (improved v2)
python scripts/backfill_arbitrage_spreads_v2.py --days 30

# Collect arbitrage spread history
python scripts/collect_spread_history.py
```

### Database Management
```bash
# Check database status
python database_tools.py check

# Clear all data
python database_tools.py clear --quick

# Fix funding intervals
python scripts/fix_funding_intervals.py

# Fill Hyperliquid gaps
python scripts/hyperliquid_gap_filler.py
```

### System Control
```bash
# Start everything
python start.py

# API server only
python api.py

# Dashboard only
cd dashboard && npm start

# Data collector only
python main.py --loop --interval 30
```

### Testing

#### Frontend Tests
```bash
# Run all React tests
cd dashboard && npm test

# Run tests in watch mode
cd dashboard && npm test -- --watch

# Run tests with coverage report
cd dashboard && npm test -- --coverage

# TypeScript type checking
cd dashboard && npx tsc --noEmit
```

#### Frontend Build
```bash
# Production build
cd dashboard && npm run build

# Serve production build locally
cd dashboard && npx serve -s build
```

#### Exchange Integration Tests
```bash
# Test exchange connections
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"
python -c "from exchanges.bybit_exchange import ByBitExchange; e=ByBitExchange(); print(f'ByBit: {len(e.fetch_data())} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); print(f'Backpack: {len(e.fetch_data())} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); print(f'Hyperliquid: {len(e.fetch_data())} contracts')"
python -c "from exchanges.aster_exchange import AsterExchange; e=AsterExchange(); print(f'Aster: {len(e.fetch_data())} contracts')"
python -c "from exchanges.lighter_exchange import LighterExchange; e=LighterExchange(); print(f'Lighter: {len(e.fetch_data())} contracts')"
python -c "from exchanges.drift_exchange import DriftExchange; e=DriftExchange(); print(f'Drift: {len(e.fetch_data())} contracts')"
```

#### Python Syntax Validation
```bash
# Verify Python syntax after edits
python -m py_compile api.py main.py
python -m py_compile utils/*.py exchanges/*.py scripts/*.py
```

---

**Quick Commands Reference**
```bash
# Start everything
python start.py

# Data collection only
python main.py --loop --interval 30 --quiet

# Check database
python database_tools.py check

# Clear database
python database_tools.py clear --quick

# Historical backfill (all exchanges)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Backfill specific exchanges
python scripts/unified_historical_backfill.py --days 30 --exchanges binance,kucoin

# Hourly backfill loop (runs at XX:00 UTC)
python scripts/unified_historical_backfill.py --days 30 --parallel --loop-hourly
```

**System Status Indicators**
- Data Collection: Look for "OK" messages in collector terminal
- API Health: Check http://localhost:8000/api/health
- Database: Green "Connected" in dashboard header
- Update Time: Shows last refresh in dashboard

---

*Last Updated: 2025-10-13*
*Version: MVP*
*Total Contracts: 2,275*
*Active Exchanges: 8*
*Unique Assets: 656*
*Project Status: MVP - Not production ready*
*Note: This is a minimum viable product for demonstration and development purposes*
