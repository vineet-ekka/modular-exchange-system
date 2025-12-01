# API Reference

Complete reference for all FastAPI endpoints in the modular exchange system.

## Base URL

```
http://localhost:8000
```

## Quick Reference

The API provides real-time and historical funding rate data across 15+ cryptocurrency exchanges with powerful filtering, analytics, and arbitrage detection capabilities.

**Key Features:**
- Real-time funding rates with 30-second refresh
- 30-day historical data for all contracts
- Statistical analysis (Z-scores, percentiles)
- Cross-exchange arbitrage detection
- Multi-parameter filtering and pagination
- Dual-cache architecture (Redis + fallback)

---

## Data Retrieval Endpoints

### GET /api/funding-rates

Returns current funding rates with optional filtering.

**Query Parameters:**
- `exchange` (optional): Filter by exchange name
- `asset` (optional): Filter by base asset
- `min_apr` (optional): Minimum APR threshold
- `max_apr` (optional): Maximum APR threshold

**Example:**
```bash
curl "http://localhost:8000/api/funding-rates?exchange=binance&min_apr=10"
```

**Response:**
```json
[
  {
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "base_asset": "BTC",
    "funding_rate": 0.0001,
    "apr": 87.6,
    "funding_interval_hours": 1,
    "next_funding_time": "2025-01-18T12:00:00Z",
    "mark_price": 95234.50,
    "index_price": 95230.00,
    "open_interest": 1234567.89,
    "last_updated": "2025-01-18T11:45:32Z"
  }
]
```

### GET /api/funding-rates-grid

Asset-based grid view showing all exchanges for each asset.

**Example:**
```bash
curl "http://localhost:8000/api/funding-rates-grid"
```

**Response:**
```json
{
  "BTC": {
    "binance": {"funding_rate": 0.0001, "apr": 87.6, ...},
    "kucoin": {"funding_rate": 0.00015, "apr": 13.14, ...},
    "bybit": {"funding_rate": 0.0002, "apr": 175.2, ...}
  }
}
```

### GET /api/historical/{symbol}

Historical funding rates for a specific symbol.

**Path Parameters:**
- `symbol` (required): Contract symbol (e.g., BTCUSDT)

**Query Parameters:**
- `days` (optional, default=30): Number of days of history
- `exchange` (optional): Filter by exchange

**Example:**
```bash
curl "http://localhost:8000/api/historical/BTCUSDT?days=7&exchange=binance"
```

### GET /api/historical-funding/{symbol}

Historical funding data with funding intervals included.

**Example:**
```bash
curl "http://localhost:8000/api/historical-funding/ETHUSDT"
```

### GET /api/historical-funding-by-asset/{asset}

All contracts for a specific asset across all exchanges.

**Path Parameters:**
- `asset` (required): Base asset (e.g., BTC, ETH)

**Example:**
```bash
curl "http://localhost:8000/api/historical-funding-by-asset/BTC"
```

### GET /api/historical-funding-by-contract/{exchange}/{symbol}

Contract-specific historical funding data.

**Path Parameters:**
- `exchange` (required): Exchange name
- `symbol` (required): Contract symbol

**Example:**
```bash
curl "http://localhost:8000/api/historical-funding-by-contract/binance/BTCUSDT"
```

### GET /api/current-funding/{asset}

Current funding rate with countdown timer to next funding.

**Path Parameters:**
- `asset` (required): Base asset

**Example:**
```bash
curl "http://localhost:8000/api/current-funding/BTC"
```

**Response:**
```json
{
  "asset": "BTC",
  "contracts": [
    {
      "exchange": "binance",
      "funding_rate": 0.0001,
      "next_funding_time": "2025-01-18T12:00:00Z",
      "seconds_until_funding": 845
    }
  ]
}
```

### GET /api/funding-sparkline/{symbol}

Sparkline data for mini-charts (last 24 hours).

**Path Parameters:**
- `symbol` (required): Contract symbol

**Example:**
```bash
curl "http://localhost:8000/api/funding-sparkline/BTCUSDT"
```

### GET /api/contracts-by-asset/{asset}

List all contracts (across all exchanges) for a specific asset.

**Path Parameters:**
- `asset` (required): Base asset

**Example:**
```bash
curl "http://localhost:8000/api/contracts-by-asset/ETH"
```

---

## Statistics & Analytics Endpoints

### GET /api/statistics

Dashboard statistics (overview of system state).

**Example:**
```bash
curl "http://localhost:8000/api/statistics"
```

**Response:**
```json
{
  "total_contracts": 2275,
  "active_exchanges": 15,
  "unique_assets": 656,
  "last_update": "2025-01-18T11:45:32Z",
  "avg_funding_rate": 0.00015,
  "contracts_by_exchange": {
    "binance": 592,
    "kucoin": 522,
    "bybit": 667
  }
}
```

### GET /api/statistics/summary

Overall system statistics with aggregations.

**Example:**
```bash
curl "http://localhost:8000/api/statistics/summary"
```

### GET /api/statistics/extreme-values

Statistical outliers and extremes (highest/lowest funding rates).

**Example:**
```bash
curl "http://localhost:8000/api/statistics/extreme-values"
```

**Response:**
```json
{
  "highest_positive": [
    {"exchange": "binance", "symbol": "XAIUSDT", "funding_rate": 0.05, "apr": 4380}
  ],
  "highest_negative": [
    {"exchange": "kucoin", "symbol": "DOGEUSDT", "funding_rate": -0.03, "apr": -262.8}
  ]
}
```

### GET /api/top-apr/{limit}

Top APR contracts (sorted by absolute APR value).

**Path Parameters:**
- `limit` (required): Number of results to return

**Example:**
```bash
curl "http://localhost:8000/api/top-apr/10"
```

### GET /api/group-by-asset

Funding rates grouped by base asset.

**Example:**
```bash
curl "http://localhost:8000/api/group-by-asset"
```

### GET /api/contracts-with-zscores

All contracts with Z-score data (statistical significance).

**Example:**
```bash
curl "http://localhost:8000/api/contracts-with-zscores"
```

**Response:**
```json
[
  {
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "base_asset": "BTC",
    "funding_rate": 0.0001,
    "z_score": 2.5,
    "percentile": 98.5,
    "confidence": "high",
    "mean": 0.00005,
    "std_dev": 0.00002
  }
]
```

### GET /api/zscore-summary

Z-score summary statistics across all contracts.

**Example:**
```bash
curl "http://localhost:8000/api/zscore-summary"
```

---

## Arbitrage Endpoints

### GET /api/arbitrage/opportunities (Legacy)

Legacy arbitrage endpoint with basic pagination.

**Query Parameters:**
- `page` (optional, default=1): Page number
- `page_size` (optional, default=20): Results per page

**Example:**
```bash
curl "http://localhost:8000/api/arbitrage/opportunities?page=1&page_size=20"
```

### GET /api/arbitrage/opportunities-v2 (Enhanced)

Enhanced arbitrage endpoint with multi-parameter filtering.

**Query Parameters:**
- `exchanges` (multi-select): Filter by exchange names (can specify multiple)
- `intervals` (multi-select): Filter by funding intervals (1h, 2h, 4h, 8h, variable)
- `min_apr_spread` (optional): Minimum APR spread threshold
- `max_apr_spread` (optional): Maximum APR spread threshold
- `asset` (optional): Filter by specific asset
- `page` (optional, default=1): Page number
- `page_size` (optional, default=20): Results per page
- `sort_by` (optional): Sort field (spread, asset, exchanges)

**Example:**
```bash
# Filter by exchanges and intervals
curl "http://localhost:8000/api/arbitrage/opportunities-v2?exchanges=binance&exchanges=kucoin&intervals=1h&intervals=8h&min_apr_spread=50"

# Filter by APR spread range
curl "http://localhost:8000/api/arbitrage/opportunities-v2?min_apr_spread=30&max_apr_spread=100"

# Search by asset
curl "http://localhost:8000/api/arbitrage/opportunities-v2?asset=BTC"
```

**Response:**
```json
{
  "opportunities": [
    {
      "asset": "BTC",
      "long_exchange": "binance",
      "short_exchange": "kucoin",
      "long_rate": -0.0001,
      "short_rate": 0.0002,
      "apr_spread": 75.5,
      "daily_spread": 0.207,
      "sync_period_spread": 0.207,
      "spread_z_score": 3.2,
      "confidence": "high"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

### GET /api/arbitrage/assets/search

Search for assets in arbitrage opportunities.

**Query Parameters:**
- `q` (required): Search query (partial asset name)

**Example:**
```bash
curl "http://localhost:8000/api/arbitrage/assets/search?q=BTC"
```

**Response:**
```json
{
  "results": ["BTC", "WBTC", "BTCB"]
}
```

### GET /api/arbitrage/opportunity-detail/{asset}/{long_exchange}/{short_exchange}

Detailed arbitrage opportunity data for a specific pairing.

**Path Parameters:**
- `asset` (required): Base asset
- `long_exchange` (required): Exchange for long position
- `short_exchange` (required): Exchange for short position

**Example:**
```bash
curl "http://localhost:8000/api/arbitrage/opportunity-detail/BTC/binance/kucoin"
```

**Response:**
```json
{
  "asset": "BTC",
  "long_exchange": "binance",
  "short_exchange": "kucoin",
  "current_spread": 0.0003,
  "apr_spread": 75.5,
  "spread_history": [...],
  "spread_z_score": 3.2,
  "historical_mean": 0.0001,
  "historical_std_dev": 0.000062,
  "confidence": "high"
}
```

---

## System Health & Performance

### GET /api/health

Basic health check (returns 200 if API is running).

**Example:**
```bash
curl "http://localhost:8000/api/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-18T11:45:32Z",
  "api_version": "1.0.0"
}
```

### GET /api/health/performance

System performance metrics including collection timing.

**Example:**
```bash
curl "http://localhost:8000/api/health/performance"
```

**Response:**
```json
{
  "batch_id": "a3f5d2",
  "batch_timestamp": "2025-01-18T11:45:00Z",
  "exchanges": {
    "binance": {
      "duration_ms": 8234,
      "record_count": 592,
      "status": "success"
    },
    "kucoin": {
      "duration_ms": 9123,
      "record_count": 522,
      "status": "success"
    }
  },
  "total_duration_ms": 29234,
  "success_count": 15,
  "failure_count": 0
}
```

### GET /api/health/cache

Cache health monitoring (Redis connection and hit/miss ratios).

**Example:**
```bash
curl "http://localhost:8000/api/health/cache"
```

**Response:**
```json
{
  "redis_connected": true,
  "cache_type": "Redis",
  "hit_rate": 0.87,
  "total_keys": 42,
  "memory_usage_mb": 3.2
}
```

---

## Backfill Management

### GET /api/backfill-status

Current backfill progress (quick status check).

**Example:**
```bash
curl "http://localhost:8000/api/backfill-status"
```

**Response:**
```json
{
  "is_running": true,
  "progress": 75.5,
  "exchanges_complete": 11,
  "exchanges_total": 15,
  "estimated_completion": "2025-01-18T12:15:00Z"
}
```

### GET /api/backfill/status

Detailed backfill status per exchange.

**Example:**
```bash
curl "http://localhost:8000/api/backfill/status"
```

### GET /api/backfill/verify

Verify backfill completeness (checks for gaps in historical data).

**Example:**
```bash
curl "http://localhost:8000/api/backfill/verify"
```

### POST /api/backfill/start

Start historical backfill (30-day parallel collection).

**Request Body:**
```json
{
  "days": 30,
  "exchanges": ["binance", "kucoin"],
  "parallel": true
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/backfill/start" \
  -H "Content-Type: application/json" \
  -d '{"days": 30, "parallel": true}'
```

### POST /api/backfill/stop

Stop running backfill process.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/backfill/stop"
```

### POST /api/backfill/retry

Retry failed backfills for specific exchanges.

**Request Body:**
```json
{
  "exchanges": ["binance", "kucoin"]
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/backfill/retry" \
  -H "Content-Type: application/json" \
  -d '{"exchanges": ["binance"]}'
```

---

## Settings Management

### GET /api/settings

Retrieve current system settings.

**Example:**
```bash
curl "http://localhost:8000/api/settings"
```

### PUT /api/settings

Update system settings.

**Request Body:**
```json
{
  "parallel_collection": true,
  "collection_interval_seconds": 30,
  "cache_ttl_seconds": 5
}
```

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/settings" \
  -H "Content-Type: application/json" \
  -d '{"parallel_collection": true}'
```

### POST /api/settings/validate

Validate settings without saving.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/settings/validate" \
  -H "Content-Type: application/json" \
  -d '{"cache_ttl_seconds": 5}'
```

### GET /api/settings/backups

List available settings backups.

**Example:**
```bash
curl "http://localhost:8000/api/settings/backups"
```

### POST /api/settings/restore

Restore settings from backup.

**Request Body:**
```json
{
  "backup_id": "2025-01-18-120000"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/settings/restore" \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "2025-01-18-120000"}'
```

### GET /api/settings/export

Export current settings as JSON.

**Example:**
```bash
curl "http://localhost:8000/api/settings/export" > settings.json
```

### POST /api/settings/import

Import settings from JSON file.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/settings/import" \
  -H "Content-Type: application/json" \
  -d @settings.json
```

### POST /api/settings/reset

Reset all settings to defaults.

**Example:**
```bash
curl -X POST "http://localhost:8000/api/settings/reset"
```

---

## Metadata & Discovery

### GET /api/exchanges

List all active exchanges with contract counts.

**Example:**
```bash
curl "http://localhost:8000/api/exchanges"
```

**Response:**
```json
{
  "exchanges": [
    {"name": "binance", "contracts": 592, "status": "active"},
    {"name": "kucoin", "contracts": 522, "status": "active"},
    {"name": "bybit", "contracts": 667, "status": "active"}
  ],
  "total": 15
}
```

### GET /api/assets

List all unique assets across all exchanges.

**Example:**
```bash
curl "http://localhost:8000/api/assets"
```

**Response:**
```json
{
  "assets": ["BTC", "ETH", "SOL", "DOGE", ...],
  "total": 656
}
```

### GET /

Root endpoint with system information.

**Example:**
```bash
curl "http://localhost:8000/"
```

**Response:**
```json
{
  "message": "Modular Exchange Funding Rate API",
  "version": "1.0.0",
  "exchanges": 15,
  "contracts": 2275,
  "documentation": "/docs"
}
```

### GET /api/test

Test endpoint for debugging and API verification.

**Example:**
```bash
curl "http://localhost:8000/api/test"
```

---

## System Control

### POST /api/shutdown

Clean shutdown of all services (API, collectors, background workers).

**Example:**
```bash
curl -X POST "http://localhost:8000/api/shutdown"
```

**Response:**
```json
{
  "message": "Shutdown initiated",
  "timestamp": "2025-01-18T11:45:32Z"
}
```

### POST /api/cache/clear

Clear Redis/fallback cache (returns number of entries cleared).

**Example:**
```bash
curl -X POST "http://localhost:8000/api/cache/clear"
```

**Response:**
```json
{
  "message": "Cache cleared",
  "entries_cleared": 42
}
```

---

## Interactive API Documentation

FastAPI provides auto-generated interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

These endpoints allow you to:
- Browse all available endpoints
- View request/response schemas
- Test API calls directly in the browser
- Download OpenAPI specification

---

## Rate Limiting & Caching

**Cache TTLs:**
- Funding rates: 5 seconds
- Statistics summaries: 10 seconds
- Arbitrage opportunities: 30 seconds
- Z-score data: 25 seconds

**Cache Invalidation:**
- Automatic after data collection completes
- Manual via POST `/api/cache/clear`
- Manual via terminal dashboard [C] key

**Connection Pooling:**
- PostgreSQL: 5-20 connections
- Redis: 10 connections max
- HTTP sessions: Thread-local with connection pooling

---

## Error Responses

All endpoints follow standard HTTP status codes:

**Success:**
- `200 OK`: Request successful
- `201 Created`: Resource created

**Client Errors:**
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error

**Server Errors:**
- `500 Internal Server Error`: Unexpected server error
- `503 Service Unavailable`: Service temporarily unavailable

**Example Error Response:**
```json
{
  "error": "Invalid exchange name",
  "detail": "Exchange 'invalid' not found. Available: binance, kucoin, bybit, ...",
  "status_code": 400
}
```
