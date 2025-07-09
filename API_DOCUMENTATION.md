# Trading Backend API Documentation

Complete API reference for the Trading Backend FastAPI service.

## 🚀 Base Information

- **Base URL**: `http://localhost:8000` (Development)
- **API Version**: v1
- **Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

## 🔐 Authentication

Most endpoints require authentication. Include the Bearer token in the Authorization header:

```http
Authorization: Bearer <your-token>
```

## 📊 API Endpoints

### 🩺 Health & Status

#### Get System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-09T18:13:45Z",
  "version": "1.0.0"
}
```

#### Get Detailed Health
```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-09T18:13:45Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12.5
    },
    "trading_engine": {
      "status": "healthy",
      "active_strategies": 5,
      "orders_today": 1647,
      "success_rate": 96.1
    },
    "market_data": {
      "status": "healthy",
      "last_update": "2024-01-09T18:13:40Z"
    }
  },
  "system": {
    "uptime_seconds": 3012,
    "memory_usage_mb": 778,
    "cpu_usage_percent": 15.2
  }
}
```

### 📈 Strategy Management

#### List All Strategies
```http
GET /strategies
```

**Query Parameters:**
- `enabled` (optional): Filter by enabled status
- `limit` (optional): Number of strategies to return (default: 100)
- `offset` (optional): Number of strategies to skip (default: 0)

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Strategy",
    "class_name": "TestStrategy",
    "enabled": true,
    "symbols": ["RELIANCE-EQ", "TCS-EQ", "INFY-EQ", "HDFCBANK-EQ"],
    "parameters": {
      "order_interval_seconds": 600,
      "test_quantity": 1,
      "max_quantity": 10,
      "min_quantity": 1
    },
    "created_at": "2024-01-09T10:00:00Z",
    "updated_at": "2024-01-09T15:30:00Z"
  }
]
```

#### Get Specific Strategy
```http
GET /strategies/{strategy_id}
```

**Path Parameters:**
- `strategy_id` (required): UUID of the strategy

**Response:** Single strategy object (same format as list)

#### Create New Strategy
```http
POST /strategies
```

**Request Body:**
```json
{
  "name": "My New Strategy",
  "class_name": "MomentumStrategy",
  "enabled": true,
  "symbols": ["RELIANCE-EQ", "TCS-EQ"],
  "parameters": {
    "lookback_period": 20,
    "threshold": 0.02
  }
}
```

**Response:** Created strategy object with generated ID

#### Update Strategy
```http
PUT /strategies/{strategy_id}
```

**Path Parameters:**
- `strategy_id` (required): UUID of the strategy

**Request Body:** Same as create (all fields optional for update)

**Response:** Updated strategy object

#### Delete Strategy
```http
DELETE /strategies/{strategy_id}
```

**Path Parameters:**
- `strategy_id` (required): UUID of the strategy

**Response:**
```json
{
  "message": "Strategy deleted successfully"
}
```

### 👤 User Strategy Configuration

#### List User Configurations
```http
GET /user-configs
```

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `strategy_id` (optional): Filter by strategy ID
- `enabled` (optional): Filter by enabled status

**Response:**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_001",
    "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
    "enabled": true,
    "max_order_value": 10000.0,
    "max_daily_orders": 50,
    "risk_percentage": 2.0,
    "order_preferences": {
      "default_quantity": 1,
      "order_type": "MARKET",
      "stop_loss_percentage": 5.0,
      "take_profit_percentage": 10.0
    },
    "created_at": "2024-01-09T10:00:00Z",
    "updated_at": "2024-01-09T15:30:00Z"
  }
]
```

#### Get User's Strategy Configurations
```http
GET /user-configs/{user_id}
```

**Path Parameters:**
- `user_id` (required): User identifier

**Response:** Array of user configuration objects

#### Create User Configuration
```http
POST /user-configs
```

**Request Body:**
```json
{
  "user_id": "user_001",
  "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
  "enabled": true,
  "max_order_value": 10000.0,
  "max_daily_orders": 50,
  "risk_percentage": 2.0,
  "order_preferences": {
    "default_quantity": 1,
    "order_type": "MARKET"
  }
}
```

**Response:** Created configuration object

#### Update User Configuration
```http
PUT /user-configs/{config_id}
```

**Path Parameters:**
- `config_id` (required): UUID of the configuration

**Request Body:** Same as create (all fields optional)

**Response:** Updated configuration object

#### Delete User Configuration
```http
DELETE /user-configs/{config_id}
```

**Path Parameters:**
- `config_id` (required): UUID of the configuration

**Response:**
```json
{
  "message": "User configuration deleted successfully"
}
```

### 📋 Order Management

#### List Orders
```http
GET /orders
```

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `strategy_id` (optional): Filter by strategy ID
- `symbol` (optional): Filter by symbol
- `status` (optional): Filter by status (PENDING, COMPLETED, FAILED, CANCELLED)
- `signal_type` (optional): Filter by signal type (BUY, SELL)
- `start_date` (optional): Filter from date (ISO format)
- `end_date` (optional): Filter to date (ISO format)
- `limit` (optional): Number of orders to return (default: 100)
- `offset` (optional): Number of orders to skip (default: 0)

**Response:**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_001",
    "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "RELIANCE-EQ",
    "signal_type": "BUY",
    "quantity": 2,
    "price": 2456.75,
    "order_type": "MARKET",
    "status": "COMPLETED",
    "broker_order_id": "240109000123456",
    "filled_quantity": 2,
    "filled_price": 2456.80,
    "timestamp": "2024-01-09T14:35:22Z",
    "filled_at": "2024-01-09T14:35:25Z",
    "metadata": {
      "strategy": "Test Strategy",
      "test_order": true,
      "confidence": 0.67,
      "randomly_selected": true
    }
  }
]
```

#### Get Specific Order
```http
GET /orders/{order_id}
```

**Path Parameters:**
- `order_id` (required): UUID of the order

**Response:** Single order object (same format as list)

#### Place New Order
```http
POST /orders
```

**Request Body:**
```json
{
  "user_id": "user_001",
  "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
  "symbol": "RELIANCE-EQ",
  "signal_type": "BUY",
  "quantity": 1,
  "price": 2456.75,
  "order_type": "LIMIT",
  "metadata": {
    "manual_order": true,
    "notes": "User placed order"
  }
}
```

**Response:** Created order object

### 📊 Position Management

#### List Positions
```http
GET /positions
```

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `symbol` (optional): Filter by symbol
- `active_only` (optional): Show only non-zero positions
- `limit` (optional): Number of positions to return (default: 100)
- `offset` (optional): Number of positions to skip (default: 0)

**Response:**
```json
[
  {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_001",
    "symbol": "RELIANCE-EQ",
    "quantity": 10,
    "average_price": 2450.25,
    "current_price": 2456.75,
    "market_value": 24567.50,
    "pnl": 65.00,
    "pnl_percentage": 0.27,
    "created_at": "2024-01-09T10:00:00Z",
    "updated_at": "2024-01-09T18:13:45Z"
  }
]
```

#### Get Specific Position
```http
GET /positions/{position_id}
```

**Path Parameters:**
- `position_id` (required): UUID of the position

**Response:** Single position object (same format as list)

### 💼 Trade Management

#### List Trades
```http
GET /trades
```

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `symbol` (optional): Filter by symbol
- `start_date` (optional): Filter from date (ISO format)
- `end_date` (optional): Filter to date (ISO format)
- `limit` (optional): Number of trades to return (default: 100)
- `offset` (optional): Number of trades to skip (default: 0)

**Response:**
```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_001",
    "order_id": "770e8400-e29b-41d4-a716-446655440000",
    "symbol": "RELIANCE-EQ",
    "side": "BUY",
    "quantity": 2,
    "price": 2456.80,
    "value": 4913.60,
    "commission": 4.91,
    "taxes": 0.98,
    "net_value": 4919.49,
    "trade_id": "T240109001234",
    "exchange": "NSE",
    "timestamp": "2024-01-09T14:35:25Z"
  }
]
```

#### Get Specific Trade
```http
GET /trades/{trade_id}
```

**Path Parameters:**
- `trade_id` (required): UUID of the trade

**Response:** Single trade object (same format as list)

## 🔄 WebSocket Events

Connect to: `ws://localhost:8000/ws`

### Event Types

#### Order Updates
```json
{
  "type": "order_update",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "status": "COMPLETED",
    "filled_quantity": 2,
    "filled_price": 2456.80,
    "filled_at": "2024-01-09T14:35:25Z"
  }
}
```

#### Position Updates
```json
{
  "type": "position_update",
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "symbol": "RELIANCE-EQ",
    "quantity": 12,
    "current_price": 2460.00,
    "pnl": 120.00
  }
}
```

#### Strategy Updates
```json
{
  "type": "strategy_update",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Strategy",
    "enabled": false,
    "updated_at": "2024-01-09T18:13:45Z"
  }
}
```

#### Trade Updates
```json
{
  "type": "trade_update",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "symbol": "RELIANCE-EQ",
    "quantity": 2,
    "price": 2456.80,
    "timestamp": "2024-01-09T14:35:25Z"
  }
}
```

## ❌ Error Responses

### Standard Error Format
```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-09T18:13:45Z"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

### Common Error Codes

- `VALIDATION_ERROR` - Request validation failed
- `STRATEGY_NOT_FOUND` - Strategy does not exist
- `USER_CONFIG_NOT_FOUND` - User configuration not found
- `ORDER_FAILED` - Order placement failed
- `INSUFFICIENT_FUNDS` - Not enough balance
- `MARKET_CLOSED` - Market is not open
- `SYMBOL_NOT_FOUND` - Invalid symbol
- `RATE_LIMIT_EXCEEDED` - Too many requests

## 📝 Request/Response Examples

### Creating a Complete Trading Setup

1. **Create Strategy:**
```bash
curl -X POST "http://localhost:8000/strategies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Momentum Strategy",
    "class_name": "MomentumStrategy",
    "enabled": true,
    "symbols": ["RELIANCE-EQ", "TCS-EQ"],
    "parameters": {
      "lookback_period": 20,
      "threshold": 0.02
    }
  }'
```

2. **Configure User Settings:**
```bash
curl -X POST "http://localhost:8000/user-configs" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
    "enabled": true,
    "max_order_value": 10000.0,
    "max_daily_orders": 50,
    "risk_percentage": 2.0
  }'
```

3. **Place Manual Order:**
```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "symbol": "RELIANCE-EQ",
    "signal_type": "BUY",
    "quantity": 5,
    "order_type": "MARKET"
  }'
```

4. **Check Positions:**
```bash
curl "http://localhost:8000/positions?user_id=user_001"
```

## 🚀 Rate Limits

- **General API**: 1000 requests per minute
- **Order Placement**: 100 requests per minute
- **Health Check**: 60 requests per minute
- **WebSocket**: 1000 messages per minute

## 🔍 Testing

Use the interactive API documentation at `http://localhost:8000/docs` to test endpoints directly in your browser.

## 📞 Support

For API issues:
1. Check system health: `GET /health/detailed`
2. Review error codes and messages
3. Check the backend logs: `journalctl -u trading-backend -f`
4. Verify your request format against this documentation

---

**Happy Trading! 🚀📈** 