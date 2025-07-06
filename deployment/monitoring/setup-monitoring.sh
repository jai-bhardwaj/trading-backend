#!/bin/bash

# Pinnacle Trading System - Monitoring Setup
# For Digital Ocean Droplet

set -e

echo "📊 Setting up monitoring for Pinnacle Trading System..."

# Install monitoring tools
sudo apt-get install -y \
    htop \
    iotop \
    nethogs \
    logrotate

# Create logrotate configuration
sudo tee /etc/logrotate.d/pinnacle-trading > /dev/null <<EOF
/var/log/pinnacle-trading/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 trading trading
    postrotate
        systemctl reload pinnacle-trading
    endscript
}
EOF

# Create monitoring script
sudo tee /opt/pinnacle-trading/scripts/monitor.sh > /dev/null <<'EOF'
#!/bin/bash

# Pinnacle Trading System Monitor

LOG_FILE="/var/log/pinnacle-trading/monitor.log"
ALERT_EMAIL="admin@your-domain.com"

# Check if services are running
check_service() {
    local service=$1
    if ! systemctl is-active --quiet $service; then
        echo "$(date): CRITICAL - $service is not running" >> $LOG_FILE
        # Send alert (uncomment if you have mail configured)
        # echo "Pinnacle Trading System Alert: $service is down" | mail -s "Service Alert" $ALERT_EMAIL
        return 1
    fi
    return 0
}

# Check memory usage
check_memory() {
    local memory_usage=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        echo "$(date): WARNING - High memory usage: ${memory_usage}%" >> $LOG_FILE
    fi
}

# Check disk usage
check_disk() {
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $disk_usage -gt 80 ]; then
        echo "$(date): WARNING - High disk usage: ${disk_usage}%" >> $LOG_FILE
    fi
}

# Check Redis memory
check_redis() {
    local redis_memory=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    echo "$(date): INFO - Redis memory usage: $redis_memory" >> $LOG_FILE
}

# Main monitoring loop
main() {
    echo "$(date): Starting monitoring check..." >> $LOG_FILE
    
    # Check services
    check_service "pinnacle-trading"
    check_service "redis-server"
    check_service "nginx"
    
    # Check system resources
    check_memory
    check_disk
    check_redis
    
    echo "$(date): Monitoring check completed" >> $LOG_FILE
}

main
EOF

# Make monitoring script executable
sudo chmod +x /opt/pinnacle-trading/scripts/monitor.sh

# Create cron job for monitoring
sudo tee /etc/cron.d/pinnacle-monitoring > /dev/null <<EOF
# Monitor Pinnacle Trading System every 5 minutes
*/5 * * * * root /opt/pinnacle-trading/scripts/monitor.sh
EOF

# Create log directory
sudo mkdir -p /var/log/pinnacle-trading
sudo chown trading:trading /var/log/pinnacle-trading

echo "✅ Monitoring setup completed!"
echo "📋 Monitoring features:"
echo "   • Service health checks every 5 minutes"
echo "   • Memory and disk usage monitoring"
echo "   • Redis memory monitoring"
echo "   • Log rotation (7 days retention)"
echo "   • Logs stored in /var/log/pinnacle-trading/" 