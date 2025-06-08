#!/bin/bash

# Trading Backend - Monitoring Management Script
# Docker Compose based Grafana + Prometheus setup

case "$1" in
    start)
        echo "🚀 Starting Trading Backend Monitoring Stack..."
        docker-compose up -d
        sleep 10
        echo ""
        echo "📊 Container Status:"
        docker-compose ps
        echo ""
        echo "🎯 ACCESS URLS:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Grafana Dashboard: http://localhost:3001"
        echo "   Username: admin | Password: trading123!"
        echo "📈 Prometheus: http://localhost:9090"
        echo "🖥️  System Metrics: http://localhost:9100"
        echo "🐳 Container Metrics: http://localhost:8080"
        ;;
    stop)
        echo "🛑 Stopping Trading Backend Monitoring Stack..."
        docker-compose down
        echo "✅ All monitoring containers stopped."
        ;;
    restart)
        echo "🔄 Restarting Trading Backend Monitoring Stack..."
        docker-compose restart
        sleep 5
        docker-compose ps
        ;;
    status)
        echo "📊 Trading Backend Monitoring Status:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        docker-compose ps
        echo ""
        echo "🔍 Health Check:"
        if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
            echo "✅ Prometheus: HEALTHY"
        else
            echo "❌ Prometheus: DOWN"
        fi
        if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
            echo "✅ Grafana: HEALTHY"
        else
            echo "❌ Grafana: DOWN"
        fi
        if curl -s http://localhost:9100/metrics > /dev/null 2>&1; then
            echo "✅ Node Exporter: HEALTHY"
        else
            echo "❌ Node Exporter: DOWN"
        fi
        if curl -s http://localhost:8080/healthz > /dev/null 2>&1; then
            echo "✅ cAdvisor: HEALTHY"
        else
            echo "❌ cAdvisor: DOWN"
        fi
        ;;
    logs)
        echo "📋 Monitoring Stack Logs:"
        docker-compose logs -f --tail=50
        ;;
    update)
        echo "🔄 Updating monitoring images..."
        docker-compose pull
        docker-compose up -d
        echo "✅ Update complete!"
        ;;
    clean)
        echo "🧹 Cleaning up monitoring data..."
        docker-compose down -v
        docker system prune -f
        echo "✅ Cleanup complete!"
        ;;
    *)
        echo "🐳 Trading Backend Monitoring Management"
        echo "========================================"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|update|clean}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the monitoring stack"
        echo "  stop    - Stop the monitoring stack"
        echo "  restart - Restart all containers"
        echo "  status  - Show container status and health"
        echo "  logs    - Show container logs (follow mode)"
        echo "  update  - Update container images"
        echo "  clean   - Stop and remove all data (DESTRUCTIVE)"
        echo ""
        echo "🎯 Quick Access URLs:"
        echo "  📊 Grafana: http://localhost:3001 (admin/trading123!)"
        echo "  📈 Prometheus: http://localhost:9090"
        echo "  🖥️  Node Exporter: http://localhost:9100"
        echo "  🐳 cAdvisor: http://localhost:8080"
        ;;
esac 