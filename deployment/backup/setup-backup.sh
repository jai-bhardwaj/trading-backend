#!/bin/bash

# Pinnacle Trading System - Backup Setup
# For Digital Ocean Droplet

set -e

echo "💾 Setting up backup system for Pinnacle Trading System..."

# Create backup directories
sudo mkdir -p /opt/backups/pinnacle-trading/{database,logs,config}
sudo chown trading:trading /opt/backups/pinnacle-trading -R

# Create backup script
sudo tee /opt/pinnacle-trading/scripts/backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Pinnacle Trading System Backup Script

BACKUP_DIR="/opt/backups/pinnacle-trading"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Database backup
echo "Backing up database..."
sudo -u postgres pg_dump pinnacle_trading > $BACKUP_DIR/database/pinnacle_trading_$DATE.sql
gzip $BACKUP_DIR/database/pinnacle_trading_$DATE.sql

# Redis backup
echo "Backing up Redis..."
sudo cp /var/lib/redis/dump.rdb $BACKUP_DIR/database/redis_$DATE.rdb

# Configuration backup
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config/config_$DATE.tar.gz \
    /opt/pinnacle-trading/.env \
    /opt/pinnacle-trading/config/ \
    /etc/nginx/sites-available/pinnacle-trading \
    /etc/systemd/system/pinnacle-trading.service

# Logs backup
echo "Backing up logs..."
tar -czf $BACKUP_DIR/logs/logs_$DATE.tar.gz /var/log/pinnacle-trading/

# Cleanup old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
EOF

# Create restore script
sudo tee /opt/pinnacle-trading/scripts/restore.sh > /dev/null <<'EOF'
#!/bin/bash

# Pinnacle Trading System Restore Script

BACKUP_DIR="/opt/backups/pinnacle-trading"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_date>"
    echo "Example: $0 20231201_143022"
    exit 1
fi

BACKUP_DATE=$1

echo "Restoring from backup: $BACKUP_DATE"

# Stop services
sudo systemctl stop pinnacle-trading
sudo systemctl stop redis-server

# Restore database
if [ -f "$BACKUP_DIR/database/pinnacle_trading_$BACKUP_DATE.sql.gz" ]; then
    echo "Restoring database..."
    gunzip -c $BACKUP_DIR/database/pinnacle_trading_$BACKUP_DATE.sql.gz | sudo -u postgres psql pinnacle_trading
fi

# Restore Redis
if [ -f "$BACKUP_DIR/database/redis_$BACKUP_DATE.rdb" ]; then
    echo "Restoring Redis..."
    sudo cp $BACKUP_DIR/database/redis_$BACKUP_DATE.rdb /var/lib/redis/dump.rdb
    sudo chown redis:redis /var/lib/redis/dump.rdb
fi

# Restore configuration
if [ -f "$BACKUP_DIR/config/config_$BACKUP_DATE.tar.gz" ]; then
    echo "Restoring configuration..."
    sudo tar -xzf $BACKUP_DIR/config/config_$BACKUP_DATE.tar.gz -C /
fi

# Start services
sudo systemctl start redis-server
sudo systemctl start pinnacle-trading

echo "Restore completed!"
EOF

# Make scripts executable
sudo chmod +x /opt/pinnacle-trading/scripts/backup.sh
sudo chmod +x /opt/pinnacle-trading/scripts/restore.sh

# Create cron job for daily backup
sudo tee /etc/cron.d/pinnacle-backup > /dev/null <<EOF
# Daily backup at 2 AM
0 2 * * * trading /opt/pinnacle-trading/scripts/backup.sh >> /var/log/pinnacle-trading/backup.log 2>&1
EOF

echo "✅ Backup system setup completed!"
echo "📋 Backup features:"
echo "   • Daily automated backups at 2 AM"
echo "   • Database, Redis, config, and logs backup"
echo "   • 7-day retention policy"
echo "   • Manual restore script available"
echo "   • Backup location: /opt/backups/pinnacle-trading/"
echo ""
echo "🔧 Manual backup commands:"
echo "   sudo -u trading /opt/pinnacle-trading/scripts/backup.sh"
echo "   sudo -u trading /opt/pinnacle-trading/scripts/restore.sh <backup_date>" 