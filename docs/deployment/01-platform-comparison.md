# Platform Comparison: Complete Analysis

> Detailed evaluation of all deployment platforms for the Funding Rate Dashboard.

---

## Comparison Matrix

### Quick Reference

| Platform | Type | Min Cost | Complexity | Workers | Managed DB |
|----------|------|----------|------------|---------|------------|
| Railway | PaaS | $25/mo | Low | Yes | Yes |
| Render | PaaS | $42/mo | Low | Yes | Yes |
| Fly.io | PaaS | $35/mo | Medium | Yes | Yes |
| Heroku | PaaS | $50/mo | Low | Yes | Yes |
| DO App Platform | PaaS | $50/mo | Medium | Limited | Yes |
| AWS App Runner | PaaS | $40/mo | Medium | No | No |
| Hetzner VPS | IaaS | $10/mo | Medium | Manual | No |
| DigitalOcean Droplet | IaaS | $20/mo | Medium | Manual | Optional |
| Linode | IaaS | $20/mo | Medium | Manual | No |
| Vultr | IaaS | $20/mo | Medium | Manual | No |
| AWS EC2 | IaaS | $30/mo | High | Manual | Optional |
| Google Cloud Run | Serverless | N/A | Medium | No | No |
| Self-hosted | On-prem | $0/mo | High | Manual | No |

---

## Platform-as-a-Service (PaaS)

### Railway.app

> Modern PaaS with usage-based pricing and excellent developer experience.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2020 |
| Headquarters | San Francisco |
| Pricing Model | Usage-based |
| Free Tier | $5 credit/month |
| Regions | US, EU |

#### Pricing Details

| Resource | Cost |
|----------|------|
| vCPU | $0.000463/minute |
| Memory | $0.000231/GB/minute |
| Disk | $0.25/GB/month |
| Bandwidth | $0.10/GB (after 100GB) |
| Hobby Plan | $5/month (includes credits) |
| Pro Plan | $20/month/seat |

#### Estimated Monthly Cost for This Project

| Component | Resources | Cost |
|-----------|-----------|------|
| API Server | 1 vCPU, 1GB RAM | $8-12 |
| Data Collector | 2 vCPU, 1GB RAM | $10-15 |
| Z-score Worker | 0.5 vCPU, 512MB | $3-5 |
| Spread Worker | 0.5 vCPU, 512MB | $3-5 |
| PostgreSQL | 15GB storage | $5-8 |
| Redis | 512MB | $2-3 |
| **Total** | | **$31-48** |

#### Strengths

| Strength | Description |
|----------|-------------|
| Usage-based billing | Pay only for actual consumption |
| Instant deploys | Push to GitHub, deployed in seconds |
| Monorepo support | Multiple services from one repo |
| Environment sync | Easy staging/production management |
| Built-in databases | PostgreSQL, MySQL, Redis, MongoDB |
| Good documentation | Clear guides and examples |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Limited regions | Only US and EU currently |
| No dedicated workers | Workers run as regular services |
| Newer platform | Less established track record |
| Limited observability | Basic metrics, no APM |

#### Best For

- Small to medium projects
- Developers wanting simplicity
- Variable workloads (usage-based billing)
- Rapid prototyping

---

### Render.com

> Traditional PaaS with dedicated service types and predictable pricing.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2018 |
| Headquarters | San Francisco |
| Pricing Model | Fixed per-service |
| Free Tier | Static sites, limited services |
| Regions | US (Oregon, Ohio), EU (Frankfurt), Singapore |

#### Pricing Details

| Service Type | Starter | Standard | Pro |
|--------------|---------|----------|-----|
| Web Service | $7/mo | $25/mo | $85/mo |
| Background Worker | $7/mo | $25/mo | $85/mo |
| Cron Job | $1/mo | - | - |
| PostgreSQL | $7/mo | $25/mo | $85/mo |
| Redis | $7/mo | $25/mo | $85/mo |
| Static Site | Free | Free | Free |

#### Estimated Monthly Cost for This Project

| Component | Tier | Cost |
|-----------|------|------|
| API Server | Starter | $7 |
| Data Collector | Starter | $7 |
| Z-score Worker | Starter | $7 |
| Spread Worker | Starter | $7 |
| PostgreSQL | Starter | $7 |
| Redis | Starter | $7 |
| Static Site | Free | $0 |
| **Total** | | **$42** |

With Standard tier for better performance: **$125/mo**

#### Strengths

| Strength | Description |
|----------|-------------|
| Dedicated worker type | Purpose-built for background jobs |
| Free static hosting | 100GB/month bandwidth |
| Blueprint deploys | Infrastructure as code (render.yaml) |
| Predictable pricing | Fixed monthly costs |
| More regions | 4 regions available |
| Cron jobs | Built-in scheduled tasks |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Fixed pricing | Pay full price even when idle |
| Starter limitations | 512MB RAM may be insufficient |
| Expensive at scale | Multiple workers add up quickly |
| Cold starts | Free tier services sleep |

#### Best For

- Teams needing predictable billing
- Projects with scheduled jobs
- Simple applications with few workers
- Those wanting free static hosting

---

### Fly.io

> Edge-first platform deploying Docker containers globally.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2017 |
| Headquarters | Chicago |
| Pricing Model | Resource-based |
| Free Tier | 3 shared VMs, 3GB storage |
| Regions | 35+ worldwide |

#### Pricing Details

| Resource | Cost |
|----------|------|
| Shared CPU-1x (256MB) | $1.94/mo |
| Shared CPU-1x (1GB) | $5.70/mo |
| Dedicated CPU-1x (2GB) | $29/mo |
| Persistent Disk | $0.15/GB/mo |
| Outbound Transfer | $0.02/GB (after 100GB) |

#### Database Pricing (Fly Postgres)

| Tier | Specs | Cost |
|------|-------|------|
| Development | Single node, 1GB | Free |
| Production | 2 nodes, HA | $51/mo |

#### Estimated Monthly Cost for This Project

| Component | Spec | Cost |
|-----------|------|------|
| API Server | Shared 1GB | $5.70 |
| Data Collector | Shared 1GB | $5.70 |
| Z-score Worker | Shared 512MB | $3.82 |
| Spread Worker | Shared 512MB | $3.82 |
| PostgreSQL | Development | $0-15 |
| Upstash Redis | Usage-based | $0-5 |
| Storage | 20GB | $3 |
| **Total** | | **$22-42** |

#### Strengths

| Strength | Description |
|----------|-------------|
| Global edge network | 35+ regions, deploy close to users |
| Docker-native | Full container control |
| Machines API | Fine-grained instance control |
| Generous free tier | Good for testing |
| Anycast IPs | Global load balancing |
| Litefs | Distributed SQLite option |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| CLI-focused | Less GUI-friendly |
| Docker knowledge required | Higher learning curve |
| Complex networking | Requires understanding Fly networking |
| Database management | More hands-on than Railway |
| Billing surprises | Easy to leave machines running |

#### Best For

- Global applications needing low latency
- Docker-experienced developers
- Edge computing use cases
- Cost-conscious with free tier

---

### Heroku

> The original PaaS, now owned by Salesforce.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2007 |
| Acquired by | Salesforce (2010) |
| Pricing Model | Fixed per-dyno |
| Free Tier | Removed in 2022 |
| Regions | US, EU |

#### Pricing Details

| Dyno Type | Specs | Cost |
|-----------|-------|------|
| Eco | Shared, sleeps | $5/mo (shared) |
| Basic | Dedicated | $7/mo |
| Standard-1X | 512MB | $25/mo |
| Standard-2X | 1GB | $50/mo |
| Performance-M | 2.5GB | $250/mo |

#### Add-ons

| Add-on | Tier | Cost |
|--------|------|------|
| Heroku Postgres | Mini | $5/mo |
| Heroku Postgres | Basic | $9/mo |
| Heroku Postgres | Standard | $50/mo |
| Heroku Redis | Mini | $3/mo |
| Heroku Redis | Premium | $15/mo |

#### Estimated Monthly Cost for This Project

| Component | Tier | Cost |
|-----------|------|------|
| API Server | Basic | $7 |
| Data Collector | Basic | $7 |
| Z-score Worker | Basic | $7 |
| Spread Worker | Basic | $7 |
| PostgreSQL | Basic | $9 |
| Redis | Mini | $3 |
| **Total** | | **$40** |

With Standard dynos: **$120+/mo**

#### Strengths

| Strength | Description |
|----------|-------------|
| Mature platform | 15+ years of operation |
| Extensive add-ons | 200+ marketplace integrations |
| Enterprise features | SSO, compliance, support |
| Review apps | PR-based preview environments |
| Good documentation | Extensive guides |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| No free tier | Removed in 2022 |
| Expensive at scale | Costs add up quickly |
| Limited regions | Only US and EU |
| Aging platform | Less modern than competitors |
| Salesforce ownership | Concerns about future direction |

#### Best For

- Enterprise teams
- Those needing extensive add-ons
- Long-term stable deployments
- Teams with Heroku experience

---

### DigitalOcean App Platform

> Managed PaaS from the popular VPS provider.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2012 (DO), 2020 (App Platform) |
| Headquarters | New York |
| Pricing Model | Fixed per-component |
| Free Tier | 3 static sites |
| Regions | Multiple |

#### Pricing Details

| Component Type | Basic | Pro |
|----------------|-------|-----|
| Web Service | $5/mo | $12/mo |
| Worker | $5/mo | $12/mo |
| Static Site | Free | Free |

| Database | Specs | Cost |
|----------|-------|------|
| PostgreSQL Basic | 1GB RAM, 10GB | $15/mo |
| PostgreSQL Standard | 2GB RAM, 25GB | $30/mo |
| Redis Basic | 1GB RAM | $15/mo |

#### Estimated Monthly Cost for This Project

| Component | Tier | Cost |
|-----------|------|------|
| API Server | Basic | $5 |
| Data Collector | Pro | $12 |
| Z-score Worker | Basic | $5 |
| Spread Worker | Basic | $5 |
| PostgreSQL | Basic | $15 |
| Redis | Basic | $15 |
| **Total** | | **$57** |

#### Strengths

| Strength | Description |
|----------|-------------|
| DO ecosystem | Easy to add Droplets, Spaces, etc. |
| Predictable pricing | Clear, fixed costs |
| Good documentation | Extensive tutorials |
| Managed databases | PostgreSQL, MySQL, Redis, MongoDB |
| Team features | Built-in collaboration |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Limited worker support | Not as flexible as Railway |
| Higher database costs | Starts at $15/mo |
| Basic features | Less sophisticated than Heroku |
| Limited scaling | Manual scaling mostly |

#### Best For

- Teams already using DigitalOcean
- Simple applications
- Those wanting managed databases
- Mid-size projects

---

## Infrastructure-as-a-Service (IaaS)

### Hetzner Cloud

> German provider known for extremely competitive pricing.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 1997 |
| Headquarters | Germany |
| Pricing Model | Hourly/Monthly |
| Reputation | Excellent price-performance |
| Regions | Germany, Finland, US |

#### Server Pricing

| Server | vCPU | RAM | Storage | Cost |
|--------|------|-----|---------|------|
| CX11 | 1 | 2GB | 20GB | $4.15/mo |
| CX21 | 2 | 4GB | 40GB | $6.00/mo |
| CX31 | 2 | 8GB | 80GB | $11.50/mo |
| CX41 | 4 | 16GB | 160GB | $22.00/mo |
| CX51 | 8 | 32GB | 240GB | $44.00/mo |

#### Estimated Monthly Cost for This Project

| Component | Spec | Cost |
|-----------|------|------|
| VPS (CX31) | 2 vCPU, 8GB | $11.50 |
| Volume Storage | 50GB | $2.40 |
| Backup | 20% of server | $2.30 |
| **Total** | | **$16.20** |

*Note: Database and Redis run on same VPS via Docker*

#### Strengths

| Strength | Description |
|----------|-------------|
| Unbeatable pricing | 50-70% cheaper than AWS/DO |
| European data centers | GDPR-friendly |
| Excellent performance | Modern AMD EPYC processors |
| Simple interface | Easy to use |
| Dedicated servers | Available for high performance |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Self-managed | You handle everything |
| Limited US presence | Only Ashburn, VA |
| No managed databases | Must run yourself |
| Basic support | Limited unless paid |
| Learning curve | Need sysadmin skills |

#### Best For

- Budget-conscious deployments
- European hosting requirements
- Developers comfortable with Linux
- High-performance needs at low cost

---

### DigitalOcean Droplets

> Popular VPS provider with excellent developer experience.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2012 |
| Headquarters | New York |
| Pricing Model | Hourly/Monthly |
| Free Credits | $200 for 60 days (new users) |
| Regions | 14 worldwide |

#### Droplet Pricing

| Droplet | vCPU | RAM | Storage | Cost |
|---------|------|-----|---------|------|
| Basic (Regular) | 1 | 1GB | 25GB | $6/mo |
| Basic (Regular) | 1 | 2GB | 50GB | $12/mo |
| Basic (Regular) | 2 | 4GB | 80GB | $24/mo |
| Basic (Premium) | 2 | 4GB | 80GB | $28/mo |
| General Purpose | 2 | 8GB | 25GB | $63/mo |

#### Estimated Monthly Cost for This Project

**Option A: Single Droplet with Docker**

| Component | Spec | Cost |
|-----------|------|------|
| Droplet | 2 vCPU, 4GB | $24 |
| Block Storage | 50GB | $5 |
| Backups | 20% of Droplet | $4.80 |
| **Total** | | **$33.80** |

**Option B: Droplet + Managed Database**

| Component | Spec | Cost |
|-----------|------|------|
| Droplet | 2 vCPU, 2GB | $18 |
| Managed PostgreSQL | 1GB RAM | $15 |
| Managed Redis | 1GB RAM | $15 |
| **Total** | | **$48** |

#### Strengths

| Strength | Description |
|----------|-------------|
| Developer-friendly | Great docs, tutorials |
| Good UI | Clean, intuitive interface |
| 1-click apps | Pre-configured images |
| Global regions | 14 data centers |
| API access | Full API for automation |
| Floating IPs | Easy IP management |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Higher than Hetzner | 2-3x more expensive |
| Self-managed | You handle OS, security |
| Basic servers | Not for enterprise workloads |

#### Best For

- Developers new to VPS
- Those wanting good documentation
- Projects needing global presence
- Learning server management

---

### Linode (Akamai)

> Veteran VPS provider, now part of Akamai.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2003 |
| Acquired by | Akamai (2022) |
| Pricing Model | Hourly/Monthly |
| Free Credits | $100 for 60 days |
| Regions | 25+ globally |

#### Pricing

| Plan | vCPU | RAM | Storage | Cost |
|------|------|-----|---------|------|
| Nanode 1GB | 1 | 1GB | 25GB | $5/mo |
| Linode 2GB | 1 | 2GB | 50GB | $12/mo |
| Linode 4GB | 2 | 4GB | 80GB | $24/mo |
| Linode 8GB | 4 | 8GB | 160GB | $48/mo |

#### Estimated Monthly Cost

| Component | Spec | Cost |
|-----------|------|------|
| Linode | 2 vCPU, 4GB | $24 |
| Block Storage | 50GB | $5 |
| Backups | 25% of Linode | $6 |
| **Total** | | **$35** |

#### Strengths

| Strength | Description |
|----------|-------------|
| Long track record | 20+ years |
| Akamai network | Global edge infrastructure |
| Good support | 24/7 phone and ticket |
| Many regions | 25+ data centers |
| Kubernetes | Managed LKE available |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Similar to DO | Not much differentiation |
| Interface less polished | Older UI |
| Transition period | Akamai integration ongoing |

#### Best For

- Those wanting Akamai edge integration
- Need for many global regions
- Preference for established providers

---

### Vultr

> VPS provider known for competitive pricing and global reach.

#### Overview

| Attribute | Value |
|-----------|-------|
| Founded | 2014 |
| Headquarters | New Jersey |
| Pricing Model | Hourly/Monthly |
| Free Credits | $250 for 30 days |
| Regions | 32 worldwide |

#### Pricing

| Plan | vCPU | RAM | Storage | Cost |
|------|------|-----|---------|------|
| Cloud Compute | 1 | 1GB | 25GB | $5/mo |
| Cloud Compute | 1 | 2GB | 55GB | $10/mo |
| Cloud Compute | 2 | 4GB | 80GB | $20/mo |
| High Frequency | 2 | 4GB | 128GB | $24/mo |

#### Estimated Monthly Cost

| Component | Spec | Cost |
|-----------|------|------|
| High Frequency | 2 vCPU, 4GB | $24 |
| Block Storage | 50GB | $5 |
| Backups | 20% | $4.80 |
| **Total** | | **$33.80** |

#### Strengths

| Strength | Description |
|----------|-------------|
| Most regions | 32 locations worldwide |
| High frequency | NVMe-based compute |
| Bare metal | Dedicated servers available |
| Kubernetes | Managed VKE available |
| Competitive pricing | Similar to DO |

#### Weaknesses

| Weakness | Description |
|----------|-------------|
| Less documentation | Not as extensive as DO |
| Smaller community | Fewer tutorials |
| Support varies | Can be slow |

#### Best For

- Need for specific geographic regions
- High-performance NVMe workloads
- Bare metal requirements

---

## Serverless & Containers

### AWS App Runner

> AWS's answer to simple container deployment.

#### Overview

| Attribute | Value |
|-----------|-------|
| Provider | Amazon Web Services |
| Type | Managed containers |
| Pricing | vCPU/Memory per second |

#### Pricing

| Resource | Cost |
|----------|------|
| vCPU | $0.064/vCPU-hour |
| Memory | $0.007/GB-hour |
| Provisioned | $0.007/GB-hour |

#### Limitations for This Project

| Limitation | Impact |
|------------|--------|
| No background workers | Cannot run always-on workers |
| Request-driven only | Workers need separate solution (ECS) |
| AWS complexity | Need AWS knowledge |

**Verdict:** Not suitable as standalone solution. Would need ECS for workers.

---

### Google Cloud Run

> Serverless containers on Google Cloud.

#### Overview

| Attribute | Value |
|-----------|-------|
| Provider | Google Cloud Platform |
| Type | Serverless containers |
| Pricing | Per-request + CPU/memory |

#### Pricing

| Resource | Cost |
|----------|------|
| vCPU | $0.00002400/vCPU-second |
| Memory | $0.00000250/GB-second |
| Requests | $0.40/million |

#### Limitations for This Project

| Limitation | Impact |
|------------|--------|
| Request-driven | Not for always-on workers |
| Cold starts | Latency on first request |
| No persistent connections | WebSocket limitations |

**Verdict:** Could work for API with Cloud Scheduler for workers, but adds complexity.

---

## Frontend Hosting

### Vercel

| Attribute | Value |
|-----------|-------|
| Free Tier | 100GB bandwidth, unlimited sites |
| Hobby Plan | Free |
| Pro Plan | $20/mo per member |
| Best For | React, Next.js, static sites |

### Netlify

| Attribute | Value |
|-----------|-------|
| Free Tier | 100GB bandwidth, 300 build minutes |
| Pro Plan | $19/mo per member |
| Best For | JAMstack, static sites |

### Cloudflare Pages

| Attribute | Value |
|-----------|-------|
| Free Tier | Unlimited bandwidth |
| Pro Plan | $20/mo |
| Best For | Maximum performance, global CDN |

### GitHub Pages

| Attribute | Value |
|-----------|-------|
| Free Tier | 100GB bandwidth, public repos |
| Best For | Documentation, simple sites |

---

## Database Hosting (Standalone)

### Supabase

| Tier | Storage | Cost |
|------|---------|------|
| Free | 500MB | $0 |
| Pro | 8GB | $25/mo |
| Team | 100GB | $599/mo |

**Features:** PostgreSQL, Auth, Realtime, Storage

### Neon

| Tier | Storage | Cost |
|------|---------|------|
| Free | 512MB | $0 |
| Launch | 10GB | $19/mo |
| Scale | 50GB | $69/mo |

**Features:** Serverless Postgres, branching, autoscaling

### PlanetScale

| Tier | Storage | Cost |
|------|---------|------|
| Free | 5GB | $0 |
| Scaler | 10GB | $29/mo |

**Note:** MySQL-based, not PostgreSQL

---

## Cost Summary

### Monthly Cost Comparison (All Services Included)

| Platform | Minimum | Typical | High Perf |
|----------|---------|---------|-----------|
| Hetzner + Docker | $16 | $25 | $50 |
| Railway | $25 | $35 | $60 |
| Fly.io | $22 | $35 | $70 |
| DigitalOcean Droplet | $24 | $35 | $65 |
| Vultr | $24 | $34 | $60 |
| Linode | $24 | $35 | $65 |
| Render | $42 | $55 | $125 |
| Heroku | $40 | $60 | $150 |
| DO App Platform | $50 | $60 | $100 |

---

## Decision Guide

### Choose by Priority

| Priority | Recommended Platform |
|----------|---------------------|
| Lowest cost | Hetzner + Docker |
| Simplest setup | Railway or Render |
| Best free tier | Fly.io |
| Most regions | Vultr (32 locations) |
| Best docs | DigitalOcean |
| Enterprise | AWS or Heroku |
| GDPR/Europe | Hetzner |

### Choose by Skill Level

| Level | Recommended |
|-------|-------------|
| Beginner | Railway, Render |
| Intermediate | Fly.io, DigitalOcean |
| Advanced | Hetzner, AWS |

---

> **Next:** Review [Architecture](02-architecture.md) for production system design.
