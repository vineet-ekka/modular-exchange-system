# Maintenance Guide

Database maintenance, data management, and system upkeep procedures.

## Database Maintenance Scripts

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `cleanup_historical_data.py` | Remove old/invalid historical records | Weekly or when storage is an issue |
| `fix_duplicate_funding_data.py` | Resolve duplicate funding rate entries | After data inconsistencies detected |
| `retry_incomplete_contracts.py` | Retry failed contract fetches | After network issues or API errors |
| `collect_spread_history.py` | Populate arbitrage spreads table | After backfilling historical rates |
| `backfill_arbitrage_spreads_v2.py` | Rebuild arbitrage spread statistics | When spread data needs refresh |

## cleanup_historical_data.py

**Purpose:** Removes old, invalid, or corrupted historical funding rate records.

**What it does:**
- Identifies records with null/invalid funding rates
- Deletes records outside configured retention window
- Optimizes database storage and query performance

**Usage:**
```bash
python scripts/cleanup_historical_data.py
```

**When to run:**
- Weekly maintenance schedule
- When database storage exceeds 80% capacity
- After detecting data quality issues
- Before major system upgrades

**Expected output:**
- Count of invalid records found
- Count of records deleted
- Database size reduction

## fix_duplicate_funding_data.py

**Purpose:** Detects and resolves duplicate funding rate entries.

**What it does:**
- Uses UNIQUE constraint (exchange, symbol, funding_time) to identify duplicates
- Keeps the most recent record when duplicates exist
- Prevents data inconsistencies in historical views

**Usage:**
```bash
python scripts/fix_duplicate_funding_data.py
```

**When to run:**
- After detecting duplicate data warnings in logs
- Before generating reports or analytics
- After manual data imports
- When historical views show inconsistent data

**Expected output:**
- Count of duplicate sets found
- Count of records removed
- List of affected exchange-symbol pairs

## retry_incomplete_contracts.py

**Purpose:** Identifies contracts with missing or incomplete historical data and retries fetching.

**What it does:**
- Scans for contracts with gaps in historical coverage
- Retries fetching data for contracts that failed during initial collection
- Ensures complete 30-day historical coverage

**Usage:**
```bash
python scripts/retry_incomplete_contracts.py
```

**When to run:**
- After network issues or API rate limit errors
- When backfill completeness is below 95%
- After adding new exchanges
- Before generating comprehensive reports

**Expected output:**
- List of incomplete contracts
- Retry attempts per contract
- Success/failure status
- Updated completeness percentage

## collect_spread_history.py

**Purpose:** Continuously records cross-exchange funding rate spreads over time.

**What it does:**
- Populates the `arbitrage_spreads` table
- Calculates funding rate spreads between exchange pairs
- Essential for arbitrage opportunity analysis

**Usage:**
```bash
# Run once (manual)
python scripts/collect_spread_history.py

# Run continuously (background process, auto-started by start.py)
# Already running as background process - no action needed
```

**When to run:**
- Automatically runs as background process (started by `start.py`)
- Manually after rebuilding arbitrage data
- After backfilling historical funding rates

**Expected output:**
- Spread records created per interval
- Exchange pairs processed
- Log file: `spread_collector.log`

## backfill_arbitrage_spreads_v2.py

**Purpose:** Rebuilds arbitrage spread statistics from historical data.

**What it does:**
- Calculates spread statistics for all exchange pairs
- Updates `arbitrage_spreads` table with historical analysis
- Required for accurate arbitrage opportunity detection

**Usage:**
```bash
python scripts/backfill_arbitrage_spreads_v2.py
```

**When to run:**
- After completing historical funding rate backfill
- When spread data appears stale or incorrect
- After modifying arbitrage detection logic
- Before generating arbitrage reports

**Expected output:**
- Number of exchange pairs processed
- Spread statistics calculated
- Total records updated in database
- Performance: ~1-3 seconds (batch operations)

## Historical Data Management

### Full 30-Day Backfill

**Purpose:** Refreshes complete 30-day historical data for all exchanges.

**Usage:**
```bash
# Automatic on startup
python start.py

# Manual execution
python scripts/unified_historical_backfill.py --days 30 --parallel
```

**Options:**
- `--days N`: Number of days to backfill (default: 30)
- `--parallel`: Use parallel processing (recommended)

**When to run:**
- Automatically runs on system startup
- After adding new exchanges
- When historical data needs refresh
- After prolonged system downtime

**Progress monitoring:**
```bash
# Check status
python check_backfill_status.py

# View detailed progress
cat .unified_backfill.status | python -m json.tool    # Unix
type .unified_backfill.status | python -m json.tool   # Windows

# Terminal monitor (real-time)
python -m utils.terminal_dashboard
# Press [B] to start, [X] to stop
```

**Expected completeness:** ≥95% of expected data points

### Fill Recent Gaps

**Purpose:** Fills small gaps in recent historical data without full backfill.

**Usage:**
```bash
python scripts/fill_recent_gaps.py
```

**When to run:**
- Daily maintenance
- After temporary API outages
- When specific contracts show gaps
- Faster alternative to full backfill for recent data

## Runtime-Generated Files

Understanding files created during system operation:

### .collection_metrics.json

**Purpose:** Per-exchange collection performance metrics

**Contents:**
- batch_id: Unique identifier for collection cycle
- batch_timestamp: When collection occurred
- Exchange-specific: duration_ms, record_count, success/failure status

**Used by:**
- Terminal dashboard
- `/api/health/performance` endpoint

**Regeneration:** Every 30 seconds during data collection

**Safe to delete:** Yes (regenerated on next cycle)

### .backfill.lock / .unified_backfill.lock

**Purpose:** Prevents multiple backfill processes running simultaneously

**Lifecycle:**
- Created: When backfill starts
- Deleted: When backfill completes successfully

**Manual removal:**
```bash
# If backfill crashes, remove lock manually
rm .backfill.lock .unified_backfill.lock         # Unix
del .backfill.lock .unified_backfill.lock        # Windows
```

**Safe to delete:** Only if backfill process is not running

### .backfill.status / .unified_backfill.status

**Purpose:** Tracks backfill progress per exchange

**Contents:**
- Exchange completion percentages (0-100%)
- Total records collected
- Timestamps
- Completeness metrics

**Used by:**
- Terminal dashboard progress bars
- `/api/backfill-status` endpoint

**Safe to delete:** Yes (recreated on next backfill run)

### Log Files

| File | Purpose | Rotation | Safe to Delete |
|------|---------|----------|----------------|
| `data_collector.log` | Main collection loop output | Manual | Yes (after archiving) |
| `spread_collector.log` | Arbitrage spread tracking | Manual | Yes (after archiving) |
| `zscore_calculator.log` | Statistical analysis | Manual | Yes (after archiving) |

**Log management:**
```bash
# Archive old logs
mv data_collector.log data_collector.log.$(date +%Y%m%d)    # Unix
ren data_collector.log data_collector.log.bak               # Windows

# Delete old logs (CAUTION)
rm data_collector.log        # Unix
del data_collector.log       # Windows

# View log size
ls -lh *.log                 # Unix
dir *.log                    # Windows
```

## Database Tools

### database_tools.py Commands

```bash
# Show table statistics
python database_tools.py status

# Test database connection
python database_tools.py check

# Clear all data (CAUTION: cannot be undone)
python database_tools.py clear --quick

# Export data (if enabled)
# Set ENABLE_CSV_EXPORT = True in config/settings.py
# Creates: unified_exchange_data.csv
```

### Database Backup

**PostgreSQL backup:**
```bash
# Full database backup
docker exec exchange_postgres pg_dump -U postgres exchange_data > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec exchange_postgres pg_dump -U postgres exchange_data | gzip > backup_$(date +%Y%m%d).sql.gz

# Table-specific backup
docker exec exchange_postgres pg_dump -U postgres -t exchange_data exchange_data > exchange_data_backup.sql
```

**Restore from backup:**
```bash
# Restore full database
cat backup_20250101.sql | docker exec -i exchange_postgres psql -U postgres -d exchange_data

# Restore compressed backup
gunzip -c backup_20250101.sql.gz | docker exec -i exchange_postgres psql -U postgres -d exchange_data
```

### Database Size Monitoring

```bash
# Check total database size
psql -U postgres -d exchange_data -c "SELECT pg_size_pretty(pg_database_size('exchange_data'));"

# Check table sizes
psql -U postgres -d exchange_data -c "
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Check index sizes
psql -U postgres -d exchange_data -c "
SELECT
  indexname,
  pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) AS size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC;
"
```

## Routine Maintenance Schedule

### Daily
- Monitor system health via terminal dashboard
- Check log files for errors
- Verify data collection is active

### Weekly
- Run `cleanup_historical_data.py`
- Check database size and growth trend
- Archive old log files
- Review cache hit/miss ratios

### Monthly
- Full database backup
- Run `fix_duplicate_funding_data.py`
- Review and optimize slow queries
- Update system dependencies

### As Needed
- `retry_incomplete_contracts.py` after network issues
- `backfill_arbitrage_spreads_v2.py` when spreads need refresh
- Full 30-day backfill after prolonged downtime

## Data Retention Policy

**Default retention:**
- Real-time data (`exchange_data`): Latest values only (UPSERT)
- Historical data (`funding_rates_historical`): 30-day rolling window
- Arbitrage spreads (`arbitrage_spreads`): Indefinite (for analysis)
- Z-scores (`funding_statistics`): Latest calculations

**Modifying retention:**
Edit `config/settings.py`:
```python
HISTORICAL_DAYS = 30  # Increase for longer retention
```

**Storage estimates:**
- 30 days, 2,275 contracts, 1h intervals: ~1.6M records
- Average database size: 500MB - 2GB (with indexes)
- Growth rate: ~50MB per day (approximation)

## System Reset Procedures

### Soft Reset (Keep Database)
```bash
# Restart all services
python shutdown_dashboard.py
python start.py
```

### Hard Reset (Clear Data, Keep Schema)
```bash
# Clear all data
python database_tools.py clear --quick

# Restart and backfill
python start.py
# Backfill runs automatically
```

### Complete Reset (Delete Everything)
```bash
# Stop services
python shutdown_dashboard.py

# Remove Docker volumes
docker-compose down -v

# Restart fresh
docker-compose up -d
python start.py
```

## Performance Optimization

### Index Maintenance
```bash
# Reindex tables
psql -U postgres -d exchange_data -c "REINDEX TABLE exchange_data;"

# Analyze tables
psql -U postgres -d exchange_data -c "ANALYZE exchange_data;"

# Vacuum (reclaim storage)
psql -U postgres -d exchange_data -c "VACUUM ANALYZE;"
```

### Cache Optimization
```bash
# Clear cache via API
curl -X POST http://localhost:8000/api/cache/clear

# Or via terminal monitor: Press [C]

# Monitor cache performance
curl http://localhost:8000/api/health/cache | python -m json.tool
```

## Troubleshooting Maintenance Issues

For errors during maintenance operations, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

Common issues:
- Lock files preventing operations → Remove manually if process not running
- Database connection failures → Check PostgreSQL status
- Backfill stuck → Check logs, remove lock, retry
- Duplicate data → Run `fix_duplicate_funding_data.py`
