# Trading Engine

Industrial-grade algorithmic trading backend with PM2 process management.

## Quick Setup

```bash
# 1. Install PM2
sudo scripts/pm2_setup.sh

# 2. Configure environment
cp config/production.env .env
# Edit .env with your credentials

# 3. Start
pm2 start ecosystem.config.js --env production
pm2 save
```

## PM2 Commands

```bash
# Process Control
pm2 start ecosystem.config.js --env production
pm2 stop trading-engine
pm2 restart trading-engine
pm2 reload trading-engine    # Zero-downtime
pm2 delete trading-engine

# Monitoring
pm2 status
pm2 logs trading-engine
pm2 monit

# Persistence  
pm2 save                     # Save for auto-restart
pm2 startup                  # Enable boot startup
```

## Configuration

Required in `.env`:
```bash
DATABASE_URL="postgresql+asyncpg://user:pass@host:port/db"
REDIS_URL="redis://localhost:6379/0"
SECRET_KEY="your-32-character-secret-key"
ANGELONE_API_KEY="your-broker-api-key"
ANGELONE_CLIENT_ID="your-client-id"
ANGELONE_PASSWORD="your-password"
```

## Health Check

```bash
python scripts/health_check.py
```

## Features

- **PM2 Management**: Auto-restart, monitoring, clustering
- **Redis Queue**: High-performance order processing
- **PostgreSQL**: Persistent data storage with proper enums
- **Risk Management**: Position limits and loss controls
- **Multi-Strategy**: Equity, derivatives, crypto support
- **AngelOne Integration**: Live broker connectivity

## Architecture

```
├── main.py                  # Application entry
├── ecosystem.config.js      # PM2 configuration
├── app/
│   ├── core/               # Configuration
│   ├── models/             # Database models
│   ├── engine/             # Trading engine
│   ├── strategies/         # Trading algorithms
│   ├── brokers/            # Exchange integrations
│   └── queue/              # Order processing
└── scripts/                # Management tools
```

## Requirements

- Python 3.8+
- Node.js 18+ (for PM2)
- PostgreSQL 12+
- Redis 6+
- Ubuntu 20.04+

## License

Proprietary 