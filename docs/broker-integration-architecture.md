# Broker Integration Architecture

## Overview

The Pinnacle Trading System uses a **two-tier broker integration architecture** to ensure security, scalability, and user-specific trading capabilities.

## Architecture Design

### 1. Market Data Service (Root Level - Environment Variables)

**Location**: `services/market-data/market_service.py`

**Purpose**: Fetch real-time market data (OHLCV, tick data, market status)

**Credentials Source**: Environment variables

```bash
ANGEL_ONE_API_KEY=your_api_key_here
ANGEL_ONE_CLIENT_ID=your_client_id_here
```

**Usage**:

- Real-time price feeds
- Historical data retrieval
- Market status monitoring
- Symbol information

**Why Environment Variables?**

- Market data is **public information**
- No user-specific data required
- Single API key can serve all users
- Simplified configuration management

### 2. Order Management & User Services (User Level - Database)

**Location**:

- `services/order-management/order_manager.py`
- `services/auth/user_service.py`

**Purpose**: User-specific trading operations (order placement, portfolio management)

**Credentials Source**: Database (user-specific)

```sql
-- User table stores per-user broker credentials
broker_api_key VARCHAR(100)
broker_secret VARCHAR(100)
broker_token VARCHAR(100)
```

**Usage**:

- Order placement and modification
- Portfolio management
- User authentication
- Personalized trading

**Why Database Storage?**

- **Security**: Each user has their own broker account
- **Isolation**: User A cannot access User B's trading account
- **Compliance**: Regulatory requirements for user-specific credentials
- **Scalability**: Support multiple broker accounts per user

## Implementation Details

### Market Data Service

```python
# Uses environment variables for Angel One API
ANGEL_ONE_API_KEY = os.getenv("ANGEL_ONE_API_KEY", "")
ANGEL_ONE_CLIENT_ID = os.getenv("ANGEL_ONE_CLIENT_ID", "")
```

### Order Management Service

```python
# Gets user-specific credentials from database
async def get_user_broker_credentials(self, user_id: str):
    user_data = await get_user_from_database(user_id)
    return {
        "broker_api_key": user_data.get("broker_api_key"),
        "broker_secret": user_data.get("broker_secret"),
        "broker_token": user_data.get("broker_token")
    }
```

### User Service

```python
# Stores and retrieves user-specific broker credentials
class User(Base):
    broker_api_key = Column(String(100), default='')
    broker_secret = Column(String(100), default='')
    broker_token = Column(String(100), default='')
```

## Security Benefits

1. **Credential Isolation**: Each user's broker credentials are separate
2. **No Cross-User Access**: User A cannot trade on User B's account
3. **Audit Trail**: All trades are tied to specific user credentials
4. **Compliance**: Meets regulatory requirements for user-specific trading

## Testing

Run the broker integration test:

```bash
python tools/test_broker_integration.py
```

This will verify:

- Market Data Service uses environment variables
- Order Management Service uses database credentials
- User Service properly stores/retrieves credentials

## Configuration

### Environment Variables (Market Data)

```bash
# .env file
ANGEL_ONE_API_KEY=your_global_api_key
ANGEL_ONE_CLIENT_ID=your_global_client_id
```

### Database Configuration (User Credentials)

```sql
-- Each user has their own broker credentials
UPDATE users
SET broker_api_key = 'user_specific_key',
    broker_secret = 'user_specific_secret',
    broker_token = 'user_specific_token'
WHERE user_id = 'trader_001';
```

## Migration Path

1. **Phase 1**: Configure global market data credentials
2. **Phase 2**: Add user-specific broker credentials to database
3. **Phase 3**: Test order placement with user credentials
4. **Phase 4**: Implement live Angel One API integration

## Best Practices

1. **Never store broker credentials in code**
2. **Use environment variables for global services**
3. **Use database for user-specific credentials**
4. **Encrypt sensitive credentials in database**
5. **Implement proper authentication before accessing credentials**
6. **Log all credential access for audit purposes**
