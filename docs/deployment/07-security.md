# Security Guide

> Securing the Funding Rate Dashboard for public deployment.

---

## Security Overview

When deploying publicly, you need to protect against:

| Threat | Mitigation |
|--------|------------|
| API abuse | Rate limiting |
| DDoS attacks | CDN + rate limits |
| Data exposure | CORS restrictions |
| Injection attacks | Input validation |
| Unauthorized access | Authentication (optional) |

---

## Platform-Provided Security

Most platforms provide baseline security automatically:

| Feature | Railway | Render | Fly.io | Vercel |
|---------|---------|--------|--------|--------|
| HTTPS/TLS | Auto | Auto | Auto | Auto |
| DDoS protection | Basic | Basic | Basic | Advanced |
| Network isolation | Yes | Yes | Yes | N/A |
| Secret management | Yes | Yes | Yes | Yes |

---

## Rate Limiting

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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.get("/api/funding-rates-grid")
@limiter.limit("60/minute")
async def get_funding_rates_grid(request: Request):
    ...

@app.get("/api/arbitrage/opportunities-v2")
@limiter.limit("30/minute")
async def get_arbitrage_opportunities(request: Request):
    ...
```

### Recommended Limits

| Endpoint Category | Limit | Rationale |
|-------------------|-------|-----------|
| Read endpoints | 60/min | Normal browsing |
| Heavy queries | 20/min | Expensive operations |
| Statistics | 30/min | Moderate load |
| Health checks | 120/min | Monitoring tools |
| Admin endpoints | 10/min | Rare operations |

### Response on Limit

```json
{
  "error": "Rate limit exceeded",
  "detail": "60 per 1 minute"
}
```

HTTP Status: `429 Too Many Requests`

---

## CORS Configuration

### Current Issue

The default configuration only allows localhost:

```python
allow_origins=["http://localhost:3000"]
```

### Secure Configuration

```python
import os

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
)
```

### Environment Variable

```bash
# Production
CORS_ORIGINS=https://dashboard.example.com,https://www.example.com

# Never use * in production
# CORS_ORIGINS=*  # BAD - allows any origin
```

---

## Security Headers

### Implementation

```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Trusted hosts (prevent host header attacks)
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # XSS protection (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy (adjust as needed)
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response
```

### Headers Explained

| Header | Purpose |
|--------|---------|
| `X-Content-Type-Options` | Prevent MIME sniffing |
| `X-Frame-Options` | Prevent clickjacking |
| `X-XSS-Protection` | XSS protection for old browsers |
| `Referrer-Policy` | Control referrer information |
| `Content-Security-Policy` | Control resource loading |
| `Strict-Transport-Security` | Force HTTPS (usually set by platform) |

---

## Request Validation

### Size Limits

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

class LimitRequestSize(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 1_000_000):  # 1MB
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large"}
            )
        return await call_next(request)

app.add_middleware(LimitRequestSize, max_size=1_000_000)
```

### Input Validation

FastAPI's Pydantic models provide automatic validation:

```python
from pydantic import BaseModel, Field, validator

class ArbitrageQuery(BaseModel):
    exchanges: list[str] = Field(max_items=13)
    min_apr: float = Field(ge=0, le=10000)
    max_apr: float = Field(ge=0, le=10000)

    @validator('exchanges')
    def validate_exchanges(cls, v):
        valid = {'binance', 'kucoin', 'bybit', ...}
        for exchange in v:
            if exchange.lower() not in valid:
                raise ValueError(f'Invalid exchange: {exchange}')
        return v
```

---

## Database Security

### Connection Security

```python
# Use SSL in production
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

# Connection with SSL
connection = psycopg2.connect(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DATABASE,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    sslmode='require'  # or 'verify-full'
)
```

### Query Safety

The application already uses parameterized queries via psycopg2:

```python
# Safe - parameterized
cursor.execute(
    "SELECT * FROM exchange_data WHERE symbol = %s",
    (symbol,)
)

# UNSAFE - string formatting (never do this)
# cursor.execute(f"SELECT * FROM exchange_data WHERE symbol = '{symbol}'")
```

### Minimal Permissions

Create a read-only user for the API if not writing:

```sql
CREATE USER api_readonly WITH PASSWORD 'xxx';
GRANT CONNECT ON DATABASE exchange_data TO api_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_readonly;
```

---

## Redis Security

### Authentication

```python
import redis

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,  # Always set in production
    ssl=True,  # Use SSL if available
    decode_responses=True
)
```

### Key Prefixing

Prevent key collisions in shared Redis:

```python
CACHE_PREFIX = "funding_dashboard:"

def cache_key(key: str) -> str:
    return f"{CACHE_PREFIX}{key}"
```

---

## Authentication (Optional)

For private deployments, add API key authentication:

### Simple API Key

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        return  # No auth required if not configured

    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# Apply to endpoints
@app.get("/api/admin/cache/clear")
async def clear_cache(api_key: str = Security(verify_api_key)):
    ...
```

### Usage

```bash
curl -H "X-API-Key: your-secret-key" https://api.example.com/api/admin/cache/clear
```

---

## Logging & Monitoring

### Security Logging

```python
import logging

security_logger = logging.getLogger("security")

@app.middleware("http")
async def log_requests(request, call_next):
    # Log suspicious activity
    client_ip = request.client.host

    response = await call_next(request)

    # Log rate limit hits
    if response.status_code == 429:
        security_logger.warning(
            f"Rate limit hit: {client_ip} - {request.url.path}"
        )

    # Log auth failures
    if response.status_code == 403:
        security_logger.warning(
            f"Auth failure: {client_ip} - {request.url.path}"
        )

    return response
```

### Alerts

Set up alerts for:

| Event | Threshold | Action |
|-------|-----------|--------|
| Rate limit hits | >100/hour | Review traffic |
| Auth failures | >10/minute | Block IP |
| 5xx errors | >10/minute | Investigate |
| Unusual traffic | 10x normal | Review |

---

## Secrets Management

### Never Commit Secrets

**`.gitignore`:**
```
.env
.env.*
*.pem
*.key
secrets/
```

### Use Platform Secrets

| Platform | Command |
|----------|---------|
| Railway | `railway variables set KEY=value` |
| Render | Dashboard or `render.yaml` |
| Fly.io | `fly secrets set KEY=value` |
| Vercel | Dashboard or `vercel env add` |

### Rotate Secrets

1. Generate new secret
2. Add to platform (both old and new)
3. Deploy with new secret
4. Remove old secret

---

## Cloudflare Protection (Recommended)

For additional protection, put Cloudflare in front:

### Setup

1. Add domain to Cloudflare
2. Point DNS to your backend
3. Enable proxy (orange cloud)

### Benefits

| Feature | Description |
|---------|-------------|
| DDoS protection | Automatic mitigation |
| WAF | Web application firewall |
| Rate limiting | Additional layer |
| Bot protection | Challenge suspicious traffic |
| SSL/TLS | Edge certificates |
| Caching | Reduce origin load |

### Configuration

```
# Cloudflare settings
SSL/TLS: Full (strict)
Security Level: Medium
Bot Fight Mode: On
Rate Limiting: Custom rules
```

---

## Security Checklist

### Before Deployment

- [ ] CORS configured for production domains
- [ ] Rate limiting implemented
- [ ] Security headers added
- [ ] Database passwords set
- [ ] Redis password set (if used)
- [ ] Secrets not in code
- [ ] Debug mode disabled

### After Deployment

- [ ] HTTPS working
- [ ] Rate limits tested
- [ ] CORS restrictions verified
- [ ] Health endpoints accessible
- [ ] Monitoring configured
- [ ] Logs collecting

### Ongoing

- [ ] Monitor for suspicious activity
- [ ] Review logs regularly
- [ ] Update dependencies
- [ ] Rotate secrets periodically
- [ ] Test backups

---

> **Next:** Review [Monitoring](08-monitoring.md) for observability setup.
