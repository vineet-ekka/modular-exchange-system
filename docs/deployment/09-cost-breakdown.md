# Cost Breakdown

> Detailed pricing analysis for all deployment options.

---

## Cost Summary Table

| Approach | Minimum | Typical | High Performance |
|----------|---------|---------|------------------|
| Hetzner VPS + Docker | $16 | $25 | $50 |
| Fly.io | $22 | $35 | $70 |
| Railway | $25 | $40 | $65 |
| DigitalOcean Droplet | $24 | $40 | $70 |
| Vultr/Linode | $24 | $38 | $65 |
| Render | $42 | $60 | $130 |
| Heroku | $40 | $65 | $160 |
| DO App Platform | $50 | $65 | $110 |
| AWS/GCP | $50 | $100 | $200+ |

---

## Detailed Breakdowns

### Option 1: Hetzner VPS + Docker (Lowest Cost)

**Total: $16-25/month**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| CX21 VPS | 2 vCPU, 4GB RAM, 40GB | $6.00 |
| CX31 VPS (recommended) | 2 vCPU, 8GB RAM, 80GB | $11.50 |
| Volume Storage | 50GB additional | $2.40 |
| Backups | 20% of server cost | $2.30 |
| Snapshots | On-demand | $0.01/GB |

**What's Included:**
- PostgreSQL (self-hosted in Docker)
- Redis (self-hosted in Docker)
- All workers running on same VPS

**What You Manage:**
- OS updates
- Docker maintenance
- Database backups
- SSL certificates (Let's Encrypt)
- Monitoring setup

**Add Frontend (Free):**
- Vercel: $0
- Cloudflare Pages: $0
- Netlify: $0

---

### Option 2: Railway (Best Balance)

**Total: $25-40/month**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Hobby Plan | Base subscription | $5.00 |
| API Server | ~1 vCPU, 1GB RAM | $8-12 |
| Data Collector | ~2 vCPU, 1GB RAM | $10-15 |
| Z-Score Worker | ~0.5 vCPU, 512MB | $3-5 |
| Spread Worker | ~0.5 vCPU, 512MB | $3-5 |
| PostgreSQL | 15GB storage | $5-8 |
| Redis | 512MB | $2-3 |
| Bandwidth | ~10GB | $0-1 |

**Billing Model:** Usage-based (per-minute)

**What's Included:**
- Managed PostgreSQL
- Managed Redis
- Automatic HTTPS
- GitHub integration
- Environment management

**What You Manage:**
- Application code
- Environment variables
- Scaling decisions

**Add Frontend (Free):**
- Vercel: $0

---

### Option 3: Render

**Total: $42-60/month**

| Component | Tier | Monthly Cost |
|-----------|------|--------------|
| API Server | Starter (512MB) | $7 |
| Data Collector | Starter (512MB) | $7 |
| Z-Score Worker | Starter (512MB) | $7 |
| Spread Worker | Starter (512MB) | $7 |
| PostgreSQL | Starter (1GB, 1GB storage) | $7 |
| Redis | Starter (25MB) | $7 |
| Static Site | Free tier | $0 |
| **Starter Total** | | **$42** |

**For Better Performance:**

| Component | Tier | Monthly Cost |
|-----------|------|--------------|
| API Server | Standard (2GB) | $25 |
| Data Collector | Standard (2GB) | $25 |
| Z-Score Worker | Starter (512MB) | $7 |
| Spread Worker | Starter (512MB) | $7 |
| PostgreSQL | Standard (2GB) | $25 |
| Redis | Standard (100MB) | $10 |
| **Standard Total** | | **$99** |

**What's Included:**
- Dedicated worker types
- Free static hosting
- Managed databases
- Auto-deploy from Git
- Blueprint deployments

---

### Option 4: Fly.io

**Total: $22-42/month**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| API Server | Shared 1GB | $5.70 |
| Data Collector | Shared 1GB | $5.70 |
| Z-Score Worker | Shared 512MB | $3.82 |
| Spread Worker | Shared 512MB | $3.82 |
| PostgreSQL | Development (free) | $0-15 |
| Upstash Redis | Usage-based | $0-5 |
| Volumes | 20GB | $3.00 |
| Bandwidth | Included | $0 |

**Free Tier Includes:**
- 3 shared VMs
- 3GB persistent storage
- 160GB outbound transfer

**What's Included:**
- Global edge deployment (35+ regions)
- Docker-native
- Anycast IPs
- Auto-scaling

---

### Option 5: DigitalOcean Droplet

**Total: $24-48/month**

**Option A: Single Droplet (All-in-One)**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Droplet | 2 vCPU, 4GB RAM | $24 |
| Block Storage | 50GB | $5 |
| Backups | Automatic | $4.80 |
| **Total** | | **$33.80** |

**Option B: Droplet + Managed Database**

| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| Droplet | 2 vCPU, 2GB RAM | $18 |
| Managed PostgreSQL | 1GB RAM, 10GB | $15 |
| Managed Redis | 1GB RAM | $15 |
| **Total** | | **$48** |

---

### Option 6: Heroku

**Total: $40-120/month**

**Basic Tier:**

| Component | Tier | Monthly Cost |
|-----------|------|--------------|
| API Dyno | Basic | $7 |
| Worker Dynos (3) | Basic | $21 |
| PostgreSQL | Mini | $5 |
| Redis | Mini | $3 |
| **Total** | | **$36** |

**Standard Tier (Recommended):**

| Component | Tier | Monthly Cost |
|-----------|------|--------------|
| API Dyno | Standard-1X | $25 |
| Worker Dynos (3) | Standard-1X | $75 |
| PostgreSQL | Basic | $9 |
| Redis | Premium-0 | $15 |
| **Total** | | **$124** |

---

## Cost Factors

### What Drives Costs

| Factor | Impact | Optimization |
|--------|--------|--------------|
| RAM usage | High | Optimize caching |
| CPU usage | High | Batch operations |
| Database storage | Medium | Prune old data |
| Bandwidth | Low | Cache aggressively |
| Number of workers | High | Combine if possible |

### Hidden Costs to Consider

| Item | Platforms Affected | Typical Cost |
|------|-------------------|--------------|
| Bandwidth overage | Most | $0.10/GB |
| Database backups | Some | 20-25% extra |
| SSL certificates | Self-hosted only | $0 (Let's Encrypt) |
| Domain name | All | $10-15/year |
| Monitoring tools | All | $0-20/month |

---

## Cost Optimization Tips

### 1. Use Free Frontend Hosting

| Provider | Free Tier |
|----------|-----------|
| Vercel | 100GB bandwidth |
| Netlify | 100GB bandwidth |
| Cloudflare Pages | Unlimited bandwidth |

**Savings: $5-15/month**

### 2. Skip Redis (Use Fallback)

The system has an in-memory cache fallback. Redis is optional.

**Savings: $2-7/month**

### 3. Combine Workers (VPS Only)

On a VPS, all workers share resources efficiently.

| Separate services | $7 each | $21/month |
| Combined on VPS | $0 extra | $0/month |

**Savings: Up to $21/month**

### 4. Use Development Database Tiers

For personal use, development/starter tiers are sufficient.

| Production DB | $15-50/month |
| Starter DB | $0-7/month |

**Savings: $10-40/month**

### 5. Right-size Resources

Monitor actual usage and scale down:

```bash
# Check actual memory usage
docker stats

# Check CPU usage
htop
```

---

## Cost Comparison by Use Case

### Personal Project

| Priority | Platform | Cost |
|----------|----------|------|
| Lowest cost | Hetzner VPS | $16/mo |
| Easy setup | Railway | $25/mo |
| Best free tier | Fly.io | $20/mo |

### Small Team

| Priority | Platform | Cost |
|----------|----------|------|
| Balanced | Railway | $35-40/mo |
| Predictable | Render | $42/mo |
| Enterprise features | Heroku | $65/mo |

### Production (Public)

| Priority | Platform | Cost |
|----------|----------|------|
| Cost-effective | Railway + Vercel | $40/mo |
| Reliability | Render | $60/mo |
| Enterprise | Heroku/AWS | $100+/mo |

---

## Annual Cost Comparison

| Platform | Monthly | Annual | Annual Savings |
|----------|---------|--------|----------------|
| Hetzner | $20 | $240 | Baseline |
| Railway | $35 | $420 | - |
| Fly.io | $35 | $420 | - |
| Render | $50 | $600 | - |
| Heroku | $65 | $780 | - |
| DO App Platform | $60 | $720 | - |

**Note:** Some platforms offer annual discounts or credits for startups.

---

## Free Tier Strategies

### Maximize Free Resources

| Platform | Free Tier | Best For |
|----------|-----------|----------|
| Fly.io | 3 VMs, 3GB storage | Testing, development |
| Render | Static sites only | Frontend |
| Supabase | 500MB database | Small datasets |
| Neon | 512MB, 10 projects | Database branching |
| Vercel | Unlimited static | Frontend |
| Cloudflare | Unlimited CDN | Frontend |

### Free Tier Limitations

| Platform | Limitation |
|----------|------------|
| Fly.io | VMs may be reclaimed after inactivity |
| Render | Free services sleep after 15 min |
| Supabase | Limited to 500MB |
| Railway | $5 credit/month (may not cover full usage) |

---

## Budget Recommendations

### $20/month Budget

- Hetzner CX21 + Docker: $6
- Cloudflare (CDN + proxy): $0
- Vercel (frontend): $0
- Domain: ~$1 (annual split)
- **Remaining buffer: $13**

### $50/month Budget

- Railway (all services): $35
- Vercel (frontend): $0
- Domain: ~$1
- Monitoring (Better Uptime): $0
- **Remaining buffer: $14**

### $100/month Budget

- Railway Pro: $20/seat
- Railway services: $50
- Render PostgreSQL Standard: $25
- Vercel Pro: $0-20
- **Remaining buffer: $5-15**

---

> **Next:** Review [Troubleshooting](10-troubleshooting.md) for common issues.
