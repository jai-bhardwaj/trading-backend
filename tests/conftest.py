"""
Pytest configuration and shared fixtures for trading engine tests
"""

import pytest
import asyncio
import sys
import uuid
from pathlib import Path
import redis
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DatabaseManager
from app.models.base import User, Strategy, Order, StrategyStatus, OrderStatus, AssetClass, TimeFrame
from app.core.instrument_manager import InstrumentManager
from app.engine.redis_engine import RedisBasedTradingEngine

# Configure asyncio for pytest
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set the event loop policy for the test session"""
    return asyncio.DefaultEventLoopPolicy()

@pytest.fixture
async def db_manager():
    """Database manager fixture for testing"""
    db = DatabaseManager()
    await db.initialize()
    yield db
    await db.close()

@pytest.fixture
async def test_user(db_manager):
    """Create a test user with unique ID"""
    unique_id = str(uuid.uuid4())
    async with db_manager.get_session() as session:
        user = User(
            id=f"test-user-{unique_id}",
            email=f"test-{unique_id}@example.com",
            username=f"test_user_{unique_id[:8]}",
            hashed_password="hashed_password_123",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        await session.commit()
        yield user

@pytest.fixture
async def test_strategy(db_manager, test_user):
    """Create a test strategy with unique ID"""
    unique_id = str(uuid.uuid4())
    async with db_manager.get_session() as session:
        strategy = Strategy(
            id=f"test-strategy-{unique_id}",
            user_id=test_user.id,
            name=f"Test Strategy {unique_id[:8]}",
            description="A test strategy for unit testing",
            strategy_type="test_strategy",
            asset_class=AssetClass.EQUITY,
            symbols=["RELIANCE", "TCS", "INFY"],
            timeframe=TimeFrame.MINUTE_1,
            status=StrategyStatus.ACTIVE,
            parameters={"test_param": 1.0},
            risk_parameters={"max_loss": 0.02}
        )
        session.add(strategy)
        await session.commit()
        yield strategy

@pytest.fixture
async def test_order(db_manager, test_user, test_strategy):
    """Create a test order with unique ID"""
    unique_id = str(uuid.uuid4())
    async with db_manager.get_session() as session:
        from app.models.base import OrderSide, OrderType, ProductType
        
        order = Order(
            id=f"test-order-{unique_id}",
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            symbol="RELIANCE",
            exchange="NSE",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            product_type=ProductType.INTRADAY,
            quantity=10,
            price=2500.0,
            status=OrderStatus.PENDING
        )
        session.add(order)
        await session.commit()
        yield order

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.lpush.return_value = 1
    mock_redis.brpop.return_value = ("test_queue", '{"test": "data"}')
    mock_redis.llen.return_value = 0
    return mock_redis

@pytest.fixture
def mock_instrument_manager():
    """Mock instrument manager for testing"""
    manager = AsyncMock(spec=InstrumentManager)
    manager.get_instruments_by_asset_class.return_value = [
        {"symbol": "RELIANCE", "exchange": "NSE", "lot_size": 1, "asset_class": "EQUITY"},
        {"symbol": "TCS", "exchange": "NSE", "lot_size": 1, "asset_class": "EQUITY"},
        {"symbol": "INFY", "exchange": "NSE", "lot_size": 1, "asset_class": "EQUITY"}
    ]
    manager.get_status.return_value = {
        "total_instruments": 48,
        "equity_count": 38,
        "derivatives_count": 10,
        "auth_status": "authenticated"
    }
    return manager

@pytest.fixture
async def trading_engine(db_manager, mock_redis):
    """Create a trading engine instance for testing"""
    # Create engine with correct parameters
    engine = RedisBasedTradingEngine(
        worker_count=2,
        max_queue_size=100,
        db_manager=db_manager
    )
    
    # Mock Redis functionality for testing
    if hasattr(engine.queue_manager, 'redis_client'):
        engine.queue_manager.redis_client = mock_redis
    
    yield engine
    
    # Cleanup
    if hasattr(engine, 'stop'):
        await engine.stop()

@pytest.fixture
async def instrument_manager(db_manager):
    """Create an instrument manager instance for testing"""
    manager = InstrumentManager(db_manager=db_manager)
    await manager.initialize()
    yield manager
    await manager.stop()

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "RELIANCE": {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "open": 2480.0,
            "high": 2520.0,
            "low": 2470.0,
            "close": 2500.0,
            "volume": 1000000,
            "timestamp": "2025-01-01T09:30:00"
        }
    } 