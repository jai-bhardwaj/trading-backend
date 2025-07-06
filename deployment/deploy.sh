#!/bin/bash

# Pinnacle Trading System - Production Deployment Script
# For Digital Ocean Droplet Deployment

set -e

# Configuration
PROJECT_NAME="pinnacle-trading"
PROJECT_DIR="/opt/pinnacle-trading"
SERVICE_USER="trading"
SERVICE_GROUP="trading"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Pinnacle Trading System - Production Deployment${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

# Update system packages
echo -e "${YELLOW}📦 Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    redis-server \
    postgresql \
    postgresql-contrib \
    nginx \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev

# Create service user
echo -e "${YELLOW}👤 Creating service user...${NC}"
sudo useradd -r -s /bin/false -d $PROJECT_DIR $SERVICE_USER || true
sudo mkdir -p $PROJECT_DIR
sudo chown $SERVICE_USER:$SERVICE_GROUP $PROJECT_DIR

# Clone or update repository
echo -e "${YELLOW}📥 Setting up project directory...${NC}"
if [ ! -d "$PROJECT_DIR/.git" ]; then
    sudo -u $SERVICE_USER git clone https://github.com/your-repo/pinnacle-trading.git $PROJECT_DIR
else
    sudo -u $SERVICE_USER git -C $PROJECT_DIR pull
fi

# Create virtual environment
echo -e "${YELLOW}🐍 Setting up Python virtual environment...${NC}"
sudo -u $SERVICE_USER python3.11 -m venv $PROJECT_DIR/venv
sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install --upgrade pip

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt

# Configure Redis
echo -e "${YELLOW}🔴 Configuring Redis...${NC}"
sudo cp $PROJECT_DIR/config/redis-configuration.conf /etc/redis/redis.conf
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Configure PostgreSQL
echo -e "${YELLOW}🐘 Configuring PostgreSQL...${NC}"
sudo -u postgres createdb pinnacle_trading || true
sudo -u postgres createuser trading || true
sudo -u postgres psql -c "ALTER USER trading WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pinnacle_trading TO trading;"

# Create log directories
echo -e "${YELLOW}📁 Creating log directories...${NC}"
sudo mkdir -p /var/log/pinnacle-trading
sudo chown $SERVICE_USER:$SERVICE_GROUP /var/log/pinnacle-trading

# Copy systemd service files
echo -e "${YELLOW}⚙️ Setting up systemd services...${NC}"
sudo cp $PROJECT_DIR/deployment/systemd/pinnacle-trading.service /etc/systemd/system/
sudo cp $PROJECT_DIR/deployment/systemd/pinnacle-redis.service /etc/systemd/system/

# Configure Nginx
echo -e "${YELLOW}🌐 Configuring Nginx...${NC}"
sudo cp $PROJECT_DIR/deployment/nginx/pinnacle-trading.conf /etc/nginx/sites-available/pinnacle-trading
sudo ln -sf /etc/nginx/sites-available/pinnacle-trading /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Set up environment file
echo -e "${YELLOW}⚙️ Setting up environment configuration...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    sudo -u $SERVICE_USER cp $PROJECT_DIR/config/environment-template.env $PROJECT_DIR/.env
    echo -e "${YELLOW}⚠️  Please edit $PROJECT_DIR/.env with your configuration${NC}"
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting proper permissions...${NC}"
sudo chown -R $SERVICE_USER:$SERVICE_GROUP $PROJECT_DIR
sudo chmod 755 $PROJECT_DIR
sudo chmod 600 $PROJECT_DIR/.env

# Reload systemd and enable services
echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable pinnacle-trading.service
sudo systemctl enable pinnacle-redis.service

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
sudo systemctl start pinnacle-redis.service
sudo systemctl start pinnacle-trading.service
sudo systemctl start nginx

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check service status
echo -e "${YELLOW}🔍 Checking service status...${NC}"
sudo systemctl status pinnacle-redis.service --no-pager
sudo systemctl status pinnacle-trading.service --no-pager
sudo systemctl status nginx --no-pager

# Test health endpoints
echo -e "${YELLOW}🏥 Testing health endpoints...${NC}"
curl -f http://localhost/health || echo -e "${RED}❌ Health check failed${NC}"
curl -f http://localhost:8000/health || echo -e "${RED}❌ Gateway health check failed${NC}"

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "=================================================="
echo -e "${GREEN}🎯 Next steps:${NC}"
echo "1. Edit $PROJECT_DIR/.env with your configuration"
echo "2. Set up SSL certificates for HTTPS"
echo "3. Configure firewall rules"
echo "4. Set up monitoring and logging"
echo "5. Test trading functionality"
echo ""
echo -e "${GREEN}📊 Access your trading system at:${NC}"
echo "   HTTP:  http://your-domain.com"
echo "   HTTPS: https://your-domain.com (after SSL setup)"
echo ""
echo -e "${GREEN}🔧 Useful commands:${NC}"
echo "   sudo systemctl status pinnacle-trading"
echo "   sudo journalctl -u pinnacle-trading -f"
echo "   sudo nginx -t"
echo "   sudo systemctl restart pinnacle-trading" 