# Updated SQLAlchemy models for cleaned trading system
from sqlalchemy import Column, Boolean, Text, DateTime, JSON, ARRAY, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, nullable=False)
    strategy_type = Column(Text, nullable=False)
    symbols = Column(ARRAY(Text), nullable=False)
    parameters = Column(JSON, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    class_name = Column(Text, nullable=False)
    module_path = Column(Text, nullable=False)
    config_json = Column(JSON, nullable=False)
    status = Column(Text, nullable=False, default="ACTIVE")
    auto_start = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))

class Order(Base):
    __tablename__ = "orders"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = Column(Text, nullable=False)
    strategyId = Column(Text, nullable=True)
    symbol = Column(Text, nullable=False)
    exchange = Column(Text, nullable=False)
    side = Column(Text, nullable=False)
    orderType = Column(Text, nullable=False)
    productType = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=True)
    triggerPrice = Column(Float, nullable=True)
    brokerOrderId = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    statusMessage = Column(Text, nullable=True)
    filledQuantity = Column(Integer, nullable=False, default=0)
    averagePrice = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    placedAt = Column(DateTime, nullable=True)
    executedAt = Column(DateTime, nullable=True)
    cancelledAt = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    variety = Column(Text, nullable=False, default="REGULAR")
    parentOrderId = Column(Text, nullable=True)
