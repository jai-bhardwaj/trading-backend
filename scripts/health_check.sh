#!/bin/bash

# Comprehensive Health Check for Trading Backend
# This script checks all system components and reports status

echo "🏥 Trading Backend Health Check"
echo "================================"
echo "Timestamp: $(date)"
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
    else
        echo "❌ $2"
    fi
}

# 1. Check systemd service
echo "1. Checking systemd service..."
if systemctl is-active --quiet trading-backend; then
    print_status 0 "Trading backend service is running"
else
    print_status 1 "Trading backend service is not running"
fi

# 2. Check Python processes
echo "2. Checking Python processes..."
PYTHON_PROCESSES=$(ps aux | grep "python.*main.py" | grep -v grep | wc -l)
if [ $PYTHON_PROCESSES -gt 0 ]; then
    print_status 0 "Python main.py processes found: $PYTHON_PROCESSES"
else
    print_status 1 "No Python main.py processes found"
fi

# 3. Check log files
echo "3. Checking log files..."
if [ -f "logs/latest_run.log" ]; then
    LOG_SIZE=$(du -h logs/latest_run.log | cut -f1)
    print_status 0 "Latest log file exists (size: $LOG_SIZE)"
    
    # Check for recent activity (last 5 minutes)
    if find logs/latest_run.log -mmin -5 | grep -q .; then
        print_status 0 "Log file has recent activity"
    else
        print_status 1 "Log file has no recent activity (last 5 minutes)"
    fi
else
    print_status 1 "Latest log file not found"
fi

# 4. Check environment variables
echo "4. Checking environment variables..."
MISSING_VARS=0
REQUIRED_VARS=("ANGEL_ONE_API_KEY" "ANGEL_ONE_CLIENT_CODE" "ANGEL_ONE_PASSWORD" "ANGEL_ONE_TOTP_SECRET" "DATABASE_URL" "REDIS_URL")

# Load environment variables from .env file
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_status 1 "Missing environment variable: $var"
        MISSING_VARS=$((MISSING_VARS + 1))
    else
        print_status 0 "Environment variable $var is set"
    fi
done

# 5. Check disk space
echo "5. Checking disk space..."
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    print_status 0 "Disk usage: ${DISK_USAGE}%"
else
    print_status 1 "Disk usage high: ${DISK_USAGE}%"
fi

# 6. Check memory usage
echo "6. Checking memory usage..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -lt 80 ]; then
    print_status 0 "Memory usage: ${MEMORY_USAGE}%"
else
    print_status 1 "Memory usage high: ${MEMORY_USAGE}%"
fi

# 7. Check recent errors in logs
echo "7. Checking for recent errors..."
ERROR_COUNT=$(tail -100 logs/latest_run.log 2>/dev/null | grep -i "error\|exception\|failed" | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    print_status 0 "No recent errors found in logs"
else
    print_status 1 "Found $ERROR_COUNT recent errors in logs"
    echo "   Recent errors:"
    tail -100 logs/latest_run.log 2>/dev/null | grep -i "error\|exception\|failed" | tail -3 | sed 's/^/   /'
fi

# 8. Check backup directory
echo "8. Checking backup directory..."
if [ -d "backups" ]; then
    BACKUP_COUNT=$(ls backups/ 2>/dev/null | wc -l)
    print_status 0 "Backup directory exists with $BACKUP_COUNT files"
else
    print_status 1 "Backup directory not found"
fi

# 9. Check cron jobs
echo "9. Checking cron jobs..."
CRON_COUNT=$(crontab -l 2>/dev/null | grep -c "trading-backend" || echo "0")
if [ $CRON_COUNT -gt 0 ]; then
    print_status 0 "Found $CRON_COUNT trading-backend cron jobs"
else
    print_status 1 "No trading-backend cron jobs found"
fi

# 10. Check logrotate configuration
echo "10. Checking logrotate configuration..."
if [ -f "/etc/logrotate.d/trading-backend" ]; then
    print_status 0 "Logrotate configuration exists"
else
    print_status 1 "Logrotate configuration not found"
fi

echo ""
echo "🏥 Health Check Summary"
echo "======================="
echo "Service Status: $(systemctl is-active trading-backend 2>/dev/null || echo 'inactive')"
echo "Python Processes: $PYTHON_PROCESSES"
echo "Missing Env Vars: $MISSING_VARS"
echo "Recent Errors: $ERROR_COUNT"
echo "Disk Usage: ${DISK_USAGE}%"
echo "Memory Usage: ${MEMORY_USAGE}%"
echo ""

# Overall health assessment
if [ $MISSING_VARS -eq 0 ] && [ $ERROR_COUNT -eq 0 ] && systemctl is-active --quiet trading-backend; then
    echo "🎉 System Health: EXCELLENT"
elif [ $MISSING_VARS -eq 0 ] && systemctl is-active --quiet trading-backend; then
    echo "⚠️ System Health: GOOD (with minor issues)"
else
    echo "🚨 System Health: NEEDS ATTENTION"
fi 