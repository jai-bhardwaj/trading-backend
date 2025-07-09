#!/bin/bash

# Setup log rotation for trading backend
echo "Setting up log rotation for trading backend..."

# Create logrotate configuration
cat > /etc/logrotate.d/trading-backend << EOF
/root/trading-backend/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        systemctl reload trading-backend
    endscript
}
EOF

echo "Log rotation configuration created at /etc/logrotate.d/trading-backend"
echo "To test log rotation: sudo logrotate -f /etc/logrotate.d/trading-backend"
echo "To enable daily rotation: sudo systemctl enable logrotate" 