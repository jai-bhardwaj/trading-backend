# �� Production Deployment Guide

This guide covers deploying the trading system in a production environment with security, performance, and reliability best practices.

## 📋 Pre-Deployment Checklist

### ✅ Security Requirements
- [ ] All environment variables configured with production values
- [ ] JWT secret key generated and secured
- [ ] Database credentials secured
- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] Rate limiting configured

### ✅ Infrastructure Requirements
- [ ] PostgreSQL database server
- [ ] Redis server for sessions
- [ ] Docker and Docker Compose installed
- [ ] Sufficient server resources (2+ CPU, 4GB+ RAM)
- [ ] Backup strategy implemented
- [ ] Monitoring system configured

### ✅ Configuration Requirements
- [ ] Production .env file created
- [ ] Trading mode set to appropriate value
- [ ] Broker credentials validated
- [ ] Database connection tested
- [ ] Redis connection tested

## �� Step-by-Step Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Application Setup

```bash
# Clone repository
git clone <your-repo-url> trading-backend
cd trading-backend

# Create production environment file
cp .env.example .env
# Edit .env with production values
nano .env
```

### 3. Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker run -d \
  --name trading-postgres \
  -e POSTGRES_DB=trading_db \
  -e POSTGRES_USER=trading_user \
  -e POSTGRES_PASSWORD=your_secure_password \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine

# Start Redis
docker run -d \
  --name trading-redis \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass your_redis_password
```

### 4. SSL/TLS Configuration

```bash
# Generate SSL certificates (example with Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Or use your own certificates
mkdir -p ssl/
# Copy your certificates to ssl/cert.pem and ssl/key.pem
```

### 5. Production Deployment

```bash
# Deploy with secure configuration
docker-compose -f docker/docker-compose.secure.yml up -d

# Verify deployment
docker-compose -f docker/docker-compose.secure.yml ps
```

### 6. Health Check

```bash
# Test system health
curl https://your-domain.com/health

# Check admin dashboard
curl https://your-domain.com/admin/system/health
```

## 🔒 Security Configuration

### Firewall Setup
```bash
# Configure UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Environment Variables Security
```bash
# Secure .env file
chmod 600 .env
chown root:root .env

# Use Docker secrets for sensitive data (recommended)
echo "your_jwt_secret" | docker secret create jwt_secret -
echo "your_db_password" | docker secret create db_password -
```

### Rate Limiting Configuration
```env
# In .env
API_RATE_LIMIT_PER_MINUTE=60
LOGIN_RATE_LIMIT_PER_15_MIN=5
MAX_REQUEST_SIZE_MB=10
```

## 📊 Monitoring Setup

### Health Monitoring
```bash
# Set up health check endpoint monitoring
# Add to your monitoring system:
# GET https://your-domain.com/health
# Expected: {"status": "healthy"}
```

### Log Management
```bash
# Configure log rotation
sudo nano /etc/logrotate.d/trading-backend

# Add:
/var/log/trading-backend/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
}
```

### Resource Monitoring
```bash
# Monitor system resources
# CPU, Memory, Disk usage
# Database connections
# Redis memory usage
# Application response times
```

## 🔄 Backup Strategy

### Database Backup
```bash
# Automated PostgreSQL backup
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec trading-postgres pg_dump -U trading_user trading_db > $BACKUP_DIR/backup_$DATE.sql
gzip $BACKUP_DIR/backup_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### Application Backup
```bash
# Backup configuration and logs
tar -czf /backups/app_config_$(date +%Y%m%d).tar.gz \
  .env config/ logs/ docker/
```

## 🚀 Performance Optimization

### Resource Limits
```yaml
# In docker-compose.secure.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Database Optimization
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Redis Optimization
```bash
# Redis configuration
echo "maxmemory 256mb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
```

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**
```bash
# Check database status
docker logs trading-postgres
# Verify connection string in .env
```

2. **Redis Connection Failed**
```bash
# Check Redis status
docker logs trading-redis
# Test connection
redis-cli -h localhost -p 6379 ping
```

3. **Authentication Issues**
```bash
# Verify JWT secret is set
grep JWT_SECRET_KEY .env
# Check auth logs
docker logs trading-backend | grep auth
```

4. **Memory Issues**
```bash
# Check memory usage
docker stats
# Monitor application memory
curl localhost:8000/admin/resources/status
```

### Log Analysis
```bash
# Application logs
docker logs trading-backend

# System logs
journalctl -u docker

# Database logs
docker logs trading-postgres
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (nginx, HAProxy)
- Configure session affinity or shared sessions
- Scale database with read replicas
- Use Redis cluster for session storage

### Vertical Scaling
- Increase container resource limits
- Optimize database configuration
- Tune Redis memory settings
- Monitor and adjust based on usage

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
docker-compose -f docker/docker-compose.secure.yml build
docker-compose -f docker/docker-compose.secure.yml up -d
```

### Database Maintenance
```bash
# Regular maintenance
docker exec trading-postgres psql -U trading_user -d trading_db -c "VACUUM ANALYZE;"
```

### Security Updates
```bash
# Update base images
docker-compose -f docker/docker-compose.secure.yml pull
docker-compose -f docker/docker-compose.secure.yml up -d
```

## 📞 Support and Monitoring

### Health Endpoints
- `/health` - Basic health check
- `/admin/system/health` - Detailed system health
- `/admin/system/dashboard` - Monitoring dashboard
- `/admin/resources/status` - Resource usage

### Alerting
Set up alerts for:
- Application down/unhealthy
- High memory usage (>80%)
- High error rate (>5%)
- Database connection issues
- Authentication failures

### Contact Information
- System Administrator: admin@yourcompany.com
- On-call Engineer: oncall@yourcompany.com
- Emergency Contact: emergency@yourcompany.com

---

**🎯 Remember: Always test deployments in a staging environment first!**
