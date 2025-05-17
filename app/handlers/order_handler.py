from app.core.database import order_queue, get_db
from app.models.order import Order, OrderStatus, OrderType
from sqlalchemy.orm import Session
from typing import Optional
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Custom exception for order validation errors."""

    pass


class OrderHandler:
    def __init__(self, db: Session):
        self.db = db

    def validate_order_params(
        self, symbol: str, order_type: str, quantity: float, price: float
    ) -> None:
        """Validate order parameters before creation."""
        if not symbol or not isinstance(symbol, str):
            raise OrderValidationError("Symbol must be a non-empty string")

        if order_type not in [ot.value for ot in OrderType]:
            raise OrderValidationError(f"Invalid order type: {order_type}")

        try:
            quantity = Decimal(str(quantity))
            if quantity <= 0:
                raise OrderValidationError("Quantity must be greater than 0")
        except (ValueError, TypeError):
            raise OrderValidationError("Quantity must be a valid number")

        try:
            price = Decimal(str(price))
            if price <= 0:
                raise OrderValidationError("Price must be greater than 0")
        except (ValueError, TypeError):
            raise OrderValidationError("Price must be a valid number")

    def create_order(
        self,
        symbol: str,
        order_type: str,
        quantity: float,
        price: float,
        strategy_id: str,
    ) -> Order:
        """Create a new order and queue it for execution"""
        # Validate parameters
        self.validate_order_params(symbol, order_type, quantity, price)

        if not strategy_id or not isinstance(strategy_id, str):
            raise OrderValidationError("Strategy ID must be a non-empty string")

        order = Order(
            symbol=symbol,
            order_type=order_type,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price)),
            strategy_id=strategy_id,
            status=OrderStatus.PENDING,
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return order

    def queue_order(self, order_id: int) -> None:
        """Queue an order for execution"""
        try:
            # Update order status to queued
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise OrderValidationError(f"Order {order_id} not found")

            order.status = OrderStatus.QUEUED
            self.db.commit()

            # Add to Redis queue (default queue)
            order_queue.enqueue(
                "app.workers.order_worker.process_order", order_id, job_timeout="1h"
            )
            logger.info(f"Order {order_id} queued for execution")
        except Exception as e:
            logger.error(f"Error queueing order {order_id}: {str(e)}")
            if order:
                order.status = OrderStatus.FAILED
                order.error_message = str(e)
                self.db.commit()
            raise

    def get_order(self, order_id: int) -> Optional[Order]:
        """Retrieve an order by ID"""
        if not isinstance(order_id, int) or order_id <= 0:
            raise OrderValidationError("Order ID must be a positive integer")
        return self.db.query(Order).filter(Order.id == order_id).first()

    def update_order_status(
        self, order_id: int, status: OrderStatus, error_message: Optional[str] = None
    ) -> Optional[Order]:
        """Update the status of an order"""
        if not isinstance(order_id, int) or order_id <= 0:
            raise OrderValidationError("Order ID must be a positive integer")

        if not isinstance(status, OrderStatus):
            raise OrderValidationError("Invalid order status")

        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            if status == OrderStatus.COMPLETED:
                order.error_message = None
            elif error_message:
                order.error_message = error_message
            self.db.commit()
            self.db.refresh(order)
        return order

    def update_order(
        self,
        order_id: int,
        status: OrderStatus,
        broker_order_id: str = None,
        error_message: str = None,
    ) -> Optional[Order]:
        """Update the status and broker_order_id of an order"""
        if not isinstance(order_id, int) or order_id <= 0:
            raise OrderValidationError("Order ID must be a positive integer")

        if not isinstance(status, OrderStatus):
            raise OrderValidationError("Invalid order status")

        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            if broker_order_id:
                order.broker_order_id = broker_order_id
            if status == OrderStatus.COMPLETED:
                order.error_message = None
            elif error_message:
                order.error_message = error_message
            self.db.commit()
            self.db.refresh(order)
        return order

    async def square_off_strategy(self, strategy_id: str) -> dict:
        """Square off all orders for a given strategy by setting their status to CANCELLED."""
        orders = self.db.query(Order).filter(Order.strategy_id == strategy_id).all()
        for order in orders:
            order.status = OrderStatus.CANCELLED
        self.db.commit()
        return {
            "message": f"Square off completed for strategy {strategy_id}",
            "orders_affected": len(orders),
        }

    async def square_off_all(self) -> dict:
        """Square off all orders across all strategies by setting their status to CANCELLED."""
        orders = self.db.query(Order).all()
        for order in orders:
            order.status = OrderStatus.CANCELLED
        self.db.commit()
        return {
            "message": "Square off completed for all strategies",
            "orders_affected": len(orders),
        }
