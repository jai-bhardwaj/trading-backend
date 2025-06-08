#!/bin/bash

# Trading Backend - Monitoring Stack Startup
# Docker Compose based Grafana + Prometheus setup

echo "🚀 TRADING BACKEND MONITORING STACK"
echo "======================================"
echo ""

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "⚠️ Docker is not running. Starting Docker..."
    sudo systemctl start docker
    sleep 3
fi

# Check Docker Compose version
echo "🔍 Docker Compose Version:"
docker-compose --version
echo ""

# Set proper permissions
echo "🔧 Setting up permissions..."
sudo chown -R 472:472 grafana/ 2>/dev/null || echo "grafana/ directory doesn't exist yet, will be created"
sudo chmod -R 755 config/
echo ""

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker-compose pull
echo ""

# Start the monitoring stack
echo "🐳 Starting monitoring containers..."
docker-compose up -d

# Wait for services to start
echo ""
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check container status
echo ""
echo "📊 Container Status:"
docker-compose ps

# Check if services are responding
echo ""
echo "🔍 Service Health Check:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus: http://localhost:9090 - HEALTHY"
else
    echo "❌ Prometheus: http://localhost:9090 - NOT RESPONDING"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Grafana: http://localhost:3000 - HEALTHY"
else
    echo "❌ Grafana: http://localhost:3000 - NOT RESPONDING"
fi

# Check Node Exporter
if curl -s http://localhost:9100/metrics > /dev/null 2>&1; then
    echo "✅ Node Exporter: http://localhost:9100 - HEALTHY"
else
    echo "❌ Node Exporter: http://localhost:9100 - NOT RESPONDING"
fi

# Check cAdvisor
if curl -s http://localhost:8080/healthz > /dev/null 2>&1; then
    echo "✅ cAdvisor: http://localhost:8080 - HEALTHY"
else
    echo "❌ cAdvisor: http://localhost:8080 - NOT RESPONDING"
fi

echo ""
echo "🎯 ACCESS INFORMATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Grafana Dashboard: http://localhost:3000"
echo "   Username: admin"
echo "   Password: trading123!"
echo ""
echo "📈 Prometheus: http://localhost:9090"
echo "🖥️  System Metrics: http://localhost:9100"
echo "🐳 Container Metrics: http://localhost:8080"
echo ""
echo "💡 To stop monitoring: docker-compose down"
echo "💡 To view logs: docker-compose logs -f"
echo "💡 To restart: docker-compose restart"
echo "" 