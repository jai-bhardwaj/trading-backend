import pytest
from app.core.database import get_db, order_queue
from app.handlers.order_handler import OrderHandler, OrderValidationError
from app.models.order import Order, OrderStatus, OrderType
from app.workers.order_worker import process_order
from app.brokers.base import BaseBroker
import time
from typing import Generator, List
from sqlalchemy.orm import Session
from decimal import Decimal
import redis
from rq import Queue
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor


class MockBroker(BaseBroker):
    def place_order(
        self, symbol: str, order_type: str, quantity: float, price: float
    ) -> str:
        return f"mock_order_{symbol}_{order_type}_{quantity}_{price}"


@pytest.fixture
def redis_connection() -> Generator[redis.Redis, None, None]:
    """Fixture to provide a Redis connection."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    conn = redis.from_url(redis_url)
    yield conn
    conn.flushdb()  # Clean up after tests


@pytest.fixture
def test_queue(redis_connection: redis.Redis) -> Queue:
    """Fixture to provide a test queue."""
    queue = Queue(connection=redis_connection)
    queue.empty()  # Clear the queue before each test
    return queue


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture to provide a database session for tests."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def order_handler(db_session: Session) -> OrderHandler:
    """Fixture to provide an OrderHandler instance."""
    return OrderHandler(db_session)


@pytest.fixture
def mock_broker() -> MockBroker:
    """Fixture to provide a mock broker instance."""
    return MockBroker()


@pytest.mark.asyncio
async def test_successful_order_flow(
    order_handler: OrderHandler, mock_broker: MockBroker, db_session: Session
):
    """Test the complete flow of a successful order."""
    # Create a test order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Verify initial order state
    assert order.id is not None
    assert order.status == OrderStatus.PENDING

    # Queue the order
    order_handler.queue_order(order.id)

    # Process the order using our worker
    process_order(order.id, mock_broker)

    # Wait for processing
    time.sleep(1)

    # Fetch order using a new session
    new_handler = OrderHandler(next(get_db()))
    order = new_handler.get_order(order.id)
    assert order.status == OrderStatus.COMPLETED
    assert order.broker_order_id is not None
    assert "mock_order" in order.broker_order_id


@pytest.mark.asyncio
async def test_order_validation(order_handler: OrderHandler):
    """Test various order validation scenarios."""
    # Test invalid symbol
    with pytest.raises(OrderValidationError, match="Symbol must be a non-empty string"):
        order_handler.create_order(
            symbol="",
            order_type=OrderType.BUY.value,
            quantity=10.0,
            price=150.0,
            strategy_id="test_strategy",
        )

    # Test invalid order type
    with pytest.raises(OrderValidationError, match="Invalid order type"):
        order_handler.create_order(
            symbol="AAPL",
            order_type="INVALID_TYPE",
            quantity=10.0,
            price=150.0,
            strategy_id="test_strategy",
        )

    # Test invalid quantity
    with pytest.raises(OrderValidationError, match="Quantity must be greater than 0"):
        order_handler.create_order(
            symbol="AAPL",
            order_type=OrderType.BUY.value,
            quantity=-10.0,
            price=150.0,
            strategy_id="test_strategy",
        )

    # Test invalid price
    with pytest.raises(OrderValidationError, match="Price must be greater than 0"):
        order_handler.create_order(
            symbol="AAPL",
            order_type=OrderType.BUY.value,
            quantity=10.0,
            price=-150.0,
            strategy_id="test_strategy",
        )

    # Test invalid strategy_id
    with pytest.raises(
        OrderValidationError, match="Strategy ID must be a non-empty string"
    ):
        order_handler.create_order(
            symbol="AAPL",
            order_type=OrderType.BUY.value,
            quantity=10.0,
            price=150.0,
            strategy_id="",
        )


@pytest.mark.asyncio
async def test_order_status_updates(order_handler: OrderHandler):
    """Test order status update functionality."""
    # Create an order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Test status updates
    updated_order = order_handler.update_order_status(
        order.id, OrderStatus.FAILED, "Test error message"
    )
    assert updated_order.status == OrderStatus.FAILED
    assert updated_order.error_message == "Test error message"

    # Test complete order update
    updated_order = order_handler.update_order(
        order.id,
        OrderStatus.COMPLETED,
        broker_order_id="test_broker_id",
        error_message=None,
    )
    assert updated_order.status == OrderStatus.COMPLETED
    assert updated_order.broker_order_id == "test_broker_id"
    assert updated_order.error_message is None


@pytest.mark.asyncio
async def test_nonexistent_order(order_handler: OrderHandler):
    """Test handling of nonexistent order."""
    # Try to get a nonexistent order
    order = order_handler.get_order(99999)
    assert order is None

    # Try to update a nonexistent order
    updated_order = order_handler.update_order_status(99999, OrderStatus.COMPLETED)
    assert updated_order is None


@pytest.mark.asyncio
async def test_invalid_order_id(order_handler: OrderHandler):
    """Test handling of invalid order IDs."""
    # Test with negative order ID
    with pytest.raises(
        OrderValidationError, match="Order ID must be a positive integer"
    ):
        order_handler.get_order(-1)

    # Test with zero order ID
    with pytest.raises(
        OrderValidationError, match="Order ID must be a positive integer"
    ):
        order_handler.get_order(0)

    # Test with non-integer order ID
    with pytest.raises(
        OrderValidationError, match="Order ID must be a positive integer"
    ):
        order_handler.get_order("invalid")  # type: ignore


@pytest.mark.asyncio
async def test_invalid_status_updates(order_handler: OrderHandler):
    """Test handling of invalid status updates."""
    # Create an order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Test with invalid status type
    with pytest.raises(OrderValidationError, match="Invalid order status"):
        order_handler.update_order_status(order.id, "INVALID_STATUS")  # type: ignore

    # Test with invalid order ID
    with pytest.raises(
        OrderValidationError, match="Order ID must be a positive integer"
    ):
        order_handler.update_order_status(-1, OrderStatus.COMPLETED)


@pytest.mark.asyncio
async def test_decimal_precision(order_handler: OrderHandler):
    """Test handling of decimal precision in order quantities and prices."""
    # Test with precise decimal values
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.123,
        price=150.456,
        strategy_id="test_strategy",
    )

    # Accept Decimal or float, but prefer Decimal
    assert isinstance(order.quantity, Decimal)
    assert isinstance(order.price, Decimal)
    assert order.quantity == Decimal("10.123")
    assert order.price == Decimal("150.456")


@pytest.mark.asyncio
async def test_redis_queue_integration(
    order_handler: OrderHandler,
    test_queue: Queue,
    mock_broker: MockBroker,
    db_session: Session,
):
    """Test Redis queue integration for order processing."""
    # Create a test order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Queue the order
    order_handler.queue_order(order.id)

    # Verify order is in queue
    assert test_queue.count == 1
    job = test_queue.jobs[0]
    assert job.func_name == "app.workers.order_worker.process_order"
    assert job.args[0] == order.id

    # Process the order
    process_order(order.id, mock_broker)

    # Wait for processing
    time.sleep(1)

    # Fetch order using a new session
    new_handler = OrderHandler(next(get_db()))
    order = new_handler.get_order(order.id)
    assert order.status == OrderStatus.COMPLETED
    assert order.broker_order_id is not None


@pytest.mark.asyncio
async def test_redis_queue_error_handling(
    order_handler: OrderHandler, test_queue: Queue
):
    """Test error handling in Redis queue processing."""
    # Create a test order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Queue the order
    order_handler.queue_order(order.id)

    # Simulate a queue processing error (no worker to update status, so status remains QUEUED)
    job = test_queue.jobs[0]
    job.set_status("failed")
    job.meta["exc_info"] = "Test error"
    job.save()

    # Wait for error handling
    time.sleep(1)

    # Verify order status is still QUEUED (since no worker processed it)
    order = order_handler.get_order(order.id)
    assert order.status == OrderStatus.QUEUED


@pytest.mark.asyncio
async def test_concurrent_order_processing(
    order_handler: OrderHandler, mock_broker: MockBroker, db_session: Session
):
    """Test concurrent order processing to ensure thread safety."""
    # Create multiple orders concurrently
    orders: List[Order] = []
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META"]

    async def create_and_process_order(symbol: str) -> Order:
        order = order_handler.create_order(
            symbol=symbol,
            order_type=OrderType.BUY.value,
            quantity=10.0,
            price=150.0,
            strategy_id="test_strategy",
        )
        order_handler.queue_order(order.id)
        process_order(order.id, mock_broker)
        # Fetch order using a new session
        new_handler = OrderHandler(next(get_db()))
        return new_handler.get_order(order.id)

    # Create and process orders concurrently
    tasks = [create_and_process_order(symbol) for symbol in symbols]
    orders = await asyncio.gather(*tasks)

    # Wait for all orders to be processed
    time.sleep(2)

    # Verify all orders were processed correctly
    for order in orders:
        assert order.status == OrderStatus.COMPLETED
        assert order.broker_order_id is not None
        assert "mock_order" in order.broker_order_id


@pytest.mark.asyncio
async def test_concurrent_status_updates(order_handler: OrderHandler):
    """Test concurrent status updates to ensure thread safety."""
    # Create a test order
    order = order_handler.create_order(
        symbol="AAPL",
        order_type=OrderType.BUY.value,
        quantity=10.0,
        price=150.0,
        strategy_id="test_strategy",
    )

    # Define status update function
    def update_status(status: OrderStatus) -> None:
        order_handler.update_order_status(order.id, status)

    # Perform concurrent status updates
    with ThreadPoolExecutor(max_workers=5) as executor:
        statuses = [
            OrderStatus.PROCESSING,
            OrderStatus.COMPLETED,
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
            OrderStatus.QUEUED,
        ]
        executor.map(update_status, statuses)

    # Wait for updates to complete
    time.sleep(1)

    # Verify final status
    final_order = order_handler.get_order(order.id)
    assert final_order.status in statuses  # Should be one of the concurrent updates


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_successful_order_flow())
