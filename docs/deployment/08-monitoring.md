# Monitoring Guide

> Setting up observability for the Funding Rate Dashboard.

---

## Overview

Monitoring ensures your deployment runs smoothly. This guide covers:

1. Health checks
2. Logging
3. Metrics
4. Alerting
5. External monitoring tools

---

## Built-in Health Endpoints

The application provides several health endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /api/health` | Basic health | `{"status": "healthy"}` |
| `GET /api/health/performance` | Detailed metrics | Collection stats |
| `GET /ready` | Database connectivity | `{"status": "ready"}` |
| `GET /live` | Process alive | `{"status": "alive"}` |

### Health Check Examples

```bash
# Basic health
curl https://your-api.com/api/health
# {"status": "healthy", "timestamp": "2024-01-15T12:00:00Z"}

# Performance metrics
curl https://your-api.com/api/health/performance
# {
#   "collection_cycle": {"duration_ms": 28500, "status": "success"},
#   "exchanges": {"binance": {"records": 592, "status": "ok"}, ...},
#   "database": {"connected": true},
#   "cache": {"type": "redis", "hit_rate": 0.85}
# }

# Readiness (includes DB check)
curl https://your-api.com/ready
# {"status": "ready", "database": "connected"}
```

---

## Platform Monitoring

### Railway

**Built-in Features:**
- Real-time CPU/memory graphs
- Request logs
- Deploy history
- Cost tracking

**Dashboard Location:** https://railway.app/dashboard

**Metrics Available:**
| Metric | Description |
|--------|-------------|
| CPU Usage | Per-service CPU utilization |
| Memory Usage | RAM consumption |
| Network | Inbound/outbound traffic |
| Disk | Storage usage |

### Render

**Built-in Features:**
- Service logs
- Deploy logs
- Basic metrics
- Health check status

**Dashboard Location:** https://dashboard.render.com

### Fly.io

**Built-in Features:**
- `fly status` - Instance status
- `fly logs` - Application logs
- `fly dashboard` - Web interface
- Prometheus metrics endpoint

**Commands:**
```bash
fly status
fly logs
fly monitor
```

### Vercel (Frontend)

**Built-in Features:**
- Web Vitals
- Function logs
- Analytics
- Deployment previews

---

## Logging Configuration

### Structured Logging

For production, use JSON logging:

```python
import logging
import json
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        return json.dumps(log_entry)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if os.getenv("LOG_FORMAT") == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    logger.addHandler(handler)
    return logger
```

### Log Levels

| Level | Use Case |
|-------|----------|
| ERROR | Exceptions, failures |
| WARNING | Rate limits, retries |
| INFO | Collection cycles, API requests |
| DEBUG | Detailed debugging (dev only) |

### Key Events to Log

| Event | Level | Data |
|-------|-------|------|
| Collection started | INFO | batch_id, timestamp |
| Collection completed | INFO | duration, record_count |
| Exchange fetch failed | WARNING | exchange, error |
| Database error | ERROR | query, error |
| Rate limit hit | WARNING | IP, endpoint |
| Cache miss | DEBUG | key |

---

## External Monitoring Tools

### Free Options

| Tool | Purpose | Free Tier |
|------|---------|-----------|
| Better Uptime | Uptime monitoring | 10 monitors |
| UptimeRobot | Uptime monitoring | 50 monitors |
| Sentry | Error tracking | 5K events/mo |
| Logtail | Log aggregation | 1GB/mo |
| Grafana Cloud | Metrics/dashboards | 10K series |

### Better Uptime Setup

1. Sign up at https://betteruptime.com
2. Add monitor:
   - Type: HTTP
   - URL: `https://your-api.com/api/health`
   - Interval: 3 minutes
3. Configure alerts (email, Slack, etc.)

### Sentry Setup

**Add to `requirements.txt`:**
```
sentry-sdk>=1.15.0
```

**Initialize in `api.py`:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production"),
)
```

### Grafana Cloud Setup

For detailed metrics visualization:

1. Sign up at https://grafana.com/products/cloud/
2. Install Grafana Agent on your server
3. Configure Prometheus endpoints
4. Create dashboards

---

## Custom Metrics

### Application Metrics

Track key application metrics:

```python
from prometheus_client import Counter, Histogram, Gauge

# Collection metrics
collection_duration = Histogram(
    'collection_duration_seconds',
    'Time spent collecting data',
    ['exchange']
)

collection_records = Counter(
    'collection_records_total',
    'Total records collected',
    ['exchange']
)

active_contracts = Gauge(
    'active_contracts',
    'Number of active contracts',
    ['exchange']
)

# Usage
with collection_duration.labels(exchange='binance').time():
    data = exchange.fetch_data()

collection_records.labels(exchange='binance').inc(len(data))
active_contracts.labels(exchange='binance').set(len(data))
```

### Expose Metrics Endpoint

```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

## Alerting

### Alert Conditions

| Condition | Threshold | Severity |
|-----------|-----------|----------|
| Health check fails | 3 consecutive | Critical |
| API response > 2s | 5 minutes | Warning |
| Collection cycle > 60s | 3 consecutive | Warning |
| Error rate > 1% | 5 minutes | Warning |
| Database connection fails | Any | Critical |
| Memory > 90% | 5 minutes | Warning |

### Alert Channels

| Channel | Best For |
|---------|----------|
| Email | Non-urgent alerts |
| Slack | Team notifications |
| PagerDuty | On-call rotation |
| SMS | Critical alerts |
| Discord | Personal projects |

### Slack Webhook Example

```python
import requests

def send_alert(message: str, severity: str = "warning"):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    color = {"warning": "#FFA500", "critical": "#FF0000", "info": "#0000FF"}

    requests.post(webhook_url, json={
        "attachments": [{
            "color": color.get(severity, "#808080"),
            "title": f"Alert: {severity.upper()}",
            "text": message,
            "ts": int(time.time())
        }]
    })
```

---

## Dashboard Recommendations

### Key Metrics to Display

**Collection Health:**
- Collection cycle duration
- Records per exchange
- Exchange success rate
- Last successful collection

**API Health:**
- Request rate
- Response time (p50, p95, p99)
- Error rate
- Active connections

**Database Health:**
- Connection pool usage
- Query duration
- Table sizes
- Cache hit rate

**System Health:**
- CPU usage
- Memory usage
- Disk usage
- Network I/O

---

## Debugging Production Issues

### Check Logs

```bash
# Railway
railway logs -f

# Fly.io
fly logs -a your-app

# Docker
docker logs -f container_name
```

### Check Health

```bash
# Basic health
curl -w "\nTime: %{time_total}s\n" https://your-api.com/api/health

# Detailed metrics
curl https://your-api.com/api/health/performance | jq

# Database connectivity
curl https://your-api.com/ready
```

### Check Data Flow

```bash
# Verify data is updating
curl https://your-api.com/api/statistics/summary | jq '.last_updated'

# Check contract counts
curl https://your-api.com/api/statistics/summary | jq '.total_contracts'

# Test specific endpoint
curl "https://your-api.com/api/funding-rates-grid" | jq 'keys | length'
```

---

## Monitoring Checklist

### Setup

- [ ] Health check endpoint configured
- [ ] Uptime monitor added (Better Uptime/UptimeRobot)
- [ ] Error tracking configured (Sentry)
- [ ] Log aggregation set up
- [ ] Alert channels configured

### Ongoing

- [ ] Review logs weekly
- [ ] Check uptime reports
- [ ] Monitor error trends
- [ ] Review performance metrics
- [ ] Update alert thresholds as needed

---

> **Next:** Review [Troubleshooting](10-troubleshooting.md) for common issues.
