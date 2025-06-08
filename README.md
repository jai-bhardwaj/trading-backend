# 🚀 Trading Backend - Multi-User Trading Engine

A comprehensive, production-ready trading engine built with Python, designed for real-time algorithmic trading across multiple asset classes. Features multi-user support, multiple broker integrations, and advanced trading capabilities.

## ✨ Key Features

### 🏗️ Core Architecture
- **Multi-User Support**: Complete isolation between users and their trading accounts
- **Multiple Brokers**: Currently supports Angel One, extensible to Zerodha, Upstox, etc.
- **Real-time Processing**: Redis-based queue system for high-performance order execution
- **Production Ready**: Full monitoring, logging, and error recovery
- **Scalable Design**: Microservices architecture with horizontal scalability

### 📊 Trading Capabilities
- **5 Built-in Strategies**: Equity, Derivatives, and Crypto strategies
- **Real-time Market Data**: Live price feeds and historical data
- **Risk Management**: Comprehensive risk controls and position monitoring
- **Order Management**: Full order lifecycle with validation and execution
- **Performance Tracking**: Real-time P&L and portfolio analytics

### 🔧 Technical Stack
- **Backend**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL with Prisma ORM
- **Cache/Queue**: Redis with priority queues
- **Authentication**: JWT with 2FA support
- **Monitoring**: Custom health checks and metrics
- **Deployment**: Docker & PM2 ecosystem

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Optional)                 │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │   Trading UI    │  │   Dashboard     │                      │
│  │   (React)       │  │   (Charts)      │                      │
│  └─────────────────┘  └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI Trading Engine                        │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │ Multi-User      │  │   Strategy      │                      │
│  │ Broker Manager  │  │   Engine        │                      │
│  └─────────────────┘  └─────────────────┘                      │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │ Redis Queue     │  │   Risk          │                      │
│  │ System          │  │   Manager       │                      │
│  └─────────────────┘  └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Angel One + Other Brokers + Database                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python 3.12+
python --version

# PostgreSQL 14+
psql --version

# Redis 7+
redis-server --version
```

### 2. Installation

```bash
# Clone repository
git clone <your-repo>
cd trading-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Generate Prisma client
prisma generate
```

### 3. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your settings
nano .env
```

**Required Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_db

# Redis
REDIS_URL=redis://localhost:6379

# Angel One Credentials
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret

# Security
MASTER_ENCRYPTION_KEY=generate_with_security_module
JWT_SECRET_KEY=your_jwt_secret

# Instrument Loading (Optional)
MAX_EQUITY_INSTRUMENTS=1000      # Default: 1000
MAX_DERIVATIVES_INSTRUMENTS=500  # Default: 500
LOAD_ALL_INSTRUMENTS=false       # Default: false
```

### 4. Database Setup

```bash
# Create database
python create_tables.py

# Run migrations
prisma db push

# Setup broker configuration
python setup_broker_config.py
```

### 5. Run the Application

```bash
# Development mode
python main.py

# Production mode with PM2
pm2 start ecosystem.config.js
```

### 6. Test the System

```bash
# Run comprehensive tests
python quick_test.py

# Check health
curl http://localhost:8000/health
```

## 📊 Multi-User Broker Management - Complete Guide

### 🚀 Initialize the Multi-User System

```python
from app.core.multi_user_broker_manager import multi_user_broker_manager

# Initialize the manager
success = await multi_user_broker_manager.initialize()
if success:
    print("✅ Multi-User Broker Manager initialized")
else:
    print("❌ Failed to initialize")
```

### 👥 Adding Multiple Users with Angel One Accounts

```python
from app.core.multi_user_broker_manager import add_user_broker

# User 1 - Primary Angel One Account
result1 = await add_user_broker("user1", "angel_config1")

# User 1 - Secondary Angel One Account  
result2 = await add_user_broker("user1", "angel_config2")

# User 2 - Angel One Account
result3 = await add_user_broker("user2", "angel_config3")

# Check results
if result1.success:
    print(f"✅ Session created: {result1.session_id}")
    print(f"Broker: {result1.broker_name}")
    print(f"Execution time: {result1.execution_time:.2f}s")
else:
    print(f"❌ Failed: {result1.message}")
    print(f"Error code: {result1.error_code}")
```

### 📈 Trading Operations

```python
from app.core.multi_user_broker_manager import place_order_for_user
from app.brokers.base import BrokerOrder
from app.models.base import OrderSide, OrderType, ProductType

# Create order
order = BrokerOrder(
    symbol="TCS",
    exchange="NSE",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    product_type=ProductType.DELIVERY,
    quantity=1
)

# Place order for specific user and broker
result = await place_order_for_user(
    user_id="user1",
    broker_config_id="angel_config1", 
    order=order
)

if result.success:
    print(f"✅ Order placed: {result.data['broker_order_id']}")
else:
    print(f"❌ Order failed: {result.message}")

# Advanced order with limits
limit_order = BrokerOrder(
    symbol="RELIANCE",
    exchange="NSE",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    product_type=ProductType.INTRADAY,
    quantity=5,
    price=2500.0
)

result = await place_order_for_user("user1", "angel_config1", limit_order)
```

### 💼 Portfolio Management

```python
from app.core.multi_user_broker_manager import (
    get_all_user_positions, get_all_user_balances, get_positions_for_user,
    get_balance_for_user
)

# Get positions from specific broker
positions_result = await get_positions_for_user("user1", "angel_config1")
if positions_result.success:
    positions = positions_result.data['positions']
    for pos in positions:
        pnl_indicator = "🟢" if pos['pnl'] >= 0 else "🔴"
        print(f"{pnl_indicator} {pos['symbol']}: {pos['quantity']} @ ₹{pos['average_price']:.2f}")

# Get balance from specific broker  
balance_result = await get_balance_for_user("user1", "angel_config1")
if balance_result.success:
    balance = balance_result.data
    print(f"💰 Available: ₹{balance['available_cash']:,.2f}")
    print(f"💳 Buying Power: ₹{balance['buying_power']:,.2f}")

# Get all positions for a user across all brokers
all_positions = await get_all_user_positions("user1")
for config_id, result in all_positions.items():
    if result.success:
        positions = result.data['positions']
        print(f"📊 {result.broker_name}: {len(positions)} positions")

# Get all balances for a user across all brokers
all_balances = await get_all_user_balances("user1")
total_balance = 0
for config_id, result in all_balances.items():
    if result.success:
        balance = result.data
        total_balance += balance['total_balance']
        print(f"💰 {result.broker_name}: ₹{balance['total_balance']:,.2f}")

print(f"💰 Total across all brokers: ₹{total_balance:,.2f}")
```

### 🔧 Advanced Usage - Safe Broker Operations

```python
# Use context manager for safe operations
async with multi_user_broker_manager.broker_session("user1", "angel_config1") as broker:
    # Direct broker access
    positions = await broker.get_positions()
    balance = await broker.get_balance()
    market_data = await broker.get_market_data("TCS", "NSE")
    
    # Broker automatically handles:
    # - Session validation
    # - Authentication refresh
    # - Error recovery
    # - Activity tracking
    
    print(f"Direct broker access: {len(positions)} positions")
```

### ⚡ Parallel Operations Across Users

```python
import asyncio

# Get balances from multiple users simultaneously
async def get_all_user_balances_parallel():
    user_broker_pairs = [
        ("user1", "angel_config1"),
        ("user1", "angel_config2"), 
        ("user2", "angel_config3")
    ]
    
    tasks = []
    for user_id, config_id in user_broker_pairs:
        task = get_balance_for_user(user_id, config_id)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results

# Execute parallel operations
balances = await get_all_user_balances_parallel()
for i, result in enumerate(balances):
    if result.success:
        balance = result.data
        print(f"User {result.user_id}: ₹{balance['total_balance']:,.2f}")
```

### 📊 System Monitoring & Health

```python
# Get comprehensive system status
status = await multi_user_broker_manager.get_system_status()

print("🔍 System Status:")
print(f"   👥 Total Users: {status['total_users']}")
print(f"   🔗 Total Sessions: {status['total_sessions']}")
print(f"   ✅ Healthy Sessions: {status['healthy_sessions']}")
print(f"   ❌ Error Sessions: {status['error_sessions']}")
print(f"   ⏰ Expired Sessions: {status['expired_sessions']}")
print(f"   🔧 Background Tasks: {status['background_tasks']}")

# Broker-wise breakdown
for broker_name, broker_stats in status['by_broker'].items():
    print(f"   📈 {broker_name}: {broker_stats['total']} total, {broker_stats['healthy']} healthy")

# Get user sessions
sessions = await multi_user_broker_manager.get_user_brokers("user1")
print(f"\n🔍 User 1 has {len(sessions)} active sessions:")
for session in sessions:
    print(f"   📱 Session: {session.session_id[:8]}... ({session.broker_name.value})")
    print(f"      Status: {session.health_status}")
    print(f"      Errors: {session.error_count}")
    print(f"      Last Activity: {session.last_activity.strftime('%H:%M:%S')}")
```

### 🔄 Session Management

```python
# Remove a specific broker session
result = await multi_user_broker_manager.remove_user_broker("user1", "angel_config2")
if result.success:
    print(f"✅ Removed session for {result.broker_name}")

# Get market data for user
result = await multi_user_broker_manager.get_market_data_for_user(
    "user1", "angel_config1", "TCS", "NSE"
)
if result.success:
    market_data = result.data
    print(f"📊 TCS: ₹{market_data['ltp']} (Change: {market_data['change']:.2f})")
```

## 🎯 Instrument Configuration

The system supports fully configurable instrument loading:

### Configuration Options

```bash
# Conservative Setup (Good for Testing)
MAX_EQUITY_INSTRUMENTS=50
MAX_DERIVATIVES_INSTRUMENTS=20
LOAD_ALL_INSTRUMENTS=false
# Result: 70 total instruments

# Balanced Setup (Recommended for Production)
MAX_EQUITY_INSTRUMENTS=1000
MAX_DERIVATIVES_INSTRUMENTS=500  
LOAD_ALL_INSTRUMENTS=false
# Result: 1,500 total instruments

# Comprehensive Setup (For Advanced Strategies)
MAX_EQUITY_INSTRUMENTS=5000
MAX_DERIVATIVES_INSTRUMENTS=2000
LOAD_ALL_INSTRUMENTS=false
# Result: 7,000 total instruments

# Load Everything (Maximum Coverage)
LOAD_ALL_INSTRUMENTS=true
MAX_TOTAL_INSTRUMENTS=150000
# Result: All ~120,000+ instruments from Angel One
```

### Smart Sorting & Prioritization

**Equity Instruments:**
1. Major Nifty 50 stocks (RELIANCE, TCS, INFY, etc.)
2. All other stocks sorted alphabetically

**Derivatives Instruments:**
1. Index Futures (NIFTY, BANKNIFTY) - highest priority
2. Stock Futures - medium priority  
3. Options - lower priority

## 🔧 API Endpoints

### Health & Status
- `GET /health` - System health check
- `GET /api/v1/brokers/admin/status` - Broker system status

### Multi-User Broker Management
- `POST /api/v1/brokers/add` - Add broker account
- `DELETE /api/v1/brokers/remove/{config_id}` - Remove broker account
- `GET /api/v1/brokers/sessions` - Get user broker sessions

### Trading Operations
- `POST /api/v1/brokers/orders/place` - Place order
- `GET /api/v1/brokers/positions` - Get positions
- `GET /api/v1/brokers/balance` - Get balance
- `GET /api/v1/brokers/market-data/{symbol}` - Get market data

### Strategy Management
- `POST /api/v1/strategies` - Create strategy
- `GET /api/v1/strategies` - List strategies
- `POST /api/v1/strategies/{id}/start` - Start strategy
- `POST /api/v1/strategies/{id}/stop` - Stop strategy

## 📁 Project Structure

```
trading-backend/
├── app/                          # Main application
│   ├── api/                      # FastAPI endpoints
│   ├── brokers/                  # Broker integrations
│   ├── core/                     # Core business logic
│   │   ├── multi_user_broker_manager.py  # Multi-user broker management
│   │   ├── order_executor.py     # Order execution
│   │   ├── risk_manager.py       # Risk management
│   │   └── strategy_engine_manager.py    # Strategy management
│   ├── engine/                   # Trading engine
│   ├── models/                   # Database models
│   ├── queue/                    # Redis queue system
│   ├── services/                 # Business services
│   ├── strategies/               # Trading strategies
│   └── utils/                    # Utility functions
├── scripts/                      # Management scripts
├── logs/                         # Application logs
├── data/                         # Data files
├── main.py                       # Application entry point
├── schema.prisma                 # Database schema
├── requirements.txt              # Dependencies
└── ecosystem.config.js           # PM2 configuration
```

## 🔒 Security Features

### Authentication & Authorization
- JWT-based authentication with refresh tokens
- Role-based access control (USER, ADMIN, SUPER_ADMIN)
- 2FA support with TOTP
- API key management

### Data Protection
- Encrypted credential storage
- Secure session management
- Rate limiting and circuit breakers
- Audit logging for compliance

### Risk Management
- Real-time position monitoring
- Daily/weekly loss limits
- Position size validation
- Exposure management

## 📈 Trading Strategies

### Available Strategies
1. **Equity Strategies**: Mean reversion, momentum
2. **Derivatives Strategies**: Options selling, futures arbitrage
3. **Crypto Strategies**: Grid trading, DCA

### Custom Strategy Development

```python
from app.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    async def generate_signals(self) -> List[Signal]:
        # Your strategy logic here
        pass
    
    async def execute_trades(self, signals: List[Signal]):
        # Trade execution logic
        pass
```

## 🚀 Production Deployment with PM2

### 🎯 Quick Production Setup

```bash
# 1. Run automated production deployment
sudo ./deploy_production.sh

# 2. Setup comprehensive monitoring
sudo ./monitoring_setup.sh

# 3. Configure your environment
sudo nano /root/trading-backend/.env.production
```

### 📋 Manual DigitalOcean Setup

For step-by-step production deployment:

```bash
# 1. Create DigitalOcean droplet (Ubuntu 22.04 LTS, 4GB+ RAM recommended)

# 2. Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git postgresql-client redis-tools curl

# 3. Clone and setup application
git clone <your-repo> /root/trading-backend
cd /root/trading-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Install Node.js and PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2

# 5. Setup directories and permissions
sudo mkdir -p /root/trading-backend/logs
sudo chown -R root:root /root/trading-backend
sudo chmod +x /root/trading-backend/main.py

# 6. Configure environment
sudo cp .env.example .env.production
# Edit with your production values:
sudo nano .env.production

# 7. Setup database
python setup_database.py

# 8. Deploy with PM2
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup systemd
```

### ⚙️ PM2 Configuration (ecosystem.config.js)

Your `ecosystem.config.js` includes:

- **Trading Engine**: Core engine with 4 workers
- **Trading API**: FastAPI with 2 cluster instances  
- **Strategy Monitor**: Background monitoring
- **Auto-restart**: On failures with exponential backoff
- **Log management**: Centralized logging with rotation
- **Environment management**: Production vs development configs

### 📊 Production Monitoring Stack

#### Option 1: Built-in PM2 Monitoring

```bash
# Real-time monitoring dashboard
pm2 monit

# Process status
pm2 status

# View logs
pm2 logs
pm2 logs trading-engine --lines 100

# Performance monitoring
pm2 logs --timestamp
```

#### Option 2: PM2 Plus (Recommended GUI)

**Best for production trading systems:**

```bash
# 1. Sign up at https://app.pm2.io (free tier available)
# 2. Create a server bucket
# 3. Link your server
pm2 link <secret_key> <public_key>

# Features:
# ✅ Real-time performance metrics
# ✅ Error tracking and notifications
# ✅ Custom alerts for trading events
# ✅ Historical data and reports
# ✅ Mobile app for monitoring on-the-go
```

#### Option 3: Comprehensive Monitoring (Full Stack)

Run the monitoring setup script for enterprise-level monitoring:

```bash
sudo ./monitoring_setup.sh
```

**Includes:**
- **📊 Grafana Dashboard** (http://localhost:3000) - Trading metrics, charts, alerts
- **🔍 Prometheus** (http://localhost:9090) - Metrics collection and alerting  
- **📈 Netdata** (http://localhost:19999) - Real-time system monitoring
- **🐳 Portainer** (http://localhost:9000) - Docker container management
- **📝 Loki + Promtail** - Centralized log management
- **⚡ Redis Exporter** - Redis performance metrics
- **🗃️ PostgreSQL Exporter** - Database performance metrics

### 🔧 PM2 Production Commands

```bash
# 🚀 Deployment
pm2 start ecosystem.config.js --env production  # Start all services
pm2 reload all                                   # Zero-downtime reload
pm2 restart all                                  # Full restart

# 📊 Monitoring  
pm2 status                                       # Process overview
pm2 monit                                        # Real-time dashboard
pm2 logs                                         # Live logs
pm2 logs trading-engine --lines 50              # Specific service logs

# 🔧 Management
pm2 stop all                                     # Stop all processes
pm2 delete all                                   # Remove all processes  
pm2 save                                         # Save current state
pm2 resurrect                                    # Restore saved state

# 📈 Performance
pm2 show trading-engine                          # Detailed process info
pm2 reset trading-engine                         # Reset counters
pm2 flush                                        # Flush logs
```

### 🔒 Security & SSL Setup

```bash
# 1. Setup Nginx reverse proxy (included in deploy script)
sudo nano /etc/nginx/sites-available/trading-backend

# 2. Install SSL certificate with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 3. Auto-renewal
sudo certbot renew --dry-run
```

### 📊 Health Monitoring URLs

After running the monitoring setup:

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Trading dashboards, alerts |
| **PM2 Plus** | https://app.pm2.io | Process monitoring, mobile alerts |
| **Netdata** | http://localhost:19999 | Real-time system metrics |
| **Portainer** | http://localhost:9000 | Docker management |
| **Prometheus** | http://localhost:9090 | Metrics collection |

**Default Grafana Login:**
- Username: `admin`
- Password: `admin123`

### 🚨 Production Alerts

Configured alerts for:
- ❌ Trading engine downtime
- 📈 High order failure rates  
- 🔗 Database connection errors
- 💾 High memory usage
- 📊 Queue overload
- ⚡ Redis connection issues

### 📱 Mobile Monitoring

**PM2 Plus Mobile App:**
- Real-time notifications
- Process management
- Performance charts
- Error tracking
- Works with iOS/Android

### 🔄 Auto-Deployment Pipeline

```bash
# Setup Git deployment hooks
cd /opt/monitoring
pm2 ecosystem deploy production setup
pm2 ecosystem deploy production

# Features:
# ✅ Git-based deployments
# ✅ Automated dependency installation
# ✅ Zero-downtime updates
# ✅ Rollback capabilities
```

### Environment Variables for Production

```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Performance
UVICORN_WORKERS=4
MAX_CONNECTIONS=1000

# Security
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com

# Database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

## 📊 Monitoring & Logging

### Health Monitoring
- Real-time system health checks
- Broker connectivity monitoring
- Database and Redis health
- Strategy performance tracking

### Logging
- Structured logging with correlation IDs
- Error tracking and alerting
- Performance metrics
- Audit trails for compliance

### Metrics
- Order execution latency
- Strategy performance
- System resource usage
- User activity tracking

## 🛠️ Development

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Security scan
bandit -r app/
```

### Testing
```bash
# Run tests
python quick_test.py

# Performance testing
python -m pytest --benchmark-only

# Load testing
python scripts/load_test.py
```

## 📚 Documentation

### Complete Guides
- **Multi-User Broker Management**: See sections above with full examples
- **API Documentation**: Available at `/docs` when running  
- **Strategy Development**: Check `/app/strategies/` examples
- **Frontend Integration**: Next.js + tRPC examples below
- **Error Handling**: Comprehensive error examples included

### Support
- 📧 Email: support@tradingengine.com
- 📖 Wiki: Check repository wiki
- 🐛 Issues: GitHub issues

## 🔄 Extending to Other Brokers

### Adding New Brokers (e.g., Zerodha)

1. **Create Broker Implementation**:
```python
# app/brokers/zerodha.py
class ZerodhaBroker(BrokerInterface):
    async def authenticate(self) -> bool:
        # Zerodha authentication logic
        pass
    
    async def place_order(self, order: BrokerOrder) -> str:
        # Zerodha order placement
        pass
```

2. **Register Broker**:
```python
BrokerRegistry.register(BrokerName.ZERODHA, ZerodhaBroker)
```

3. **Update Database Schema**:
```prisma
enum BrokerName {
  ANGEL_ONE
  ZERODHA  // Add new broker
  UPSTOX
}
```

## 🌐 Frontend Integration with Next.js + tRPC

### Option 1: FastAPI Only (Current Setup)
Keep using FastAPI for both backend and frontend API. Your current setup works perfectly.

### Option 2: Hybrid with Next.js + tRPC (Advanced)

**Next.js tRPC Client Setup:**
```typescript
// lib/trpc.ts
import { createTRPCNext } from '@trpc/next';
import { httpBatchLink } from '@trpc/client';

export const trpc = createTRPCNext<AppRouter>({
  config({ ctx }) {
    return {
      links: [
        httpBatchLink({
          url: '/api/trpc',
        }),
      ],
    };
  },
});
```

**tRPC Router calling FastAPI:**
```typescript
// pages/api/trpc/[trpc].ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';
import axios from 'axios';

const t = initTRPC.create();
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export const appRouter = t.router({
  // Get user positions
  getUserPositions: t.procedure
    .input(z.object({ userId: z.string(), brokerConfigId: z.string() }))
    .query(async ({ input }) => {
      const response = await axios.get(
        `${FASTAPI_URL}/api/v1/brokers/positions/${input.brokerConfigId}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      return response.data;
    }),

  // Place order
  placeOrder: t.procedure
    .input(z.object({
      brokerConfigId: z.string(),
      order: z.object({
        symbol: z.string(),
        side: z.enum(['BUY', 'SELL']),
        quantity: z.number(),
        orderType: z.enum(['MARKET', 'LIMIT']),
        price: z.number().optional(),
      })
    }))
    .mutation(async ({ input }) => {
      const response = await axios.post(
        `${FASTAPI_URL}/api/v1/brokers/orders/place`,
        input,
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      return response.data;
    }),

  // Get system status
  getSystemStatus: t.procedure
    .query(async () => {
      const response = await axios.get(
        `${FASTAPI_URL}/api/v1/brokers/admin/status`,
        { headers: { Authorization: `Bearer ${getAdminToken()}` } }
      );
      return response.data;
    }),
});

export type AppRouter = typeof appRouter;
```

**React Trading Dashboard:**
```tsx
// pages/dashboard.tsx
import { trpc } from '../lib/trpc';
import { useState } from 'react';

export default function TradingDashboard() {
  const [selectedBroker, setSelectedBroker] = useState('');
  
  // Get user positions with real-time updates
  const { data: positions, isLoading, refetch } = trpc.getUserPositions.useQuery(
    { userId: 'user123', brokerConfigId: selectedBroker },
    { 
      enabled: !!selectedBroker,
      refetchInterval: 5000 // Refresh every 5 seconds
    }
  );
  
  // Place order mutation
  const placeOrderMutation = trpc.placeOrder.useMutation({
    onSuccess: (data) => {
      alert(`✅ Order placed: ${data.data?.broker_order_id}`);
      refetch(); // Refresh positions
    },
    onError: (error) => {
      alert(`❌ Order failed: ${error.message}`);
    },
  });

  // System status
  const { data: systemStatus } = trpc.getSystemStatus.useQuery(undefined, {
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  const handlePlaceOrder = (symbol: string, side: 'BUY' | 'SELL') => {
    placeOrderMutation.mutate({
      brokerConfigId: selectedBroker,
      order: {
        symbol,
        side,
        quantity: 1,
        orderType: 'MARKET',
      }
    });
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Trading Dashboard</h1>
      
      {/* System Status */}
      {systemStatus && (
        <div className="mb-6 p-4 bg-gray-100 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">System Status</h2>
          <div className="grid grid-cols-4 gap-4">
            <div>Total Users: {systemStatus.total_users}</div>
            <div>Total Sessions: {systemStatus.total_sessions}</div>
            <div>Healthy: {systemStatus.healthy_sessions}</div>
            <div>Errors: {systemStatus.error_sessions}</div>
          </div>
        </div>
      )}
      
      {/* Broker Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">Select Broker Account</label>
        <select 
          value={selectedBroker} 
          onChange={(e) => setSelectedBroker(e.target.value)}
          className="w-full p-3 border rounded-lg"
        >
          <option value="">Choose a broker account...</option>
          <option value="config1">Angel One - Primary Account</option>
          <option value="config2">Angel One - Secondary Account</option>
        </select>
      </div>

      {/* Positions */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold mb-4">Current Positions</h2>
        {isLoading ? (
          <p>Loading positions...</p>
        ) : positions?.success ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {positions.data.positions.map((position: any, index: number) => (
              <div key={index} className="p-4 border rounded-lg bg-white shadow">
                <h3 className="font-bold text-lg">{position.symbol}</h3>
                <p>Quantity: {position.quantity}</p>
                <p>Avg Price: ₹{position.average_price?.toFixed(2)}</p>
                <p className={`font-semibold ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  P&L: ₹{position.pnl?.toFixed(2)}
                </p>
                <div className="mt-2 space-x-2">
                  <button
                    onClick={() => handlePlaceOrder(position.symbol, 'SELL')}
                    className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                    disabled={placeOrderMutation.isLoading}
                  >
                    Sell
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No positions found or failed to load</p>
        )}
      </div>

      {/* Quick Orders */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold mb-4">Quick Orders</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {['TCS', 'RELIANCE', 'INFY', 'HDFCBANK'].map((symbol) => (
            <div key={symbol} className="p-4 border rounded-lg">
              <h3 className="font-semibold mb-2">{symbol}</h3>
              <div className="space-y-2">
                <button
                  onClick={() => handlePlaceOrder(symbol, 'BUY')}
                  disabled={!selectedBroker || placeOrderMutation.isLoading}
                  className="w-full px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                >
                  Buy 1
                </button>
                <button
                  onClick={() => handlePlaceOrder(symbol, 'SELL')}
                  disabled={!selectedBroker || placeOrderMutation.isLoading}
                  className="w-full px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                >
                  Sell 1
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loading indicator */}
      {placeOrderMutation.isLoading && (
        <div className="fixed bottom-4 right-4 p-4 bg-blue-500 text-white rounded-lg">
          Placing order...
        </div>
      )}
    </div>
  );
}
```

## 🔒 Comprehensive Error Handling

### Error Types and Handling

```python
from app.core.multi_user_broker_manager import place_order_for_user, BrokerOperationResult

async def handle_trading_operation():
    """Comprehensive error handling example"""
    
    result = await place_order_for_user(user_id, config_id, order)
    
    if not result.success:
        print(f"❌ Operation failed: {result.message}")
        print(f"🔍 Error Code: {result.error_code}")
        print(f"⏱️ Execution Time: {result.execution_time:.2f}s")
        
        # Handle specific error types
        if result.error_code == "INSUFFICIENT_FUNDS":
            print("💰 Solution: Add funds to your account")
            # Get current balance
            balance_result = await get_balance_for_user(user_id, config_id)
            if balance_result.success:
                balance = balance_result.data
                print(f"   Available: ₹{balance['available_cash']:,.2f}")
                print(f"   Required: ₹{order.quantity * order.price:,.2f}")
                
        elif result.error_code == "AUTH_ERROR":
            print("🔐 Solution: Check broker credentials and TOTP")
            # Try to re-add the broker
            retry_result = await add_user_broker(user_id, config_id)
            if retry_result.success:
                print("✅ Broker re-authenticated successfully")
            else:
                print("❌ Re-authentication failed, check credentials")
                
        elif result.error_code == "INVALID_ORDER":
            print("📋 Solution: Check order parameters")
            print(f"   Symbol: {order.symbol}")
            print(f"   Quantity: {order.quantity}")
            print(f"   Price: {order.price}")
            print("   Ensure symbol exists and parameters are valid")
            
        elif result.error_code == "SESSION_NOT_FOUND":
            print("🔄 Solution: Session expired, recreating...")
            # Remove old session and create new one
            await remove_user_broker(user_id, config_id)
            new_result = await add_user_broker(user_id, config_id)
            if new_result.success:
                print("✅ New session created, retry the operation")
            
        elif result.error_code == "CONFIG_NOT_FOUND":
            print("⚙️ Solution: Broker configuration missing")
            print("   Run: python setup_broker_config.py")
            
        elif result.error_code == "SYSTEM_ERROR":
            print("🛠️ Solution: System error, check logs")
            print("   Check system status and retry")
            
    else:
        print(f"✅ Operation successful!")
        print(f"📊 Data: {result.data}")
        print(f"⏱️ Execution Time: {result.execution_time:.2f}s")

# Error recovery example
async def robust_order_placement(user_id: str, config_id: str, order: BrokerOrder, max_retries: int = 3):
    """Robust order placement with automatic retry"""
    
    for attempt in range(max_retries):
        try:
            result = await place_order_for_user(user_id, config_id, order)
            
            if result.success:
                return result
                
            # Handle retryable errors
            if result.error_code in ["SESSION_NOT_FOUND", "AUTH_ERROR"]:
                print(f"⚠️ Attempt {attempt + 1}/{max_retries}: {result.message}")
                if attempt < max_retries - 1:
                    # Wait and retry
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            else:
                # Non-retryable error
                return result
                
        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: System error: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise
    
    # All retries exhausted
    return BrokerOperationResult(
        success=False,
        message="Max retries exhausted",
        user_id=user_id,
        broker_name="unknown",
        config_id=config_id,
        error_code="MAX_RETRIES_EXHAUSTED"
    )
```

### System Health Monitoring

```python
async def monitor_system_health():
    """Comprehensive system health monitoring"""
    
    try:
        status = await multi_user_broker_manager.get_system_status()
        
        # Overall health check
        total_sessions = status['total_sessions']
        healthy_sessions = status['healthy_sessions']
        error_sessions = status['error_sessions']
        
        health_percentage = (healthy_sessions / total_sessions * 100) if total_sessions > 0 else 100
        
        print(f"🏥 System Health: {health_percentage:.1f}%")
        
        if health_percentage < 80:
            print("⚠️ System health degraded!")
            
            # Investigate unhealthy sessions
            for user_id in status.get('users', []):
                sessions = await multi_user_broker_manager.get_user_brokers(user_id)
                for session in sessions:
                    if session.health_status != 'healthy':
                        print(f"🔧 Fixing unhealthy session: {session.session_id}")
                        
                        # Try to recreate session
                        await remove_user_broker(user_id, session.config_id)
                        result = await add_user_broker(user_id, session.config_id)
                        
                        if result.success:
                            print(f"✅ Session {session.session_id} fixed")
                        else:
                            print(f"❌ Failed to fix session: {result.message}")
        
        # Resource monitoring
        print(f"📊 Resource Usage:")
        print(f"   Active Background Tasks: {status['background_tasks']}")
        print(f"   Total Memory Sessions: {total_sessions}")
        
        # Broker-specific health
        for broker_name, broker_stats in status['by_broker'].items():
            broker_health = (broker_stats['healthy'] / broker_stats['total'] * 100) if broker_stats['total'] > 0 else 100
            print(f"   {broker_name}: {broker_health:.1f}% healthy ({broker_stats['healthy']}/{broker_stats['total']})")
            
    except Exception as e:
        print(f"❌ Health monitoring failed: {e}")
```

## 🧪 Complete Testing Examples

### Basic System Test
```python
# Test the entire system
python quick_test.py
```

### Advanced Testing
```python
async def comprehensive_system_test():
    """Complete system test with all features"""
    
    print("🧪 Starting Comprehensive System Test")
    print("=" * 50)
    
    # Test 1: Initialize system
    print("\n1️⃣ Testing System Initialization")
    success = await multi_user_broker_manager.initialize()
    assert success, "System initialization failed"
    print("✅ System initialized")
    
    # Test 2: Add multiple users
    print("\n2️⃣ Testing Multi-User Setup")
    test_users = [
        ("test_user_1", "test_config_1"),
        ("test_user_2", "test_config_2")
    ]
    
    for user_id, config_id in test_users:
        result = await add_user_broker(user_id, config_id)
        if result.success:
            print(f"✅ Added {user_id}")
        else:
            print(f"⚠️ Failed to add {user_id}: {result.message}")
    
    # Test 3: Parallel operations
    print("\n3️⃣ Testing Parallel Operations")
    balance_tasks = [get_balance_for_user(user_id, config_id) for user_id, config_id in test_users]
    balance_results = await asyncio.gather(*balance_tasks, return_exceptions=True)
    
    for i, result in enumerate(balance_results):
        if isinstance(result, BrokerOperationResult) and result.success:
            print(f"✅ User {i+1} balance retrieved")
        else:
            print(f"⚠️ User {i+1} balance failed: {result}")
    
    # Test 4: System health
    print("\n4️⃣ Testing System Health")
    status = await multi_user_broker_manager.get_system_status()
    print(f"📊 Status: {status['healthy_sessions']}/{status['total_sessions']} healthy")
    
    # Test 5: Cleanup
    print("\n5️⃣ Testing Cleanup")
    for user_id, config_id in test_users:
        result = await remove_user_broker(user_id, config_id)
        if result.success:
            print(f"✅ Removed {user_id}")
    
    await multi_user_broker_manager.shutdown()
    print("✅ System shutdown complete")
    
    print("\n🎉 All tests completed!")

# Run the test
asyncio.run(comprehensive_system_test())
```

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🚀 Getting Started

Ready to start? Follow the [Quick Start](#-quick-start) guide above and explore all the examples provided!

**This single documentation contains everything you need:**
- ✅ Complete setup instructions
- ✅ Multi-user broker management examples  
- ✅ Trading operations with real code
- ✅ Frontend integration (Next.js + tRPC)
- ✅ Comprehensive error handling
- ✅ System monitoring examples
- ✅ Production deployment guide
- ✅ Testing examples

For questions or support, please check the examples above or raise an issue. Happy trading! 🎉 