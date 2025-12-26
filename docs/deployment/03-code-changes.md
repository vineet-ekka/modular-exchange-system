# Required Code Changes for Deployment

> Modifications needed to deploy the application to production, regardless of platform.

---

## Overview

Before deploying to any platform, certain code changes are required to make the application production-ready. This document covers all necessary modifications.

---

## 1. CORS Configuration

### Current State

**File:** `api.py` (line ~49)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Required Change

```python
import os

# Get allowed origins from environment variable
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Environment Variable

| Variable | Development | Production |
|----------|-------------|------------|
| `CORS_ORIGINS` | `http://localhost:3000` | `https://your-app.vercel.app,https://your-domain.com` |

---

## 2. API Rate Limiting

### Why Needed

Public deployments need protection against abuse. Rate limiting prevents:
- API abuse
- DDoS attacks
- Excessive resource usage

### Implementation

**Add to `requirements.txt`:**

```
slowapi>=0.1.9
```

**Add to `api.py`:**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints (example)
@app.get("/api/funding-rates-grid")
@limiter.limit("60/minute")
async def get_funding_rates_grid(request: Request):
    # ... existing code
```

### Rate Limit Recommendations

| Endpoint Type | Limit | Rationale |
|---------------|-------|-----------|
| Read endpoints | 60/minute | Normal usage |
| Heavy queries | 20/minute | Expensive operations |
| Health checks | 120/minute | Monitoring tools |
| Cache clear | 10/minute | Admin only |

---

## 3. Health Check Endpoints

### Current State

Basic `/api/health` exists but may need enhancement for platform health checks.

### Enhanced Implementation

**Add to `api.py`:**

```python
from datetime import datetime, timezone

@app.get("/health")
async def health():
    """Basic health check for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/ready")
async def readiness():
    """Readiness check - verifies database connection."""
    try:
        # Test database connection
        with postgres_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        return {
            "status": "ready",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "error": str(e)}
        )

@app.get("/live")
async def liveness():
    """Liveness check - basic process health."""
    return {"status": "alive"}
```

### Platform Health Check Configuration

| Platform | Health Endpoint | Interval |
|----------|-----------------|----------|
| Railway | `/health` | Automatic |
| Render | `/health` | 10 seconds |
| Fly.io | `/health` | Configurable |
| Kubernetes | `/ready`, `/live` | Configurable |

---

## 4. Environment Variable Updates

### Files to Update

**`config/settings.py`:**

```python
import os

# API Configuration (add these)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# CORS (add this)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Debug Mode
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
```

**`api.py` (startup):**

```python
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

    uvicorn.run(app, host=host, port=port)
```

> **Note:** Railway and other PaaS use `$PORT` environment variable.

---

## 5. Procfile (For PaaS Platforms)

Create `Procfile` in project root:

```
api: uvicorn api:app --host 0.0.0.0 --port $PORT
collector: python main.py --loop --interval 30 --quiet
zscore: python utils/zscore_calculator.py
spreads: python scripts/collect_spread_history.py
```

### Platform-Specific Notes

| Platform | Uses Procfile | Notes |
|----------|---------------|-------|
| Railway | Yes | Each line = separate service |
| Render | No | Uses render.yaml |
| Heroku | Yes | Native support |
| Fly.io | No | Uses fly.toml |

---

## 6. Railway Configuration

**Create `railway.json`:**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 7. Render Configuration

**Create `render.yaml`:**

```yaml
services:
  - type: web
    name: api-server
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: postgres
          property: connectionString
      - key: CORS_ORIGINS
        value: https://your-frontend.vercel.app

  - type: worker
    name: data-collector
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py --loop --interval 30 --quiet
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: postgres
          property: connectionString

  - type: worker
    name: zscore-calculator
    runtime: python
    startCommand: python utils/zscore_calculator.py

  - type: worker
    name: spread-collector
    runtime: python
    startCommand: python scripts/collect_spread_history.py

databases:
  - name: postgres
    plan: starter
```

---

## 8. Fly.io Configuration

**Create `fly.toml`:**

```toml
app = "funding-rate-dashboard"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[env]
  PORT = "8000"

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.http_checks]]
    interval = "10s"
    timeout = "2s"
    path = "/health"
```

---

## 9. Docker Configuration

**Create/Update `Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Update `docker-compose.yml` for production:**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - CORS_ORIGINS=${CORS_ORIGINS}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  collector:
    build: .
    command: python main.py --loop --interval 30 --quiet
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - api
    restart: unless-stopped

  zscore:
    build: .
    command: python utils/zscore_calculator.py
    environment:
      - POSTGRES_HOST=postgres
    depends_on:
      - collector
    restart: unless-stopped

  spreads:
    build: .
    command: python scripts/collect_spread_history.py
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - collector
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=exchange_data
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

---

## 10. Frontend Configuration

**Update `dashboard/.env.production`:**

```bash
REACT_APP_API_URL=https://your-api-domain.com
```

**Build command:**

```bash
cd dashboard && npm run build
```

**Output:** `dashboard/build/` directory (static files)

---

## 11. Security Headers

**Add to `api.py`:**

```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Add trusted host middleware
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")

if not DEBUG_MODE:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=ALLOWED_HOSTS
    )

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

## 12. Logging Configuration

**Add structured logging for production:**

```python
import logging
import json
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)

    if os.getenv("LOG_FORMAT") == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

---

## Summary Checklist

### Required Changes

- [ ] Update CORS to use environment variable
- [ ] Add rate limiting with slowapi
- [ ] Add/enhance health check endpoints
- [ ] Update API port configuration for `$PORT`
- [ ] Create platform-specific config files

### Recommended Changes

- [ ] Add security headers middleware
- [ ] Configure structured logging
- [ ] Add request size limits
- [ ] Add trusted host middleware

### Platform-Specific Files

| Platform | Required Files |
|----------|----------------|
| Railway | `Procfile`, `railway.json` |
| Render | `render.yaml` |
| Fly.io | `fly.toml`, `Dockerfile` |
| VPS/Docker | `Dockerfile`, `docker-compose.yml` |
| Heroku | `Procfile`, `runtime.txt` |

---

> **Next:** Follow the platform-specific setup guide for your chosen deployment target.
