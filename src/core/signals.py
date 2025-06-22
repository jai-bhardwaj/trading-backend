"""
Enterprise Trading Signal System
Future-proof, extensible, maintainable signal format
Supports all order types with comprehensive metadata
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import json

class SignalAction(Enum):
    """Trading signal actions"""
    BUY = "BUY"
    SELL = "SELL"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    SQUARE_OFF = "SQUARE_OFF"

class OrderType(Enum):
    """Angel One supported order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "STOPLOSS_LIMIT"
    STOPLOSS_MARKET = "STOPLOSS_MARKET"
    AMO = "AMO"  # After Market Order
    CO = "CO"    # Cover Order
    BO = "BO"    # Bracket Order

class ProductType(Enum):
    """Product types for different segments"""
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    BO = "BO"
    CO = "CO"

class TimeInForce(Enum):
    """Order validity"""
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    GTD = "GTD"  # Good Till Date

class SignalPriority(Enum):
    """Signal execution priority"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class RiskParameters:
    """Risk management parameters"""
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    max_loss_per_trade: Optional[Decimal] = None
    max_position_size: Optional[Decimal] = None
    trailing_stop: Optional[Decimal] = None
    
    # Advanced risk controls
    max_drawdown_limit: Optional[Decimal] = None
    correlation_limit: Optional[float] = None  # For portfolio risk
    sector_exposure_limit: Optional[float] = None

@dataclass
class OrderSpecification:
    """Detailed order specification"""
    order_type: OrderType
    product_type: ProductType
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Price specifications
    price: Optional[Decimal] = None  # For LIMIT orders
    trigger_price: Optional[Decimal] = None  # For SL orders
    disclosed_quantity: Optional[int] = None
    
    # Bracket/Cover order specific
    target_price: Optional[Decimal] = None
    stoploss_price: Optional[Decimal] = None
    trailing_stoploss: Optional[Decimal] = None
    
    # Validity
    validity_date: Optional[datetime] = None  # For GTD orders
    
    def to_angel_one_format(self) -> Dict[str, Any]:
        """Convert to Angel One API format"""
        order_data = {
            "ordertype": self.order_type.value,
            "producttype": self.product_type.value,
            "duration": self.time_in_force.value
        }
        
        if self.price:
            order_data["price"] = str(self.price)
        if self.trigger_price:
            order_data["triggerprice"] = str(self.trigger_price)
        if self.disclosed_quantity:
            order_data["disclosedquantity"] = str(self.disclosed_quantity)
            
        return order_data

@dataclass
class StrategyMetadata:
    """Strategy identification and metadata"""
    strategy_id: str
    strategy_name: str
    strategy_version: str
    strategy_type: str  # "momentum", "mean_reversion", "arbitrage", etc.
    
    # Performance tracking
    backtest_sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    
    # Strategy parameters (for debugging/analysis)
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MarketContext:
    """Market context when signal was generated"""
    market_session: str  # "PRE_OPEN", "NORMAL", "CLOSING", "POST_MARKET"
    volatility_regime: Optional[str] = None  # "LOW", "NORMAL", "HIGH"
    market_trend: Optional[str] = None  # "BULLISH", "BEARISH", "SIDEWAYS"
    
    # Technical context
    support_level: Optional[Decimal] = None
    resistance_level: Optional[Decimal] = None
    volume_profile: Optional[str] = None  # "HIGH", "NORMAL", "LOW"

@dataclass
class TradingSignal:
    """
    Comprehensive trading signal format
    Future-proof, extensible, maintainable
    """
    
    # Core identification
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Trading specifications
    symbol: str = ""
    exchange: str = ""
    action: SignalAction = SignalAction.BUY
    quantity: int = 0
    
    # Order details
    order_spec: OrderSpecification = field(default_factory=lambda: OrderSpecification(
        order_type=OrderType.MARKET,
        product_type=ProductType.INTRADAY
    ))
    
    # Strategy information
    strategy: StrategyMetadata = field(default_factory=lambda: StrategyMetadata(
        strategy_id="", strategy_name="", strategy_version="1.0", strategy_type=""
    ))
    
    # Risk management
    risk_params: RiskParameters = field(default_factory=RiskParameters)
    
    # Market context
    market_context: MarketContext = field(default_factory=MarketContext)
    
    # Execution control
    priority: SignalPriority = SignalPriority.NORMAL
    max_execution_delay: int = 30  # seconds
    allow_partial_fills: bool = True
    
    # Future extensibility
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Internal tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None  # For tracking related signals
    
    def __post_init__(self):
        """Validation and post-processing"""
        if not self.signal_id:
            self.signal_id = str(uuid.uuid4())
        
        if not self.expires_at:
            # Default expiry: 1 hour for intraday, 1 day for delivery
            if self.order_spec.product_type == ProductType.INTRADAY:
                from datetime import timedelta
                self.expires_at = self.created_at + timedelta(hours=1)
            else:
                from datetime import timedelta
                self.expires_at = self.created_at + timedelta(days=1)
    
    def is_expired(self) -> bool:
        """Check if signal has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        
        # Convert datetime objects to ISO format
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Create from dictionary"""
        # Handle datetime conversion
        datetime_fields = ['timestamp', 'created_at', 'expires_at']
        for field_name in datetime_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TradingSignal':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> List[str]:
        """Validate signal data and return list of errors"""
        errors = []
        
        if not self.symbol:
            errors.append("Symbol is required")
        
        if not self.exchange:
            errors.append("Exchange is required")
            
        if self.quantity <= 0:
            errors.append("Quantity must be positive")
            
        if not self.strategy.strategy_id:
            errors.append("Strategy ID is required")
        
        # Order type specific validations
        if self.order_spec.order_type == OrderType.LIMIT and not self.order_spec.price:
            errors.append("Price required for LIMIT orders")
            
        if self.order_spec.order_type in [OrderType.STOPLOSS_LIMIT, OrderType.STOPLOSS_MARKET]:
            if not self.order_spec.trigger_price:
                errors.append("Trigger price required for stop loss orders")
        
        return errors
    
    def get_execution_key(self) -> str:
        """Get unique key for execution tracking"""
        return f"{self.strategy.strategy_id}_{self.symbol}_{self.signal_id[:8]}"

# Factory functions for common signal types
def create_market_buy_signal(
    symbol: str,
    exchange: str,
    quantity: int,
    strategy_id: str,
    strategy_name: str,
    **kwargs
) -> TradingSignal:
    """Create a simple market buy signal"""
    return TradingSignal(
        symbol=symbol,
        exchange=exchange,
        action=SignalAction.BUY,
        quantity=quantity,
        order_spec=OrderSpecification(
            order_type=OrderType.MARKET,
            product_type=ProductType.INTRADAY
        ),
        strategy=StrategyMetadata(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_version="1.0",
            strategy_type="manual"
        ),
        **kwargs
    )

def create_limit_order_signal(
    symbol: str,
    exchange: str,
    action: SignalAction,
    quantity: int,
    price: Decimal,
    strategy_id: str,
    strategy_name: str,
    **kwargs
) -> TradingSignal:
    """Create a limit order signal"""
    return TradingSignal(
        symbol=symbol,
        exchange=exchange,
        action=action,
        quantity=quantity,
        order_spec=OrderSpecification(
            order_type=OrderType.LIMIT,
            product_type=ProductType.INTRADAY,
            price=price
        ),
        strategy=StrategyMetadata(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_version="1.0",
            strategy_type="manual"
        ),
        **kwargs
    )

def create_stop_loss_signal(
    symbol: str,
    exchange: str,
    action: SignalAction,
    quantity: int,
    trigger_price: Decimal,
    strategy_id: str,
    strategy_name: str,
    limit_price: Optional[Decimal] = None,
    **kwargs
) -> TradingSignal:
    """Create a stop loss signal"""
    order_type = OrderType.STOPLOSS_LIMIT if limit_price else OrderType.STOPLOSS_MARKET
    
    return TradingSignal(
        symbol=symbol,
        exchange=exchange,
        action=action,
        quantity=quantity,
        order_spec=OrderSpecification(
            order_type=order_type,
            product_type=ProductType.INTRADAY,
            trigger_price=trigger_price,
            price=limit_price
        ),
        strategy=StrategyMetadata(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_version="1.0",
            strategy_type="manual"
        ),
        **kwargs
    ) 