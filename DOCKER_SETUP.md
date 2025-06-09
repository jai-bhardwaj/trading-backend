# 🐳 Docker Setup for Trading Engine

Simple Docker setup that **completely replaces PM2** with native Docker Compose commands.
**Optimized for DigitalOcean managed database services.**

## Quick Start

```bash
# 1. Copy environment template
cp docker.env.example .env

# 2. Configure your DigitalOcean managed services in .env
nano .env

# 3. Start core trading services
docker-compose up -d

# 4. Check status
docker-compose ps
```

## Core Commands

### 🚀 Deployment
```bash
# Start core trading services (engine + API)
docker-compose up -d

# Start with local Redis (if not using managed Redis)
docker-compose --profile local-redis up -d

# Start with monitoring stack
docker-compose --profile monitoring up -d

# Start everything (local Redis + monitoring)
docker-compose --profile local-redis --profile monitoring up -d

# Build and start (after code changes)
docker-compose up -d --build
```

### 📊 Monitoring
```bash
# View all service status
docker-compose ps

# Follow logs (all services)
docker-compose logs -f

# Follow logs (specific service)
docker-compose logs -f trading-engine

# Resource usage
docker stats
```

### 🔧 Management
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart trading-engine

# Stop all
docker-compose down

# Stop and remove volumes (CAREFUL!)
docker-compose down -v
```

### 🏥 Health & Debugging
```bash
# Execute commands in containers
docker-compose exec trading-engine python -c "import redis; print('Redis OK')"

# Check service health
curl http://localhost:8000/health

# View container logs
docker-compose logs -f trading-api

# Connect to container shell
docker-compose exec trading-engine bash
```

### ⚡ Scaling
```bash
# Scale trading engine to 3 instances
docker-compose up -d --scale trading-engine=3

# Scale API to 2 instances
docker-compose up -d --scale trading-api=2
```

## Service URLs

- **Trading API**: http://localhost:8000
- **API Health**: http://localhost:8000/health  
- **Grafana**: http://localhost:3000 (admin/trading_admin_2025!) *(with --profile monitoring)*
- **Prometheus**: http://localhost:9090 *(with --profile monitoring)*
- **System Metrics**: http://localhost:9100 *(with --profile monitoring)*

## DigitalOcean Configuration

### Required Environment Variables in `.env`:

```bash
# Your DigitalOcean managed PostgreSQL
DATABASE_URL=postgresql://doadmin:your_password@db-postgresql-nyc1-12345-do-user-123456-0.b.db.ondigitalocean.com:25060/defaultdb?sslmode=require

# Your DigitalOcean managed Redis (or local Redis)
REDIS_URL=redis://default:your_redis_password@redis-cluster-nyc1-12345-do-user-123456-0.b.db.ondigitalocean.com:25061
```

### Get your connection strings from:
1. **DigitalOcean Dashboard** → **Databases** → **Your Database** → **Connection Details**
2. Copy the **Connection String** and paste into `.env`

## Deployment Profiles

### Core Services Only (Minimal)
```bash
docker-compose up -d
```
**Includes**: trading-engine, trading-api, strategy-monitor

### With Local Redis
```bash
docker-compose --profile local-redis up -d
```
**Includes**: Core services + local Redis container

### With Monitoring
```bash
docker-compose --profile monitoring up -d
```
**Includes**: Core services + Prometheus, Grafana, Node Exporter

### Full Stack
```bash
docker-compose --profile local-redis --profile monitoring up -d
```
**Includes**: Everything (if you want local Redis + monitoring)

## Production Notes

- **No PostgreSQL container** - uses your DigitalOcean managed database
- **Redis is optional** - can use managed Redis or local container
- All services auto-restart on failure
- Logs are rotated (100MB max, 5 files)
- Health checks monitor all services
- Single database connection (optimized)
- Redis-first architecture for performance

## Migration from PM2

**PM2 is completely removed!** 🎉

| PM2 Command | Docker Compose Command |
|-------------|-------------------------|
| `pm2 start ecosystem.config.js` | `docker-compose up -d` |
| `pm2 status` | `docker-compose ps` |
| `pm2 logs` | `docker-compose logs -f` |
| `pm2 restart all` | `docker-compose restart` |
| `pm2 stop all` | `docker-compose down` |
| `pm2 monit` | `docker stats` |

## Troubleshooting

### Database Connection Issues
```bash
# Test DB connection
docker-compose exec trading-engine python -c "
import asyncpg
import asyncio
async def test_db():
    conn = await asyncpg.connect('YOUR_DATABASE_URL')
    print('Database connected!')
    await conn.close()
asyncio.run(test_db())
"
```

### Redis Connection Issues
```bash
# Test Redis connection
docker-compose exec trading-engine python -c "
import redis
r = redis.from_url('YOUR_REDIS_URL')
print(r.ping())
"
```

### View Service Logs
```bash
# All services
docker-compose logs

# Specific service with timestamps
docker-compose logs -f -t trading-engine
``` 