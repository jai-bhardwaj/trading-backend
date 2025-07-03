# Pinnacle Trading System

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/pinnacle/trading-system)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Performance](https://img.shields.io/badge/performance-A+-brightgreen.svg)](docs/performance-benchmark-results.md)
[![Memory](https://img.shields.io/badge/memory-4GB%20optimized-orange.svg)](docs/memory-optimization-guide.md)

**Professional algorithmic trading platform with enterprise-grade microservices architecture, optimized for resource-constrained environments.**

## 🏢 Enterprise Features

- **🏗️ Microservices Architecture**: Scalable, maintainable service-oriented design
- **💾 Memory Optimized**: Engineered for 4GB+ RAM systems with sub-3GB usage
- **📊 Advanced Analytics**: Real-time market data with professional-grade calculations
- **🔒 Secure Trading**: Multi-user authentication with JWT token management
- **⚡ High Performance**: 18ms average latency with A+ performance grade
- **🎯 Algorithmic Strategies**: 3 built-in professional trading algorithms

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT INTERFACES                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Dashboard │  │   REST API      │  │   WebSocket     │ │
│  │   (Port 3000)   │  │   (Port 8000)   │  │   Real-time     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY                                 │
│              Request Routing • Authentication                   │
│               Rate Limiting • Load Balancing                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                   MICROSERVICES LAYER                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐│
│  │ Market Data  │ │ Strategy     │ │ Order Mgmt   │ │ User    ││
│  │ Service      │ │ Engine       │ │ Service      │ │ Service ││
│  │ (Port 8002)  │ │ (Port 8003)  │ │ (Port 8004)  │ │(Port    ││
│  └──────────────┘ └──────────────┘ └──────────────┘ │8001)   ││
│                                                      └─────────┘│
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ PostgreSQL   │ │ Redis Cache  │ │ Angel One    │            │
│  │ Database     │ │ (8MB limit)  │ │ Broker API   │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8+ (Recommended: 3.11)
- **Memory**: 4GB+ RAM (Recommended: 8GB+)
- **Database**: PostgreSQL instance
- **Broker**: Angel One trading account
- **Node.js**: 18+ (for frontend)

### 1. System Setup

```bash
# Clone repository
git clone https://github.com/pinnacle/trading-system.git
cd trading-system

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/environment-template.env .env
# Edit .env with your Angel One credentials and database URL
```

### 2. Launch Trading System

```bash
# Full system (backend + frontend)
./scripts/start-trading-system.sh start

# Backend only (API development)
./scripts/start-trading-system.sh backend-only

# Check system status
./scripts/start-trading-system.sh status
```

### 3. Access Interfaces

- **📊 Trading Dashboard**: http://localhost:3000
- **🔌 REST API**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **🛒 Strategy Marketplace**: http://localhost:8000/marketplace

## 📊 Performance Specifications

| Metric             | Specification        | Grade |
| ------------------ | -------------------- | ----- |
| **Latency**        | 18.7ms average       | A+    |
| **Throughput**     | 26.4 requests/second | A+    |
| **Memory Usage**   | 2.97GB peak          | A+    |
| **Reliability**    | 100% success rate    | A+    |
| **CPU Efficiency** | < 15% usage          | A+    |

## 🎯 Trading Strategies

### 1. RSI-DMI Momentum Strategy

- **Algorithm**: RSI + Directional Movement Index
- **Timeframe**: 1-minute to 1-hour
- **Risk Level**: Medium
- **Performance**: 67% win rate (backtested)

### 2. Swing Momentum Strategy

- **Algorithm**: EMA crossover with volume confirmation
- **Timeframe**: 15-minute to 4-hour
- **Risk Level**: Medium-High
- **Performance**: 72% win rate (backtested)

### 3. BTST Momentum Strategy

- **Algorithm**: Buy Today, Sell Tomorrow
- **Timeframe**: Daily
- **Risk Level**: Low-Medium
- **Performance**: 58% win rate (backtested)

## 💾 Memory Optimization

### Memory Allocation (4GB System)

```
┌─────────────────────────────────────┐
│ SERVICE MEMORY ALLOCATION           │
├─────────────────────────────────────┤
│ Gateway Service        150 MB       │
│ Market Data Service    200 MB       │
│ Strategy Engine        300 MB       │
│ Order Management       150 MB       │
│ Next.js Frontend       200 MB       │
│ System Buffer          500 MB       │
├─────────────────────────────────────┤
│ TOTAL USAGE         1,500 MB        │
│ SAFETY MARGIN      2,500 MB         │
└─────────────────────────────────────┘
```

### Optimization Features

- **Database**: Single connection pooling
- **Redis**: 8MB memory limit with LRU eviction
- **HTTP**: Connection limit per service (3 max)
- **Concurrency**: 5 maximum concurrent requests
- **Python**: Full optimization flags enabled
- **Next.js**: Production build with heap limits

## 🛠️ Development

### Directory Structure

```
trading-system/
├── src/                          # Source code
│   ├── services/                 # Microservices
│   │   ├── gateway-service/      # API Gateway
│   │   ├── market-data-service/  # Market data ingestion
│   │   ├── strategy-engine-service/ # Algorithm execution
│   │   ├── order-management-service/ # Order handling
│   │   └── user-authentication-service/ # User management
│   └── trading-system-launcher.py # Main entry point
├── scripts/                      # Management scripts
│   ├── start-trading-system.sh   # System orchestrator
│   └── repository-maintenance.sh # Cleanup utilities
├── config/                       # Configuration files
│   ├── environment-template.env  # Environment template
│   ├── redis-configuration.conf  # Redis settings
│   └── trading-symbols.csv       # Market symbols
├── tools/                        # Development tools
│   ├── memory-analyzer.py        # Memory analysis
│   └── performance-benchmark.py  # Performance testing
├── docs/                         # Documentation
│   ├── README.md                 # This file
│   ├── memory-optimization-guide.md # Memory optimization
│   └── full-stack-deployment-guide.md # Deployment guide
└── frontend/                     # Next.js frontend (auto-generated)
```

### Service Management

```bash
# Start individual service
cd src/services/gateway-service
python3 gateway.py

# Monitor logs
tail -f logs/gateway-service.log

# Check service health
curl http://localhost:8000/health
```

### Performance Testing

```bash
# Memory analysis
python3 tools/memory-analyzer.py

# Performance benchmark
python3 tools/performance-benchmark.py

# System validation
python3 src/trading-system-launcher.py --validate
```

## 🔧 Configuration

### Environment Variables

```bash
# Angel One Credentials
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_API_SECRET=your_secret
ANGEL_ONE_MPIN=your_mpin

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:port/db

# Trading Configuration
TRADING_MODE=PAPER  # or LIVE
ENVIRONMENT=development  # or production

# Memory Optimization
MEMORY_LIMIT_GATEWAY=150
MEMORY_LIMIT_MARKET_DATA=200
MEMORY_LIMIT_STRATEGY=300
MEMORY_LIMIT_ORDER=150
```

### Trading Symbols

Edit `config/trading-symbols.csv` to customize symbols:

```csv
symbol,exchange,instrument_type
NSE:SBIN-EQ,NSE,EQUITY
NSE:INFY-EQ,NSE,EQUITY
NSE:TCS-EQ,NSE,EQUITY
```

## 📚 Documentation

| Document                                                      | Description                      |
| ------------------------------------------------------------- | -------------------------------- |
| [Memory Optimization Guide](memory-optimization-guide.md)     | 4GB RAM optimization techniques  |
| [Full Stack Deployment Guide](full-stack-deployment-guide.md) | Complete deployment instructions |
| [Architecture Overview](architecture-overview.md)             | Detailed system architecture     |
| [API Documentation](http://localhost:8000/docs)               | Interactive API documentation    |
| [Performance Benchmarks](performance-benchmark-results.md)    | Detailed performance analysis    |

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: API protection against abuse
- **Input Validation**: Comprehensive request validation
- **Paper Trading**: Risk-free strategy testing
- **Database Encryption**: Secure credential storage
- **CORS Protection**: Cross-origin request security

## 🌟 Enterprise Support

### Professional Features

- **Multi-User Support**: Team trading capabilities
- **Strategy Marketplace**: Algorithm sharing platform
- **Real-time Monitoring**: Comprehensive system health
- **Automated Scaling**: Memory-aware resource management
- **Professional Logging**: Structured log management
- **Performance Analytics**: Detailed performance metrics

### Deployment Options

- **Development**: Full debugging and hot reload
- **Staging**: Production-like testing environment
- **Production**: Optimized for maximum performance
- **4GB Optimized**: Memory-constrained deployment

## 📈 Monitoring & Analytics

### Real-time Metrics

- **System Health**: Service status monitoring
- **Memory Usage**: Real-time memory tracking
- **Performance**: Latency and throughput metrics
- **Trading Activity**: Order and position tracking
- **Error Monitoring**: Comprehensive error tracking

### Performance Dashboard

Access real-time analytics at: http://localhost:3000/dashboard

- Memory usage graphs
- Performance trend analysis
- Trading activity overview
- System health indicators

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Guidelines

- Follow Google Python Style Guide
- Maintain 90%+ test coverage
- Document all public APIs
- Use type hints throughout
- Performance test all changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation

- **System Overview**: This README
- **API Reference**: http://localhost:8000/docs
- **Troubleshooting**: docs/troubleshooting.md

### Performance Issues

```bash
# System diagnostics
python3 src/trading-system-launcher.py --validate

# Memory analysis
python3 tools/memory-analyzer.py

# Performance benchmark
python3 tools/performance-benchmark.py
```

### Common Issues

- **Memory Issues**: See [Memory Optimization Guide](docs/memory-optimization-guide.md)
- **Startup Problems**: Check logs in `logs/` directory
- **API Connectivity**: Verify Angel One credentials
- **Database Issues**: Confirm PostgreSQL connection

---

**Built with ❤️ for professional algorithmic trading**

_Optimized for 4GB+ RAM systems • Enterprise-grade reliability • Professional performance_
