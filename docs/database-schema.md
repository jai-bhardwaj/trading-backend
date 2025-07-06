# Database Schema Documentation

## Overview

The Pinnacle Trading System uses a PostgreSQL database to store all trading-related data. The schema is designed to support:

- User management and authentication
- Order management and execution
- Strategy management and execution
- Position tracking
- Risk management
- Notifications and alerts
- Trading sessions and performance tracking

## Database Tables

### 1. Users Table

**Purpose**: Store user profiles and broker credentials

**Table Name**: `users`

| Field            | Type          | Constraints       | Description                |
| ---------------- | ------------- | ----------------- | -------------------------- |
| `user_id`        | VARCHAR(50)   | PRIMARY KEY       | Unique user identifier     |
| `name`           | VARCHAR(100)  | NOT NULL          | User's full name           |
| `email`          | VARCHAR(100)  | UNIQUE, NOT NULL  | User's email address       |
| `api_key`        | VARCHAR(64)   | UNIQUE, NOT NULL  | API key for authentication |
| `broker_api_key` | VARCHAR(100)  | DEFAULT ''        | User's Angel One API key   |
| `broker_secret`  | VARCHAR(100)  | DEFAULT ''        | User's Angel One secret    |
| `broker_token`   | VARCHAR(100)  | DEFAULT ''        | User's Angel One token     |
| `total_capital`  | DECIMAL(15,2) | DEFAULT 100000.00 | User's total capital       |
| `risk_tolerance` | VARCHAR(20)   | DEFAULT 'medium'  | Risk tolerance level       |
| `enabled`        | BOOLEAN       | DEFAULT true      | Account status             |
| `created_at`     | TIMESTAMP     | DEFAULT NOW()     | Account creation time      |
| `last_login`     | TIMESTAMP     | NULL              | Last login timestamp       |

**Key Features**:

- Stores user-specific broker credentials for secure trading
- Tracks user capital and risk preferences
- Supports account enable/disable functionality

### 2. Orders Table

**Purpose**: Store all trading orders

**Table Name**: `orders`

| Field             | Type         | Constraints     | Description                     |
| ----------------- | ------------ | --------------- | ------------------------------- |
| `order_id`        | VARCHAR(50)  | PRIMARY KEY     | Unique order identifier         |
| `user_id`         | VARCHAR(50)  | FOREIGN KEY     | Reference to users table        |
| `strategy_id`     | VARCHAR(50)  | NULL            | Strategy that generated order   |
| `symbol`          | VARCHAR(20)  | NOT NULL        | Trading symbol (e.g., RELIANCE) |
| `side`            | ENUM         | NOT NULL        | BUY/SELL                        |
| `order_type`      | ENUM         | NOT NULL        | MARKET/LIMIT/STOP_LOSS          |
| `quantity`        | INTEGER      | NOT NULL        | Number of shares                |
| `price`           | FLOAT        | NOT NULL        | Order price                     |
| `filled_quantity` | INTEGER      | DEFAULT 0       | Actually filled quantity        |
| `filled_price`    | FLOAT        | DEFAULT 0.0     | Average fill price              |
| `status`          | ENUM         | DEFAULT PENDING | Order status                    |
| `broker_order_id` | VARCHAR(100) | DEFAULT ''      | External broker order ID        |
| `error_message`   | TEXT         | DEFAULT ''      | Error details if failed         |
| `retry_count`     | INTEGER      | DEFAULT 0       | Number of retry attempts        |
| `created_at`      | TIMESTAMP    | DEFAULT NOW()   | Order creation time             |
| `updated_at`      | TIMESTAMP    | DEFAULT NOW()   | Last update time                |

**Order Status Values**:

- `PENDING`: Order created, not yet sent to broker
- `PLACED`: Order sent to broker, waiting for response
- `FILLED`: Order completely filled
- `PARTIALLY_FILLED`: Order partially filled
- `REJECTED`: Order rejected by broker
- `CANCELLED`: Order cancelled by user

### 3. Strategies Table

**Purpose**: Store available trading strategies

**Table Name**: `strategies`

| Field                    | Type         | Constraints   | Description                  |
| ------------------------ | ------------ | ------------- | ---------------------------- |
| `strategy_id`            | VARCHAR(50)  | PRIMARY KEY   | Unique strategy identifier   |
| `name`                   | VARCHAR(100) | NOT NULL      | Strategy name                |
| `description`            | TEXT         | NOT NULL      | Strategy description         |
| `category`               | VARCHAR(50)  | NOT NULL      | Strategy category            |
| `risk_level`             | VARCHAR(20)  | NOT NULL      | Risk level (Low/Medium/High) |
| `min_capital`            | FLOAT        | NOT NULL      | Minimum capital required     |
| `expected_return_annual` | FLOAT        | NOT NULL      | Expected annual return %     |
| `max_drawdown`           | FLOAT        | NOT NULL      | Maximum expected drawdown %  |
| `symbols`                | JSON         | NOT NULL      | Array of trading symbols     |
| `parameters`             | JSON         | NOT NULL      | Strategy parameters          |
| `is_active`              | BOOLEAN      | DEFAULT true  | Strategy availability        |
| `created_at`             | TIMESTAMP    | DEFAULT NOW() | Creation time                |

**Example Strategy Data**:

```json
{
  "strategy_id": "rsi_dmi",
  "name": "RSI DMI Strategy",
  "symbols": ["RELIANCE", "TCS", "INFY"],
  "parameters": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  }
}
```

### 4. User Strategies Table

**Purpose**: Track which strategies each user has activated

**Table Name**: `user_strategies`

| Field               | Type        | Constraints              | Description             |
| ------------------- | ----------- | ------------------------ | ----------------------- |
| `user_id`           | VARCHAR(50) | PRIMARY KEY, FOREIGN KEY | User reference          |
| `strategy_id`       | VARCHAR(50) | PRIMARY KEY, FOREIGN KEY | Strategy reference      |
| `status`            | ENUM        | DEFAULT ACTIVE           | Strategy status         |
| `activated_at`      | TIMESTAMP   | DEFAULT NOW()            | Activation time         |
| `deactivated_at`    | TIMESTAMP   | NULL                     | Deactivation time       |
| `allocation_amount` | FLOAT       | DEFAULT 0.0              | Capital allocated       |
| `custom_parameters` | JSON        | DEFAULT {}               | User's custom settings  |
| `total_orders`      | INTEGER     | DEFAULT 0                | Total orders generated  |
| `successful_orders` | INTEGER     | DEFAULT 0                | Successful orders       |
| `total_pnl`         | FLOAT       | DEFAULT 0.0              | Total P&L from strategy |
| `created_at`        | TIMESTAMP   | DEFAULT NOW()            | Creation time           |
| `updated_at`        | TIMESTAMP   | DEFAULT NOW()            | Last update time        |

**Strategy Status Values**:

- `ACTIVE`: Strategy is running
- `PAUSED`: Strategy temporarily paused
- `STOPPED`: Strategy stopped permanently

### 5. Positions Table

**Purpose**: Track current and historical positions

**Table Name**: `positions`

| Field            | Type        | Constraints   | Description                |
| ---------------- | ----------- | ------------- | -------------------------- |
| `position_id`    | VARCHAR(50) | PRIMARY KEY   | Unique position identifier |
| `user_id`        | VARCHAR(50) | FOREIGN KEY   | User reference             |
| `symbol`         | VARCHAR(20) | NOT NULL      | Trading symbol             |
| `side`           | ENUM        | NOT NULL      | LONG/SHORT                 |
| `quantity`       | INTEGER     | NOT NULL      | Position size              |
| `average_price`  | FLOAT       | NOT NULL      | Average entry price        |
| `current_price`  | FLOAT       | NOT NULL      | Current market price       |
| `unrealized_pnl` | FLOAT       | DEFAULT 0.0   | Unrealized profit/loss     |
| `realized_pnl`   | FLOAT       | DEFAULT 0.0   | Realized profit/loss       |
| `strategy_id`    | VARCHAR(50) | NULL          | Strategy reference         |
| `order_id`       | VARCHAR(50) | FOREIGN KEY   | Opening order reference    |
| `status`         | ENUM        | DEFAULT OPEN  | Position status            |
| `opened_at`      | TIMESTAMP   | DEFAULT NOW() | Position opening time      |
| `closed_at`      | TIMESTAMP   | NULL          | Position closing time      |
| `created_at`     | TIMESTAMP   | DEFAULT NOW() | Creation time              |
| `updated_at`     | TIMESTAMP   | DEFAULT NOW() | Last update time           |

**Position Status Values**:

- `OPEN`: Position is currently open
- `CLOSED`: Position has been closed

### 6. Notifications Table

**Purpose**: Store system notifications and alerts

**Table Name**: `notifications`

| Field               | Type         | Constraints       | Description                           |
| ------------------- | ------------ | ----------------- | ------------------------------------- |
| `notification_id`   | VARCHAR(50)  | PRIMARY KEY       | Unique notification ID                |
| `user_id`           | VARCHAR(50)  | FOREIGN KEY, NULL | User reference (NULL for system-wide) |
| `notification_type` | ENUM         | NOT NULL          | Type of notification                  |
| `alert_level`       | ENUM         | DEFAULT INFO      | Alert severity                        |
| `title`             | VARCHAR(200) | NOT NULL          | Notification title                    |
| `message`           | TEXT         | NOT NULL          | Notification message                  |
| `data`              | JSON         | DEFAULT {}        | Additional data                       |
| `read_at`           | TIMESTAMP    | NULL              | When user read notification           |
| `created_at`        | TIMESTAMP    | DEFAULT NOW()     | Creation time                         |

**Notification Types**:

- `ORDER_FILLED`: Order successfully filled
- `ORDER_REJECTED`: Order rejected by broker
- `SERVICE_DOWN`: Service unavailable
- `SERVICE_RESTORED`: Service restored
- `SYSTEM_ERROR`: System error occurred
- `STRATEGY_SIGNAL`: Strategy generated signal
- `RISK_ALERT`: Risk management alert

**Alert Levels**:

- `INFO`: Informational message
- `WARNING`: Warning message
- `ERROR`: Error message
- `CRITICAL`: Critical alert

### 7. Trading Sessions Table

**Purpose**: Track user trading sessions and performance

**Table Name**: `trading_sessions`

| Field               | Type        | Constraints    | Description             |
| ------------------- | ----------- | -------------- | ----------------------- |
| `session_id`        | VARCHAR(50) | PRIMARY KEY    | Unique session ID       |
| `user_id`           | VARCHAR(50) | FOREIGN KEY    | User reference          |
| `start_time`        | TIMESTAMP   | DEFAULT NOW()  | Session start time      |
| `end_time`          | TIMESTAMP   | NULL           | Session end time        |
| `total_orders`      | INTEGER     | DEFAULT 0      | Total orders in session |
| `successful_orders` | INTEGER     | DEFAULT 0      | Successful orders       |
| `total_pnl`         | FLOAT       | DEFAULT 0.0    | Total P&L for session   |
| `max_drawdown`      | FLOAT       | DEFAULT 0.0    | Maximum drawdown        |
| `capital_at_start`  | FLOAT       | NOT NULL       | Starting capital        |
| `capital_at_end`    | FLOAT       | NULL           | Ending capital          |
| `status`            | ENUM        | DEFAULT ACTIVE | Session status          |
| `created_at`        | TIMESTAMP   | DEFAULT NOW()  | Creation time           |
| `updated_at`        | TIMESTAMP   | DEFAULT NOW()  | Last update time        |

**Session Status Values**:

- `ACTIVE`: Session is currently active
- `COMPLETED`: Session has ended

### 8. Risk Management Table

**Purpose**: Store risk management rules and violations

**Table Name**: `risk_rules`

| Field               | Type        | Constraints   | Description            |
| ------------------- | ----------- | ------------- | ---------------------- |
| `rule_id`           | VARCHAR(50) | PRIMARY KEY   | Unique rule identifier |
| `user_id`           | VARCHAR(50) | FOREIGN KEY   | User reference         |
| `rule_type`         | ENUM        | NOT NULL      | Type of risk rule      |
| `rule_value`        | FLOAT       | NOT NULL      | Rule threshold value   |
| `current_value`     | FLOAT       | DEFAULT 0.0   | Current actual value   |
| `is_violated`       | BOOLEAN     | DEFAULT false | Rule violation status  |
| `violation_message` | TEXT        | DEFAULT ''    | Violation details      |
| `created_at`        | TIMESTAMP   | DEFAULT NOW() | Creation time          |
| `updated_at`        | TIMESTAMP   | DEFAULT NOW() | Last update time       |

**Rule Types**:

- `MAX_POSITION_SIZE`: Maximum position size allowed
- `MAX_DRAWDOWN`: Maximum drawdown percentage
- `MAX_DAILY_LOSS`: Maximum daily loss amount
- `MAX_ORDERS_PER_DAY`: Maximum orders per day
- `MIN_CAPITAL_THRESHOLD`: Minimum capital threshold

## Database Relationships

### One-to-Many Relationships

1. **User → Orders**: One user can have many orders
2. **User → Positions**: One user can have many positions
3. **User → Notifications**: One user can have many notifications
4. **User → Trading Sessions**: One user can have many trading sessions
5. **User → Risk Rules**: One user can have many risk rules

### Many-to-Many Relationships

1. **User ↔ Strategy**: Through `user_strategies` table
   - One user can activate multiple strategies
   - One strategy can be activated by multiple users

### Foreign Key Constraints

- `orders.user_id` → `users.user_id`
- `orders.order_id` → `positions.order_id` (for opening orders)
- `user_strategies.user_id` → `users.user_id`
- `user_strategies.strategy_id` → `strategies.strategy_id`
- `positions.user_id` → `users.user_id`
- `notifications.user_id` → `users.user_id`
- `trading_sessions.user_id` → `users.user_id`
- `risk_rules.user_id` → `users.user_id`

## Data Storage Strategy

### Real-time Data (Redis)

- Market data cache
- Active order status
- User sessions
- Real-time notifications

### Persistent Data (PostgreSQL)

- User profiles and credentials
- Order history
- Position history
- Strategy configurations
- Risk management rules
- Trading session history

## Indexes

### Primary Indexes

- All primary keys are automatically indexed

### Recommended Secondary Indexes

```sql
-- Orders table
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Positions table
CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);

-- User Strategies table
CREATE INDEX idx_user_strategies_user_id ON user_strategies(user_id);
CREATE INDEX idx_user_strategies_status ON user_strategies(status);

-- Notifications table
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- Trading Sessions table
CREATE INDEX idx_trading_sessions_user_id ON trading_sessions(user_id);
CREATE INDEX idx_trading_sessions_status ON trading_sessions(status);
```

## Data Retention Policy

### Keep Forever

- User profiles
- Order history
- Position history
- Strategy configurations

### Keep for 1 Year

- Trading sessions
- Risk management rules

### Keep for 30 Days

- Notifications (unread)
- Market data cache

### Keep for 7 Days

- Real-time order status
- Active user sessions

## Security Considerations

1. **Encryption**: All broker credentials are stored encrypted
2. **Access Control**: Database access is restricted to application services only
3. **Audit Trail**: All critical operations are logged
4. **Data Backup**: Regular automated backups
5. **Connection Security**: SSL/TLS for database connections

## Migration Strategy

1. **Phase 1**: Create core tables (users, orders, strategies)
2. **Phase 2**: Add position tracking and user strategies
3. **Phase 3**: Implement notifications and trading sessions
4. **Phase 4**: Add risk management and advanced features

## Performance Considerations

1. **Connection Pooling**: Use connection pools for efficient database access
2. **Read Replicas**: Consider read replicas for reporting queries
3. **Partitioning**: Partition large tables by date (orders, positions)
4. **Caching**: Cache frequently accessed data in Redis
5. **Query Optimization**: Use appropriate indexes and query optimization
