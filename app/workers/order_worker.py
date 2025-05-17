from app.core.database import get_db
from app.handlers.order_handler import OrderHandler
from app.models.order import OrderStatus
from app.brokers.base import BaseBroker
from decimal import Decimal


def process_order(order_id: int, broker: BaseBroker) -> None:
    """
    Process an order from the queue using the provided broker.

    Args:
        order_id: The ID of the order to process
        broker: The broker instance to use for order execution
    """
    db = next(get_db())
    try:
        handler = OrderHandler(db)
        order = handler.get_order(order_id)

        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status != OrderStatus.QUEUED:
            raise ValueError(f"Order {order_id} is not in QUEUED status")

        # Set status to PROCESSING
        handler.update_order_status(order_id, OrderStatus.PROCESSING)

        try:
            # Place the order with the broker
            broker_order_id = broker.place_order(
                symbol=order.symbol,
                order_type=order.order_type,
                quantity=(
                    float(order.quantity)
                    if isinstance(order.quantity, Decimal)
                    else order.quantity
                ),
                price=(
                    float(order.price)
                    if isinstance(order.price, Decimal)
                    else order.price
                ),
            )

            # Update order status and broker order ID
            handler.update_order(
                order_id=order_id,
                status=OrderStatus.COMPLETED,
                broker_order_id=broker_order_id,
            )
        except Exception as e:
            # Update order status to FAILED if there's an error
            handler.update_order(
                order_id=order_id,
                status=OrderStatus.FAILED,
                error_message=str(e),
            )
            raise

    finally:
        db.close()
