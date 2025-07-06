from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.models.base import Base
import enum

class StrategyStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"

class Strategy(Base):
    __tablename__ = 'strategies'

    strategy_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)
    min_capital = Column(Float, nullable=False)
    expected_return_annual = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    symbols = Column(JSON, nullable=False)  # Array of trading symbols
    parameters = Column(JSON, nullable=False)  # Strategy parameters
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_strategies = relationship("UserStrategy", back_populates="strategy")

class UserStrategy(Base):
    __tablename__ = 'user_strategies'

    user_id = Column(String(50), ForeignKey('users.user_id'), primary_key=True)
    strategy_id = Column(String(50), ForeignKey('strategies.strategy_id'), primary_key=True)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.ACTIVE)
    activated_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)
    allocation_amount = Column(Float, default=0.0)
    custom_parameters = Column(JSON, default=dict)
    total_orders = Column(Integer, default=0)
    successful_orders = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_strategies")
    strategy = relationship("Strategy", back_populates="user_strategies") 