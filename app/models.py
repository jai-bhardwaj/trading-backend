from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    strategies = relationship("Strategy", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.username"))
    name = Column(String)
    margin = Column(Float)
    marginType = Column(String)  # "percentage" or "rupees"
    basePrice = Column(Float)
    status = Column(String)  # "active" or "inactive"
    lastUpdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "margin": self.margin,
            "marginType": self.marginType,
            "basePrice": self.basePrice,
            "status": self.status,
            "lastUpdated": self.lastUpdated.isoformat() if self.lastUpdated else None,
            "user_id": self.user_id,
        }


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.username"))
    strategy_id = Column(String, ForeignKey("strategies.id"))
    symbol = Column(String)
    order_type = Column(String)  # "BUY" or "SELL"
    quantity = Column(Integer)
    price = Column(Float)
    status = Column(String)  # "PENDING", "COMPLETED", "CANCELLED", "REJECTED"
    order_time = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    exchange_order_id = Column(String, nullable=True)
    exchange_status = Column(String, nullable=True)
    exchange_message = Column(String, nullable=True)

    user = relationship("User", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "order_time": self.order_time.isoformat() if self.order_time else None,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "exchange_order_id": self.exchange_order_id,
            "exchange_status": self.exchange_status,
            "exchange_message": self.exchange_message,
        }
