"""
Pydantic models for FastAPI endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class UserStrategyConfig(BaseModel):
    id: Optional[str] = None
    user_id: str
    strategy_id: str
    enabled: bool = True
    risk_limits: Optional[Dict] = None
    order_preferences: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UpdateUserStrategyConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    risk_limits: Optional[Dict] = None
    order_preferences: Optional[Dict] = None

class OrderRequest(BaseModel):
    user_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int = Field(gt=0)
    price: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class OrderResponse(BaseModel):
    order_id: str
    status: str
    broker_order_id: Optional[str] = None
    message: str
    error: Optional[str] = None

class Strategy(BaseModel):
    id: str
    name: str
    strategy_type: str
    symbols: List[str]
    parameters: Dict
    enabled: bool
    created_at: datetime
    updated_at: datetime

class Position(BaseModel):
    id: str
    user_id: str
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    market_value: float
    pnl: float
    realized_pnl: float
    day_change: float
    day_change_pct: float
    created_at: datetime
    updated_at: datetime

class Trade(BaseModel):
    id: str
    user_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    net_amount: float
    trade_timestamp: Optional[datetime] = None
    created_at: datetime

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_connected: bool
    redis_connected: bool
    trading_system_active: bool 