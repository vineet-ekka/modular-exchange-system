# Multi-Exchange Cryptocurrency Funding Rate Dashboard (MVP)

An MVP cryptocurrency funding rate tracking system supporting 13 exchanges (6 CEX, 7 DEX) with real-time updates, historical data analysis, and cross-exchange arbitrage detection.

**Note: This is a minimum viable product (MVP) for demonstration and development purposes only. Not intended for production use.**

## Table of Contents

- [Quick Start](#quick-start)
- [Documentation](#documentation)
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

### Prerequisites
- [Docker Desktop](https://docker.com/products/docker-desktop) (must be running)
- [Python 3.8+](https://python.org/downloads)
- [Node.js 16+](https://nodejs.org) (optional, for dashboard)

### First-Time Setup
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/modular-exchange-system.git
cd modular-exchange-system

# 2. Start Docker Desktop (must be running before next step)

# 3. Run setup (creates .env files, installs dependencies, starts containers)
python setup.py

# 4. Start the system
python start.py

# 5. (Optional) Verify everything is working
python verify_setup.py
```

### What setup.py does
1. Creates `.env` from `.env.example`
2. Creates `dashboard/.env` from `dashboard/.env.example`
3. Installs Python dependencies (`pip install -r requirements.txt`)
4. Installs npm dependencies (`npm install` in dashboard/)
5. Pulls and starts Docker containers (PostgreSQL, Redis)
6. Verifies database connection

### Access Points
- **Dashboard**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## Documentation

This README provides a high-level overview and quickstart guide. For detailed technical documentation:

- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - Complete API endpoint reference
  - 40+ REST endpoints with examples
  - Request/response schemas
  - Query parameters and error codes
  - Interactive Swagger UI at http://localhost:8000/docs

- **[docs/EXCHANGES.md](docs/EXCHANGES.md)** - Exchange integration details
  - Per-exchange specifications (13 active exchanges)
  - Symbol normalization patterns
  - Rate limits and historical data availability
  - Exchange comparison table
  - Guide for adding new exchanges

- **[CHANGELOG.md](CHANGELOG.md)** - Development history
  - Chronological development phases (Phase 1-34)
  - Feature additions and improvements
  - Critical fixes implemented
  - System expansion milestones

- **[CLAUDE.md](CLAUDE.md)** - Technical implementation guide
  - Critical architectural patterns
  - Non-obvious implementation details
  - Background process coordination
  - Performance optimization techniques

## System Overview

### Core Capabilities
- **Multi-Exchange Collection**: Real-time funding rates from 13 exchanges (Binance, KuCoin, ByBit, MEXC, Backpack, Deribit, Hyperliquid, Drift, Aster, Lighter, Pacifica, Hibachi, dYdX)
- **Sequential Collection**: Staggered API calls to manage rate limits (0s, 30s, 120s, 180s delays)
- **Asset Aggregation**: 700+ unique assets consolidated from 3,474 individual contracts
- **Historical Analysis**: 30-day rolling window with automated backfill and gap detection
- **Dashboard**: React-based interface with real-time updates and charts
- **APR Calculations**: Automatic annualized percentage rate computation
- **Data Export**: CSV export functionality for historical data
- **Redis Caching**: High-performance caching with 5s TTL for contracts, 10s for summaries

### System Statistics
- **Total Contracts**: 3,474 perpetual futures
- **Active Exchanges**: 13 (6 CEX: Binance, KuCoin, ByBit, MEXC, Backpack, Deribit; 7 DEX: Hyperliquid, Drift, Aster, Lighter, Pacifica, Hibachi, dYdX)
- **Unique Assets**: 700+ with cross-exchange comparison
- **Update Frequency**: 30-second real-time refresh
- **Historical Coverage**: 30-day rolling window
- **API Endpoints**: 42 RESTful endpoints
- **Database Tables**: 9 core tables + materialized views (real-time, historical, streaming, websocket, statistics, metadata, arbitrage, funding_statistics, query_performance)
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
- **React 19.1.1**: Modern JavaScript framework with TypeScript 4.9.5
- **shadcn/ui**: Component library built on Radix UI primitives
- **TanStack Table 8**: Headless table library for data grids
- **TanStack Query 5**: Server state management
- **Tailwind CSS 3.4**: Utility-first CSS framework
- **Recharts 3.1**: Interactive data visualization

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
- **Modern Stack**: React 19.1.1 + TypeScript + shadcn/ui + TanStack Table
- Asset-based grid view (700+ assets across 13 exchanges)
- Expandable rows showing individual contracts with on-demand fetching
- **Funding Interval Display**: Shows funding frequency (1h, 2h, 4h, 8h) for each contract
- **View Modes**: APR, 1H, 8H, 1D, 7D funding rate displays
- **Enhanced Search**: Search both assets AND contracts simultaneously
- **Auto-expansion**: Automatically expands assets when contracts match search
- **Search Highlighting**: Matching contracts highlighted in blue
- Multi-contract historical charts with Recharts
- Live funding rate ticker
- Countdown timer to next funding
- Color-coded rates (green positive, red negative)
- Advanced sorting and filtering with TanStack Table
- CSV export functionality
- Settings management interface
- Backfill progress indicator
- Z-score statistical analysis with highlighting
- Cross-exchange arbitrage detection with enhanced filtering
- 30-second auto-refresh with preserved UI state

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

#### Binance (600 contracts)
| Market Type | Contracts | Funding Intervals | Features |
|------------|-----------|-------------------|----------|
| USD-M | 572 | 4h (66.8%), 8h (28.8%), 1h (4.4%) | USDT-margined perpetuals |
| COIN-M | 28 | 8 hours | Coin-margined perpetuals |

#### KuCoin (526 contracts)
| Funding Interval | Contracts | Percentage | Notable Examples |
|-----------------|-----------|------------|------------------|
| 4 hours | 330 | 62.7% | Higher frequency |
| 8 hours | 176 | 33.5% | Standard perpetuals |
| 1 hour | 17 | 3.2% | CARVUSDTM, XEMUSDTM |
| 2 hours | 3 | 0.6% | MAGICUSDTM |

#### ByBit (625 contracts)
| Market Type | Contracts | Funding Intervals | Features |
|------------|-----------|-------------------|----------|
| Linear | 602 | 4h (52%), 8h (39%), 1h (6%), 2h (3%) | USDT/USDC-margined |
| Inverse | 23 | 8h (100%) | USD-margined perpetuals |

#### Backpack (67 contracts)
| Funding Interval | Contracts | Percentage | Features |
|-----------------|-----------|------------|----------|
| 1 hour | 67 | 100% | All contracts now 1-hour funding |

#### Hyperliquid (184 contracts)
| Funding Interval | Contracts | Percentage | Features |
|-----------------|-----------|------------|----------|
| 1 hour | 184 | 100% | Unique DEX with hourly funding |

#### Aster (165 contracts)
| Funding Interval | Contracts | Rate Limit | Features |
|-----------------|-----------|------------|----------|
| 4 hours | 165 | 40 req/s | DEX with async/parallel fetching, USDT pairs |

#### Lighter (115 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 8 hours | 115 | DEX Aggregator | CEX-standard equivalent, aggregates from Binance/OKX/ByBit |

#### Drift (51 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 1 hour | 51 | Solana | Solana-based DEX, excludes betting markets |

#### MEXC (826 contracts)
| Funding Interval | Contracts | Rate Limit | Features |
|-----------------|-----------|------------|----------|
| 8 hours | 826 | 20 req/s | CEX with bulk funding rate fetching, USDT pairs |

#### Pacifica (35 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 1 hour | 35 | DEX | Pacifica Finance perpetual contracts |

#### Hibachi (15 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 8 hours | 15 | DEX | Hibachi DEX perpetual contracts |

#### Deribit (20 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 8 hours | 20 | CEX | Options and perpetual futures platform |

#### dYdX (245 contracts)
| Funding Interval | Contracts | Platform | Features |
|-----------------|-----------|----------|----------|
| 1 hour | 245 | DEX | dYdX v4 decentralized perpetual exchange |

### Ready for Integration
- **Kraken**: 353 contracts (module available but disabled)
- **EdgeX**: API not accessible (disabled)
- **ApeX**: API not accessible (disabled)

**Total Active**: 3,474 perpetual contracts across 700+ unique assets

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
# Python dependencies (all required packages included)
pip install -r requirements.txt

# Dashboard dependencies
cd dashboard && npm install && cd ..
```

#### 3. Start PostgreSQL
```bash
docker-compose up -d

# Verify services are running
docker ps  # Should show exchange_postgres, redis, and pgAdmin
```

#### 4. Configure Environment
Create `.env` file (copy from `.env.example` and configure):
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
```

**Important:** You MUST set `POSTGRES_PASSWORD` to match your Docker configuration. The system will not connect to the database without a valid password.

For Docker Compose, also set the environment variable or update `docker-compose.yml`:
```bash
# Option 1: Set environment variable
export POSTGRES_PASSWORD=your_secure_password_here

# Option 2: Create .env file in project root with POSTGRES_PASSWORD
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

### Complete API Endpoints (42 Total)

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

### Technology Stack
- **React 19.1.1** with TypeScript 4.9.5
- **shadcn/ui** component library (New York style) with Radix UI primitives
- **TanStack Table 8.21.3** for headless data grid functionality
- **TanStack React Query 5.90.10** for server state management
- **Tailwind CSS 3.4.17** for utility-first styling
- **Recharts 3.1.2** for data visualization
- **Framer Motion 12.23.24** for animations

### Asset Grid View (AssetFundingGridV2)
- **Consolidated Display**: 700+ assets across 13 exchanges
- **Multi-Exchange Columns**: Dynamic columns for all active exchanges
- **Expandable Details**: Click to see individual contracts with on-demand fetching
- **Color Coding**: Visual indicators for rate direction (green=positive, red=negative)
- **View Modes**: APR, 1H, 8H, 1D, 7D funding rate displays
- **Z-Score Highlighting**: Statistical anomaly indicators
- **Advanced Search**:
  - Search assets by name (e.g., "BTC", "ETH")
  - Search contracts by symbol (e.g., "BTCUSDT", "XBTUSDTM")
  - Search by partial match (e.g., "USDT" finds all USDT pairs)
  - Search by exchange name (e.g., "Binance", "KuCoin")
  - Auto-expands assets when contracts match (300ms debounced)
  - Highlights matching contracts in blue
- **Sorting**: Multi-column sorting with sticky first column
- **Auto-refresh**: 30-second updates with preserved UI state

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
├── docker-compose.yml              # PostgreSQL/Redis container setup
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
│   │   │   ├── Arbitrage/          # Arbitrage filtering system
│   │   │   │   ├── APRRangeFilter.tsx
│   │   │   │   ├── ArbitrageFilterPanel.tsx
│   │   │   │   ├── AssetAutocomplete.tsx
│   │   │   │   ├── IntervalSelector.tsx
│   │   │   │   └── LiquidityFilter.tsx
│   │   │   ├── Cards/              # Metric display cards
│   │   │   │   ├── APRExtremeCard.tsx
│   │   │   │   ├── DashboardStatsCard.tsx
│   │   │   │   ├── StatCard.tsx
│   │   │   │   └── SystemOverviewCard.tsx
│   │   │   ├── Charts/             # Data visualization
│   │   │   │   ├── ArbitrageHistoricalChart.tsx
│   │   │   │   ├── FundingChartTooltip.tsx
│   │   │   │   └── Sparkline.tsx
│   │   │   ├── Grid/               # Asset grid components
│   │   │   │   ├── AssetFundingGrid.tsx
│   │   │   │   ├── AssetFundingGridV2/     # Primary grid (shadcn/TanStack)
│   │   │   │   │   ├── index.tsx
│   │   │   │   │   ├── types.ts
│   │   │   │   │   ├── utils.ts
│   │   │   │   │   ├── columns.tsx
│   │   │   │   │   ├── data-table.tsx
│   │   │   │   │   ├── ContractTable.tsx
│   │   │   │   │   └── GridCell.tsx
│   │   │   │   ├── ExchangeFilter/
│   │   │   │   │   └── ExchangeFilterPanel.tsx
│   │   │   │   ├── Historical/
│   │   │   │   │   ├── ContractHistoricalChart.tsx
│   │   │   │   │   ├── ContractHistoricalFilters.tsx
│   │   │   │   │   ├── ContractHistoricalMetrics.tsx
│   │   │   │   │   └── ContractHistoricalTable.tsx
│   │   │   │   ├── HistoricalFundingView.tsx
│   │   │   │   └── HistoricalFundingViewContract.tsx
│   │   │   ├── Layout/             # Layout components
│   │   │   │   └── Header.tsx
│   │   │   ├── Ticker/             # Live ticker components
│   │   │   │   ├── FundingCountdown.tsx
│   │   │   │   └── LiveFundingTicker.tsx
│   │   │   ├── ui/                 # shadcn/ui components (19 files)
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── checkbox.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── select.tsx
│   │   │   │   ├── skeleton.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   └── ...
│   │   │   ├── ArbitrageOpportunities.tsx
│   │   │   ├── BackfillProgress.tsx
│   │   │   ├── ContractLink.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── constants/
│   │   │   └── exchangeMetadata.ts
│   │   ├── hooks/                  # Custom React hooks
│   │   │   ├── useArbitrageFilter.ts
│   │   │   ├── useContractPreload.ts
│   │   │   ├── useDataQueries.ts
│   │   │   ├── useExchangeFilter.ts
│   │   │   ├── useFilterPersistence.ts
│   │   │   └── useFilterURL.ts
│   │   ├── pages/                  # Page components
│   │   │   ├── ArbitrageDetailPage.tsx
│   │   │   ├── ArbitragePage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── HistoricalFundingPage.tsx
│   │   │   └── LandingPage.tsx
│   │   ├── services/               # API services
│   │   │   └── api.ts
│   │   ├── utils/
│   │   │   ├── exchangeUrlMapper.ts
│   │   │   └── filterAlgorithms.ts
│   │   ├── App.tsx                 # Main app component
│   │   └── index.tsx               # Entry point with QueryClient
│   ├── components.json            # shadcn/ui configuration
│   ├── package.json               # Node dependencies
│   ├── tailwind.config.js         # Tailwind CSS configuration
│   └── tsconfig.json              # TypeScript configuration
│
├── database/                      # Database management
│   └── postgres_manager.py        # PostgreSQL operations
│
├── data_processing/               # Data processing modules
│   └── data_processor.py          # Transformation & APR calculation
│
├── exchanges/                     # Exchange integrations (13 active + 3 disabled)
│   ├── base_exchange.py           # Abstract base class
│   ├── binance_exchange.py        # Binance CEX (600 contracts)
│   ├── kucoin_exchange.py         # KuCoin CEX (526 contracts)
│   ├── bybit_exchange.py          # ByBit CEX (625 contracts)
│   ├── mexc_exchange.py           # MEXC CEX (826 contracts)
│   ├── backpack_exchange.py       # Backpack CEX (67 contracts)
│   ├── deribit_exchange.py        # Deribit CEX (20 contracts)
│   ├── hyperliquid_exchange.py    # Hyperliquid DEX (184 contracts)
│   ├── drift_exchange.py          # Drift DEX (51 contracts)
│   ├── aster_exchange.py          # Aster DEX (165 contracts)
│   ├── lighter_exchange.py        # Lighter DEX (115 contracts)
│   ├── pacifica_exchange.py       # Pacifica DEX (35 contracts)
│   ├── hibachi_exchange.py        # Hibachi DEX (15 contracts)
│   ├── dydx_exchange.py           # dYdX DEX (245 contracts)
│   ├── kraken_exchange.py         # Kraken (disabled)
│   ├── edgex_exchange.py          # EdgeX (disabled)
│   ├── apex_exchange.py           # ApeX (disabled)
│   └── exchange_factory.py        # Factory pattern manager
│
├── scripts/                       # Utility scripts
│   ├── unified_historical_backfill.py    # Multi-exchange backfill
│   ├── backfill_arbitrage_spreads_v2.py  # Arbitrage spread backfill
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
│   ├── redis_cache.py             # Redis caching layer
│   └── terminal_dashboard.py      # CLI monitoring
│
├── docs/                          # Documentation
│   ├── API_REFERENCE.md           # Complete API endpoint reference
│   ├── EXCHANGES.md               # Exchange-specific details
│   ├── COMMANDS_REFERENCE.md      # All operational commands
│   ├── DOCKER_REFERENCE.md        # Container management
│   ├── TROUBLESHOOTING.md         # Debugging guide
│   └── MAINTENANCE.md             # Database maintenance
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

-- Streaming data table (WebSocket feeds)
CREATE TABLE streaming_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    market_type VARCHAR(20),
    funding_rate NUMERIC(20, 10),
    mark_price NUMERIC(20, 10),
    index_price NUMERIC(20, 10),
    next_funding_time TIMESTAMP WITH TIME ZONE,
    stream_timestamp TIMESTAMP WITH TIME ZONE,
    server_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- WebSocket connections table
CREATE TABLE websocket_connections (
    id SERIAL PRIMARY KEY,
    connection_name VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    market_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'disconnected',
    url TEXT,
    connected_at TIMESTAMP WITH TIME ZONE,
    disconnected_at TIMESTAMP WITH TIME ZONE,
    messages_received INTEGER DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    reconnect_count INTEGER DEFAULT 0,
    last_message_time TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Query performance log
CREATE TABLE query_performance_log (
    id SERIAL PRIMARY KEY,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    query_hash TEXT,
    query_text TEXT,
    calls INTEGER,
    total_time NUMERIC,
    mean_time NUMERIC,
    min_time NUMERIC,
    max_time NUMERIC,
    rows INTEGER,
    hit_percent NUMERIC
);
```

### Materialized Views (Pre-computed for Performance)

```sql
-- Asset-level aggregations
CREATE MATERIALIZED VIEW mv_grouped_funding_rates AS
SELECT base_asset, COUNT(*) as contract_count,
       AVG(apr) as avg_apr, SUM(open_interest) as total_oi
FROM exchange_data GROUP BY base_asset;

-- Top funding rates
CREATE MATERIALIZED VIEW mv_top_funding_rates AS
SELECT * FROM exchange_data ORDER BY apr DESC LIMIT 100;

-- Per-exchange summaries
CREATE MATERIALIZED VIEW mv_exchange_stats AS
SELECT exchange, COUNT(DISTINCT symbol) as symbol_count,
       COUNT(DISTINCT base_asset) as asset_count, AVG(apr) as avg_apr
FROM exchange_data GROUP BY exchange;

-- Arbitrage spread statistics
CREATE MATERIALIZED VIEW mv_arbitrage_spread_stats AS
SELECT asset, exchange_a, exchange_b,
       AVG(apr_spread) as mean_spread, STDDEV(apr_spread) as stddev_spread,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY apr_spread) as median_spread
FROM arbitrage_spreads GROUP BY asset, exchange_a, exchange_b;
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

For detailed development history organized by phase, see **[CHANGELOG.md](CHANGELOG.md)**.

**Recent Major Milestones:**
- **Phase 34** (2025-10-13): ByBit (663 contracts) and Lighter (91 contracts) integration, enhanced dashboard filtering
- **Phase 33** (2025-09-23): Redis cache implementation with graceful fallback
- **Phase 32** (2025-09-20): Aster and Drift DEX integration, system expanded to 1,403 contracts
- **Phase 31** (2025-09-15): Arbitrage detection system with cross-exchange scanning
- **Phase 30** (2025-09-03): Z-score statistical monitoring with zone-based updates
- **Phase 1-29** (2025-08-07 to 2025-08-29): Core system development, multi-exchange support, dashboard enhancements

The system has evolved through 34+ development phases, starting from Binance-only integration (541 contracts) to the current multi-exchange system with 3,474 contracts across 13 exchanges.

## Performance Metrics

### System Performance
- **Total Contracts**: 3,474 across 13 exchanges
- **Unique Assets**: 700+ consolidated view
- **Update Cycle**: 30 seconds with parallel collection (default)
- **API Response**: <100ms with Redis caching
- **Dashboard Load**: ~2 seconds initial
- **Chart Rendering**: Smooth with forward-fill normalization
- **Z-Score Calculation**: <1s for all contracts (parallel processing)
- **Cache Performance**: 5s TTL contracts, 10s summaries, 30s arbitrage

### Data Metrics
- **Historical Records**: 400,000+ total across all exchanges
- **Data Completeness**: 100% (gaps filled)
- **Backfill Speed**: ~5-7 minutes for 30 days
- **Database Size**: ~5GB with full history
- **Memory Usage**: <500MB typical

### Current Status (MVP)
- **Uptime**: System runs continuously when started
- **Error Recovery**: Circuit breaker pattern with graceful fallback
- **Data Collection**: Functional across 13 exchanges (6 CEX, 7 DEX)
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

*Last Updated: 2025-12-01*
*Version: MVP*
*Total Contracts: 3,474*
*Active Exchanges: 13 (6 CEX, 7 DEX)*
*Unique Assets: 700+*
*Project Status: MVP - Not production ready*
*Note: This is a minimum viable product for demonstration and development purposes*
