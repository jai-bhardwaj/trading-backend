# Trading Engine Architecture & Flow Documentation

## Overview

This is a high-performance, industrial-grade trading backend system built with Python, designed for real-time algorithmic trading across multiple asset classes. The system uses a microservices architecture with Redis-based queue processing, PostgreSQL for data persistence, and supports multiple broker integrations.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Engine System                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Web API   │  │  Strategy   │  │   Market    │             │
│  │ Management  │  │  Executor   │  │ Data Feed   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Redis     │  │ PostgreSQL  │  │   Broker    │             │
│  │   Queue     │  │  Database   │  │ Integration │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Queue System**: Redis with custom priority queues
- **Broker Integration**: Angel One SmartAPI (extensible to other brokers)
- **Process Management**: PM2 with ecosystem configuration
- **Monitoring**: Custom health checks and performance metrics

## Directory Structure

```
trading-backend/
├── app/                          # Main application package
│   ├── api/                      # API endpoints and management
│   ├── brokers/                  # Broker integrations
│   ├── core/                     # Core business logic
│   ├── engine/                   # Trading engine implementation
│   ├── models/                   # Database models
│   ├── queue/                    # Redis queue management
│   ├── services/                 # Business services
│   ├── strategies/               # Trading strategies
│   └── monitoring/               # Health checks and monitoring
├── config/                       # Configuration files
├── scripts/                      # Utility and management scripts
├── logs/                         # Application logs
└── data/                         # Data files and instruments
```

## Core Architecture Components

### 1. Trading Engine (`app/engine/redis_engine.py`)

The heart of the system is the `RedisBasedTradingEngine` which provides:

- **Real-time Order Processing**: No polling delays, immediate order execution
- **Horizontal Scalability**: Multiple workers for parallel processing
- **Priority-based Routing**: Critical orders get priority processing
- **Fault Tolerance**: Circuit breaker pattern with automatic retry
- **Performance Monitoring**: Comprehensive metrics and health checks

**Key Features:**
- Worker-based architecture with configurable worker count
- Priority queue for urgent orders (stop-loss, market orders)
- Background tasks for strategy execution and monitoring
- Graceful shutdown with proper cleanup

### 2. Queue Management System (`app/queue/`)

#### Queue Manager (`queue_manager.py`)
- Coordinates multiple Redis queues and workers
- Load balancing across workers
- Queue rebalancing and health monitoring
- Retry processing for failed orders

#### Order Queue (`order_queue.py`)
- Standard order processing queue
- FIFO processing with retry mechanisms
- Worker assignment and load distribution

#### Priority Queue (`priority_queue.py`)
- High-priority order processing
- Urgency-based routing (NORMAL, HIGH, CRITICAL, STOP_LOSS)
- Deadline-based processing for time-sensitive orders

### 3. Strategy System (`app/strategies/`)

#### Base Strategy (`base_strategy.py`)
- Abstract base class for all trading strategies
- Standardized interface for signal generation
- Position and order management
- Performance tracking and metrics
- Risk management integration

#### Strategy Manager (`manager.py`)
- Strategy lifecycle management
- Concurrent strategy execution
- Resource allocation and monitoring
- Strategy registry and discovery

#### Strategy Registry (`registry.py`)
- Dynamic strategy loading and registration
- Strategy metadata management
- Version control and deployment

### 4. Broker Integration (`app/brokers/`)

#### Base Broker Interface (`base.py`)
- Standardized broker interface
- Common data structures (BrokerOrder, BrokerPosition, etc.)
- Error handling and exception mapping
- Authentication and session management

#### Angel One Integration (`angelone_new.py`)
- SmartAPI integration with TOTP authentication
- Order placement, modification, and cancellation
- Position and balance retrieval
- Market data access
- Symbol search and mapping

#### Mapping Utils (`mapping_utils.py`)
- Data transformation between internal and broker formats
- Symbol token resolution
- Order status mapping
- Error code translation

### 5. Core Services (`app/core/`)

#### Instrument Manager (`instrument_manager.py`)
- Symbol and instrument data management
- Exchange mapping and validation
- Real-time instrument updates
- Strategy symbol allocation

#### Order Executor (`order_executor.py`)
- Order validation and preprocessing
- Broker routing and execution
- Order status tracking
- Execution reporting

#### Risk Manager (`risk_manager.py`)
- Real-time risk monitoring
- Position size validation
- Daily/weekly loss limits
- Exposure management

#### Notification Service (`notification_service.py`)
- Multi-channel notifications (email, SMS, webhook)
- Event-driven alerts
- Risk violation notifications
- System status updates

### 6. Database Layer (`app/models/base.py`)

#### Core Models:
- **User**: User management with roles and authentication
- **Strategy**: Strategy configuration and metadata
- **Order**: Order lifecycle and execution tracking
- **Trade**: Trade execution records
- **Position**: Current position tracking
- **Balance**: Account balance and margin tracking
- **BrokerConfig**: Broker authentication and settings
- **RiskProfile**: User-specific risk parameters

#### Features:
- PostgreSQL with SQLAlchemy ORM
- Async database operations
- Connection pooling and optimization
- Audit logging and compliance

## System Flow

### 1. Application Startup Flow

```
1. Load Configuration (environment variables, settings)
2. Initialize Database Connection Pool
3. Setup Redis Connection and Queue System
4. Initialize Instrument Manager (fetch symbols)
5. Load Active Strategies from Database
6. Start Redis Trading Engine
7. Launch Background Tasks:
   - Strategy Executor
   - Market Data Feed
   - Performance Monitor
   - Health Checker
8. Setup Signal Handlers for Graceful Shutdown
```

### 2. Strategy Execution Flow

```
Strategy Timer Trigger
        ↓
Load Strategy Configuration
        ↓
Fetch Market Data (Redis/Database)
        ↓
Execute Strategy Logic
        ↓
Generate Trading Signals
        ↓
Create Orders in Database
        ↓
Submit Orders to Redis Queue
        ↓
Queue Manager Routes to Workers
        ↓
Worker Processes Order
        ↓
Execute via Broker API
        ↓
Update Order Status
        ↓
Update Positions & Portfolio
        ↓
Send Notifications
```

### 3. Order Processing Flow

```
Order Creation (Strategy/Manual)
        ↓
Validate Order Parameters
        ↓
Risk Management Checks
        ↓
Save to Database (PENDING status)
        ↓
Submit to Redis Queue
        ↓
Queue Manager Assignment:
   ├── Priority Queue (urgent orders)
   └── Standard Queue (normal orders)
        ↓
Worker Picks Up Order
        ↓
Authenticate with Broker
        ↓
Place Order via Broker API
        ↓
Update Order Status (PLACED/REJECTED)
        ↓
Monitor Order Execution
        ↓
Update Final Status (COMPLETE/CANCELLED)
        ↓
Update Positions and Balance
        ↓
Generate Trade Records
        ↓
Send Execution Notifications
```

### 4. Market Data Flow

```
Market Data Sources
        ↓
Data Normalization
        ↓
Store in Redis (real-time)
        ↓
Store in PostgreSQL (historical)
        ↓
Notify Subscribed Strategies
        ↓
Trigger Strategy Evaluation
        ↓
Generate Signals if Conditions Met
```

### 5. Risk Management Flow

```
Order/Position Change Event
        ↓
Calculate Current Exposure
        ↓
Check Against Risk Limits:
   ├── Daily Loss Limit
   ├── Position Size Limit
   ├── Exposure per Symbol
   └── Maximum Orders per Minute
        ↓
Risk Violation Detected?
   ├── Yes: Block Order/Close Positions
   └── No: Allow Execution
        ↓
Log Risk Events
        ↓
Send Risk Notifications
```

## Configuration Management

### Environment Variables
- Database connection strings
- Redis configuration
- Broker API credentials
- Risk management parameters
- Logging configuration

### Settings (`app/core/config.py`)
- Centralized configuration with Pydantic validation
- Environment-specific settings
- Runtime parameter validation
- Secure credential management

## Deployment Architecture

### Production Setup
- **Process Manager**: PM2 with ecosystem configuration
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis cluster for high availability
- **Monitoring**: Health checks and performance metrics
- **Logging**: Structured logging with rotation
- **Security**: Environment-based credential management

### Scaling Considerations
- Horizontal scaling via worker count adjustment
- Redis cluster for queue distribution
- Database read replicas for analytics
- Load balancing for API endpoints

## Security Features

- **Authentication**: JWT-based with 2FA support
- **Authorization**: Role-based access control
- **API Security**: Rate limiting and input validation
- **Data Protection**: Encrypted sensitive data storage
- **Audit Logging**: Comprehensive activity tracking

## Monitoring & Observability

### Health Checks
- Database connectivity
- Redis queue health
- Broker API status
- Worker performance
- Memory and CPU usage

### Performance Metrics
- Order processing latency
- Strategy execution time
- Queue depth and throughput
- Error rates and types
- System resource utilization

### Alerting
- System failures and errors
- Risk limit violations
- Performance degradation
- Broker connectivity issues

## Development Workflow

### Local Development
1. Setup virtual environment
2. Install dependencies from `requirements.txt`
3. Configure environment variables
4. Run database migrations
5. Start Redis server
6. Run application with `python main.py`

### Production Deployment
1. Environment setup and validation
2. Database migration and seeding
3. PM2 process deployment
4. Health check validation
5. Monitoring setup
6. Gradual traffic routing

## API Integration

### Strategy Management API (`app/api/strategy_management.py`)
- Create, update, delete strategies
- Start/stop strategy execution
- Performance monitoring
- Risk parameter management

### Broker Integration Points
- Order placement and management
- Position and balance queries
- Market data access
- Symbol search and validation

## Future Enhancements

### Planned Features
- Multi-broker support (Zerodha, Upstox, etc.)
- Advanced strategy backtesting
- Machine learning integration
- Real-time dashboard
- Mobile application support

### Scalability Improvements
- Microservices decomposition
- Event-driven architecture
- Cloud-native deployment
- Advanced caching strategies

## Troubleshooting Guide

### Common Issues
- Redis connection failures
- Database connection pool exhaustion
- Broker API rate limiting
- Strategy execution errors
- Queue processing delays

### Debugging Tools
- Comprehensive logging system
- Health check endpoints
- Performance monitoring
- Error tracking and alerting
- Database query optimization

---

This architecture provides a robust, scalable, and maintainable foundation for algorithmic trading operations with proper separation of concerns, fault tolerance, and comprehensive monitoring capabilities. 