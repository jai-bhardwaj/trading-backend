from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.models.base import Base
import enum

class PositionSide(enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class PositionStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Position(Base):
    __tablename__ = 'positions'

    position_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(PositionSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    strategy_id = Column(String(50), nullable=True)
    order_id = Column(String(50), ForeignKey('orders.order_id'), nullable=True)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="positions")
    order = relationship("Order") 