# Railway Deployment Guide

> Step-by-step guide to deploy the complete system on Railway.

---

## Overview

| Attribute | Value |
|-----------|-------|
| Platform | Railway.app |
| Estimated Cost | $25-40/month |
| Complexity | Low |
| Deployment Time | ~30 minutes |

---

## Prerequisites

- GitHub account with repository access
- Railway account (https://railway.app)
- Credit card (for usage billing)

---

## Architecture on Railway

```
Railway Project
├── api-server        (Web Service)
├── data-collector    (Worker)
├── zscore-calculator (Worker)
├── spread-collector  (Worker)
├── PostgreSQL        (Database)
└── Redis             (Cache - Optional)
```

---

## Step 1: Create Railway Project

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select your repository

---

## Step 2: Add PostgreSQL

1. In your project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway provisions the database automatically

**Note the variables created:**
- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`
- `DATABASE_URL`

---

## Step 3: Add Redis (Optional)

1. Click "New"
2. Select "Database" → "Add Redis"
3. Railway provisions Redis automatically

**Variables created:**
- `REDISHOST`
- `REDISPORT`
- `REDISPASSWORD`
- `REDIS_URL`

---

## Step 4: Configure API Server

### Select Your GitHub Service

Click on the service created from your GitHub repo.

### Configure Build

Settings → Build:
- Builder: Nixpacks (automatic)
- Watch Paths: Leave empty for all

### Configure Start Command

Settings → Deploy → Start Command:
```
uvicorn api:app --host 0.0.0.0 --port $PORT
```

### Add Environment Variables

Settings → Variables → Add:

| Variable | Value |
|----------|-------|
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` |
| `POSTGRES_DATABASE` | `${{Postgres.PGDATABASE}}` |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` |
| `REDIS_HOST` | `${{Redis.REDISHOST}}` |
| `REDIS_PORT` | `${{Redis.REDISPORT}}` |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app` |

### Generate Domain

Settings → Networking → Generate Domain

Note the URL (e.g., `your-app.up.railway.app`)

---

## Step 5: Add Data Collector Worker

1. Click "New" → "GitHub Repo"
2. Select the same repository
3. Configure:

**Settings → Deploy → Start Command:**
```
python main.py --loop --interval 30 --quiet
```

**Settings → Variables:**
Same as API server (copy all variables)

**Settings → Networking:**
- No domain needed (worker doesn't receive HTTP)

---

## Step 6: Add Z-Score Calculator

1. Click "New" → "GitHub Repo"
2. Select the same repository
3. Configure:

**Start Command:**
```
python utils/zscore_calculator.py
```

**Variables:** Same as API server

---

## Step 7: Add Spread Collector

1. Click "New" → "GitHub Repo"
2. Select the same repository
3. Configure:

**Start Command:**
```
python scripts/collect_spread_history.py
```

**Variables:** Same as API server

---

## Step 8: Verify Deployment

### Check Service Status

All services should show "Active" in the dashboard.

### Check API Health

```bash
curl https://your-app.up.railway.app/api/health
# {"status": "healthy", "timestamp": "..."}
```

### Check Data Collection

```bash
curl https://your-app.up.railway.app/api/statistics/summary
# Should show contract counts
```

---

## Step 9: Run Initial Backfill

Option A: Via Railway CLI
```bash
railway run python scripts/unified_historical_backfill.py --days 30 --parallel
```

Option B: Add as temporary service
1. Create new service with command:
   ```
   python scripts/unified_historical_backfill.py --days 30 --parallel
   ```
2. Remove after completion

---

## Configuration Files

### railway.json

Create in project root:

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

### Procfile (Optional)

For reference, but Railway uses start commands per service:

```
api: uvicorn api:app --host 0.0.0.0 --port $PORT
collector: python main.py --loop --interval 30 --quiet
zscore: python utils/zscore_calculator.py
spreads: python scripts/collect_spread_history.py
```

---

## Railway CLI Usage

### Install CLI

```bash
npm install -g @railway/cli
```

### Login

```bash
railway login
```

### Common Commands

```bash
# Link to project
railway link

# View logs
railway logs

# View specific service logs
railway logs -s api-server

# Run command in project context
railway run python manage.py migrate

# Set variables
railway variables set KEY=value

# Open dashboard
railway open
```

---

## Troubleshooting

### Service Crashes on Start

1. Check logs: `railway logs -s service-name`
2. Verify start command is correct
3. Check environment variables are set

### Database Connection Fails

1. Verify PostgreSQL service is running
2. Check variable references use correct syntax: `${{Postgres.PGHOST}}`
3. Restart API service after database is ready

### CORS Errors

1. Verify `CORS_ORIGINS` includes your frontend domain
2. Include protocol: `https://your-frontend.vercel.app`
3. Redeploy after changing variables

### High Costs

1. Check usage in dashboard
2. Review service resource consumption
3. Consider combining services if possible

---

## Cost Management

### Monitor Usage

Dashboard → Usage tab shows:
- CPU hours
- Memory GB-hours
- Storage usage
- Bandwidth

### Set Spending Limit

Settings → Billing → Spending Limit

Recommended: Set to $50-75/month initially

### Optimize Costs

| Optimization | Savings |
|--------------|---------|
| Skip Redis (use fallback) | $2-3/mo |
| Reduce worker memory | Variable |
| Prune old data | Storage costs |

---

## Maintenance

### Redeploying

Push to GitHub triggers automatic redeploy.

```bash
git push origin main
```

### Manual Redeploy

Dashboard → Service → Deployments → Redeploy

### Rollback

Dashboard → Service → Deployments → Select previous → Rollback

### Database Backup

```bash
railway run pg_dump $DATABASE_URL > backup.sql
```

---

## Environment Summary

| Service | Start Command | Resources |
|---------|--------------|-----------|
| api-server | `uvicorn api:app --host 0.0.0.0 --port $PORT` | 1GB RAM |
| data-collector | `python main.py --loop --interval 30 --quiet` | 1GB RAM |
| zscore-calculator | `python utils/zscore_calculator.py` | 512MB RAM |
| spread-collector | `python scripts/collect_spread_history.py` | 512MB RAM |

---

## Next Steps

1. Deploy frontend to Vercel (see [Vercel Setup](05-vercel-setup.md))
2. Configure monitoring (see [Monitoring](08-monitoring.md))
3. Set up alerts

---

> **Back to:** [Overview](00-overview.md)
