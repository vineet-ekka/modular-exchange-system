# Maintenance Guide

> Ongoing operations and maintenance for deployed systems.

---

## Regular Maintenance Tasks

### Daily

| Task | Command/Action |
|------|----------------|
| Check health | `curl /api/health` |
| Review error logs | Platform dashboard |
| Verify data updating | Check `last_updated` timestamp |

### Weekly

| Task | Command/Action |
|------|----------------|
| Review metrics | Platform dashboard |
| Check storage usage | Database size query |
| Review costs | Billing dashboard |
| Test backups | Verify backup exists |

### Monthly

| Task | Command/Action |
|------|----------------|
| Update dependencies | `pip install --upgrade` |
| Security patches | Platform updates |
| Prune old data | SQL cleanup |
| Review performance | Optimize as needed |

---

## Updating the Application

### Code Updates

**Railway:**
```bash
git push origin main
# Automatic deploy triggered
```

**Render:**
```bash
git push origin main
# Automatic deploy triggered
```

**Fly.io:**
```bash
git push origin main
fly deploy
```

**VPS/Docker:**
```bash
git pull
docker-compose build
docker-compose up -d
```

### Zero-Downtime Deploys

Most PaaS platforms handle this automatically:

| Platform | Method |
|----------|--------|
| Railway | Rolling deploys |
| Render | Rolling deploys |
| Fly.io | Rolling deploys |
| VPS | Manual blue-green |

### Rollback

**Railway:**
```bash
# From dashboard: Deployments → Previous → Redeploy
```

**Fly.io:**
```bash
fly releases list
fly deploy --image registry.fly.io/app:version
```

**Docker:**
```bash
docker-compose down
docker-compose up -d --build
# Or rollback to specific image tag
```

---

## Dependency Updates

### Python Dependencies

```bash
# Check for updates
pip list --outdated

# Update all
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade fastapi

# Pin versions after testing
pip freeze > requirements.txt
```

### Node Dependencies

```bash
cd dashboard

# Check for updates
npm outdated

# Update all
npm update

# Update specific package
npm install react@latest

# Security fixes
npm audit fix
```

### Security Updates

```bash
# Python security scan
pip install safety
safety check

# Node security scan
npm audit
```

---

## Database Maintenance

### Check Database Size

```sql
-- Total database size
SELECT pg_size_pretty(pg_database_size('exchange_data'));

-- Table sizes
SELECT
    relname AS table,
    pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Prune Old Data

```sql
-- Delete historical data older than 30 days
DELETE FROM funding_rates_historical
WHERE funding_time < NOW() - INTERVAL '30 days';

-- Delete old arbitrage spreads
DELETE FROM arbitrage_spreads
WHERE timestamp < NOW() - INTERVAL '30 days';

-- Reclaim space
VACUUM FULL;
ANALYZE;
```

### Optimize Queries

```sql
-- Check slow queries (if pg_stat_statements enabled)
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Rebuild indexes
REINDEX TABLE exchange_data;
REINDEX TABLE funding_rates_historical;
```

### Backup Database

**Railway:**
```bash
# Automatic backups enabled
# Manual backup
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

**Fly.io:**
```bash
fly postgres connect -a your-db
\! pg_dump > backup.sql
```

**Manual:**
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
gzip backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Restore from backup
psql $DATABASE_URL < backup.sql

# Or with compression
gunzip -c backup.sql.gz | psql $DATABASE_URL
```

---

## Cache Maintenance

### Clear Cache

```bash
# Via API
curl -X POST https://your-api.com/api/cache/clear

# Direct Redis
redis-cli -h $REDIS_HOST FLUSHDB
```

### Monitor Cache

```bash
# Redis stats
redis-cli -h $REDIS_HOST INFO stats

# Memory usage
redis-cli -h $REDIS_HOST INFO memory

# Key count
redis-cli -h $REDIS_HOST DBSIZE
```

---

## Scaling Operations

### Vertical Scaling

**Railway:**
```bash
# Adjust in dashboard or railway.json
```

**Fly.io:**
```bash
fly scale memory 1024
fly scale count 2
```

**VPS:**
- Resize droplet/instance in dashboard
- May require restart

### Horizontal Scaling

**API Server (Safe to Scale):**
```bash
# Fly.io
fly scale count 2

# Railway
# Add multiple service instances
```

**Workers (Do NOT Scale):**
- Data collector: Single instance only
- Z-score calculator: Single instance only
- Spread collector: Single instance only

---

## Log Management

### View Logs

**Railway:**
```bash
railway logs
railway logs -f  # Follow
railway logs -s service-name
```

**Fly.io:**
```bash
fly logs
fly logs -a app-name
```

**Docker:**
```bash
docker logs container_name
docker logs -f container_name  # Follow
```

### Log Retention

| Platform | Default Retention |
|----------|-------------------|
| Railway | 7 days |
| Render | 7 days |
| Fly.io | 7 days |
| Vercel | 1 hour (free) |

### Export Logs

```bash
# Save logs to file
railway logs > logs_$(date +%Y%m%d).txt

# Fly.io
fly logs > logs_$(date +%Y%m%d).txt
```

---

## SSL Certificate Renewal

### Platform-Managed (Automatic)

| Platform | Certificate Provider |
|----------|---------------------|
| Railway | Let's Encrypt |
| Render | Let's Encrypt |
| Fly.io | Let's Encrypt |
| Vercel | Let's Encrypt |

### Custom Domain Certificates

Usually auto-renewed. If manual:

```bash
# Fly.io
fly certs add your-domain.com
fly certs show your-domain.com

# Check expiration
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
```

---

## Disaster Recovery

### Recovery Procedures

| Scenario | Steps |
|----------|-------|
| API down | 1. Check logs 2. Restart service 3. Check DB |
| Data stale | 1. Check collector 2. Restart worker 3. Check exchanges |
| Database corrupt | 1. Restore backup 2. Verify data 3. Restart services |
| Full outage | 1. Restore DB 2. Deploy services 3. Verify health |

### Emergency Contacts

Prepare list of:
- Platform support channels
- Team contacts
- Escalation procedures

### Runbook Template

```markdown
## Incident: [Name]

### Detection
- Alert source:
- Time detected:
- Symptoms:

### Diagnosis
- Root cause:
- Affected services:
- Impact:

### Resolution
1. Step 1
2. Step 2
3. Step 3

### Prevention
- Changes to prevent recurrence
```

---

## Cost Optimization

### Review Usage

```bash
# Check actual resource usage
# Railway: Dashboard → Usage
# Fly.io: fly scale show
# Render: Dashboard → Metrics
```

### Optimization Opportunities

| Area | Action | Savings |
|------|--------|---------|
| Unused services | Remove | Variable |
| Oversized instances | Downsize | 20-50% |
| Old backups | Prune | Storage costs |
| Unused databases | Delete | $7-15/mo |

### Set Spending Limits

| Platform | How |
|----------|-----|
| Railway | Dashboard → Settings → Spending Limit |
| Render | Automatic for free tier |
| Fly.io | `fly orgs show` for spending |

---

## Health Monitoring Automation

### Cron Jobs for Monitoring

```bash
# Check health every 5 minutes
*/5 * * * * curl -s https://your-api.com/api/health || send_alert

# Daily backup
0 3 * * * pg_dump $DATABASE_URL | gzip > /backups/daily_$(date +\%Y\%m\%d).sql.gz

# Weekly cleanup
0 4 * * 0 psql $DATABASE_URL -c "DELETE FROM funding_rates_historical WHERE funding_time < NOW() - INTERVAL '30 days'"
```

### Automated Alerts

```python
import requests
import smtplib

def check_health():
    try:
        r = requests.get("https://your-api.com/api/health", timeout=10)
        if r.status_code != 200:
            send_alert(f"Health check failed: {r.status_code}")
    except Exception as e:
        send_alert(f"Health check error: {e}")

def send_alert(message):
    # Send email, Slack, etc.
    pass
```

---

## Documentation Maintenance

### Keep Updated

- [ ] Update CHANGELOG after deployments
- [ ] Document new environment variables
- [ ] Update runbooks after incidents
- [ ] Review and update this guide quarterly

### Version Documentation

```bash
# Tag releases
git tag -a v1.2.3 -m "Description"
git push origin v1.2.3
```

---

## Checklist Summary

### Daily
- [ ] Verify health endpoints responding
- [ ] Check for error spikes in logs
- [ ] Confirm data is updating

### Weekly
- [ ] Review platform metrics
- [ ] Check database size
- [ ] Review costs
- [ ] Test backup restoration

### Monthly
- [ ] Update dependencies
- [ ] Security patches
- [ ] Performance review
- [ ] Documentation updates

### Quarterly
- [ ] Full disaster recovery test
- [ ] Review and optimize costs
- [ ] Security audit
- [ ] Architecture review

---

> **Back to:** [Overview](00-overview.md)
