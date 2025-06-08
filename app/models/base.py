"""
Base models for the trading engine database
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    DateTime,
    Enum,
    Text,
    JSON,
    func,
    Numeric,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from datetime import datetime
import enum

Base = declarative_base()

# Enums matching Prisma schema exactly
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

class NotificationType(enum.Enum):
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    RISK_VIOLATION = "RISK_VIOLATION"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    PRICE_ALERT = "PRICE_ALERT"

class NotificationStatus(enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"

class AuditAction(enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    STRATEGY_CREATED = "STRATEGY_CREATED"
    STRATEGY_UPDATED = "STRATEGY_UPDATED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_DELETED = "API_KEY_DELETED"

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

# Models matching Prisma schema exactly with camelCase column names
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column("hashedPassword", String, nullable=False)
    first_name = Column("firstName", String)
    last_name = Column("lastName", String)
    phone = Column(String)
    role = Column(Enum(UserRole, name="UserRole"), default=UserRole.USER)
    status = Column(Enum(UserStatus, name="UserStatus"), default=UserStatus.PENDING_VERIFICATION)
    email_verified = Column("emailVerified", Boolean, default=False)
    phone_verified = Column("phoneVerified", Boolean, default=False)
    two_factor_enabled = Column("twoFactorEnabled", Boolean, default=False)
    two_factor_secret = Column("twoFactorSecret", String)
    last_login_at = Column("lastLoginAt", DateTime)
    login_attempts = Column("loginAttempts", Integer, default=0)
    locked_until = Column("lockedUntil", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    # Relations
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    broker_configs = relationship("BrokerConfig", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    balance = relationship("Balance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    risk_profile = relationship("RiskProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    strategy_configs = relationship("StrategyConfig", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alert_templates = relationship("AlertTemplate", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), unique=True, nullable=False)
    avatar = Column(String)
    bio = Column(String)
    timezone = Column(String, default="Asia/Kolkata")
    language = Column(String, default="en")
    trading_experience = Column("tradingExperience", String)
    risk_tolerance = Column("riskTolerance", String)
    investment_goals = Column("investmentGoals", String)
    preferred_assets = Column("preferredAssets", ARRAY(String))
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    ip_address = Column("ipAddress", String)
    user_agent = Column("userAgent", String)
    expires_at = Column("expiresAt", DateTime, nullable=False)
    created_at = Column("createdAt", DateTime, default=func.now())

    user = relationship("User", back_populates="sessions")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column("keyHash", String, unique=True, nullable=False)
    permissions = Column(ARRAY(String))
    last_used_at = Column("lastUsedAt", DateTime)
    expires_at = Column("expiresAt", DateTime)
    is_active = Column("isActive", Boolean, default=True)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")

class BrokerConfig(Base):
    __tablename__ = "broker_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    broker_name = Column("brokerName", Enum(BrokerName, name="BrokerName"), nullable=False)
    display_name = Column("displayName", String)
    api_key = Column("apiKey", String, nullable=False)
    client_id = Column("clientId", String, nullable=False)
    password = Column(String, nullable=False)
    totp_secret = Column("totpSecret", String)
    access_token = Column("accessToken", String)
    refresh_token = Column("refreshToken", String)
    is_active = Column("isActive", Boolean, default=True)
    is_connected = Column("isConnected", Boolean, default=False)
    last_sync_at = Column("lastSyncAt", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="broker_configs")

class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), unique=True, nullable=False)
    risk_level = Column("riskLevel", Enum(RiskLevel, name="RiskLevel"), default=RiskLevel.MODERATE)
    max_daily_loss_pct = Column("maxDailyLossPct", Float, default=0.02)
    max_weekly_loss_pct = Column("maxWeeklyLossPct", Float, default=0.05)
    max_monthly_loss_pct = Column("maxMonthlyLossPct", Float, default=0.10)
    max_position_size_pct = Column("maxPositionSizePct", Float, default=0.10)
    max_order_value = Column("maxOrderValue", Float, default=50000)
    max_orders_per_minute = Column("maxOrdersPerMinute", Integer, default=10)
    max_exposure_per_symbol = Column("maxExposurePerSymbol", Float, default=0.05)
    stop_loss_enabled = Column("stopLossEnabled", Boolean, default=True)
    default_stop_loss_pct = Column("defaultStopLossPct", Float, default=0.02)
    take_profit_enabled = Column("takeProfitEnabled", Boolean, default=True)
    default_take_profit_pct = Column("defaultTakeProfitPct", Float, default=0.04)
    allowed_asset_classes = Column("allowedAssetClasses", ARRAY(String))
    allowed_exchanges = Column("allowedExchanges", ARRAY(String))
    trading_hours_only = Column("tradingHoursOnly", Boolean, default=True)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="risk_profile")

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    strategy_type = Column("strategyType", String, nullable=False)
    asset_class = Column("assetClass", Enum(AssetClass, name="AssetClass"), nullable=False)
    symbols = Column(ARRAY(String))
    timeframe = Column(Enum(TimeFrame, name="TimeFrame"), nullable=False)
    status = Column(Enum(StrategyStatus, name="StrategyStatus"), default=StrategyStatus.DRAFT)
    
    # Strategy Parameters (JSON)
    parameters = Column(JSON)
    risk_parameters = Column("riskParameters", JSON)
    
    # Trading Configuration
    max_positions = Column("maxPositions", Integer, default=5)
    capital_allocated = Column("capitalAllocated", Float, default=100000)
    
    # Performance Metrics
    total_pnl = Column("totalPnl", Float, default=0)
    total_trades = Column("totalTrades", Integer, default=0)
    winning_trades = Column("winningTrades", Integer, default=0)
    losing_trades = Column("losingTrades", Integer, default=0)
    win_rate = Column("winRate", Float, default=0)
    max_drawdown = Column("maxDrawdown", Float, default=0)
    
    # Scheduling
    start_time = Column("startTime", String)
    end_time = Column("endTime", String)
    active_days = Column("activeDays", ARRAY(String))
    
    # Versioning and Execution
    version = Column(Integer, default=1)
    last_executed_at = Column("lastExecutedAt", DateTime)
    
    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy", cascade="all, delete-orphan")
    strategy_logs = relationship("StrategyLog", back_populates="strategy", cascade="all, delete-orphan")
    strategy_configs = relationship("StrategyConfig", back_populates="strategy", cascade="all, delete-orphan")

class StrategyLog(Base):
    __tablename__ = "strategy_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column("strategyId", String, ForeignKey("strategies.id"), nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON)
    timestamp = Column(DateTime, default=func.now())

    strategy = relationship("Strategy", back_populates="strategy_logs")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    strategy_id = Column("strategyId", String, ForeignKey("strategies.id"))
    
    # Order Details
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    side = Column(Enum(OrderSide, name="OrderSide"), nullable=False)
    order_type = Column("orderType", Enum(OrderType, name="OrderType"), nullable=False)
    product_type = Column("productType", Enum(ProductType, name="ProductType"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float)  # Made nullable to match Prisma schema
    trigger_price = Column("triggerPrice", Float)
    variety = Column(String, default="NORMAL")
    
    # Execution Details
    broker_order_id = Column("brokerOrderId", String)
    status = Column(Enum(OrderStatus, name="OrderStatus"), default=OrderStatus.PENDING)
    status_message = Column("statusMessage", String)
    filled_quantity = Column("filledQuantity", Integer, default=0)
    average_price = Column("averagePrice", Float)
    
    # Metadata
    parent_order_id = Column("parentOrderId", String, ForeignKey("orders.id"))
    tags = Column(ARRAY(String))
    notes = Column(String)
    
    # Timestamps
    placed_at = Column("placedAt", DateTime)
    executed_at = Column("executedAt", DateTime)
    cancelled_at = Column("cancelledAt", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")
    parent_order = relationship("Order", remote_side=[id], foreign_keys=[parent_order_id])
    child_orders = relationship("Order", foreign_keys=[parent_order_id], overlaps="parent_order")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    order_id = Column("orderId", String, ForeignKey("orders.id"), nullable=False)
    
    # Trade Details
    trade_id = Column("tradeId", String)
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    side = Column(Enum(OrderSide, name="OrderSide"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    product_type = Column("productType", Enum(ProductType, name="ProductType"), nullable=False)
    order_type = Column("orderType", Enum(OrderType, name="OrderType"), nullable=False)
    
    # Fees & Charges
    brokerage = Column(Float, default=0)
    taxes = Column(Float, default=0)
    total_charges = Column("totalCharges", Float, default=0)
    net_amount = Column("netAmount", Float, nullable=False)
    
    # Timestamps
    trade_timestamp = Column("tradeTimestamp", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())

    # Relations
    user = relationship("User", back_populates="trades")
    order = relationship("Order", back_populates="trades")

class Position(Base):
    __tablename__ = "positions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    product_type = Column("productType", Enum(ProductType, name="ProductType"), nullable=False)
    
    # Position Details
    quantity = Column(Integer, nullable=False)
    average_price = Column("averagePrice", Float, nullable=False)
    last_traded_price = Column("lastTradedPrice", Float, nullable=False)
    pnl = Column(Float, nullable=False)
    realized_pnl = Column("realizedPnl", Float, default=0)
    
    # Market Data
    market_value = Column("marketValue", Float, nullable=False)
    day_change = Column("dayChange", Float, default=0)
    day_change_pct = Column("dayChangePct", Float, default=0)
    
    # Metadata
    first_buy_date = Column("firstBuyDate", DateTime)
    last_trade_date = Column("lastTradeDate", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="positions")

class Balance(Base):
    __tablename__ = "balances"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Cash Balances
    available_cash = Column("availableCash", Float, default=0)
    used_margin = Column("usedMargin", Float, default=0)
    total_balance = Column("totalBalance", Float, default=0)
    
    # Portfolio Values
    portfolio_value = Column("portfolioValue", Float, default=0)
    total_pnl = Column("totalPnl", Float, default=0)
    day_pnl = Column("dayPnl", Float, default=0)
    
    # Limits
    buying_power = Column("buyingPower", Float, default=0)
    margin_used = Column("marginUsed", Float, default=0)
    margin_available = Column("marginAvailable", Float, default=0)
    
    # Timestamps
    last_updated = Column("lastUpdated", DateTime, default=func.now())
    created_at = Column("createdAt", DateTime, default=func.now())

    # Relations
    user = relationship("User", back_populates="balance")

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    symbols = Column(ARRAY(String))
    is_default = Column("isDefault", Boolean, default=False)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="watchlists")

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    
    # OHLCV Data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Additional Data
    previous_close = Column("previousClose", Float)
    change = Column(Float)
    change_pct = Column("changePct", Float)
    
    # Metadata
    timestamp = Column(DateTime, nullable=False)
    timeframe = Column(Enum(TimeFrame, name="TimeFrame"), nullable=False)
    created_at = Column("createdAt", DateTime, default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType, name="NotificationType"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON)
    status = Column(Enum(NotificationStatus, name="NotificationStatus"), default=NotificationStatus.UNREAD)
    created_at = Column("createdAt", DateTime, default=func.now())
    read_at = Column("readAt", DateTime)

    user = relationship("User", back_populates="notifications")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    condition = Column(String, nullable=False)
    target_price = Column("targetPrice", Float, nullable=False)
    is_active = Column("isActive", Boolean, default=True)
    is_triggered = Column("isTriggered", Boolean, default=False)
    triggered_at = Column("triggeredAt", DateTime)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="alerts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"))
    action = Column(Enum(AuditAction, name="AuditAction"), nullable=False)
    resource = Column(String)
    details = Column(JSON)
    ip_address = Column("ipAddress", String)
    user_agent = Column("userAgent", String)
    timestamp = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="audit_logs")

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    description = Column(String)
    is_public = Column("isPublic", Boolean, default=False)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

# ============================================================================
# ENHANCED STRATEGY EXECUTION
# ============================================================================

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

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    strategy_id = Column("strategyId", String, ForeignKey("strategies.id"))
    name = Column(String, unique=True, nullable=False)
    class_name = Column("className", String, nullable=False)
    module_path = Column("modulePath", String, nullable=False)
    config_json = Column("configJson", JSON, nullable=False)
    status = Column(Enum(StrategyConfigStatus, name="StrategyConfigStatus"), default=StrategyConfigStatus.ACTIVE)
    auto_start = Column("autoStart", Boolean, default=True)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="strategy_configs")
    strategy = relationship("Strategy", back_populates="strategy_configs")
    commands = relationship("StrategyCommand", back_populates="strategy_config", cascade="all, delete-orphan")
    metrics = relationship("StrategyMetric", back_populates="strategy_config", cascade="all, delete-orphan")

class StrategyCommand(Base):
    __tablename__ = "strategy_commands"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_config_id = Column("strategyConfigId", String, ForeignKey("strategy_configs.id"), nullable=False)
    command = Column(Enum(StrategyCommandType, name="StrategyCommandType"), nullable=False)
    parameters = Column(JSON)
    status = Column(Enum(CommandStatus, name="CommandStatus"), default=CommandStatus.PENDING)
    created_at = Column("createdAt", DateTime, default=func.now())
    executed_at = Column("executedAt", DateTime)

    # Relations
    strategy_config = relationship("StrategyConfig", back_populates="commands")

class StrategyMetric(Base):
    __tablename__ = "strategy_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_config_id = Column("strategyConfigId", String, ForeignKey("strategy_configs.id"), nullable=False)
    timestamp = Column(DateTime, default=func.now())
    pnl = Column(Numeric, default=0)
    positions_count = Column("positionsCount", Integer, default=0)
    orders_count = Column("ordersCount", Integer, default=0)
    success_rate = Column("successRate", Numeric, default=0)
    metrics_json = Column("metricsJson", JSON)

    # Relations
    strategy_config = relationship("StrategyConfig", back_populates="metrics")

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Real-time alerts (Redis-based)
    order_execution = Column("orderExecution", Boolean, default=True)
    strategy_status = Column("strategyStatus", Boolean, default=True)
    price_alerts = Column("priceAlerts", Boolean, default=True)
    risk_violations = Column("riskViolations", Boolean, default=True)
    
    # SMS alerts (critical only)
    sms_risk_violations = Column("smsRiskViolations", Boolean, default=True)
    sms_order_failures = Column("smsOrderFailures", Boolean, default=True)
    sms_account_security = Column("smsAccountSecurity", Boolean, default=True)
    sms_system_downtime = Column("smsSystemDowntime", Boolean, default=True)
    
    # Email notifications
    email_daily_summary = Column("emailDailySummary", Boolean, default=False)
    email_weekly_report = Column("emailWeeklyReport", Boolean, default=True)
    email_monthly_statement = Column("emailMonthlyStatement", Boolean, default=True)
    email_regulatory = Column("emailRegulatory", Boolean, default=True)
    
    # Alert frequency controls
    max_alerts_per_minute = Column("maxAlertsPerMinute", Integer, default=10)
    quiet_hours_start = Column("quietHoursStart", String)  # HH:MM format
    quiet_hours_end = Column("quietHoursEnd", String)      # HH:MM format
    
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="notification_settings")

class AlertTemplate(Base):
    __tablename__ = "alert_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column("userId", String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # User-friendly name
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    condition = Column(String, nullable=False)  # JSON condition for Redis processing
    message = Column(String)  # Custom alert message
    is_active = Column("isActive", Boolean, default=True)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="alert_templates") 