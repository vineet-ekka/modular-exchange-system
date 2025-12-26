# Production Architecture

> Platform-agnostic system design for deploying the Funding Rate Dashboard.

---

## System Components Overview

The application consists of six main components that must work together:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │   Binance    │  │   KuCoin     │  │   ByBit      │  ... 10 more    │
│   │     API      │  │     API      │  │     API      │                  │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│          │                 │                 │                           │
│          └─────────────────┼─────────────────┘                           │
│                            │                                             │
│                            ▼                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                         YOUR INFRASTRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     BACKGROUND WORKERS                           │    │
│  ├──────────────┬──────────────┬──────────────┬──────────────────┤    │
│  │ Data         │ Z-Score      │ Spread       │ Historical       │    │
│  │ Collector    │ Calculator   │ Collector    │ Backfill         │    │
│  │ (30s loop)   │ (continuous) │ (continuous) │ (on startup)     │    │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────────────────┘    │
│         │              │              │                                 │
│         └──────────────┼──────────────┘                                 │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      DATA LAYER                                  │    │
│  ├────────────────────────────┬────────────────────────────────────┤    │
│  │        PostgreSQL          │            Redis                    │    │
│  │      (Primary Store)       │          (Cache)                    │    │
│  │                            │                                     │    │
│  │  • exchange_data           │  • 5s TTL for rates                │    │
│  │  • funding_rates_historical│  • 30s TTL for arbitrage           │    │
│  │  • funding_statistics      │  • Optional (has fallback)         │    │
│  │  • contract_metadata       │                                     │    │
│  │  • arbitrage_spreads       │                                     │    │
│  └────────────────────────────┴────────────────────────────────────┘    │
│                        │                                                 │
│                        ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      API SERVER                                  │    │
│  │                                                                  │    │
│  │  FastAPI Application                                             │    │
│  │  • REST endpoints                                                │    │
│  │  • CORS configuration                                            │    │
│  │  • Rate limiting                                                 │    │
│  │  • Health checks                                                 │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (CDN)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   React Application (Static Build)                                       │
│   • Served from CDN (Vercel, Netlify, Cloudflare)                       │
│   • Calls API for data                                                   │
│   • Auto-refreshes every 30 seconds                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. API Server

| Attribute | Details |
|-----------|---------|
| **Technology** | FastAPI + Uvicorn |
| **Language** | Python 3.8+ |
| **Port** | 8000 (configurable) |
| **Memory** | 512MB - 1GB |
| **CPU** | 0.5 - 1 vCPU |

**Responsibilities:**
- Serve REST API endpoints
- Query PostgreSQL database
- Manage Redis cache
- Handle CORS for frontend
- Rate limit requests

**Key Endpoints:**

| Endpoint | Purpose | Cache TTL |
|----------|---------|-----------|
| `/api/funding-rates-grid` | Main dashboard data | 5s |
| `/api/arbitrage/opportunities-v2` | Arbitrage detection | 30s |
| `/api/statistics/summary` | System statistics | 10s |
| `/api/health` | Health check | None |
| `/api/contracts-with-zscores` | Z-score data | 25s |

---

### 2. Data Collector Worker

| Attribute | Details |
|-----------|---------|
| **Script** | `main.py --loop --interval 30` |
| **Schedule** | Every 30 seconds |
| **Memory** | 1GB - 2GB |
| **CPU** | 2 vCPU (parallel fetching) |

**Responsibilities:**
- Fetch data from 13 exchanges
- Normalize to standard format
- Calculate APR values
- Update PostgreSQL
- Invalidate cache

**Exchange Fetching:**

```
Parallel Mode (Default):
┌─────────────────────────────────────────────────────────────┐
│  ThreadPoolExecutor (10 workers)                            │
├─────────────────────────────────────────────────────────────┤
│  T1: Binance    T2: KuCoin    T3: ByBit    T4: MEXC        │
│  T5: Hyperliquid T6: Drift   T7: Aster    T8: Lighter      │
│  T9: Backpack   T10: Deribit ...                            │
├─────────────────────────────────────────────────────────────┤
│  All complete in ~30 seconds                                │
└─────────────────────────────────────────────────────────────┘

Sequential Mode (Optional):
┌─────────────────────────────────────────────────────────────┐
│  Exchange 1 (0s) → Exchange 2 (30s) → Exchange 3 (60s) ... │
│  Total time: 4-5 minutes                                    │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Z-Score Calculator Worker

| Attribute | Details |
|-----------|---------|
| **Script** | `utils/zscore_calculator.py` |
| **Schedule** | Continuous (30-60s intervals) |
| **Memory** | 256MB - 512MB |
| **CPU** | 0.5 vCPU |

**Responsibilities:**
- Calculate Z-scores for all contracts
- Update funding_statistics table
- Zone-based scheduling (active vs stable)

**Processing:**

| Zone | Z-Score Range | Update Interval |
|------|---------------|-----------------|
| Active | \|Z\| > 2.0 | Every 30 seconds |
| Stable | \|Z\| <= 2.0 | Every 60 seconds |

---

### 4. Spread Collector Worker

| Attribute | Details |
|-----------|---------|
| **Script** | `scripts/collect_spread_history.py` |
| **Schedule** | Continuous |
| **Memory** | 256MB |
| **CPU** | 0.25 vCPU |

**Responsibilities:**
- Track cross-exchange arbitrage spreads
- Build historical spread data
- Calculate spread statistics

---

### 5. PostgreSQL Database

| Attribute | Details |
|-----------|---------|
| **Version** | 15+ |
| **Storage** | 15GB+ (grows ~500MB/month) |
| **Memory** | 1GB recommended |
| **Connections** | 5-20 pool |

**Core Tables:**

| Table | Purpose | Estimated Size |
|-------|---------|----------------|
| `exchange_data` | Real-time rates | ~500KB |
| `funding_rates_historical` | 30-day history | ~10GB |
| `funding_statistics` | Z-scores | ~2MB |
| `contract_metadata` | Lifecycle | ~1MB |
| `arbitrage_spreads` | Opportunities | ~2GB |

---

### 6. Redis Cache (Optional)

| Attribute | Details |
|-----------|---------|
| **Version** | 7+ |
| **Memory** | 512MB |
| **Eviction** | LRU (Least Recently Used) |
| **Persistence** | AOF recommended |

**Cache Strategy:**

| Data Type | TTL | Fallback |
|-----------|-----|----------|
| Funding rates | 5s | In-memory |
| Statistics | 10s | In-memory |
| Arbitrage | 30s | In-memory |
| Z-scores | 25s | In-memory |

> **Note:** Redis is optional. The system has an in-memory SimpleCache fallback.

---

### 7. Frontend Dashboard

| Attribute | Details |
|-----------|---------|
| **Framework** | React 19 + TypeScript |
| **Build Output** | Static files (`dashboard/build/`) |
| **Size** | ~5MB compressed |
| **CDN** | Recommended |

**Hosting Options:**

| Provider | Cost | Features |
|----------|------|----------|
| Vercel | Free | React optimized, global CDN |
| Netlify | Free | 100GB bandwidth |
| Cloudflare Pages | Free | Unlimited bandwidth |
| GitHub Pages | Free | Basic static hosting |

---

## Deployment Patterns

### Pattern A: All-in-One PaaS

All services on a single PaaS provider.

```
┌─────────────────────────────────────────┐
│              Railway / Render            │
├─────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │   API   │  │ Workers │  │  Static │ │
│  └────┬────┘  └────┬────┘  └────┬────┘ │
│       │            │            │       │
│  ┌────┴────────────┴────────────┴────┐ │
│  │         PostgreSQL + Redis         │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Pros:** Simple, unified billing, easy management
**Cons:** Vendor lock-in, potentially higher cost

---

### Pattern B: Split Frontend/Backend

Frontend on free hosting, backend on PaaS.

```
┌──────────────────┐     ┌──────────────────────────┐
│      Vercel      │     │         Railway          │
│    (Frontend)    │────▶│        (Backend)         │
│       FREE       │     │                          │
└──────────────────┘     │  API + Workers + DB      │
                         └──────────────────────────┘
```

**Pros:** Free frontend, optimized CDN
**Cons:** Two platforms to manage

---

### Pattern C: VPS with Docker

Everything on a single VPS using Docker Compose.

```
┌─────────────────────────────────────────────────┐
│               VPS (Hetzner/DO/Vultr)            │
├─────────────────────────────────────────────────┤
│                  Docker Compose                  │
│  ┌──────────────────────────────────────────┐   │
│  │  ┌─────┐ ┌─────────┐ ┌─────────────────┐│   │
│  │  │ API │ │ Workers │ │ Postgres+Redis  ││   │
│  │  │     │ │ (4)     │ │                 ││   │
│  │  └─────┘ └─────────┘ └─────────────────┘│   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│            Cloudflare (CDN + Proxy)             │
└─────────────────────────────────────────────────┘
```

**Pros:** Lowest cost, full control
**Cons:** Self-managed, requires Docker knowledge

---

### Pattern D: Hybrid with Managed Database

Compute on VPS, database managed externally.

```
┌─────────────────────┐     ┌─────────────────────┐
│        VPS          │     │   Managed Database  │
│  (API + Workers)    │────▶│  (Supabase/Neon)    │
│                     │     │                     │
└─────────────────────┘     └─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Vercel (Frontend)                   │
└─────────────────────────────────────────────────┘
```

**Pros:** Managed backups, easy scaling
**Cons:** More complexity, potential latency

---

## Networking Requirements

### Inbound Traffic

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 443 | HTTPS | Internet | API requests |
| 443 | HTTPS | Internet | Frontend (CDN) |

### Outbound Traffic

| Destination | Protocol | Purpose |
|-------------|----------|---------|
| Exchange APIs | HTTPS | Data collection |
| CDN | HTTPS | Frontend assets |

### Internal Traffic

| From | To | Protocol | Purpose |
|------|-----|----------|---------|
| API | PostgreSQL | TCP:5432 | Database queries |
| API | Redis | TCP:6379 | Cache operations |
| Workers | PostgreSQL | TCP:5432 | Data writes |
| Workers | Redis | TCP:6379 | Cache invalidation |

---

## Resource Allocation Guide

### Minimum (Development/Personal)

| Component | Resources | Cost Estimate |
|-----------|-----------|---------------|
| All-in-one VPS | 2 vCPU, 4GB RAM | $10-20/mo |
| Managed DB | 1GB RAM | $0-15/mo |
| Frontend | CDN | $0 |
| **Total** | | **$10-35/mo** |

### Standard (Production)

| Component | Resources | Cost Estimate |
|-----------|-----------|---------------|
| API | 1 vCPU, 1GB RAM | $10-15/mo |
| Workers | 2 vCPU, 2GB RAM | $15-20/mo |
| PostgreSQL | 1GB RAM, 20GB | $10-15/mo |
| Redis | 512MB | $5/mo |
| Frontend | CDN | $0 |
| **Total** | | **$40-55/mo** |

### High Availability

| Component | Resources | Cost Estimate |
|-----------|-----------|---------------|
| API (2x) | 2x 1 vCPU, 1GB | $20-30/mo |
| Workers | 2 vCPU, 2GB RAM | $15-20/mo |
| PostgreSQL (HA) | 2 nodes | $30-50/mo |
| Redis (Sentinel) | 3 nodes | $15-25/mo |
| Load Balancer | Managed | $10-20/mo |
| Frontend | CDN | $0 |
| **Total** | | **$90-145/mo** |

---

## Startup Sequence

The services must start in a specific order:

```
1. PostgreSQL
   │
   ├── Wait for healthy
   │
2. Redis (optional)
   │
   ├── Continue even if fails (fallback available)
   │
3. API Server
   │
   ├── Creates database schema
   ├── Wait 10 seconds
   │
4. Data Collector
   │
   ├── Requires schema to exist
   │
5. Z-Score Calculator
   │
   ├── Requires historical data
   │
6. Spread Collector
   │
   ├── Requires arbitrage data
   │
7. Frontend
   │
   └── Connects to API
```

---

## Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /api/health` | Basic health | `{"status": "healthy"}` |
| `GET /api/health/performance` | Detailed metrics | Collection stats |
| `GET /ready` | Readiness (DB check) | `{"status": "ready"}` |

---

## Scaling Considerations

### Horizontal Scaling

| Component | Scalable? | Notes |
|-----------|-----------|-------|
| API Server | Yes | Add load balancer |
| Data Collector | No | Would cause duplicates |
| Z-Score Worker | No | Single instance only |
| Spread Collector | No | Single instance only |
| PostgreSQL | Yes | Read replicas |
| Redis | Yes | Cluster mode |

### Vertical Scaling

| Bottleneck | Solution |
|------------|----------|
| API slow | Increase RAM for caching |
| Collection slow | Increase CPU for parallel fetch |
| Database slow | Add indexes, increase RAM |
| Cache misses | Increase Redis memory |

---

> **Next:** Review [Code Changes](03-code-changes.md) required for deployment.
