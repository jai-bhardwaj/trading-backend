#!/bin/bash

# Trading Backend - Monitoring Setup Script
# Sets up comprehensive monitoring with GUI solutions

set -e

echo "📊 Trading Backend - Monitoring Setup"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

# Install Docker (if not present)
install_docker() {
    if ! command -v docker &> /dev/null; then
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
        usermod -aG docker $USER
        print_status "Docker installed"
    else
        print_status "Docker already installed"
    fi
}

# Setup Grafana + Prometheus monitoring stack
setup_grafana_stack() {
    print_info "Setting up Grafana + Prometheus monitoring stack..."
    
    mkdir -p /opt/monitoring
    cd /opt/monitoring
    
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://host.docker.internal:6379
    restart: unless-stopped

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres-exporter
    ports:
      - "9187:9187"
    environment:
      - DATA_SOURCE_NAME=postgresql://username:password@host.docker.internal:5432/trading_db?sslmode=disable
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
EOF

    # Create Prometheus configuration
    cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'trading-engine'
    static_configs:
      - targets: ['host.docker.internal:8001']  # Your app metrics endpoint
    scrape_interval: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
EOF

    # Create Grafana provisioning
    mkdir -p grafana/provisioning/dashboards
    mkdir -p grafana/provisioning/datasources
    
    cat > grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    cat > grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    print_status "Grafana + Prometheus stack configured"
}

# Setup Portainer for Docker management
setup_portainer() {
    print_info "Setting up Portainer for Docker management..."
    
    docker volume create portainer_data
    docker run -d -p 9443:9443 -p 9000:9000 \
        --name portainer --restart=always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v portainer_data:/data \
        portainer/portainer-ce:latest
    
    print_status "Portainer installed - Access at http://localhost:9000"
}

# Setup PM2 Plus monitoring (optional premium)
setup_pm2_plus() {
    print_info "PM2 Plus setup information:"
    echo "PM2 Plus provides advanced monitoring with:"
    echo "  • Real-time monitoring dashboard"
    echo "  • Custom metrics and alerts"
    echo "  • Exception tracking"
    echo "  • Log management"
    echo ""
    echo "To setup PM2 Plus:"
    echo "  1. Sign up at https://app.pm2.io"
    echo "  2. Create a bucket for your server"
    echo "  3. Run: pm2 link <secret_key> <public_key>"
    echo "  4. Your processes will appear in the dashboard"
    print_warning "PM2 Plus is a paid service but offers free tier"
}

# Setup Netdata for real-time monitoring
setup_netdata() {
    print_info "Setting up Netdata for real-time monitoring..."
    
    # Install Netdata
    bash <(curl -Ss https://my-netdata.io/kickstart.sh) --dont-wait
    
    # Configure Netdata for production
    cat > /etc/netdata/netdata.conf << 'EOF'
[global]
    process scheduling policy = idle
    OOM score = 1000

[web]
    bind to = localhost
    allow connections from = localhost 127.0.0.1

[plugins]
    python.d = yes
    node.d = yes
    apps = yes
    proc = yes
    diskspace = yes
EOF

    systemctl restart netdata
    systemctl enable netdata
    
    print_status "Netdata installed - Access at http://localhost:19999"
}

# Setup log monitoring with Loki + Promtail
setup_loki_stack() {
    print_info "Setting up Loki + Promtail for log monitoring..."
    
    cd /opt/monitoring
    
    cat >> docker-compose.yml << 'EOF'

  loki:
    image: grafana/loki:latest
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/tmp/loki
      - ./loki-config.yml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    volumes:
      - /var/log:/var/log:ro
      - /root/trading-backend/logs:/trading-logs:ro
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped

volumes:
  loki_data:
EOF

    # Loki configuration
    cat > loki-config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /tmp/loki/index

  filesystem:
    directory: /tmp/loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
EOF

    # Promtail configuration
    cat > promtail-config.yml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          __path__: /var/log/*log

  - job_name: trading-backend
    static_configs:
      - targets:
          - localhost
        labels:
          job: trading
          __path__: /trading-logs/*.log
EOF

    print_status "Loki + Promtail stack configured"
}

# Create monitoring dashboards
create_dashboards() {
    print_info "Creating custom Grafana dashboards..."
    
    # Trading Engine Dashboard
    cat > /opt/monitoring/grafana/provisioning/dashboards/trading-engine.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Trading Engine Monitoring",
    "tags": ["trading", "engine"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Orders Per Minute",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(orders_total[1m])",
            "legendFormat": "Orders/min"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Active Strategies",
        "type": "stat",
        "targets": [
          {
            "expr": "active_strategies",
            "legendFormat": "Active"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      }
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "10s"
  }
}
EOF

    print_status "Custom dashboards created"
}

# Setup alerting
setup_alerting() {
    print_info "Setting up alerting..."
    
    # Create alert rules for Prometheus
    mkdir -p /opt/monitoring/rules
    
    cat > /opt/monitoring/rules/trading-alerts.yml << 'EOF'
groups:
  - name: trading-engine
    rules:
      - alert: TradingEngineDown
        expr: up{job="trading-engine"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Trading Engine is down"
          description: "Trading Engine has been down for more than 1 minute"

      - alert: HighOrderFailureRate
        expr: rate(orders_failed_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High order failure rate"
          description: "Order failure rate is above 10% for 2 minutes"

      - alert: DatabaseConnectionError
        expr: database_connections_failed > 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Database connection error"
          description: "Database connection failures detected"
EOF

    print_status "Alerting rules configured"
}

# Start all monitoring services
start_monitoring() {
    print_info "Starting monitoring services..."
    
    cd /opt/monitoring
    docker-compose up -d
    
    print_status "All monitoring services started"
}

# Show monitoring URLs
show_monitoring_urls() {
    print_info "Monitoring Services Access URLs:"
    echo ""
    echo "📊 Grafana Dashboard:     http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo ""
    echo "🔍 Prometheus:            http://localhost:9090"
    echo "📈 Netdata:              http://localhost:19999"
    echo "🐳 Portainer:            http://localhost:9000"
    echo "📝 Loki Logs:            http://localhost:3100"
    echo ""
    echo "📱 PM2 Monitoring:"
    echo "   Terminal: pm2 monit"
    echo "   Logs: pm2 logs"
    echo "   Status: pm2 status"
    echo ""
    print_status "All monitoring services configured!"
}

# Main execution
main() {
    print_info "Setting up comprehensive monitoring..."
    
    install_docker
    setup_grafana_stack
    setup_loki_stack
    create_dashboards
    setup_alerting
    setup_portainer
    setup_netdata
    setup_pm2_plus
    start_monitoring
    show_monitoring_urls
    
    print_status "Monitoring setup completed!"
    print_warning "Remember to configure your database credentials in docker-compose.yml"
}

# Run main function
main "$@" 