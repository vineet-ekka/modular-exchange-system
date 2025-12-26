# Environment Variables Reference

> Complete configuration reference for all deployment environments.

---

## Overview

This document lists all environment variables used by the application, organized by component.

---

## Quick Reference

### Required Variables

| Variable | Component | Example |
|----------|-----------|---------|
| `POSTGRES_HOST` | Database | `localhost` or `db.railway.app` |
| `POSTGRES_PORT` | Database | `5432` |
| `POSTGRES_DATABASE` | Database | `exchange_data` |
| `POSTGRES_USER` | Database | `postgres` |
| `POSTGRES_PASSWORD` | Database | `your-secure-password` |

### Optional Variables

| Variable | Component | Default | Purpose |
|----------|-----------|---------|---------|
| `REDIS_HOST` | Cache | `localhost` | Redis server |
| `REDIS_PORT` | Cache | `6379` | Redis port |
| `PORT` | API | `8000` | Server port (PaaS sets this) |
| `CORS_ORIGINS` | API | `localhost:3000` | Allowed origins |
| `DEBUG` | API | `false` | Debug mode |

---

## Database Configuration

### PostgreSQL

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_HOST` | Yes | `localhost` | Database hostname |
| `POSTGRES_PORT` | Yes | `5432` | Database port |
| `POSTGRES_DATABASE` | Yes | `exchange_data` | Database name |
| `POSTGRES_USER` | Yes | `postgres` | Database username |
| `POSTGRES_PASSWORD` | Yes | None | Database password |
| `DATABASE_URL` | No | None | Full connection string (overrides above) |

**Connection String Format:**
```
postgresql://user:password@host:port/database
```

**Platform-Specific Notes:**

| Platform | How Provided |
|----------|--------------|
| Railway | Auto-injected as individual vars + `DATABASE_URL` |
| Render | `DATABASE_URL` from linked database |
| Fly.io | Set manually or via `fly secrets` |
| Heroku | `DATABASE_URL` from add-on |

### Table Names

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_TABLE_NAME` | `exchange_data` | Real-time data table |
| `HISTORICAL_TABLE_NAME` | `exchange_data_historical` | Historical data table |

---

## Cache Configuration

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | No | `localhost` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_PASSWORD` | No | None | Redis password |
| `REDIS_DB` | No | `0` | Redis database number |
| `REDIS_URL` | No | None | Full connection string |

**Connection String Format:**
```
redis://[:password@]host:port/db
```

**Fallback Behavior:**
If Redis is unavailable, the system automatically falls back to in-memory caching.

---

## API Server Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8000` | Server port (PaaS sets this) |
| `API_HOST` | No | `0.0.0.0` | Bind address |
| `API_PORT` | No | `8000` | Server port (fallback) |
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FORMAT` | No | `text` | `text` or `json` |

### CORS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | Yes (prod) | `http://localhost:3000` | Comma-separated origins |
| `ALLOWED_HOSTS` | No | `*` | Trusted host header values |

**Example CORS Values:**

```bash
# Development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Production
CORS_ORIGINS=https://dashboard.example.com,https://www.example.com
```

---

## Data Collection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_SEQUENTIAL_COLLECTION` | `False` | Use sequential mode |
| `EXCHANGE_COLLECTION_DELAY` | `30` | Delay between exchanges (sequential) |
| `API_DELAY` | `0.5` | Delay between API calls |
| `ENABLE_OPEN_INTEREST_FETCH` | `True` | Fetch open interest data |
| `ENABLE_FUNDING_RATE_FETCH` | `True` | Fetch funding rates |

### Exchange Enable/Disable

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_BINANCE` | `True` | Enable Binance |
| `ENABLE_KUCOIN` | `True` | Enable KuCoin |
| `ENABLE_BYBIT` | `True` | Enable ByBit |
| `ENABLE_MEXC` | `True` | Enable MEXC |
| `ENABLE_HYPERLIQUID` | `True` | Enable Hyperliquid |
| `ENABLE_DRIFT` | `True` | Enable Drift |
| `ENABLE_ASTER` | `True` | Enable Aster |
| `ENABLE_LIGHTER` | `True` | Enable Lighter |
| `ENABLE_BACKPACK` | `True` | Enable Backpack |
| `ENABLE_DERIBIT` | `True` | Enable Deribit |
| `ENABLE_PACIFICA` | `True` | Enable Pacifica |
| `ENABLE_HIBACHI` | `True` | Enable Hibachi |
| `ENABLE_DYDX` | `True` | Enable dYdX |

---

## Historical Data Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_HISTORICAL_COLLECTION` | `True` | Enable historical backfill |
| `HISTORICAL_FETCH_INTERVAL` | `300` | Fetch interval (seconds) |
| `HISTORICAL_WINDOW_DAYS` | `30` | Days of history to maintain |
| `HISTORICAL_SYNC_ENABLED` | `True` | Sync historical windows |
| `HISTORICAL_ALIGN_TO_MIDNIGHT` | `True` | Align to UTC midnight |

---

## Z-Score Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ZSCORE_CALCULATION_INTERVAL` | `30` | Calculation interval (seconds) |
| `ZSCORE_ACTIVE_THRESHOLD` | `2.0` | Threshold for active zone |
| `ZSCORE_MIN_DATA_POINTS` | `10` | Minimum data for calculation |

---

## Frontend Configuration

**File:** `dashboard/.env` or `dashboard/.env.production`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REACT_APP_API_URL` | Yes | `http://localhost:8000` | Backend API URL |

**Example Values:**

```bash
# Development
REACT_APP_API_URL=http://localhost:8000

# Production
REACT_APP_API_URL=https://api.your-domain.com
```

---

## Platform-Specific Variables

### Railway

Railway automatically injects these when you add services:

| Variable | Source | Description |
|----------|--------|-------------|
| `PORT` | Railway | Assigned port for web service |
| `RAILWAY_ENVIRONMENT` | Railway | `production` or `staging` |
| `PGHOST` | PostgreSQL service | Database host |
| `PGPORT` | PostgreSQL service | Database port |
| `PGDATABASE` | PostgreSQL service | Database name |
| `PGUSER` | PostgreSQL service | Database user |
| `PGPASSWORD` | PostgreSQL service | Database password |
| `DATABASE_URL` | PostgreSQL service | Full connection string |
| `REDISHOST` | Redis service | Redis host |
| `REDISPORT` | Redis service | Redis port |
| `REDISPASSWORD` | Redis service | Redis password |
| `REDIS_URL` | Redis service | Full connection string |

**Variable References:**
```bash
# Reference other service variables
POSTGRES_HOST=${{Postgres.PGHOST}}
REDIS_HOST=${{Redis.REDISHOST}}
```

### Render

| Variable | Source | Description |
|----------|--------|-------------|
| `PORT` | Render | Assigned port |
| `RENDER` | Render | `true` when on Render |
| `IS_PULL_REQUEST` | Render | `true` for PR previews |
| `DATABASE_URL` | Linked database | Connection string |
| `REDIS_URL` | Linked Redis | Connection string |

### Fly.io

| Variable | Source | Description |
|----------|--------|-------------|
| `PORT` | Fly.io | Internal port (usually 8080) |
| `FLY_APP_NAME` | Fly.io | Application name |
| `FLY_REGION` | Fly.io | Deployment region |
| `PRIMARY_REGION` | Fly.io | Primary region |

Set secrets with:
```bash
fly secrets set POSTGRES_PASSWORD=xxx
```

### Heroku

| Variable | Source | Description |
|----------|--------|-------------|
| `PORT` | Heroku | Assigned port |
| `DATABASE_URL` | Heroku Postgres | Connection string |
| `REDIS_URL` | Heroku Redis | Connection string |

---

## Environment Files

### Development (.env)

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=exchange_data
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-local-password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API
DEBUG=true
CORS_ORIGINS=http://localhost:3000
```

### Production (.env.production)

```bash
# Database (use platform variables or secrets)
POSTGRES_HOST=${PGHOST}
POSTGRES_PORT=${PGPORT}
POSTGRES_DATABASE=${PGDATABASE}
POSTGRES_USER=${PGUSER}
POSTGRES_PASSWORD=${PGPASSWORD}

# Redis
REDIS_HOST=${REDISHOST}
REDIS_PORT=${REDISPORT}

# API
DEBUG=false
CORS_ORIGINS=https://your-frontend.vercel.app
ALLOWED_HOSTS=your-api.railway.app,your-domain.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Dashboard (.env.production)

```bash
REACT_APP_API_URL=https://your-api.railway.app
```

---

## Secrets Management

### Best Practices

| Practice | Description |
|----------|-------------|
| Never commit secrets | Use `.gitignore` for `.env` files |
| Use platform secrets | Railway, Render, Fly all have secret management |
| Rotate regularly | Change passwords periodically |
| Minimal permissions | Use least-privilege database users |

### Platform Secret Commands

**Railway:**
```bash
railway variables set POSTGRES_PASSWORD=xxx
```

**Render:**
```bash
# Use dashboard or render.yaml with fromDatabase
```

**Fly.io:**
```bash
fly secrets set POSTGRES_PASSWORD=xxx
fly secrets list
```

**Heroku:**
```bash
heroku config:set POSTGRES_PASSWORD=xxx
heroku config
```

---

## Validation

### Check Required Variables

```python
import os
import sys

REQUIRED = [
    'POSTGRES_HOST',
    'POSTGRES_PORT',
    'POSTGRES_DATABASE',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
]

missing = [var for var in REQUIRED if not os.getenv(var)]
if missing:
    print(f"Missing required variables: {missing}")
    sys.exit(1)
```

### Health Check Endpoint

The `/ready` endpoint verifies database connectivity:

```bash
curl https://your-api.com/ready
# {"status": "ready", "database": "connected"}
```

---

> **Next:** Review [Security](07-security.md) for securing public deployments.
