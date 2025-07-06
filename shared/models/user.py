from sqlalchemy import Column, String, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.models.base import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    broker_api_key = Column(String(100), default='')
    broker_secret = Column(String(100), default='')
    broker_token = Column(String(100), default='')
    total_capital = Column(Numeric(15, 2), default=100000.00)
    risk_tolerance = Column(String(20), default='medium')
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="user")
    user_strategies = relationship("UserStrategy", back_populates="user")
    positions = relationship("Position", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    trading_sessions = relationship("TradingSession", back_populates="user")
    risk_rules = relationship("RiskRule", back_populates="user") 