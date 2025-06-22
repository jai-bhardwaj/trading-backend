"""
Simple Trading Database Models
Clean, focused schema for multi-user trading system
"""

import enum
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, DateTime, 
    Text, JSON, ForeignKey, Index, DECIMAL
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.pool import QueuePool
import uuid

logger = logging.getLogger(__name__)
Base = declarative_base()

# Enums
class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class BrokerName(enum.Enum):
    ANGEL_ONE = "ANGEL_ONE"

class StrategyStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"

class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL_M"

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

# Core Models
class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    trading_enabled = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Strategy(Base):
    __tablename__ = 'strategies'
    
    strategy_id = Column(String(50), primary_key=True)
    strategy_name = Column(String(255), nullable=False)
    strategy_type = Column(String(50), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserStrategy(Base):
    """Core table - maps users to strategies they want to trade"""
    __tablename__ = 'user_strategies'
    
    user_id = Column(String(50), ForeignKey('users.user_id'), primary_key=True)
    strategy_id = Column(String(50), ForeignKey('strategies.strategy_id'), primary_key=True)
    enabled = Column(Boolean, default=False, nullable=False, index=True)
    quantity_multiplier = Column(DECIMAL(10, 2), default=1.0)
    max_position_size = Column(DECIMAL(15, 2))
    risk_multiplier = Column(DECIMAL(10, 2), default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Critical indexes for fast lookups
    __table_args__ = (
        Index('idx_strategy_users', 'strategy_id', 'enabled'),
        Index('idx_user_strategies', 'user_id', 'enabled'),
    )

class UserBrokerCredential(Base):
    __tablename__ = 'user_broker_credentials'
    
    user_id = Column(String(50), ForeignKey('users.user_id'), primary_key=True)
    broker = Column(ENUM(BrokerName), primary_key=True)
    client_code = Column(String(100))
    encrypted_api_key = Column(Text)
    encrypted_password = Column(Text)
    encrypted_totp_secret = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderExecution(Base):
    __tablename__ = 'order_executions'
    
    execution_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    strategy_id = Column(String(50), ForeignKey('strategies.strategy_id'))
    signal_id = Column(String(50), index=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    action = Column(ENUM(OrderSide), nullable=False)
    order_type = Column(ENUM(OrderType), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(15, 2))
    status = Column(ENUM(OrderStatus), default=OrderStatus.PENDING)
    broker_order_id = Column(String(100))
    broker_response = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_user_orders', 'user_id', 'created_at'),
        Index('idx_strategy_orders', 'strategy_id', 'created_at'),
    )

class DatabaseManager:
    _instance = None
    
    def __new__(cls, database_url: str = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, database_url: str = None):
        if hasattr(self, '_initialized'):
            return
        
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable required")
        
        self.engine = create_engine(
            self.database_url,
            echo=False,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self._initialized = True
        logger.info("Database Manager initialized")
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def get_session(self):
        return self.SessionLocal()
    
    def close(self):
        self.engine.dispose()

# Global instance
_db_manager = None

def get_db_manager(database_url: str = None):
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager 