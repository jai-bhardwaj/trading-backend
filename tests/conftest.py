"""
Pytest configuration and shared fixtures for the trading backend test suite.
"""
import pytest
import asyncio
import redis.asyncio as redis
import os
import tempfile
import shutil
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Test configuration
TEST_CONFIG = {
    "redis_url": "redis://localhost:6379/1",  # Use DB 1 for testing
    "test_db_path": None,
    "mock_external_apis": True,
    "test_user_id": "test_user_123",
    "test_broker_id": "test_broker_456"
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Provide a Redis client for testing."""
    client = redis.from_url(TEST_CONFIG["redis_url"])
    try:
        await client.ping()
        yield client
    finally:
        await client.close()

@pytest.fixture(scope="function")
async def clean_redis(redis_client: redis.Redis):
    """Clean Redis before each test."""
    await redis_client.flushdb()
    yield redis_client

@pytest.fixture(scope="session")
def test_db():
    """Create a temporary test database."""
    temp_dir = tempfile.mkdtemp()
    TEST_CONFIG["test_db_path"] = temp_dir
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_user_data() -> Dict[str, Any]:
    """Provide mock user data for testing."""
    return {
        "user_id": TEST_CONFIG["test_user_id"],
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password_123",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "broker_credentials": {
            "broker_id": TEST_CONFIG["test_broker_id"],
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "access_token": "test_access_token"
        }
    }

@pytest.fixture
def mock_broker_data() -> Dict[str, Any]:
    """Provide mock broker data for testing."""
    return {
        "broker_id": TEST_CONFIG["test_broker_id"],
        "name": "Test Broker",
        "api_endpoint": "https://test-api.broker.com",
        "is_active": True,
        "credentials": {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret"
        }
    }

@pytest.fixture
def mock_market_data() -> Dict[str, Any]:
    """Provide mock market data for testing."""
    return {
        "symbol": "RELIANCE",
        "ltp": 2500.50,
        "change": 25.50,
        "change_percent": 1.03,
        "volume": 1000000,
        "high": 2520.00,
        "low": 2480.00,
        "open": 2490.00,
        "prev_close": 2475.00,
        "timestamp": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_order_data() -> Dict[str, Any]:
    """Provide mock order data for testing."""
    return {
        "order_id": "order_123",
        "user_id": TEST_CONFIG["test_user_id"],
        "symbol": "RELIANCE",
        "quantity": 100,
        "price": 2500.00,
        "order_type": "BUY",
        "order_status": "PENDING",
        "timestamp": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_portfolio_data() -> Dict[str, Any]:
    """Provide mock portfolio data for testing."""
    return {
        "user_id": TEST_CONFIG["test_user_id"],
        "total_value": 100000.00,
        "cash_balance": 50000.00,
        "invested_amount": 50000.00,
        "positions": [
            {
                "symbol": "RELIANCE",
                "quantity": 100,
                "avg_price": 2500.00,
                "current_value": 250000.00,
                "pnl": 5000.00
            }
        ],
        "last_updated": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_risk_data() -> Dict[str, Any]:
    """Provide mock risk data for testing."""
    return {
        "user_id": TEST_CONFIG["test_user_id"],
        "portfolio_risk_score": 0.15,
        "max_position_size": 10000.00,
        "max_daily_loss": 5000.00,
        "current_exposure": 250000.00,
        "risk_limits": {
            "max_single_position": 0.20,
            "max_sector_exposure": 0.30,
            "max_daily_turnover": 100000.00
        },
        "last_updated": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_strategy_data() -> Dict[str, Any]:
    """Provide mock strategy data for testing."""
    return {
        "strategy_id": "ma_crossover",
        "name": "Moving Average Crossover",
        "description": "Simple moving average crossover strategy",
        "parameters": {
            "short_period": 10,
            "long_period": 20,
            "symbols": ["RELIANCE", "TCS", "INFY"]
        },
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def mock_notification_data() -> Dict[str, Any]:
    """Provide mock notification data for testing."""
    return {
        "notification_id": "notif_123",
        "user_id": TEST_CONFIG["test_user_id"],
        "type": "ORDER_EXECUTED",
        "title": "Order Executed",
        "message": "Your order for RELIANCE has been executed",
        "data": {
            "order_id": "order_123",
            "symbol": "RELIANCE",
            "quantity": 100,
            "price": 2500.00
        },
        "is_read": False,
        "created_at": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_position_data() -> Dict[str, Any]:
    """Provide mock position data for testing."""
    return {
        "symbol": "RELIANCE",
        "quantity": 100,
        "avg_price": 2500.00,
        "current_value": 250000.00,
        "pnl": 5000.00,
        "unrealized_pnl": 5000.00,
        "realized_pnl": 0.00,
        "last_updated": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def mock_transaction_data() -> Dict[str, Any]:
    """Provide mock transaction data for testing."""
    return {
        "transaction_id": "txn_123",
        "user_id": TEST_CONFIG["test_user_id"],
        "symbol": "RELIANCE",
        "action": "BUY",
        "quantity": 100,
        "price": 2500.00,
        "total_amount": 250000.00,
        "commission": 25.00,
        "timestamp": "2024-01-01T10:00:00Z",
        "status": "COMPLETED"
    }

@pytest.fixture
def mock_external_api():
    """Mock external API calls."""
    mock = AsyncMock()
    
    # Mock Angel One API responses
    mock.get_quotes.return_value = {
        "status": "success",
        "data": {
            "RELIANCE": {
                "ltp": 2500.50,
                "change": 25.50,
                "volume": 1000000
            }
        }
    }
    
    mock.place_order.return_value = {
        "status": "success",
        "order_id": "broker_order_123",
        "message": "Order placed successfully"
    }
    
    mock.get_user_profile.return_value = {
        "status": "success",
        "data": {
            "user_id": TEST_CONFIG["test_user_id"],
            "name": "Test User",
            "email": "test@example.com"
        }
    }
    
    return mock

@pytest.fixture
def test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ.update({
        "TESTING": "true",
        "REDIS_URL": TEST_CONFIG["redis_url"],
        "MOCK_EXTERNAL_APIS": "true",
        "LOG_LEVEL": "DEBUG"
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
async def test_user(clean_redis: redis.Redis, mock_user_data: Dict[str, Any]):
    """Create a test user in the system."""
    user_key = f"user:{mock_user_data['user_id']}"
    await clean_redis.hset(user_key, mapping=mock_user_data)
    await clean_redis.sadd("users", mock_user_data['user_id'])
    
    yield mock_user_data
    
    # Cleanup
    await clean_redis.delete(user_key)
    await clean_redis.srem("users", mock_user_data['user_id'])

@pytest.fixture
async def test_broker(clean_redis: redis.Redis, mock_broker_data: Dict[str, Any]):
    """Create a test broker in the system."""
    broker_key = f"broker:{mock_broker_data['broker_id']}"
    await clean_redis.hset(broker_key, mapping=mock_broker_data)
    await clean_redis.sadd("brokers", mock_broker_data['broker_id'])
    
    yield mock_broker_data
    
    # Cleanup
    await clean_redis.delete(broker_key)
    await clean_redis.srem("brokers", mock_broker_data['broker_id'])

@pytest.fixture
def mock_services():
    """Mock all trading services for isolated testing."""
    return {
        "auth": AsyncMock(),
        "market_data": AsyncMock(),
        "order_management": AsyncMock(),
        "risk_management": AsyncMock(),
        "strategy_engine": AsyncMock(),
        "portfolio": AsyncMock(),
        "notification": AsyncMock()
    }

# Test markers for different test types
def pytest_configure(config):
    """Configure custom test markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    ) 