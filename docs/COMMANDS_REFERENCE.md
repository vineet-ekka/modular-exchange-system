# Command Reference

Quick reference for all system commands. For architecture and implementation details, see [CLAUDE.md](../CLAUDE.md).

## Platform Notes

- **Windows**: Use `python` (not `python3`)
- **Linux/Mac**: Use `python3`
- **Paths**: Use forward slashes or `Path()` in Python code

## Platform-Specific Commands

| Task | Windows | Linux/Mac |
|------|---------|-----------|
| Python | `python` | `python3` |
| List processes | `tasklist \| findstr "python"` | `ps aux \| grep python` |
| View log | `type data_collector.log` | `tail -f data_collector.log` |
| Search log | `type data_collector.log \| findstr "ERROR"` | `tail -f data_collector.log \| grep ERROR` |
| Find port | `netstat -ano \| findstr :8000` | `lsof -i :8000` |
| Kill process | `taskkill /PID <pid> /F` | `kill -9 <pid>` |
| Check directory | `dir` | `ls -la` |
| Environment var | `set VAR=value` | `export VAR=value` |

## Startup & Shutdown

```bash
# Start all services
python start.py

# Start without terminal monitor
python start.py --no-monitor

# Start without main dashboard
python start.py --no-dashboard

# Launch terminal monitor only (separate window)
python start.py --dashboard-only

# Manually launch terminal monitor
python -m utils.terminal_dashboard

# Clean shutdown
python shutdown_dashboard.py
```

### Terminal Monitor Keyboard Shortcuts

Launch: `python -m utils.terminal_dashboard`

| Key | Action | Description |
|-----|--------|-------------|
| **C** | Clear cache | Flushes Redis/fallback cache, forces fresh data |
| **B** | Start backfill | Launches 30-day historical data collection |
| **X** | Stop backfill | Gracefully terminates backfill process |
| **S** | Shutdown | Clean shutdown of all services |
| **H** | Help | Shows keyboard shortcuts |
| **Q** | Quit monitor | Exits monitor only (services continue) |

## Pre-Commit Validation

Run these checks before ANY git commit:

```bash
# 1. TypeScript type checking (frontend)
cd dashboard && npx tsc --noEmit

# 2. Python syntax validation (backend)
python -m py_compile api.py main.py

# 3. Validate utility modules
python -m py_compile utils/*.py exchanges/*.py scripts/*.py

# 4. Run frontend tests
cd dashboard && npm test -- --watchAll=false
```

All must pass before committing.

## Frontend Development

```bash
# Development server (port 3000)
cd dashboard && npm start

# Production build
cd dashboard && npm run build

# Serve production build
cd dashboard && npx serve -s build

# Install dependency
cd dashboard && npm install package-name

# Check outdated packages
cd dashboard && npm outdated
```

## Frontend Testing

```bash
# Run all tests once
cd dashboard && npm test -- --watchAll=false

# Watch mode (development)
cd dashboard && npm test

# Coverage report
cd dashboard && npm test -- --coverage

# Specific test file
cd dashboard && npm test -- ArbitrageFilter.test.tsx

# Type checking
cd dashboard && npx tsc --noEmit
```

## Testing Exchange Implementations

```bash
# Test new exchange
python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"

# Test all exchanges quickly
python -c "from exchanges.exchange_factory import ExchangeFactory; from config.settings import Settings; f=ExchangeFactory(Settings()); [print(f'{ex}: {len(f.get_exchange(ex).fetch_data())} contracts') for ex in ['binance','kucoin','bybit']]"

# Test arbitrage filter
curl "http://localhost:8000/api/arbitrage/opportunities-v2?exchanges=binance&exchanges=kucoin" | python -m json.tool

# Verify Python syntax
python -m py_compile utils/arbitrage_scanner.py exchanges/new_exchange.py
```

## System Health & Monitoring

```bash
# Overall system health
curl http://localhost:8000/api/health | python -m json.tool

# Performance metrics
curl http://localhost:8000/api/health/performance | python -m json.tool

# Database inspection
python database_tools.py status
python database_tools.py check

# PostgreSQL direct query
psql -U postgres -d exchange_data -c "SELECT exchange, COUNT(*) FROM exchange_data GROUP BY exchange;"

# Cache health
curl http://localhost:8000/api/health/cache

# Cache performance
curl http://localhost:8000/api/health/performance | python -m json.tool

# Clear cache
curl -X POST http://localhost:8000/api/cache/clear | python -m json.tool

# Z-score status
curl http://localhost:8000/api/contracts-with-zscores | python -m json.tool | head -50

# Backfill status
curl http://localhost:8000/api/backfill-status | python -m json.tool

# API response times
time curl -s http://localhost:8000/api/funding-rates-grid > /dev/null

# Arbitrage filter performance
curl "http://localhost:8000/api/arbitrage/opportunities-v2?exchanges=binance&exchanges=kucoin" -w "\nTime: %{time_total}s\n"
```

## Historical Data Management

```bash
# Full 30-day backfill (runs automatically on startup)
python scripts/unified_historical_backfill.py --days 30 --parallel

# Fill recent gaps
python scripts/fill_recent_gaps.py

# Rebuild arbitrage spreads
python scripts/backfill_arbitrage_spreads_v2.py

# Data maintenance (see MAINTENANCE.md for details)
python scripts/cleanup_historical_data.py
python scripts/fix_duplicate_funding_data.py
python scripts/retry_incomplete_contracts.py
python scripts/collect_spread_history.py

# Check backfill progress
python check_backfill_status.py
```

## Interactive API Documentation

FastAPI auto-generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these for:
- Testing endpoints
- Viewing request/response schemas
- Understanding query parameters
- Generating example requests
