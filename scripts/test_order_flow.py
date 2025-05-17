import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db, order_queue
from app.handlers.order_handler import OrderHandler
from app.models.order import OrderType
from app.workers.order_worker import process_order
from app.brokers.base import BaseBroker
import time


class MockBroker(BaseBroker):
    def place_order(
        self, symbol: str, order_type: str, quantity: float, price: float
    ) -> str:
        print(
            f"Mock broker executing order: {symbol} {order_type} {quantity} @ {price}"
        )
        return f"mock_order_{symbol}_{order_type}_{quantity}_{price}"


def main():
    print("Starting order flow test...")

    # Get database session
    db = next(get_db())

    try:
        # Create order handler
        handler = OrderHandler(db)

        # Create a test order
        print("\nCreating test order...")
        order = handler.create_order(
            symbol="AAPL",
            order_type=OrderType.BUY.value,
            quantity=10.0,
            price=150.0,
            strategy_id="test_strategy",
        )

        print(f"Order created with ID: {order.id}")
        print(f"Initial status: {order.status}")

        # Wait for order to be queued
        print("\nWaiting for order to be queued...")
        time.sleep(1)

        # Check order status
        order = handler.get_order(order.id)
        print(f"Order status after queueing: {order.status}")

        # Process the order
        print("\nProcessing order...")
        broker = MockBroker()
        process_order(order.id, broker)

        # Wait for processing
        print("Waiting for order processing...")
        time.sleep(1)

        # Check final status
        order = handler.get_order(order.id)
        print(f"\nFinal order status: {order.status}")
        print(f"Broker order ID: {order.broker_order_id}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
