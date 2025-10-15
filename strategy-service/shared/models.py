"""
Shared models for strategy service
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class MarketDataTick:
    """Market data tick from Redis Stream"""
    symbol: str
    token: str
    ltp: float  # Last traded price
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    bid: float
    ask: float
    open: float
    close: float
    timestamp: datetime
    exchange_timestamp: datetime
    raw_data: Dict[str, Any] = field(default_factory=dict)

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
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    strategy_id: str
    symbols: List[str]
    parameters: Dict[str, Any]
    enabled: bool = True
    redis_url: str = "redis://redis:6379"
    consumer_group: str = "strategy_consumers"
    signal_channel: str = "strategy_signals"

@dataclass
class StrategyStats:
    """Strategy performance statistics"""
    strategy_id: str
    signals_generated: int = 0
    last_signal_time: Optional[datetime] = None
    ticks_processed: int = 0
    errors_count: int = 0
    uptime_start: datetime = field(default_factory=datetime.now)
    is_healthy: bool = True
    last_error: Optional[str] = None
