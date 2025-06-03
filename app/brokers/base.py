"""
Comprehensive Broker Architecture - Extensible multi-broker support

This module provides a robust, extensible architecture for supporting multiple brokers
with standardized interfaces, proper error handling, and database integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import asyncio

from app.models.base import (
    BrokerName, OrderSide, OrderType, ProductType, OrderStatus,
    Order as DBOrder, Trade as DBTrade, Position as DBPosition, 
    Balance as DBBalance, BrokerConfig as DBBrokerConfig
)

logger = logging.getLogger(__name__)

@dataclass
class BrokerOrder:
    """Standardized order structure across all brokers"""
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    product_type: ProductType
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    variety: str = "NORMAL"
    
    # Execution details
    broker_order_id: Optional[str] = None
    status: Optional[OrderStatus] = None
    status_message: Optional[str] = None
    filled_quantity: int = 0
    average_price: Optional[float] = None
    
    # Metadata
    symbol_token: Optional[str] = None  # For brokers that need symbol tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

@dataclass
class BrokerPosition:
    """Standardized position structure across all brokers"""
    symbol: str
    exchange: str
    product_type: ProductType
    quantity: int
    average_price: float
    last_traded_price: float
    pnl: float
    market_value: float
    day_change: float = 0.0
    day_change_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class BrokerBalance:
    """Standardized balance structure across all brokers"""
    available_cash: float
    used_margin: float
    total_balance: float
    buying_power: float
    portfolio_value: float = 0.0
    total_pnl: float = 0.0
    day_pnl: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class BrokerTrade:
    """Standardized trade structure across all brokers"""
    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    side: OrderSide
    quantity: int
    price: float
    trade_timestamp: datetime
    brokerage: float = 0.0
    taxes: float = 0.0
    total_charges: float = 0.0
    net_amount: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['trade_timestamp'] = self.trade_timestamp.isoformat()
        return result

@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'previous_close': self.previous_close,
            'change': self.change,
            'change_pct': self.change_pct
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create from dictionary"""
        return cls(
            symbol=data['symbol'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            previous_close=data.get('previous_close'),
            change=data.get('change'),
            change_pct=data.get('change_pct')
        )

# Broker-specific exceptions
class BrokerError(Exception):
    """Base exception for broker-related errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, broker_response: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.broker_response = broker_response
        super().__init__(self.message)

class AuthenticationError(BrokerError):
    """Authentication failed with broker"""
    pass

class OrderError(BrokerError):
    """Order placement/modification failed"""
    pass

class InsufficientFundsError(BrokerError):
    """Insufficient funds for order"""
    pass

class SymbolNotFoundError(BrokerError):
    """Symbol not found or not tradeable"""
    pass

class RateLimitError(BrokerError):
    """API rate limit exceeded"""
    pass

class BrokerInterface(ABC):
    """
    Abstract base class for all broker implementations
    
    This interface ensures consistency across different broker implementations
    and provides a standardized way to interact with various brokers.
    """
    
    def __init__(self, config: DBBrokerConfig):
        """
        Initialize broker with database configuration
        
        Args:
            config: BrokerConfig from database
        """
        self.config = config
        self.broker_name = config.broker_name
        self.is_authenticated = False
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._session = None
        
    @property
    @abstractmethod
    def supported_exchanges(self) -> List[str]:
        """List of exchanges supported by this broker"""
        pass
    
    @property
    @abstractmethod
    def supported_product_types(self) -> List[ProductType]:
        """List of product types supported by this broker"""
        pass
    
    @property
    @abstractmethod
    def supported_order_types(self) -> List[OrderType]:
        """List of order types supported by this broker"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the broker
        
        Returns:
            bool: True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def place_order(self, order: BrokerOrder) -> str:
        """
        Place an order with the broker
        
        Args:
            order: BrokerOrder object with order details
            
        Returns:
            str: Broker order ID
            
        Raises:
            OrderError: If order placement fails
            InsufficientFundsError: If insufficient funds
            SymbolNotFoundError: If symbol not found
        """
        pass
    
    @abstractmethod
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        """
        Modify an existing order
        
        Args:
            order_id: Broker order ID
            **kwargs: Fields to modify (price, quantity, etc.)
            
        Returns:
            bool: True if modification successful
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Broker order ID
            
        Returns:
            bool: True if cancellation successful
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> BrokerOrder:
        """
        Get status of an order
        
        Args:
            order_id: Broker order ID
            
        Returns:
            BrokerOrder: Order with current status
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """
        Get all current positions
        
        Returns:
            List[BrokerPosition]: List of current positions
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> BrokerBalance:
        """
        Get account balance and margin information
        
        Returns:
            BrokerBalance: Current balance information
        """
        pass
    
    @abstractmethod
    async def get_trades(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[BrokerTrade]:
        """
        Get trade history
        
        Args:
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            
        Returns:
            List[BrokerTrade]: List of trades
        """
        pass
    
    @abstractmethod
    async def search_symbols(self, query: str, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for trading symbols
        
        Args:
            query: Search query (symbol name or part of it)
            exchange: Optional exchange filter
            
        Returns:
            List[Dict]: List of matching symbols with details
        """
        pass
    
    # Optional methods that brokers can override
    async def get_market_data(self, symbol: str, exchange: str) -> Optional[MarketData]:
        """
        Get real-time market data for a symbol
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            MarketData: Market data or None if not supported
        """
        return None
    
    async def subscribe_to_feeds(self, symbols: List[str], callback=None) -> bool:
        """
        Subscribe to real-time data feeds
        
        Args:
            symbols: List of symbols to subscribe
            callback: Optional callback function for data updates
            
        Returns:
            bool: True if subscription successful
        """
        return False
    
    async def get_historical_data(self, symbol: str, exchange: str, 
                                 from_date: str, to_date: str, 
                                 interval: str = "1D") -> List[Dict[str, Any]]:
        """
        Get historical market data
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            interval: Data interval (1D, 1H, etc.)
            
        Returns:
            List[Dict]: Historical OHLCV data
        """
        return []
    
    async def disconnect(self):
        """Clean up and disconnect from broker"""
        self.is_authenticated = False
        if self._session:
            await self._session.close()
        self.logger.info(f"Disconnected from {self.broker_name.value}")
    
    def validate_order(self, order: BrokerOrder) -> bool:
        """
        Validate order before placing
        
        Args:
            order: Order to validate
            
        Returns:
            bool: True if order is valid
            
        Raises:
            OrderError: If order validation fails
        """
        # Basic validation
        if not order.symbol:
            raise OrderError("Symbol is required")
        
        if order.quantity <= 0:
            raise OrderError("Quantity must be positive")
        
        if order.order_type == OrderType.LIMIT and not order.price:
            raise OrderError("Price is required for limit orders")
        
        if order.order_type in [OrderType.SL, OrderType.SL_M] and not order.trigger_price:
            raise OrderError("Trigger price is required for stop loss orders")
        
        # Broker-specific validation
        if order.exchange not in self.supported_exchanges:
            raise OrderError(f"Exchange {order.exchange} not supported by {self.broker_name.value}")
        
        if order.product_type not in self.supported_product_types:
            raise OrderError(f"Product type {order.product_type.value} not supported by {self.broker_name.value}")
        
        if order.order_type not in self.supported_order_types:
            raise OrderError(f"Order type {order.order_type.value} not supported by {self.broker_name.value}")
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check broker connection health
        
        Returns:
            Dict: Health status information
        """
        try:
            if not self.is_authenticated:
                await self.authenticate()
            
            # Try to get balance as a health check
            balance = await self.get_balance()
            
            return {
                'status': 'healthy',
                'authenticated': self.is_authenticated,
                'broker': self.broker_name.value,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'authenticated': self.is_authenticated,
                'broker': self.broker_name.value,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

class BrokerRegistry:
    """
    Registry for managing multiple broker implementations
    """
    
    _brokers: Dict[BrokerName, Type[BrokerInterface]] = {}
    _instances: Dict[str, BrokerInterface] = {}
    
    @classmethod
    def register(cls, broker_name: BrokerName, broker_class: Type[BrokerInterface]):
        """
        Register a broker implementation
        
        Args:
            broker_name: BrokerName enum value
            broker_class: Broker class implementing BrokerInterface
        """
        cls._brokers[broker_name] = broker_class
        logger.info(f"Registered broker: {broker_name.value}")
    
    @classmethod
    def get_broker(cls, config: DBBrokerConfig) -> BrokerInterface:
        """
        Get a broker instance
        
        Args:
            config: BrokerConfig from database
            
        Returns:
            BrokerInterface: Broker instance
            
        Raises:
            ValueError: If broker not found
        """
        broker_name = config.broker_name
        
        if broker_name not in cls._brokers:
            available = ", ".join([b.value for b in cls._brokers.keys()])
            raise ValueError(f"Broker '{broker_name.value}' not found. Available: {available}")
        
        # Use config ID as instance key for caching
        instance_key = f"{broker_name.value}_{config.id}"
        
        if instance_key in cls._instances:
            return cls._instances[instance_key]
        
        # Create new instance
        broker_class = cls._brokers[broker_name]
        instance = broker_class(config)
        cls._instances[instance_key] = instance
        
        return instance
    
    @classmethod
    def list_brokers(cls) -> List[BrokerName]:
        """
        List all registered brokers
        
        Returns:
            List[BrokerName]: List of broker names
        """
        return list(cls._brokers.keys())
    
    @classmethod
    def get_supported_brokers(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about supported brokers
        
        Returns:
            Dict: Broker information including supported features
        """
        result = {}
        for broker_name, broker_class in cls._brokers.items():
            # Create a temporary instance to get capabilities
            temp_config = DBBrokerConfig(
                broker_name=broker_name,
                api_key="temp",
                client_id="temp",
                password="temp"
            )
            temp_instance = broker_class(temp_config)
            
            result[broker_name.value] = {
                'name': broker_name.value,
                'class': broker_class.__name__,
                'supported_exchanges': temp_instance.supported_exchanges,
                'supported_product_types': [pt.value for pt in temp_instance.supported_product_types],
                'supported_order_types': [ot.value for ot in temp_instance.supported_order_types],
                'supports_market_data': hasattr(temp_instance, 'get_market_data'),
                'supports_real_time_feeds': hasattr(temp_instance, 'subscribe_to_feeds'),
                'supports_historical_data': hasattr(temp_instance, 'get_historical_data')
            }
        
        return result
    
    @classmethod
    async def health_check_all(cls) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all active broker instances
        
        Returns:
            Dict: Health status for all brokers
        """
        results = {}
        
        for instance_key, broker in cls._instances.items():
            try:
                health = await broker.health_check()
                results[instance_key] = health
            except Exception as e:
                results[instance_key] = {
                    'status': 'error',
                    'error': str(e),
                    'broker': broker.broker_name.value,
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return results
    
    @classmethod
    def clear_instances(cls):
        """Clear all broker instances"""
        cls._instances.clear()

# Decorator for registering brokers
def register_broker(broker_name: BrokerName):
    """
    Decorator to register a broker implementation
    
    Usage:
        @register_broker(BrokerName.ANGEL_ONE)
        class AngelOneBroker(BrokerInterface):
            ...
    """
    def decorator(broker_class):
        BrokerRegistry.register(broker_name, broker_class)
        return broker_class
    return decorator

class BrokerManager:
    """
    High-level broker management class
    
    Provides convenient methods for managing multiple brokers,
    order routing, and portfolio aggregation.
    """
    
    def __init__(self):
        self.active_brokers: Dict[str, BrokerInterface] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def add_broker(self, config: DBBrokerConfig) -> bool:
        """
        Add and authenticate a broker
        
        Args:
            config: Broker configuration from database
            
        Returns:
            bool: True if broker added successfully
        """
        try:
            broker = BrokerRegistry.get_broker(config)
            await broker.authenticate()
            
            self.active_brokers[config.id] = broker
            self.logger.info(f"Added broker: {config.broker_name.value} (ID: {config.id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add broker {config.broker_name.value}: {e}")
            return False
    
    async def remove_broker(self, config_id: str):
        """Remove a broker"""
        if config_id in self.active_brokers:
            await self.active_brokers[config_id].disconnect()
            del self.active_brokers[config_id]
            self.logger.info(f"Removed broker: {config_id}")
    
    async def place_order_with_broker(self, config_id: str, order: BrokerOrder) -> str:
        """
        Place order with specific broker
        
        Args:
            config_id: Broker config ID
            order: Order to place
            
        Returns:
            str: Broker order ID
        """
        if config_id not in self.active_brokers:
            raise ValueError(f"Broker {config_id} not found")
        
        broker = self.active_brokers[config_id]
        return await broker.place_order(order)
    
    async def get_aggregated_positions(self) -> List[BrokerPosition]:
        """
        Get positions from all active brokers
        
        Returns:
            List[BrokerPosition]: Aggregated positions
        """
        all_positions = []
        
        for broker in self.active_brokers.values():
            try:
                positions = await broker.get_positions()
                all_positions.extend(positions)
            except Exception as e:
                self.logger.error(f"Failed to get positions from {broker.broker_name.value}: {e}")
        
        return all_positions
    
    async def get_aggregated_balance(self) -> Dict[str, BrokerBalance]:
        """
        Get balance from all active brokers
        
        Returns:
            Dict[str, BrokerBalance]: Balance by broker
        """
        balances = {}
        
        for config_id, broker in self.active_brokers.items():
            try:
                balance = await broker.get_balance()
                balances[config_id] = balance
            except Exception as e:
                self.logger.error(f"Failed to get balance from {broker.broker_name.value}: {e}")
        
        return balances
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check all active brokers"""
        results = {}
        
        for config_id, broker in self.active_brokers.items():
            results[config_id] = await broker.health_check()
        
        return results

# Global broker manager instance
broker_manager = BrokerManager()
