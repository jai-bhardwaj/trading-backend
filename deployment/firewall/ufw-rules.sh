#!/bin/bash

# Pinnacle Trading System - Firewall Configuration
# For Digital Ocean Droplet

set -e

echo "🔒 Configuring firewall for Pinnacle Trading System..."

# Reset UFW to default
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if you use non-standard SSH port)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow trading system ports (internal only)
sudo ufw allow from 127.0.0.1 to any port 8000  # Gateway
sudo ufw allow from 127.0.0.1 to any port 8001  # Auth
sudo ufw allow from 127.0.0.1 to any port 8002  # Market Data
sudo ufw allow from 127.0.0.1 to any port 8004  # Order Management
sudo ufw allow from 127.0.0.1 to any port 8006  # Risk Management
sudo ufw allow from 127.0.0.1 to any port 8007  # Strategy Engine
sudo ufw allow from 127.0.0.1 to any port 8008  # Portfolio

# Allow Redis (internal only)
sudo ufw allow from 127.0.0.1 to any port 6379

# Allow PostgreSQL (internal only)
sudo ufw allow from 127.0.0.1 to any port 5432

# Enable UFW
sudo ufw --force enable

echo "✅ Firewall configured successfully!"
echo "📋 Firewall rules:"
sudo ufw status numbered 