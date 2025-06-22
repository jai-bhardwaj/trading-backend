"""
Comprehensive Type Definitions for Trading System
Provides type hints and validation for all trading components
"""

from typing import Dict, List, Optional, Union, Tuple, Any, Callable, Protocol
from datetime import datetime
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator

# Core Trading Types
Price = Union[float, Decimal]
Volume = Union[int, float]
Quantity = Union[int, float]
Amount = Union[float, Decimal]

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TradingMode(Enum):
    """Trading modes"""
    LIVE = "LIVE"
    PAPER = "PAPER"
    BACKTEST = "BACKTEST"

class StrategyStatus(Enum):
    """Strategy status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

@dataclass
class PriceData:
    """Price data structure"""
    symbol: str
    price: Price
    volume: Volume
    timestamp: datetime
    bid: Optional[Price] = None
    ask: Optional[Price] = None
    high: Optional[Price] = None
    low: Optional[Price] = None
    open: Optional[Price] = None
    close: Optional[Price] = None

@dataclass
class OrderData:
    """Order data structure"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Quantity
    price: Optional[Price] = None
    stop_price: Optional[Price] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Quantity = 0
    average_price: Optional[Price] = None
    timestamp: datetime = None
    user_id: str = ""

@dataclass
class PositionData:
    """Position data structure"""
    symbol: str
    quantity: Quantity
    average_price: Price
    market_value: Amount
    unrealized_pnl: Amount
    realized_pnl: Amount
    timestamp: datetime

@dataclass
class AccountData:
    """Account data structure"""
    account_id: str
    balance: Amount
    equity: Amount
    margin_used: Amount
    margin_available: Amount
    buying_power: Amount
    positions: List[PositionData]
    timestamp: datetime

# Strategy Types
class StrategySignal(Enum):
    """Strategy signals"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"

@dataclass
class StrategySignalData:
    """Strategy signal data"""
    signal: StrategySignal
    symbol: str
    confidence: float  # 0.0 to 1.0
    quantity: Optional[Quantity] = None
    price: Optional[Price] = None
    reason: str = ""
    timestamp: datetime = None

# Validation Models
class OrderRequest(BaseModel):
    """Order request validation"""
    symbol: str = Field(..., min_length=1, max_length=20)
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Symbol must be alphanumeric')
        return v.upper()

class StrategyConfig(BaseModel):
    """Strategy configuration validation"""
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    enabled: bool = True
    risk_level: str = Field(..., regex=r'^(low|medium|high)$')
    max_position_size: float = Field(..., gt=0)
    stop_loss_percent: Optional[float] = Field(None, ge=0, le=100)
    take_profit_percent: Optional[float] = Field(None, ge=0, le=1000)
    symbols: List[str] = Field(..., min_items=1, max_items=100)
    parameters: Dict[str, Any] = Field(default_factory=dict)

class MarketDataRequest(BaseModel):
    """Market data request validation"""
    symbols: List[str] = Field(..., min_items=1, max_items=100)
    interval: str = Field(..., regex=r'^(1m|5m|15m|30m|1h|4h|1d)$')
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = Field(None, ge=1, le=5000)

# Protocol Definitions
class BrokerProtocol(Protocol):
    """Broker interface protocol"""
    
    def connect(self) -> bool:
        """Connect to broker"""
        ...
    
    def disconnect(self) -> bool:
        """Disconnect from broker"""
        ...
    
    def place_order(self, order: OrderData) -> str:
        """Place order and return order ID"""
        ...
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        ...
    
    def get_account_info(self) -> AccountData:
        """Get account information"""
        ...
    
    def get_positions(self) -> List[PositionData]:
        """Get current positions"""
        ...
    
    def get_market_data(self, symbol: str) -> PriceData:
        """Get market data for symbol"""
        ...

class StrategyProtocol(Protocol):
    """Strategy interface protocol"""
    
    def initialize(self, config: StrategyConfig) -> bool:
        """Initialize strategy"""
        ...
    
    def on_market_data(self, data: PriceData) -> Optional[StrategySignalData]:
        """Process market data and generate signals"""
        ...
    
    def on_order_update(self, order: OrderData) -> None:
        """Handle order updates"""
        ...
    
    def get_status(self) -> StrategyStatus:
        """Get strategy status"""
        ...

class DatabaseProtocol(Protocol):
    """Database interface protocol"""
    
    def connect(self) -> bool:
        """Connect to database"""
        ...
    
    def save_order(self, order: OrderData) -> bool:
        """Save order to database"""
        ...
    
    def save_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Save trade to database"""
        ...
    
    def get_orders(self, filters: Dict[str, Any]) -> List[OrderData]:
        """Get orders with filters"""
        ...

# Function Type Definitions
StrategyFunction = Callable[[PriceData], Optional[StrategySignalData]]
OrderCallback = Callable[[OrderData], None]
ErrorHandler = Callable[[Exception], None]
DataProcessor = Callable[[Any], Any]

# Complex Type Definitions
OrderBook = Dict[str, List[Tuple[Price, Volume]]]  # symbol -> [(price, volume)]
PortfolioWeights = Dict[str, float]  # symbol -> weight
RiskMetrics = Dict[str, Union[float, str]]  # metric_name -> value
PerformanceMetrics = Dict[str, Union[float, int, str]]  # metric_name -> value

# Configuration Types
TradingConfig = Dict[str, Any]
BrokerConfig = Dict[str, Any]
DatabaseConfig = Dict[str, Any]
StrategyParameters = Dict[str, Union[str, int, float, bool]]

# API Response Types
class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class OrderResponse(APIResponse):
    """Order API response"""
    order_id: Optional[str] = None
    status: Optional[OrderStatus] = None

class PositionResponse(APIResponse):
    """Position API response"""
    positions: List[PositionData] = Field(default_factory=list)

class AccountResponse(APIResponse):
    """Account API response"""
    account: Optional[AccountData] = None

# Error Types
class TradingError(Exception):
    """Base trading error"""
    pass

class OrderError(TradingError):
    """Order-related error"""
    pass

class BrokerError(TradingError):
    """Broker-related error"""
    pass

class StrategyError(TradingError):
    """Strategy-related error"""
    pass

class ValidationError(TradingError):
    """Validation error"""
    pass

# Type Aliases for Complex Structures
CandlestickData = Tuple[datetime, Price, Price, Price, Price, Volume]  # OHLCV
TechnicalIndicator = Callable[[List[Price]], List[float]]
RiskCalculator = Callable[[PositionData, PriceData], float]
PerformanceCalculator = Callable[[List[OrderData]], PerformanceMetrics]

# Utility Types
JSONData = Dict[str, Any]
Headers = Dict[str, str]
QueryParams = Dict[str, Union[str, int, float]]
PathParams = Dict[str, str]

# Event Types
class EventType(Enum):
    """System event types"""
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    MARKET_DATA = "MARKET_DATA"
    ERROR = "ERROR"

@dataclass
class SystemEvent:
    """System event data"""
    event_type: EventType
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = ""
    user_id: Optional[str] = None

# Callback Types
EventCallback = Callable[[SystemEvent], None]
MarketDataCallback = Callable[[PriceData], None]
OrderUpdateCallback = Callable[[OrderData], None]
ErrorCallback = Callable[[Exception, str], None]

# Type Guards
def is_valid_price(value: Any) -> bool:
    """Check if value is a valid price"""
    try:
        price = float(value)
        return price > 0
    except (ValueError, TypeError):
        return False

def is_valid_quantity(value: Any) -> bool:
    """Check if value is a valid quantity"""
    try:
        quantity = float(value)
        return quantity > 0
    except (ValueError, TypeError):
        return False

def is_valid_symbol(value: Any) -> bool:
    """Check if value is a valid symbol"""
    if not isinstance(value, str):
        return False
    return len(value) >= 1 and len(value) <= 20 and value.replace('-', '').replace('_', '').isalnum()

# Export all types for easy importing
__all__ = [
    # Basic types
    'Price', 'Volume', 'Quantity', 'Amount',
    
    # Enums
    'OrderType', 'OrderSide', 'OrderStatus', 'TradingMode', 'StrategyStatus', 'StrategySignal', 'EventType',
    
    # Data classes
    'PriceData', 'OrderData', 'PositionData', 'AccountData', 'StrategySignalData', 'SystemEvent',
    
    # Validation models
    'OrderRequest', 'StrategyConfig', 'MarketDataRequest', 'APIResponse', 'OrderResponse', 'PositionResponse', 'AccountResponse',
    
    # Protocols
    'BrokerProtocol', 'StrategyProtocol', 'DatabaseProtocol',
    
    # Function types
    'StrategyFunction', 'OrderCallback', 'ErrorHandler', 'DataProcessor', 'EventCallback', 'MarketDataCallback', 'OrderUpdateCallback', 'ErrorCallback',
    
    # Complex types
    'OrderBook', 'PortfolioWeights', 'RiskMetrics', 'PerformanceMetrics', 'CandlestickData', 'TechnicalIndicator', 'RiskCalculator', 'PerformanceCalculator',
    
    # Configuration types
    'TradingConfig', 'BrokerConfig', 'DatabaseConfig', 'StrategyParameters',
    
    # Utility types
    'JSONData', 'Headers', 'QueryParams', 'PathParams',
    
    # Errors
    'TradingError', 'OrderError', 'BrokerError', 'StrategyError', 'ValidationError',
    
    # Type guards
    'is_valid_price', 'is_valid_quantity', 'is_valid_symbol'
]
