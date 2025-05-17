from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Numeric
from datetime import datetime
import enum
from app.core.database import Base


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OrderType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    order_type = Column(Enum(OrderType))
    quantity = Column(Numeric(precision=18, scale=8))
    price = Column(Numeric(precision=18, scale=8))
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    strategy_id = Column(String, index=True)
    broker_order_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
