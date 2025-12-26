# Troubleshooting Guide

> Solutions for common deployment issues.

---

## Quick Diagnostics

### Health Check Commands

```bash
# API health
curl https://your-api.com/api/health

# Database connectivity
curl https://your-api.com/ready

# Performance metrics
curl https://your-api.com/api/health/performance

# Contract count (should be ~3,400+)
curl https://your-api.com/api/statistics/summary | jq '.total_contracts'
```

---

## Deployment Issues

### Build Fails

**Symptom:** Deployment fails during build phase.

**Common Causes:**

| Cause | Solution |
|-------|----------|
| Missing dependencies | Check `requirements.txt` is complete |
| Python version mismatch | Specify version in `runtime.txt` |
| Node version mismatch | Check `.nvmrc` or `package.json` |
| TypeScript errors | Run `npx tsc --noEmit` locally first |

**Railway Fix:**
```bash
# Check build logs
railway logs --build

# Force rebuild
railway up --force
```

**Render Fix:**
```bash
# Trigger manual deploy from dashboard
# Or push empty commit
git commit --allow-empty -m "Trigger rebuild"
git push
```

### Service Won't Start

**Symptom:** Deployment succeeds but service immediately crashes.

**Check logs:**
```bash
# Railway
railway logs

# Fly.io
fly logs

# Render
# Check dashboard logs
```

**Common Causes:**

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing package | Add to requirements.txt |
| `Port already in use` | Wrong port config | Use `$PORT` env variable |
| `Connection refused` | Database not ready | Check startup order |
| `relation does not exist` | Schema not created | Start API first |

---

## Database Issues

### Cannot Connect to Database

**Symptom:** API returns 503, logs show database connection errors.

**Check:**
```bash
# Verify database is running
curl https://your-api.com/ready
# Should return {"status": "ready", "database": "connected"}
```

**Solutions:**

| Platform | Solution |
|----------|----------|
| Railway | Check PostgreSQL service is running in dashboard |
| Render | Verify database is linked to service |
| Fly.io | Check `fly postgres list` |
| VPS | `docker ps` to verify container |

**Common Fixes:**
```bash
# Check environment variables are set
echo $POSTGRES_HOST
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT 1"
```

### Schema Not Created

**Symptom:** `relation "exchange_data" does not exist`

**Cause:** Data collector started before API created schema.

**Solution:**
1. Restart API server
2. Wait 10 seconds
3. Restart data collector

**Prevention:**
- Ensure API starts before workers
- Add startup delay to workers

### Database Full

**Symptom:** Write operations fail, disk space errors.

**Check:**
```sql
SELECT pg_size_pretty(pg_database_size('exchange_data'));
```

**Solutions:**
```sql
-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Prune old historical data (keep 30 days)
DELETE FROM funding_rates_historical
WHERE funding_time < NOW() - INTERVAL '30 days';

-- Reclaim space
VACUUM FULL;
```

---

## API Issues

### CORS Errors

**Symptom:** Frontend shows CORS errors in browser console.

**Check:**
```bash
curl -I -X OPTIONS https://your-api.com/api/funding-rates-grid \
  -H "Origin: https://your-frontend.com"
```

**Solution:**
```bash
# Set CORS_ORIGINS environment variable
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

### Rate Limiting

**Symptom:** `429 Too Many Requests`

**Check:** Review rate limit configuration.

**Solutions:**
- Increase limits if legitimate traffic
- Implement client-side caching
- Add CDN caching layer

### Slow Responses

**Symptom:** API responses take > 1 second.

**Diagnostics:**
```bash
# Check response time
curl -w "\nTime: %{time_total}s\n" https://your-api.com/api/funding-rates-grid

# Check cache status
curl https://your-api.com/api/health/cache
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| Cache misses | Verify Redis is connected |
| Database slow | Check indexes, add connection pool |
| High load | Scale up or add caching |
| Cold start | Use minimum 1 replica |

---

## Worker Issues

### Data Not Updating

**Symptom:** Dashboard shows stale data (last_updated > 5 minutes old).

**Check:**
```bash
curl https://your-api.com/api/statistics/summary | jq '.last_updated'
```

**Diagnostics:**
```bash
# Check worker logs
railway logs -s collector

# Check worker status
fly status -a your-collector
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| Worker crashed | Check logs, restart |
| Rate limited by exchange | Increase delays |
| Network issues | Check outbound connectivity |
| Database full | Clear old data |

### Exchange Fetch Failures

**Symptom:** Some exchanges show no data.

**Check performance endpoint:**
```bash
curl https://your-api.com/api/health/performance | jq '.exchanges'
```

**Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Network issues | Check firewall |
| 429 Too Many Requests | Rate limited | Increase delays |
| 403 Forbidden | IP blocked | Change IP/use proxy |
| Empty response | API changed | Check exchange docs |

---

## Cache Issues

### Redis Connection Failed

**Symptom:** Logs show Redis connection errors.

**Impact:** System falls back to in-memory cache (functional but slower).

**Check:**
```bash
# Verify Redis is running
redis-cli -h $REDIS_HOST ping
```

**Solutions:**

| Platform | Solution |
|----------|----------|
| Railway | Check Redis service in dashboard |
| Render | Verify Redis is linked |
| VPS | `docker ps` to check container |

### Cache Not Working

**Symptom:** High database load, slow responses.

**Check:**
```bash
curl https://your-api.com/api/health/cache
```

**Solutions:**
- Verify REDIS_HOST and REDIS_PORT are set
- Check Redis memory limit (should be > 256MB)
- Review cache TTL settings

---

## Frontend Issues

### API Connection Failed

**Symptom:** Dashboard shows "Unable to connect to API"

**Check:**
1. API is running: `curl https://your-api.com/api/health`
2. CORS is configured for frontend domain
3. Frontend API URL is correct

**Fix:**
```bash
# Check frontend environment
# dashboard/.env.production
REACT_APP_API_URL=https://your-api.com
```

### Stale Data Displayed

**Symptom:** Data updates but dashboard doesn't refresh.

**Solutions:**
- Hard refresh: Ctrl+Shift+R
- Clear browser cache
- Check React Query cache settings

---

## Platform-Specific Issues

### Railway

**Service Not Starting:**
```bash
railway logs -s service-name
railway status
```

**Environment Variables:**
```bash
railway variables list
railway variables set KEY=value
```

### Render

**Deployment Stuck:**
1. Cancel current deploy
2. Check for errors in logs
3. Trigger new deploy

**Worker Not Running:**
- Verify worker type is "Background Worker" not "Web Service"
- Check health check is disabled for workers

### Fly.io

**Out of Memory:**
```bash
fly scale memory 512
```

**Machine Not Starting:**
```bash
fly machine list
fly machine start <id>
```

**Secrets Not Loading:**
```bash
fly secrets list
fly secrets set KEY=value
fly deploy
```

---

## Network Issues

### Outbound Requests Blocked

**Symptom:** Cannot reach exchange APIs.

**Check:**
```bash
curl -I https://api.binance.com/api/v3/ping
```

**Solutions:**
- Check firewall rules allow HTTPS outbound
- Verify DNS resolution works
- Check if exchange blocks your IP

### SSL Certificate Errors

**Symptom:** SSL/TLS errors in logs.

**Solutions:**
- Update CA certificates
- Check system time is correct
- Verify certificate chain

---

## Recovery Procedures

### Full System Restart

```bash
# Railway
railway up --force

# Fly.io
fly deploy

# Docker
docker-compose down && docker-compose up -d
```

### Database Recovery

```bash
# Connect to database
psql $DATABASE_URL

# Check tables exist
\dt

# Verify data
SELECT COUNT(*) FROM exchange_data;
```

### Force Data Refresh

```bash
# Clear cache
curl -X POST https://your-api.com/api/cache/clear

# Trigger backfill
curl -X POST https://your-api.com/api/backfill/start
```

---

## Getting Help

### Information to Gather

Before seeking help, collect:

1. Platform and plan
2. Error messages (exact text)
3. Relevant logs
4. When issue started
5. What changed recently

### Support Channels

| Platform | Support |
|----------|---------|
| Railway | Discord, email |
| Render | Dashboard support |
| Fly.io | Community forum |
| DigitalOcean | Tickets, community |

---

> **Next:** Review [Maintenance](11-maintenance.md) for ongoing operations.
