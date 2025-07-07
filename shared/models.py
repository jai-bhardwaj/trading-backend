"""
Shared models for the trading system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    strategy_id: str
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    price: float
    quantity: int
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

@dataclass
class Order:
    """Order structure"""
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    strategy_id: str
    created_at: datetime
    broker_order_id: Optional[str] = None
    filled_quantity: int = 0
    filled_price: float = 0.0
    error_message: Optional[str] = None

@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    ltp: float  # Last traded price
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    bid: float
    ask: float
    timestamp: datetime

@dataclass
class User:
    """User structure"""
    user_id: str
    name: str
    email: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    strategy_id: str
    strategy_type: str
    symbols: List[str]
    parameters: Dict
    enabled: bool = True
    risk_level: str = "MEDIUM"
    max_position_size: float = 100000.0
    stop_loss_percent: float = 0.05
    take_profit_percent: float = 0.10 