#!/bin/bash
# PM2 Setup Script for Trading Engine
# Installs and configures PM2 for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install Node.js and npm (required for PM2)
install_nodejs() {
    log_info "Installing Node.js and npm..."
    
    if command -v node >/dev/null 2>&1; then
        log_success "Node.js already installed: $(node --version)"
        return
    fi
    
    # Install Node.js 18.x LTS
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    apt-get install -y nodejs
    
    log_success "Node.js installed: $(node --version)"
    log_success "npm installed: $(npm --version)"
}

# Install PM2
install_pm2() {
    log_info "Installing PM2..."
    
    if command -v pm2 >/dev/null 2>&1; then
        log_success "PM2 already installed: $(pm2 --version)"
        return
    fi
    
    npm install -g pm2
    
    # Install PM2 startup script
    pm2 startup systemd -u root --hp /root
    
    log_success "PM2 installed: $(pm2 --version)"
}

# Configure PM2 for production
configure_pm2() {
    log_info "Configuring PM2..."
    
    # Create PM2 logs directory
    mkdir -p /var/log/pm2
    
    # Set PM2 environment
    pm2 set pm2:autodump true
    pm2 set pm2:watch true
    pm2 set pm2:log-date-format 'YYYY-MM-DD HH:mm:ss Z'
    
    # Configure PM2 monitoring
    pm2 install pm2-server-monit
    
    log_success "PM2 configured for production"
}

# Verify installation
verify_installation() {
    log_info "Verifying PM2 installation..."
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js not found"
        exit 1
    fi
    
    # Check PM2
    if ! command -v pm2 >/dev/null 2>&1; then
        log_error "PM2 not found"
        exit 1
    fi
    
    # Check PM2 status
    pm2 ping
    
    log_success "PM2 installation verified"
}

# Display PM2 commands
show_usage() {
    log_info "PM2 Trading Engine Commands:"
    echo "
┌─────────────────────────────────────────────────────────────┐
│                     PM2 Commands                            │
├─────────────────────────────────────────────────────────────┤
│ Start:     pm2 start ecosystem.config.js --env production  │
│ Stop:      pm2 stop trading-engine                         │
│ Restart:   pm2 restart trading-engine                      │
│ Reload:    pm2 reload trading-engine                       │
│ Delete:    pm2 delete trading-engine                       │
│                                                             │
│ Status:    pm2 status                                       │
│ Logs:      pm2 logs trading-engine                         │
│ Monitor:   pm2 monit                                        │
│ Dashboard: pm2 plus                                         │
│                                                             │
│ Save:      pm2 save                                         │
│ Resurrect: pm2 resurrect                                    │
└─────────────────────────────────────────────────────────────┘

Environment files:
- Production: pm2 start ecosystem.config.js --env production
- Development: pm2 start ecosystem.config.js --env development

Log files location: ./logs/
"
}

# Main execution
main() {
    log_info "Setting up PM2 for Trading Engine..."
    
    check_root
    install_nodejs
    install_pm2
    configure_pm2
    verify_installation
    show_usage
    
    log_success "PM2 setup completed!"
    log_info "You can now start the trading engine with:"
    log_info "pm2 start ecosystem.config.js --env production"
}

# Run main function
main "$@" 