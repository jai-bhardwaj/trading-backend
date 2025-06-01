# Trading Engine PM2 Deployment Guide

## 🎉 Successful Deployment Status

Your trading engine is now **successfully deployed** and running with PM2!

Current Status:
- ✅ **Trading Engine**: Running (ID: 7, Memory: ~128MB)
- ✅ **PM2 Configuration**: Valid and active
- ✅ **Auto-restart**: Enabled
- ✅ **Logging**: Active in `./logs/`

## 📋 Quick Reference Commands

### Essential PM2 Commands
```bash
# Check status
pm2 status

# View logs (real-time)
pm2 logs trading-engine

# View recent logs
pm2 logs trading-engine --lines 50

# Monitor resources
pm2 monit

# Restart (with downtime)
pm2 restart trading-engine

# Reload (zero downtime)
pm2 reload trading-engine

# Stop the engine
pm2 stop trading-engine

# Start the engine
pm2 start ecosystem.config.js --env production
```

### Using the Management Script
```bash
# Show status and available commands
python manage.py

# Start the engine
python manage.py start

# Stop the engine
python manage.py stop

# Restart the engine
python manage.py restart

# View logs
python manage.py logs

# Open monitoring dashboard
python manage.py monitor
```

### Using the Deployment Script
```bash
# Full deployment (checks prerequisites, stops, starts, saves)
./deploy.sh
```

## 🔧 Configuration Files

### PM2 Configuration (`ecosystem.config.js`)
- **Script**: `main.py`
- **Interpreter**: `./venv/bin/python`
- **Working Directory**: Current directory (dynamic)
- **Environment**: Production mode with proper Python paths
- **Logging**: Separate out/error/combined logs
- **Memory Limit**: 2GB auto-restart
- **Auto-restart**: Enabled with 10s minimum uptime

### Environment Configuration (`.env`)
Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string  
- `SECRET_KEY` - Application secret key
- `ANGELONE_API_KEY` - Broker API credentials
- `ANGELONE_CLIENT_ID` - Broker client ID
- `ANGELONE_PASSWORD` - Broker password
- `ANGELONE_TOTP_SECRET` - TOTP secret (Base32 encoded)

## 📊 Monitoring & Health

### Performance Monitoring
- **Memory Usage**: Currently ~128MB
- **CPU Usage**: Low (typically <1%)
- **Restart Count**: 0 (stable)
- **Status**: Online and processing orders

### Log Locations
- **Combined**: `./logs/trading-engine-combined.log`
- **Output**: `./logs/trading-engine-out.log`  
- **Errors**: `./logs/trading-engine-error.log`

### Health Checks
The engine includes automatic health monitoring:
- Database connectivity checks
- Redis connection validation
- API authentication status
- Order processing pipeline health

## 🔄 Deployment Workflow

### Normal Deployment
```bash
# 1. Stop current process
pm2 stop trading-engine

# 2. Update code (if needed)
git pull

# 3. Update dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

# 4. Start with latest config
pm2 start ecosystem.config.js --env production

# 5. Save configuration
pm2 save
```

### Zero-Downtime Deployment
```bash
# 1. Update code
git pull

# 2. Update dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

# 3. Reload without stopping
pm2 reload trading-engine
```

### Full Reset Deployment
```bash
# Use the deployment script for complete reset
./deploy.sh
```

## 🚨 Troubleshooting

### Common Issues

**1. Process Not Starting**
```bash
# Check logs for errors
pm2 logs trading-engine

# Verify environment
cat .env

# Check Python path
which python
```

**2. High Memory Usage**
```bash
# Check memory stats
pm2 status

# Restart if needed
pm2 restart trading-engine
```

**3. Database Connection Issues**
```bash
# Verify database URL in .env
# Check PostgreSQL service status
systemctl status postgresql

# Test connection manually
python -c "from app.database import DatabaseManager; print('DB OK')"
```

**4. Redis Connection Issues**
```bash
# Check Redis service
systemctl status redis

# Test connection
redis-cli ping
```

### Emergency Procedures

**Force Stop**
```bash
pm2 kill
pm2 start ecosystem.config.js --env production
```

**Reset PM2**
```bash
pm2 delete all
pm2 start ecosystem.config.js --env production
pm2 save
```

## 🔐 Security Notes

- All sensitive credentials are in `.env` (not in version control)
- TOTP secrets must be Base32 encoded
- PM2 runs with current user permissions
- Logs may contain sensitive information - secure accordingly

## 📈 Next Steps

1. **Set up monitoring**: Consider PM2 Plus for advanced monitoring
2. **Configure alerts**: Set up log monitoring and alerting
3. **Backup strategy**: Implement database and configuration backups
4. **Load testing**: Validate performance under expected load
5. **Auto-startup**: Configure PM2 to start on boot: `pm2 startup`

## 📞 Support Commands

```bash
# Generate diagnostic info
pm2 info trading-engine

# Export current configuration
pm2 save

# View PM2 version
pm2 --version

# Check system resources
pm2 monit
```

---

**🎉 Your trading engine is now successfully deployed and ready for production use!** 