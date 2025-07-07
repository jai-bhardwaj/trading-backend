# Updated SQLAlchemy models for cleaned trading system
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(Text, nullable=False, unique=True)
    username = Column(Text, nullable=False, unique=True)
    hashed_password = Column(Text, nullable=False)
    first_name = Column(Text, nullable=True)
    last_name = Column(Text, nullable=True)
    role = Column(Text, nullable=False, default="USER")
    status = Column(Text, nullable=False, default="ACTIVE")
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    positions = relationship("Position", back_populates="user")
    broker_configs = relationship("BrokerConfig", back_populates="user")

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    strategy_type = Column(Text, nullable=False)
    symbols = Column(ARRAY(Text), nullable=False)  # Array of symbols
    parameters = Column(JSON, nullable=False)  # Strategy parameters
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    configs = relationship("StrategyConfig")

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    
    id = Column(Text, primary_key=True)
    strategy_id = Column(Text, ForeignKey("strategies.id"), nullable=False)
    name = Column(Text, nullable=False)
    class_name = Column(Text, nullable=False)
    module_path = Column(Text, nullable=False)
    config_json = Column(JSON, nullable=False)
    status = Column(Text, nullable=False, default="ACTIVE")
    auto_start = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="configs")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Text, nullable=True)
    symbol = Column(Text, nullable=False)
    exchange = Column(Text, nullable=False)
    side = Column(Text, nullable=False)  # BUY, SELL
    order_type = Column(Text, nullable=False)  # MARKET, LIMIT, etc.
    product_type = Column(Text, nullable=False)  # EQ, FUT, OPT, etc.
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=True)
    trigger_price = Column(Float, nullable=True)
    broker_order_id = Column(Text, nullable=True)
    status = Column(Text, nullable=False)  # PENDING, PLACED, EXECUTED, CANCELLED
    status_message = Column(Text, nullable=True)
    filled_quantity = Column(Integer, nullable=False, default=0)
    average_price = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    notes = Column(Text, nullable=True)
    placed_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    variety = Column(Text, nullable=False, default="REGULAR")
    parent_order_id = Column(Text, ForeignKey("orders.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
    parent_order = relationship("Order", remote_side=[id])

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    order_id = Column(Text, ForeignKey("orders.id"), nullable=False)
    trade_id = Column(Text, nullable=True)  # Broker trade ID
    symbol = Column(Text, nullable=False)
    exchange = Column(Text, nullable=False)
    side = Column(Text, nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    product_type = Column(Text, nullable=False)
    order_type = Column(Text, nullable=False)
    brokerage = Column(Float, nullable=False, default=0.0)
    taxes = Column(Float, nullable=False, default=0.0)
    total_charges = Column(Float, nullable=False, default=0.0)
    net_amount = Column(Float, nullable=False)
    trade_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    order = relationship("Order", back_populates="trades")

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    symbol = Column(Text, nullable=False)
    exchange = Column(Text, nullable=False)
    product_type = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    last_traded_price = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    market_value = Column(Float, nullable=False, default=0.0)
    day_change = Column(Float, nullable=False, default=0.0)
    day_change_pct = Column(Float, nullable=False, default=0.0)
    first_buy_date = Column(DateTime, nullable=True)
    last_trade_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="positions")

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(Text, nullable=False)
    exchange = Column(Text, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    previous_close = Column(Float, nullable=True)
    change = Column(Float, nullable=True)
    change_pct = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    timeframe = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class BrokerConfig(Base):
    __tablename__ = "broker_configs"
    
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    broker_name = Column(Text, nullable=False)
    display_name = Column(Text, nullable=True)
    api_key = Column(Text, nullable=False)
    client_id = Column(Text, nullable=False)
    password = Column(Text, nullable=False)
    totp_secret = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_connected = Column(Boolean, nullable=False, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="broker_configs")
