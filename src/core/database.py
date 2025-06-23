"""
Database models for Industrial Trading Engine
Based on comprehensive Prisma schema
"""

import enum
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator
from decimal import Decimal

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Index, UniqueConstraint, DECIMAL, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.pool import QueuePool
import uuid

logger = logging.getLogger(__name__)
Base = declarative_base()

# Enums
class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"

class BrokerName(enum.Enum):
    ANGEL_ONE = "ANGEL_ONE"
    ZERODHA = "ZERODHA"
    UPSTOX = "UPSTOX"
    FYERS = "FYERS"
    ALICE_BLUE = "ALICE_BLUE"

class RiskLevel(enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    CUSTOM = "CUSTOM"

class StrategyStatus(enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class AssetClass(enum.Enum):
    EQUITY = "EQUITY"
    DERIVATIVES = "DERIVATIVES"
    CRYPTO = "CRYPTO"
    COMMODITIES = "COMMODITIES"
    FOREX = "FOREX"

class TimeFrame(enum.Enum):
    SECOND_1 = "SECOND_1"
    SECOND_5 = "SECOND_5"
    SECOND_15 = "SECOND_15"
    SECOND_30 = "SECOND_30"
    MINUTE_1 = "MINUTE_1"
    MINUTE_3 = "MINUTE_3"
    MINUTE_5 = "MINUTE_5"
    MINUTE_15 = "MINUTE_15"
    MINUTE_30 = "MINUTE_30"
    HOUR_1 = "HOUR_1"
    HOUR_4 = "HOUR_4"
    DAY_1 = "DAY_1"
    WEEK_1 = "WEEK_1"
    MONTH_1 = "MONTH_1"

class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL_M"

class ProductType(enum.Enum):
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    NORMAL = "NORMAL"
    CARRYFORWARD = "CARRYFORWARD"
    BO = "BO"
    CO = "CO"

class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PLACED = "PLACED"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

class StrategyConfigStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    PAUSED = "PAUSED"

class StrategyCommandType(enum.Enum):
    START = "START"
    STOP = "STOP"
    RESTART = "RESTART"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    UPDATE_CONFIG = "UPDATE_CONFIG"

class CommandStatus(enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

# Core Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    role = Column(ENUM(UserRole), default=UserRole.USER)
    status = Column(ENUM(UserStatus), default=UserStatus.PENDING_VERIFICATION, index=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String)
    last_login_at = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    broker_configs = relationship("BrokerConfig", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    strategy_configs = relationship("StrategyConfig", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_role_status', 'role', 'status'),
    )

class BrokerConfig(Base):
    __tablename__ = 'broker_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    broker_name = Column(ENUM(BrokerName), nullable=False)
    display_name = Column(String)
    api_key = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    password = Column(String, nullable=False)
    totp_secret = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="broker_configs")

class Strategy(Base):
    __tablename__ = 'strategies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    strategy_type = Column(String, nullable=False)
    asset_class = Column(ENUM(AssetClass), nullable=False, index=True)
    symbols = Column(ARRAY(String), nullable=False)
    timeframe = Column(ENUM(TimeFrame), nullable=False)
    status = Column(ENUM(StrategyStatus), default=StrategyStatus.DRAFT, index=True)
    parameters = Column(JSON)
    risk_parameters = Column(JSON)
    max_positions = Column(Integer, default=5)
    capital_allocated = Column(Float, default=100000)
    total_pnl = Column(Float, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    start_time = Column(String)
    end_time = Column(String)
    active_days = Column(ARRAY(String))
    version = Column(Integer, default=1)
    last_executed_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy")
    strategy_configs = relationship("StrategyConfig", back_populates="strategy")
    strategy_logs = relationship("StrategyLog", back_populates="strategy", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_strategies_user_status', 'user_id', 'status'),
    )

class StrategyConfig(Base):
    __tablename__ = 'strategy_configs'
    
    # Match existing Prisma schema column names
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = Column(String, nullable=True)  # Match existing Prisma camelCase
    strategyId = Column(String, nullable=True)  # Match existing Prisma camelCase  
    name = Column(String, unique=True, nullable=False)
    className = Column(String, nullable=False)  # Match existing Prisma camelCase
    modulePath = Column(String, nullable=False)  # Match existing Prisma camelCase
    configJson = Column(JSON, nullable=False)  # Match existing Prisma camelCase
    status = Column(String, default='ACTIVE')  # Use string for compatibility
    autoStart = Column(Boolean, default=True)  # Match existing Prisma camelCase
    createdAt = Column(DateTime, default=datetime.utcnow)  # Match existing Prisma camelCase
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Match existing Prisma camelCase

class StrategyCommand(Base):
    __tablename__ = 'strategy_commands'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_config_id = Column(UUID(as_uuid=True), ForeignKey('strategy_configs.id', ondelete='CASCADE'), nullable=False)
    command = Column(ENUM(StrategyCommandType), nullable=False)
    parameters = Column(JSON)
    status = Column(ENUM(CommandStatus), default=CommandStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    
    strategy_config = relationship("StrategyConfig", back_populates="commands")

class StrategyMetric(Base):
    __tablename__ = 'strategy_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_config_id = Column(UUID(as_uuid=True), ForeignKey('strategy_configs.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    pnl = Column(DECIMAL, default=0)
    positions_count = Column(Integer, default=0)
    orders_count = Column(Integer, default=0)
    success_rate = Column(DECIMAL, default=0)
    metrics_json = Column(JSON)
    
    strategy_config = relationship("StrategyConfig", back_populates="metrics")

class StrategyLog(Base):
    __tablename__ = 'strategy_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    strategy = relationship("Strategy", back_populates="strategy_logs")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey('strategies.id', ondelete='SET NULL'))
    symbol = Column(String, nullable=False, index=True)
    exchange = Column(String, nullable=False, index=True)
    side = Column(ENUM(OrderSide), nullable=False)
    order_type = Column(ENUM(OrderType), nullable=False)
    product_type = Column(ENUM(ProductType), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    trigger_price = Column(Float)
    variety = Column(String, default="NORMAL")
    broker_order_id = Column(String, index=True)
    status = Column(ENUM(OrderStatus), default=OrderStatus.PENDING, index=True)
    status_message = Column(String)
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Float)
    parent_order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'))
    tags = Column(ARRAY(String))
    notes = Column(String)
    placed_at = Column(DateTime, index=True)
    executed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    parent_order = relationship("Order", remote_side=[id], back_populates="child_orders")
    child_orders = relationship("Order", back_populates="parent_order")
    
    __table_args__ = (
        Index('idx_orders_user_created', 'user_id', 'created_at'),
        Index('idx_orders_strategy_status', 'strategy_id', 'status'),
        Index('idx_orders_symbol_exchange', 'symbol', 'exchange'),
    )

class SystemConfig(Base):
    __tablename__ = 'system_config'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    description = Column(String)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Singleton Database Manager with Connection Pooling
class DatabaseManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, database_url: str = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///trading.db')
        
        # Handle SSL for PostgreSQL connections
        connect_args = {}
        if self.database_url.startswith('postgresql'):
            # Add SSL configuration for PostgreSQL
            connect_args = {
                'sslmode': 'require',
                'connect_timeout': 30,
                'application_name': 'trading_backend'
            }
            
            # If URL already has sslmode, extract it
            if 'sslmode=' in self.database_url:
                logger.info("🔐 SSL mode detected in database URL")
            else:
                # Add sslmode=require if not present
                separator = '&' if '?' in self.database_url else '?'
                self.database_url += f"{separator}sslmode=require"
                logger.info("🔐 Added SSL requirement to database URL")
        
        # Create engine with appropriate configuration
        if self.database_url.startswith('sqlite'):
            self.engine = create_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True
            )
        else:
            # PostgreSQL with connection pooling and SSL
            self.engine = create_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args=connect_args
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("Database Manager initialized")
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    def get_session(self):
        """Get database session from connection pool"""
        return self.SessionLocal()
    
    def get_session_context(self):
        """Get database session with context manager"""
        return self._session_context()
    
    def _session_context(self):
        """Database session context manager"""
        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close_all_connections(self):
        """Close all database connections (for shutdown)"""
        try:
            self.engine.dispose()
            logger.info("🔌 All database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")
    
    def get_pool_status(self):
        """Get connection pool status for monitoring"""
        try:
            pool = self.engine.pool
            return {
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalidated_connections': 0  # Use a default value instead of invalidated()
            }
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {
                'size': 0,
                'checked_in': 0,
                'checked_out': 0,
                'overflow': 0,
                'invalidated_connections': 0
            }

# Global database manager instance
_db_manager = None

def get_db_manager(database_url: str = None) -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager

def close_db_manager():
    """Close the global database manager"""
    global _db_manager
    if _db_manager:
        _db_manager.close_all_connections()
        _db_manager = None 