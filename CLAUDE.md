# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Start everything (one command)
python start.py

# Check system status
curl -s http://localhost:8000/api/health
```

## Essential Commands

### Build & Test
```bash
# Type check TypeScript (run before committing)
cd dashboard && npx tsc --noEmit

# Build dashboard  
cd dashboard && npm run build

# Run dashboard tests
cd dashboard && npm test

# Install Python dependencies (if imports fail)
pip install -r requirements.txt
pip install fastapi uvicorn psutil aiohttp asyncio-throttle

# Python formatting (if black installed)
black . --line-length=120
```

### System Control
```bash
# Start everything
python start.py

# Individual components
python api.py                              # API server (port 8000)
cd dashboard && npm start                  # Dashboard (port 3000)
python main.py --loop --interval 30        # Data collector

# Check background processes
/bashes

# Monitor collector output
BashOutput tool with bash_id="<id>"

# Kill stuck process
KillBash tool with shell_id="<id>"
```

### Data Operations
```bash
# Test individual exchange modules
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(f'Binance: {len(e.fetch_data())} contracts')"
python -c "from exchanges.kucoin_exchange import KuCoinExchange; e=KuCoinExchange(); print(f'KuCoin: {len(e.fetch_data())} contracts')"
python -c "from exchanges.backpack_exchange import BackpackExchange; e=BackpackExchange(); print(f'Backpack: {len(e.fetch_data())} contracts')"
python -c "from exchanges.hyperliquid_exchange import HyperliquidExchange; e=HyperliquidExchange(); print(f'Hyperliquid: {len(e.fetch_data())} contracts')"

# Historical backfill (30 days, all exchanges)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Check database connection
python database_tools.py check

# Clear database (careful!)
python database_tools.py clear --quick

# Fix funding intervals
python scripts/fix_funding_intervals.py

# Fill Hyperliquid gaps (hourly funding)
python scripts/hyperliquid_gap_filler.py
```

## Architecture Overview

### System Components
- **Data Collector** (`main.py`): Fetches funding rates every 30 seconds from 4 exchanges
- **FastAPI Backend** (`api.py`): 17+ endpoints serving PostgreSQL data
- **React Dashboard** (`dashboard/`): TypeScript frontend with real-time updates
- **Exchange Modules** (`exchanges/`): Factory pattern with BaseExchange inheritance
- **PostgreSQL Database**: Two tables - real-time and 30-day historical

### Key Architecture Patterns
1. **Factory Pattern**: `ExchangeFactory` creates exchange instances from `BaseExchange`
2. **Rate Limiting**: Sequential collection with configurable delays in `config/sequential_config.py`
3. **Symbol Normalization**: All exchanges normalize to base assets (e.g., `1000SHIB` → `SHIB`)
4. **UPSERT Strategy**: PostgreSQL composite indexes prevent duplicate entries
5. **Background Tasks**: Data collector runs in subprocess, logs to `data_collector.log`

### Key Files
- `start.py` - One-command launcher for all services
- `api.py` - FastAPI server with all endpoints
- `main.py` - Data collector orchestrator
- `config/settings.py` - System configuration
- `database/postgres_manager.py` - Database operations
- `exchanges/base_exchange.py` - Abstract base for exchanges
- `dashboard/src/components/Grid/AssetFundingGrid.tsx` - Main dashboard grid

## Critical Implementation Details

### Exchange Module Structure
All exchanges must inherit from `BaseExchange` and implement:
- `fetch_data()`: Get raw API data
- `normalize_data()`: Convert to unified format with these columns:
  - exchange, symbol, base_asset, quote_asset, funding_rate
  - funding_interval_hours, apr, index_price, mark_price, open_interest

### Database Indexes
```sql
-- Composite indexes for performance
CREATE INDEX idx_exchange_symbol ON exchange_data(exchange, symbol);
CREATE UNIQUE INDEX idx_unique_funding ON funding_rates_historical(exchange, symbol, funding_time);
```

## Symbol Normalization

All exchanges normalize to base assets:
- **Numeric Prefixes**: `1000SHIB` → `SHIB`, `10000CAT` → `CAT`, `1000000MOG` → `MOG`
- **Special Cases**: `1MBABYDOGE` → `BABYDOGE`, `1000X` → `X` (KuCoin)
- **Letter Prefixes**: `kPEPE` → `PEPE` (Hyperliquid/Backpack)
- **Exchange Specific**: `XBTUSDTM` → `BTC` (KuCoin Bitcoin)

## API Endpoints

### Core Data
- `GET /api/funding-rates-grid` - Asset-based grid view
- `GET /api/historical-funding-by-asset/{asset}` - Historical by asset
- `GET /api/contracts-by-asset/{asset}` - List contracts for asset
- `GET /api/statistics` - Dashboard statistics
- `GET /api/backfill-status` - Backfill progress

### Settings & Control
- `GET/PUT /api/settings` - Configuration management
- `POST /api/backfill/start` - Start historical backfill
- `GET /api/health` - System health check

## Dashboard Features

- **Asset Grid**: 600+ assets with expandable contract details
- **Smart Search**: Search assets AND contracts with auto-expansion
- **Historical Charts**: Step functions with funding intervals
- **Live Updates**: 30-second refresh with countdown timer
- **Performance**: Debounced search, lazy loading, no pre-fetching

## Troubleshooting

### No Data Showing
```bash
# Windows
docker ps | findstr postgres
curl -s http://localhost:8000/api/funding-rates-grid
type data_collector.log

# Linux/Mac
docker ps | grep postgres
curl -s http://localhost:8000/api/funding-rates-grid
cat data_collector.log
```

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :8000
kill -9 <pid>
```

### Data Collector Not Starting
```bash
# Check log
type data_collector.log  # Windows
cat data_collector.log   # Linux/Mac

# Manual start
python main.py --loop --interval 30

# Verify Python
python --version
```

### Database Issues
```bash
# Test connection
python database_tools.py check

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Stuck Backfill
```bash
# Remove status file
del .unified_backfill.status  # Windows
rm .unified_backfill.status   # Linux/Mac

# API auto-fixes on next call
curl http://localhost:8000/api/backfill-status
```

## Development Tips

### Testing Exchange Modules
```python
from exchanges.kucoin_exchange import KuCoinExchange
e = KuCoinExchange()
data = e.fetch_data()
print(f"Fetched {len(data)} contracts")
```

### Background Process Management
Use Claude Code tools:
- `/bashes` - List all background processes
- `BashOutput` tool - Monitor specific process
- `KillBash` tool - Kill stuck process

### Common Operations
```bash
# Fix funding intervals
python scripts/fix_funding_intervals.py

# Fill Hyperliquid gaps (hourly funding)
python scripts/hyperliquid_gap_filler.py

# Clean shutdown of dashboard
python shutdown_dashboard.py
```

### Exchange Testing
```python
# Test all exchanges at once
from exchanges.exchange_factory import ExchangeFactory
factory = ExchangeFactory()
for name in ['binance', 'kucoin', 'backpack', 'hyperliquid']:
    exchange = factory.create(name)
    data = exchange.fetch_data()
    print(f"{name}: {len(data)} contracts")
```

## Important Notes

### Prerequisites
- Python 3.8+ (`python --version`)
- Node.js 16+ (`node --version`)
- Docker Desktop running (`docker ps`)
- PostgreSQL container (`docker-compose up -d postgres`)

### Environment Variables
Required `.env` file in project root:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
```

### Files to Never Commit
- `.unified_backfill.status`, `.backfill.status` - Backfill progress
- `data_collector.log` - Collector output (can be large)
- `temp_data.json` - Temporary data
- `.env` - Secrets (use .env.example as template)

### Common Issues & Solutions

#### API server not starting
- Check if port 8000 is already in use
- Verify all Python dependencies are installed: `pip install -r requirements.txt`
- Check for Python import errors in console output

#### Dashboard not loading data
- Verify API server is running: `curl http://localhost:8000/api/health`
- Check CORS settings in api.py if getting CORS errors
- Ensure PostgreSQL is running: `docker ps | findstr postgres` (Windows)

#### Data collector failing
- Check `data_collector.log` for specific errors
- Verify exchange modules are working (see Exchange Testing section)
- Check rate limiting settings in `config/sequential_config.py`

## Git Workflow

When creating commits:
1. Run type check first: `cd dashboard && npx tsc --noEmit`
2. Batch git commands: `git status`, `git diff`, `git log`
3. Commit message format:
   ```
   🤖 Generated with [Claude Code](https://claude.ai/code)
   
   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
4. Never update git config or push unless explicitly requested