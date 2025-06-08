# 🐳 Trading Backend Monitoring Stack

**Professional Docker Compose based monitoring solution using Grafana + Prometheus**

## 🚀 Quick Start

```bash
# Start monitoring stack
./manage-monitoring.sh start

# Check status
./manage-monitoring.sh status

# View logs
./manage-monitoring.sh logs

# Stop monitoring
./manage-monitoring.sh stop
```

## 🎯 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **📊 Grafana Dashboard** | http://localhost:3001 | admin / trading123! |
| **📈 Prometheus** | http://localhost:9090 | - |
| **🖥️ System Metrics** | http://localhost:9100 | - |
| **🐳 Container Metrics** | http://localhost:8080 | - |

## 📦 Components

### 🔍 **Prometheus** (Port 9090)
- **Purpose**: Metrics collection and storage
- **Collects**: System metrics, container metrics, trading API metrics
- **Retention**: 200 hours of data
- **Config**: Uses default configuration with basic scraping

### 📊 **Grafana** (Port 3000)
- **Purpose**: Visualization and dashboards
- **Features**: Pre-configured with Prometheus datasource
- **Plugins**: Clock panel, Simple JSON datasource
- **Storage**: Persistent volume for dashboards and settings

### 🖥️ **Node Exporter** (Port 9100)
- **Purpose**: System-level metrics
- **Metrics**: CPU, Memory, Disk, Network usage
- **Host Access**: Monitors the actual server resources

### 🐳 **cAdvisor** (Port 8080)
- **Purpose**: Container-level metrics
- **Metrics**: Docker container resource usage
- **Real-time**: Live container performance data

## 🛠️ Management Commands

```bash
# Management script usage
./manage-monitoring.sh {start|stop|restart|status|logs|update|clean}

# Individual Docker Compose commands
docker-compose up -d        # Start in background
docker-compose down         # Stop all containers
docker-compose ps           # Show container status
docker-compose logs -f      # Follow logs
docker-compose pull         # Update images
```

## 📈 Setting Up Dashboards

1. **Access Grafana**: http://localhost:3001
2. **Login**: admin / trading123!
3. **Add Prometheus Datasource** (if not auto-configured):
   - URL: `http://prometheus:9090`
   - Access: Server (default)
4. **Import Dashboards**:
   - Node Exporter Dashboard: ID `1860`
   - Docker Container Dashboard: ID `193`
   - Custom trading metrics dashboards

## 🔧 Configuration

### Environment Variables
- `GF_SECURITY_ADMIN_USER=admin`
- `GF_SECURITY_ADMIN_PASSWORD=trading123!`
- `GF_USERS_ALLOW_SIGN_UP=false`

### Volumes
- `prometheus_data`: Prometheus metrics storage
- `grafana_data`: Grafana dashboards and settings

### Networks
- `monitoring`: Internal Docker network for service communication

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full restart
./manage-monitoring.sh restart
```

### Port Conflicts
If ports are already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Change external port
```

### Data Persistence
- Grafana dashboards: Stored in `grafana_data` volume
- Prometheus metrics: Stored in `prometheus_data` volume
- To reset: `./manage-monitoring.sh clean` (⚠️ DESTRUCTIVE)

## 🔒 Security Notes

- **Default Password**: Change `trading123!` in production
- **Network Access**: Services only accessible from localhost
- **Firewall**: Ensure ports 3000, 9090, 9100, 8080 are secured

## 📊 Monitoring Your Trading Backend

The stack automatically monitors:
- ✅ **System Resources**: CPU, RAM, Disk, Network
- ✅ **Docker Containers**: Resource usage, health status
- ✅ **Trading API**: Health endpoints (if configured)
- ✅ **PM2 Processes**: Process monitoring (if PM2 metrics enabled)

## 🔄 Updates

```bash
# Update all container images
./manage-monitoring.sh update

# Manual update
docker-compose pull
docker-compose up -d
```

---

**🎯 This is a production-ready monitoring solution that requires no external repositories or complex installations - just Docker!** 