#!/bin/bash
# Professional Trading System Manager
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

start() {
    log_info "🚀 Starting Professional Trading System..."
    docker-compose down --remove-orphans 2>/dev/null || true
    docker-compose build --parallel
    docker-compose up -d
    log_info "Waiting for services..."
    sleep 15
    status
}

stop() {
    log_info "🛑 Stopping Trading System..."
    docker-compose down --remove-orphans
    log_success "System stopped"
}

status() {
    echo -e "\n${PURPLE}📊 TRADING SYSTEM STATUS${NC}"
    echo "=========================="
    
    services=("gateway:8000" "auth:8001" "market-data:8002" 
              "strategy-engine:8003" "order-management:8004" "notification:8005")
    
    for service in "${services[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name (Port $port)${NC}"
        else
            echo -e "${RED}❌ $name (Port $port)${NC}"
        fi
    done
    
    echo ""
    docker-compose ps
}

help() {
    echo -e "${CYAN}Professional Trading System Manager${NC}"
    echo "==================================="
    echo "Usage: $0 [start|stop|restart|status|help]"
}

case "${1:-}" in
    "start") start ;;
    "stop") stop ;;
    "restart") stop && start ;;
    "status") status ;;
    "help"|"--help"|"-h") help ;;
    "") help ;;
    *) log_error "Unknown command: $1" && help && exit 1 ;;
esac
