# Docker Setup for Trading Backend

This document explains how to run the trading backend system using Docker containers.

## Prerequisites

- Docker and Docker Compose installed
- Angel One API credentials

## Quick Start

### 1. Clone and Setup Environment

```bash
# Copy environment template
cp env.template .env

# Edit .env with your Angel One credentials
nano .env
```

### 2. Start the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Access the Services

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432

## Services

The Docker setup includes:

1. **trading-api**: FastAPI backend service (port 8000)
2. **trading-engine**: Strategy engine and order manager
3. **redis**: Redis server for pub/sub messaging (port 6379)
4. **postgres**: PostgreSQL database (port 5432)

## Environment Variables

Key environment variables you need to configure in `.env`:

```env
# Angel One API Credentials (REQUIRED)
ANGEL_ONE_API_KEY=your_api_key_here
ANGEL_ONE_CLIENT_CODE=your_client_code_here
ANGEL_ONE_PASSWORD=your_password_here
ANGEL_ONE_TOTP_SECRET=your_totp_secret_here

# Trading Configuration
PAPER_TRADING=true
STRATEGY_EXECUTION_INTERVAL=5
```

## Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-api
docker-compose logs -f trading-engine
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild and Start
```bash
docker-compose up --build -d
```

### Access Container Shell
```bash
# API container
docker-compose exec trading-api bash

# Engine container
docker-compose exec trading-engine bash
```

## Data Persistence

- **PostgreSQL data**: Stored in `postgres_data` volume
- **Redis data**: Stored in `redis_data` volume
- **Application data**: Mounted from `./data` directory
- **Logs**: Mounted from `./logs` directory

## Health Checks

The system includes health checks for all services:

- API health: `curl http://localhost:8000/api/health`
- Redis: `docker-compose exec redis redis-cli ping`
- PostgreSQL: `docker-compose exec postgres pg_isready -U trading_user`

## Troubleshooting

### Common Issues

1. **Port conflicts**: Make sure ports 8000, 5432, and 6379 are available
2. **Permission issues**: Ensure Docker has proper permissions
3. **Environment variables**: Verify all required variables are set in `.env`

### Debugging

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs --tail=100 trading-api

# Check resource usage
docker stats

# Inspect container
docker-compose exec trading-api bash
```

### Reset Everything

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up --build -d
```

## Development

For development, you can mount your source code:

```bash
# Override the build with volume mounts
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Production Considerations

1. **Security**: Change default passwords and API keys
2. **Networking**: Use proper network segmentation
3. **Monitoring**: Add monitoring and logging solutions
4. **Backup**: Implement database backup strategies
5. **Scaling**: Consider horizontal scaling for high loads

## Support

For issues or questions, check the logs and ensure all environment variables are properly configured.
