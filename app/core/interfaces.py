# app/core/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

# --- Domain Models (could also live in app/models/domain.py) ---
# More detailed internal representation than API models

class Order:
    """Internal representation of an order."""
    def __init__(self,
                 user_id: str,
                 symbol: str,          # e.g., "RELIANCE-EQ" or "NIFTY25MAY2518000CE"
                 exchange: str,        # e.g., "NSE", "BSE", "NFO", "MCX"
                 product_type: str,    # e.g., "INTRADAY", "DELIVERY", "MARGIN", "NORMAL" (Broker specific)
                 order_type: str,      # e.g., "MARKET", "LIMIT", "SL", "SL-M"
                 side: str,            # "BUY" or "SELL"
                 quantity: int,        # Use integers for quantity where applicable
                 broker_id: str,       # Identifier like "angelone", "mock_broker"
                 price: Optional[float] = None,       # Required for LIMIT, SL orders
                 trigger_price: Optional[float] = None, # Required for SL, SL-M orders
                 variety: Optional[str] = None,       # Broker specific (e.g., Angel One: "NORMAL", "AMO", "STOPLOSS")
                 tag: Optional[str] = None,           # Optional tag for strategy/user tracking
                 is_paper_trade: bool = False,
                 # Internal state fields
                 internal_order_id: Optional[str] = None, # Our system's unique ID
                 broker_order_id: Optional[str] = None,   # ID from the broker
                 status: str = "PENDING",           # e.g., PENDING, PLACED, REJECTED, OPEN, COMPLETE, CANCELLED, ERROR
                 status_message: Optional[str] = None,
                 filled_quantity: int = 0,
                 average_price: Optional[float] = None,
                 order_timestamp: Optional[Any] = None, # Use datetime objects
                 last_update_timestamp: Optional[Any] = None
                ):
        # Assign all parameters... (example for brevity)
        self.user_id = user_id
        self.symbol = symbol
        self.exchange = exchange
        self.product_type = product_type
        self.order_type = order_type
        self.side = side.upper() # Standardize side
        self.quantity = quantity
        self.broker_id = broker_id
        self.price = price
        self.trigger_price = trigger_price
        self.variety = variety
        self.tag = tag
        self.is_paper_trade = is_paper_trade
        self.internal_order_id = internal_order_id
        self.broker_order_id = broker_order_id
        self.status = status
        self.status_message = status_message
        self.filled_quantity = filled_quantity
        self.average_price = average_price
        self.order_timestamp = order_timestamp
        self.last_update_timestamp = last_update_timestamp

        # Basic Validation
        if self.side not in ["BUY", "SELL"]:
            raise ValueError("Order side must be 'BUY' or 'SELL'")
        if self.order_type in ["LIMIT", "SL"] and self.price is None:
            raise ValueError(f"Price is required for {self.order_type} orders")
        if self.order_type in ["SL", "SL-M"] and self.trigger_price is None:
            raise ValueError(f"Trigger price is required for {self.order_type} orders")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

class Position:
    """Internal representation of a trading position."""
    symbol: str
    exchange: str
    product_type: str
    quantity: int # Can be negative for short positions
    average_price: float
    last_traded_price: Optional[float] = None
    pnl: Optional[float] = None
    # Add more fields as needed (e.g., realised_pnl, unrealised_pnl, value)

class Balance:
    """Internal representation of account balance/margins."""
    available_cash: float
    margin_used: float
    total_balance: float # Could be equity, funds, etc. depends on broker terminology
    # Add many more fields as needed (collateral, exposure, limits etc.)

# --- Interfaces ---

class BrokerInterface(ABC):
    """Abstract Base Class for all broker integrations."""

    @abstractmethod
    async def initialize(self, user_id: str, config: Dict[str, Any]):
        """Initialize the broker connection for a specific user with specific config."""
        # user_id added to handle multi-user sessions if needed by broker/library
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place an order through the broker. Returns dict with broker_order_id, status."""
        pass

    @abstractmethod
    async def cancel_order(self, user_id: str, broker_order_id: str, variety: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an existing order using the broker's order ID."""
        # user_id might be needed for context. Variety often required by brokers.
        pass

    @abstractmethod
    async def get_order_status(self, user_id: str, broker_order_id: str) -> Dict[str, Any]:
        """Get the status details of a specific order from the broker."""
        # Returns a dict representing the full order status from broker perspective
        pass

    @abstractmethod
    async def get_order_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get the history of orders for the day (or a specified period)."""
        pass

    @abstractmethod
    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get current trading positions."""
        pass

    @abstractmethod
    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Get account balance and margin details."""
        pass

    @abstractmethod
    async def get_trade_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get the history of executed trades (fills)."""
        pass

    # Optional: Methods for market data, instrument lookup etc.
    # @abstractmethod
    # async def search_instrument(self, query: str) -> List[Dict[str, Any]]:
    #    pass

# --- Market Interface (Placeholder - Not Implemented in Detail) ---
class MarketInterface(ABC):
    """Abstract Base Class for market-specific logic."""
    @abstractmethod
    def get_market_hours(self, exchange: str, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate_order_details(self, order: Order) -> bool:
        # e.g., check tick size, lot size for derivatives
        pass

# --- Strategy Interface (Placeholder - Not Implemented) ---
class StrategyInterface(ABC):
    """Abstract Base Class for trading strategies."""
    @abstractmethod
    async def initialize(self, config: Dict[str, Any], broker: BrokerInterface):
        pass

    @abstractmethod
    async def on_tick(self, tick_data: Dict[str, Any]):
        pass

    @abstractmethod
    async def on_bar(self, bar_data: Dict[str, Any]):
        pass

    @abstractmethod
    async def on_order_update(self, order_update: Dict[str, Any]):
        pass

    @abstractmethod
    async def on_fill(self, trade_update: Dict[str, Any]):
        pass