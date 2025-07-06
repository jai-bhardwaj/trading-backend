# Database Storage Requirements Summary

## What You Need to Store in Your Database

Based on your trading system architecture, here's exactly what data you need to store and where:

## 1. **User Data** (Table: `users`)

**What to store:**

- User profile information (name, email, API key)
- **User-specific broker credentials** (Angel One API key, secret, token)
- Trading capital and risk preferences
- Account status and login history

**Why this matters:**

- Each user has their own broker account credentials
- Secure storage of sensitive trading credentials
- User-specific trading parameters

## 2. **Order Data** (Table: `orders`)

**What to store:**

- All trading orders (BUY/SELL)
- Order details (symbol, quantity, price, type)
- Order status and execution results
- Broker order IDs and error messages
- Strategy that generated the order (if applicable)

**Why this matters:**

- Complete audit trail of all trading activity
- Order execution tracking
- Performance analysis
- Compliance and reporting

## 3. **Strategy Data** (Tables: `strategies` + `user_strategies`)

**What to store:**

- Available trading strategies (RSI, Momentum, etc.)
- Strategy parameters and configurations
- Which strategies each user has activated
- Strategy performance metrics
- User-specific strategy settings

**Why this matters:**

- Strategy marketplace functionality
- User strategy preferences
- Performance tracking per strategy
- Risk management per strategy

## 4. **Position Data** (Table: `positions`)

**What to store:**

- Current open positions
- Historical closed positions
- Position details (symbol, quantity, entry price)
- Unrealized and realized P&L
- Position opening/closing orders

**Why this matters:**

- Real-time portfolio tracking
- P&L calculation and reporting
- Risk management
- Performance analysis

## 5. **Notification Data** (Table: `notifications`)

**What to store:**

- System alerts and notifications
- Order status updates
- Service health notifications
- Risk management alerts
- Strategy signal notifications

**Why this matters:**

- User communication
- System monitoring
- Alert management
- Audit trail

## 6. **Trading Session Data** (Table: `trading_sessions`)

**What to store:**

- User trading sessions
- Session performance metrics
- Capital changes during sessions
- Order counts and success rates

**Why this matters:**

- Performance tracking
- Session analysis
- Risk management
- User behavior analysis

## 7. **Risk Management Data** (Table: `risk_rules`)

**What to store:**

- User-specific risk rules
- Risk thresholds and limits
- Rule violations and alerts
- Risk monitoring data

**Why this matters:**

- Capital protection
- Risk control
- Compliance requirements
- Automated risk management

## Data Storage Strategy

### **Real-time Data (Redis)**

- Market data cache
- Active order status
- User sessions
- Real-time notifications

### **Persistent Data (PostgreSQL)**

- User profiles and credentials
- Order history
- Position history
- Strategy configurations
- Risk management rules
- Trading session history

## Key Data Relationships

### **User-Centric Design**

```
User → Orders → Positions
User → Strategies → Orders
User → Risk Rules → Alerts
User → Trading Sessions → Performance
```

### **Order Flow**

```
Strategy → Order → Position → P&L
Market Data → Strategy → Signal → Order
```

## Critical Data Points

### **Must Store:**

1. **User broker credentials** - For secure trading
2. **All orders** - For audit trail and compliance
3. **All positions** - For portfolio tracking
4. **Strategy configurations** - For strategy management
5. **Risk rules** - For capital protection

### **Should Store:**

1. **Trading sessions** - For performance analysis
2. **Notifications** - For user communication
3. **Market data history** - For backtesting

### **Optional Storage:**

1. **Real-time market data** - Can be cached in Redis
2. **Temporary order status** - Can be in Redis
3. **User sessions** - Can be in Redis

## Database Schema Summary

| Table              | Purpose                     | Critical Data         |
| ------------------ | --------------------------- | --------------------- |
| `users`            | User profiles & credentials | ✅ Broker credentials |
| `orders`           | Order history               | ✅ All orders         |
| `strategies`       | Available strategies        | ✅ Strategy configs   |
| `user_strategies`  | User strategy activations   | ✅ User preferences   |
| `positions`        | Position tracking           | ✅ All positions      |
| `notifications`    | System alerts               | ⚠️ Important          |
| `trading_sessions` | Performance tracking        | ⚠️ Important          |
| `risk_rules`       | Risk management             | ✅ Risk rules         |

## Implementation Priority

### **Phase 1 (Critical)**

1. Users table - Store user credentials
2. Orders table - Track all orders
3. Strategies table - Manage strategies

### **Phase 2 (Important)**

1. Positions table - Track positions
2. User strategies table - User strategy activations
3. Risk rules table - Risk management

### **Phase 3 (Enhancement)**

1. Notifications table - User alerts
2. Trading sessions table - Performance tracking

## Data Security Considerations

### **Encrypt:**

- Broker API keys
- Broker secrets
- User tokens

### **Index:**

- User ID lookups
- Order status queries
- Position symbol searches

### **Backup:**

- All critical tables
- User credentials
- Order history

## Performance Considerations

### **High-Volume Tables:**

- Orders (potentially millions of records)
- Positions (thousands per user)
- Market data (real-time updates)

### **Optimization:**

- Partition orders by date
- Index frequently queried fields
- Cache hot data in Redis
- Use read replicas for reporting

## Next Steps

1. **Create the database schema** using the provided SQLAlchemy models
2. **Run Alembic migrations** to create all tables
3. **Update your services** to use the database instead of Redis for persistent data
4. **Test the data flow** from order creation to position tracking
5. **Implement data backup** and recovery procedures

This database schema will support all your trading system requirements while maintaining data integrity, security, and performance.
