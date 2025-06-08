#!/bin/bash

# Trading Backend - Production Deployment Script
# This script sets up PM2 for production deployment

set -e  # Exit on any error

echo "🚀 Trading Backend - Production Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/root/trading-backend"
USER="root"
PYTHON_PATH="$APP_DIR/venv/bin/python"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Check if running as root
check_user() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
    print_status "Running as root user"
}

# Install Node.js and PM2
install_pm2() {
    print_info "Installing Node.js and PM2..."
    
    # Install Node.js (if not already installed)
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        apt-get install -y nodejs
        print_status "Node.js installed"
    else
        print_status "Node.js already installed"
    fi
    
    # Install PM2 globally
    if ! command -v pm2 &> /dev/null; then
        npm install -g pm2
        print_status "PM2 installed globally"
    else
        print_status "PM2 already installed"
    fi
    
    # Install PM2 log rotate
    pm2 install pm2-logrotate
    print_status "PM2 log rotate installed"
}

# Setup directories and permissions
setup_directories() {
    print_info "Setting up directories and permissions..."
    
    # Create logs directory
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/tmp"
    mkdir -p "$APP_DIR/backups"
    
    # Set permissions
    chown -R $USER:$USER "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    chmod +x "$APP_DIR/main.py"
    
    print_status "Directories and permissions configured"
}

# Configure PM2 log rotation
configure_pm2_logrotate() {
    print_info "Configuring PM2 log rotation..."
    
    pm2 set pm2-logrotate:max_size 100M
    pm2 set pm2-logrotate:retain 30
    pm2 set pm2-logrotate:compress true
    pm2 set pm2-logrotate:dateFormat 'YYYY-MM-DD_HH-mm-ss'
    pm2 set pm2-logrotate:workerInterval 30
    pm2 set pm2-logrotate:rotateInterval '0 0 * * *'  # Daily rotation
    
    print_status "PM2 log rotation configured"
}

# Setup environment variables
setup_environment() {
    print_info "Setting up environment variables..."
    
    # Create .env file for production if it doesn't exist
    if [[ ! -f "$APP_DIR/.env.production" ]]; then
        cat > "$APP_DIR/.env.production" << 'EOF'
# Production Environment Variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (Update with your production values)
DATABASE_URL=postgresql+asyncpg://username:password@localhost/trading_db

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-super-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Angel One (Update with your credentials)
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password

# Trading Engine
TRADING_ENGINE_WORKERS=4
TRADING_ENGINE_MAX_QUEUE_SIZE=10000

# API
API_HOST=0.0.0.0
API_PORT=8000
EOF
        print_warning "Created .env.production file - PLEASE UPDATE WITH YOUR CREDENTIALS"
    else
        print_status "Environment file already exists"
    fi
}

# Setup systemd service for PM2 (optional but recommended)
setup_systemd() {
    print_info "Setting up systemd service for PM2..."
    
    # Generate PM2 startup script
    pm2 startup systemd -u $USER --hp /root
    
    print_status "PM2 systemd service configured"
}

# Deploy application with PM2
deploy_application() {
    print_info "Deploying application with PM2..."
    
    cd "$APP_DIR"
    
    # Stop any existing PM2 processes
    pm2 stop all || true
    pm2 delete all || true
    
    # Start application using ecosystem file
    pm2 start ecosystem.config.js --env production
    
    # Save PM2 configuration
    pm2 save
    
    # Show status
    pm2 status
    
    print_status "Application deployed with PM2"
}

# Setup monitoring
setup_monitoring() {
    print_info "Setting up monitoring..."
    
    # Install PM2 monitoring (optional)
    print_info "PM2 monitoring commands:"
    echo "  pm2 monit              - Real-time monitoring"
    echo "  pm2 status             - Process status"
    echo "  pm2 logs               - View logs"
    echo "  pm2 logs --lines 100   - View last 100 lines"
    
    print_status "Monitoring setup complete"
}

# Setup nginx reverse proxy (optional)
setup_nginx() {
    print_info "Setting up Nginx reverse proxy..."
    
    # Install nginx if not present
    if ! command -v nginx &> /dev/null; then
        apt-get update
        apt-get install -y nginx
        print_status "Nginx installed"
    fi
    
    # Create nginx configuration
    cat > /etc/nginx/sites-available/trading-backend << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

    # Enable the site
    ln -sf /etc/nginx/sites-available/trading-backend /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    nginx -t
    
    # Restart nginx
    systemctl restart nginx
    systemctl enable nginx
    
    print_status "Nginx reverse proxy configured"
    print_warning "Don't forget to update server_name in /etc/nginx/sites-available/trading-backend"
}

# Install SSL certificate (optional)
setup_ssl() {
    print_info "SSL setup information:"
    echo "To setup SSL with Let's Encrypt:"
    echo "  1. Update server_name in nginx config"
    echo "  2. Run: sudo apt install certbot python3-certbot-nginx"
    echo "  3. Run: sudo certbot --nginx -d your-domain.com"
    echo "  4. Test renewal: sudo certbot renew --dry-run"
}

# Show final status
show_status() {
    print_info "Deployment Status:"
    echo ""
    
    echo "📊 PM2 Status:"
    pm2 status
    echo ""
    
    echo "📝 Useful Commands:"
    echo "  pm2 status             - Show process status"
    echo "  pm2 logs               - View all logs"
    echo "  pm2 logs trading-engine - View specific app logs"
    echo "  pm2 restart all        - Restart all processes"
    echo "  pm2 reload all         - Reload all processes (zero downtime)"
    echo "  pm2 stop all           - Stop all processes"
    echo "  pm2 monit              - Real-time monitoring"
    echo ""
    
    echo "🔧 Configuration Files:"
    echo "  $APP_DIR/ecosystem.config.js    - PM2 configuration"
    echo "  $APP_DIR/.env.production         - Environment variables"
    echo "  /etc/nginx/sites-available/trading-backend - Nginx config"
    echo ""
    
    print_status "Deployment completed successfully!"
    print_warning "Don't forget to update your environment variables in .env.production"
}

# Main execution
main() {
    print_info "Starting production deployment..."
    
    check_user
    install_pm2
    setup_directories
    configure_pm2_logrotate
    setup_environment
    setup_systemd
    deploy_application
    setup_monitoring
    
    # Optional components
    read -p "Setup Nginx reverse proxy? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_nginx
    fi
    
    setup_ssl
    show_status
}

# Run main function
main "$@" 