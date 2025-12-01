# Troubleshooting Guide

Common issues and solutions for the exchange data system.

## Quick Diagnostic Commands

| Task | Command | Notes |
|------|---------|-------|
| Check API health | `curl http://localhost:8000/api/health` | Should return status: "healthy" |
| View performance metrics | `curl http://localhost:8000/api/health/performance` | Shows collection times |
| Test database connection | `python database_tools.py check` | Verifies PostgreSQL access |
| Check logs | `type data_collector.log` (Win) / `tail -f data_collector.log` (Unix) | Real-time log monitoring |
| Monitor API response | `time curl -s http://localhost:8000/api/funding-rates-grid > /dev/null` | Measure response time |

## Process Management

### Find and Kill Processes

**Windows:**
```bash
# Find process on port 8000
netstat -ano | findstr :8000

# Kill specific process
taskkill /PID <pid> /F

# List all Python processes
tasklist | findstr "python"

# Kill all Python processes (CAUTION)
taskkill /F /IM python.exe
```

**Linux/Mac:**
```bash
# Find process on port 8000
lsof -i :8000

# Kill specific process
kill -9 <pid>

# List all Python processes
ps aux | grep python

# Kill specific Python script
pkill -f "python main.py"
```

### Monitor Background Processes

```bash
# Monitor Z-score calculator
ps aux | grep zscore_calculator    # Linux/Mac
tasklist | findstr "zscore"        # Windows

# Monitor arbitrage spread collector
ps aux | grep collect_spread       # Linux/Mac
tasklist | findstr "spread"        # Windows

# Monitor data collector
ps aux | grep "python main.py"     # Linux/Mac
tasklist | findstr "main.py"       # Windows
```

## Log File Analysis

### Check for errors

**Windows:**
```bash
# Search for errors in data collector log
type data_collector.log | findstr "ERROR"

# Search for specific exchange issues
type data_collector.log | findstr "binance"

# View last 50 lines
powershell -Command "Get-Content data_collector.log -Tail 50"
```

**Linux/Mac:**
```bash
# Follow log in real-time
tail -f data_collector.log

# Search for errors
tail -f data_collector.log | grep ERROR

# Search for specific exchange
grep "binance" data_collector.log

# View last 50 lines
tail -50 data_collector.log
```

### Common log patterns

| Pattern | Meaning | Action |
|---------|---------|--------|
| `ERROR.*relation does not exist` | Database schema missing | Restart API server to create schema |
| `ERROR.*connection refused.*5432` | PostgreSQL not running | Start Docker: `docker-compose up -d` |
| `ERROR.*connection refused.*6379` | Redis not running | System uses fallback cache (OK) |
| `WARNING.*rate limit` | API rate limit hit | Automatic retry will handle |
| `ERROR.*timeout` | Exchange API slow/down | Skips exchange, continues with others |

## Database Issues

### Connection problems

```bash
# Test database connection
python database_tools.py check

# Check if PostgreSQL is running
docker ps | grep exchange_postgres    # Docker
pg_isready -h localhost -p 5432      # Native PostgreSQL

# Verify connection parameters
psql -h localhost -U postgres -d exchange_data -c "SELECT 1;"

# Check database exists
psql -h localhost -U postgres -c "\l" | grep exchange_data
```

### Schema issues

```bash
# Check if tables exist
psql -U postgres -d exchange_data -c "\dt"

# Verify exchange_data table
psql -U postgres -d exchange_data -c "SELECT COUNT(*) FROM exchange_data;"

# Check table structure
psql -U postgres -d exchange_data -c "\d exchange_data"

# Recreate schema (CAUTION: deletes data)
python database_tools.py clear --quick
python start.py    # API server recreates schema
```

### Performance issues

```bash
# Check table sizes
python database_tools.py status

# Check active connections
psql -U postgres -d exchange_data -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Check slow queries
psql -U postgres -d exchange_data -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"

# Analyze table statistics
psql -U postgres -d exchange_data -c "ANALYZE VERBOSE exchange_data;"
```

## Redis Cache Issues

### Check Redis connectivity

```bash
# Test Redis connection
docker exec -it exchange_redis redis-cli PING
# Expected: PONG

# Check cache health
curl http://localhost:8000/api/health/cache | python -m json.tool

# View cache statistics
docker exec -it exchange_redis redis-cli INFO stats

# Check memory usage
docker exec -it exchange_redis redis-cli INFO memory
```

### Cache performance problems

```bash
# Check hit/miss ratio
docker exec -it exchange_redis redis-cli INFO stats | grep keyspace

# View all cached keys
docker exec -it exchange_redis redis-cli KEYS "*"

# Check specific key TTL
docker exec -it exchange_redis redis-cli TTL "funding_rates_grid"

# Clear cache if stale
curl -X POST http://localhost:8000/api/cache/clear | python -m json.tool

# Or via terminal monitor: Press [C]
```

## API Server Issues

### Server won't start

```bash
# Check if port 8000 is already in use
netstat -ano | findstr :8000    # Windows
lsof -i :8000                   # Linux/Mac

# Kill process on port 8000 (see Process Management above)

# Check for missing dependencies
pip list | grep fastapi
pip list | grep uvicorn
pip list | grep psutil

# Install missing packages
pip install fastapi uvicorn psutil scipy websockets

# Start API server manually (for debugging)
uvicorn api:app --host 0.0.0.0 --port 8000
```

### API endpoints return errors

```bash
# Check API health
curl http://localhost:8000/api/health

# Test specific endpoint
curl http://localhost:8000/api/funding-rates-grid | python -m json.tool

# Check API logs (if running in terminal)
# Look for stack traces and error messages

# Verify database has data
psql -U postgres -d exchange_data -c "SELECT exchange, COUNT(*) FROM exchange_data GROUP BY exchange;"
```

## Collection Issues

### Data not updating

```bash
# Check if data collector is running
ps aux | grep "python main.py"       # Linux/Mac
tasklist | findstr "main.py"         # Windows

# Check last update time
curl http://localhost:8000/api/health/performance | python -m json.tool

# View collection metrics
cat .collection_metrics.json | python -m json.tool    # Unix
type .collection_metrics.json | python -m json.tool   # Windows

# Manually trigger collection (if not in loop mode)
python main.py
```

### Specific exchange failing

```bash
# Test individual exchange
python -c "from exchanges.binance_exchange import BinanceExchange; e=BinanceExchange(); print(len(e.fetch_data()))"

# Check exchange-specific logs
grep "binance" data_collector.log | grep ERROR

# Verify exchange API is accessible
curl https://fapi.binance.com/fapi/v1/premiumIndex    # Binance
curl https://api-futures.kucoin.com/api/v1/contracts/active    # KuCoin

# Check if exchange is enabled
grep "ENABLED_EXCHANGES" config/settings.py
```

## Backfill Issues

### Backfill stuck or slow

```bash
# Check backfill status
python check_backfill_status.py

# View backfill progress
cat .unified_backfill.status | python -m json.tool    # Unix
type .unified_backfill.status | python -m json.tool   # Windows

# Check for lock file (prevents concurrent backfills)
ls -la .backfill.lock         # Unix
dir .backfill.lock            # Windows

# Remove lock if backfill crashed
rm .backfill.lock             # Unix
del .backfill.lock            # Windows

# Stop running backfill (terminal monitor)
# Press [X] in terminal monitor
```

### Backfill errors

```bash
# Check backfill logs
grep "backfill" data_collector.log | grep ERROR

# Retry failed contracts
python scripts/retry_incomplete_contracts.py

# Fill recent gaps only
python scripts/fill_recent_gaps.py

# Restart full backfill
python scripts/unified_historical_backfill.py --days 30 --parallel
```

## Frontend Issues

### Dashboard won't load

```bash
# Check if React dev server is running
netstat -ano | findstr :3000    # Windows
lsof -i :3000                   # Linux/Mac

# Start dashboard manually
cd dashboard && npm start

# Check for missing dependencies
cd dashboard && npm install

# Build production version
cd dashboard && npm run build
cd dashboard && npx serve -s build
```

### Type errors in frontend

```bash
# Run TypeScript type checking
cd dashboard && npx tsc --noEmit

# Fix type errors shown in output

# Run tests to verify
cd dashboard && npm test -- --watchAll=false
```

## Common Error Patterns and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "relation does not exist" | Database schema not created | Restart API server |
| "connection refused (5432)" | PostgreSQL not running | `docker-compose up -d` |
| "connection refused (6379)" | Redis not running | System uses fallback (OK) |
| "Module not found: fastapi" | Missing dependencies | `pip install fastapi uvicorn psutil scipy websockets` |
| "Port 8000 already in use" | Previous API instance running | Kill process on port 8000 |
| "Lock file exists" | Backfill already running | Remove `.backfill.lock` if crashed |
| "UNIQUE constraint violation" | Duplicate data insert | Fixed automatically by UPSERT |
| "Too many connections" | PostgreSQL connection pool exhausted | Restart API server |
| "Rate limit exceeded" | Exchange API throttling | Wait 60s, system auto-retries |
| "Timeout reading from socket" | Exchange API slow | System skips exchange, continues |

## System Health Checklist

Run these checks to verify system health:

```bash
# 1. Docker containers running
docker ps | grep -E "exchange_postgres|exchange_redis"

# 2. API server responding
curl http://localhost:8000/api/health

# 3. Database accessible
python database_tools.py check

# 4. Data being collected
curl http://localhost:8000/api/health/performance

# 5. Recent data exists
psql -U postgres -d exchange_data -c "SELECT exchange, MAX(last_updated) FROM exchange_data GROUP BY exchange;"

# 6. Cache working
curl http://localhost:8000/api/health/cache

# 7. Frontend accessible
curl http://localhost:3000
```

All checks should pass for a healthy system.

## Getting Help

If issues persist:

1. Check recent logs: `tail -100 data_collector.log | grep ERROR`
2. Verify system health checklist above
3. Review [CLAUDE.md](../CLAUDE.md) for architectural context
4. Check [API_REFERENCE.md](API_REFERENCE.md) for endpoint documentation
5. Report issue at https://github.com/anthropics/claude-code/issues (if Claude Code related)
