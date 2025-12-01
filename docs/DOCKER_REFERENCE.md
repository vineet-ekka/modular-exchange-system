# Docker Reference

Docker container configuration and management for the exchange data system.

## Container Overview

| Container | Image | Ports | Purpose |
|-----------|-------|-------|---------|
| **exchange_postgres** | postgres:15 | 5432 | Primary PostgreSQL database |
| **exchange_redis** | redis:7-alpine | 6379 | Cache layer (optional) |
| **pgadmin** | dpage/pgadmin4:latest | 5050 | Web-based PostgreSQL admin (optional) |

## Port Allocation

Ensure these ports are available:

- **3000**: React dashboard
- **8000**: FastAPI backend
- **5432**: PostgreSQL (exchange_postgres)
- **6379**: Redis (exchange_redis, optional)
- **5050**: pgAdmin (optional)

## Common Docker Commands

```bash
# Start all containers
docker-compose up -d

# Check container status
docker ps

# Stop all containers
docker-compose down

# View logs (follow mode)
docker-compose logs -f postgres
docker-compose logs -f redis

# Restart specific container
docker-compose restart postgres
docker-compose restart redis

# Remove containers and volumes (CAUTION: deletes all data)
docker-compose down -v
```

## PostgreSQL Container (exchange_postgres)

**Configuration:**
- Image: `postgres:15`
- Volume: `postgres_data` (persistent storage)
- Database: `exchange_data`
- Default user/password: See `docker-compose.yml`

**Quick commands:**
```bash
# Check status
docker ps | grep exchange_postgres

# View logs
docker logs exchange_postgres

# Access psql shell
docker exec -it exchange_postgres psql -U postgres -d exchange_data

# Execute SQL query
docker exec -it exchange_postgres psql -U postgres -d exchange_data -c "SELECT exchange, COUNT(*) FROM exchange_data GROUP BY exchange;"

# Database backup
docker exec exchange_postgres pg_dump -U postgres exchange_data > backup.sql

# Database restore
cat backup.sql | docker exec -i exchange_postgres psql -U postgres -d exchange_data
```

## Redis Container (exchange_redis)

**Configuration:**
- Image: `redis:7-alpine`
- Max memory: 512MB
- Eviction policy: LRU (Least Recently Used)

**Quick commands:**
```bash
# Check status
docker ps | grep exchange_redis

# View logs
docker logs exchange_redis

# Access Redis CLI
docker exec -it exchange_redis redis-cli

# Redis INFO stats
docker exec -it exchange_redis redis-cli INFO stats

# Number of cached keys
docker exec -it exchange_redis redis-cli DBSIZE

# Memory usage
docker exec -it exchange_redis redis-cli INFO memory

# Monitor live commands
docker exec -it exchange_redis redis-cli MONITOR

# Check specific keys
docker exec -it exchange_redis redis-cli KEYS "*funding-rates*"

# Get key value
docker exec -it exchange_redis redis-cli GET "cache_key_name"

# Check TTL (time to live)
docker exec -it exchange_redis redis-cli TTL "cache_key_name"

# Flush all cache
docker exec -it exchange_redis redis-cli FLUSHALL
```

## pgAdmin Container (Optional)

**Configuration:**
- Image: `dpage/pgadmin4:latest`
- Web interface: http://localhost:5050
- Default credentials: See `docker-compose.yml`

**Quick commands:**
```bash
# Check status
docker ps | grep pgadmin

# Access web interface
# Navigate to: http://localhost:5050
# Login with credentials from docker-compose.yml
# Add server: Host=exchange_postgres, Port=5432
```

## Troubleshooting Docker Issues

### Container won't start
```bash
# Check container logs
docker logs exchange_postgres
docker logs exchange_redis

# Inspect container
docker inspect exchange_postgres

# Check port conflicts
netstat -ano | findstr :5432     # Windows
lsof -i :5432                    # Linux/Mac
```

### Database connection fails
```bash
# Verify PostgreSQL is running
docker ps | grep exchange_postgres

# Test connection from host
psql -h localhost -U postgres -d exchange_data

# Check PostgreSQL logs
docker logs exchange_postgres | grep ERROR
```

### Redis connection fails
```bash
# Verify Redis is running
docker ps | grep exchange_redis

# Test connection
docker exec -it exchange_redis redis-cli PING
# Should return: PONG

# Check Redis logs
docker logs exchange_redis
```

### Container health check
```bash
# Check container health status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Inspect specific container health
docker inspect --format='{{json .State.Health}}' exchange_postgres | python -m json.tool
```

## Data Persistence

### PostgreSQL Data
- Volume: `postgres_data`
- Location: Docker-managed volume (persistent across container restarts)
- Backup: Use `pg_dump` (see PostgreSQL commands above)

### Redis Data
- **Not persistent by default** - in-memory cache only
- Data is lost on container restart (by design)
- System falls back to SimpleCache if Redis unavailable

### Complete Data Reset (CAUTION)
```bash
# Stop all containers and remove volumes
docker-compose down -v

# Restart fresh
docker-compose up -d

# Re-run backfill
python scripts/unified_historical_backfill.py --days 30 --parallel
```

## Docker Compose Tips

### Update images
```bash
# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d --force-recreate
```

### View resource usage
```bash
# Show container resource usage
docker stats

# Specific container
docker stats exchange_postgres exchange_redis
```

### Clean up unused resources
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes (CAUTION)
docker volume prune
```

## Environment Variables

See `.env` file or `docker-compose.yml` for:
- PostgreSQL credentials
- Redis configuration
- Port mappings
- Volume mappings

**Note**: Never commit `.env` file to version control.
