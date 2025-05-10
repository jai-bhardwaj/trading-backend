# app/api/models/order.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal

class OrderCreate(BaseModel):
    """Request model for creating an order via API."""
    user_id: str = Field(..., example="user123")
    symbol: str = Field(..., example="SBIN-EQ") # Broker specific symbol, e.g., SBIN-EQ, NIFTY25MAY2518500CE
    exchange: Literal["NSE", "BSE", "NFO", "MCX", "CDS", "BFO"] = Field(..., example="NSE") # Add more as needed
    product_type: str = Field(..., example="INTRADAY") # DELIVERY, INTRADAY, MARGIN, NORMAL etc. (Broker specific)
    order_type: Literal["MARKET", "LIMIT", "SL", "SL-M"] = Field(..., example="LIMIT")
    side: Literal["BUY", "SELL"] = Field(..., example="BUY")
    quantity: int = Field(..., gt=0, example=10) # Integer quantity

    price: Optional[float] = Field(None, example=350.50) # Required for LIMIT, SL
    trigger_price: Optional[float] = Field(None, example=348.00) # Required for SL, SL-M

    variety: Optional[str] = Field("NORMAL", example="NORMAL") # Broker specific: NORMAL, AMO, STOPLOSS, etc.
    tag: Optional[str] = Field(None, example="my_strategy_tag") # Optional user/strategy tag

    # --- Target Broker Selection ---
    broker_id: str = Field(..., example="angelone") # "angelone" or "mock_broker" etc.
    is_paper_trade: bool = Field(False, description="Set to true to force use of mock_broker, overrides broker_id for execution.")

    # --- Pydantic Validators ---
    @validator('price', always=True)
    def check_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in ['LIMIT', 'SL'] and v is None:
            raise ValueError(f'Price is required for {order_type} orders')
        if order_type not in ['LIMIT', 'SL'] and v is not None:
             # Optional: warn or ignore price for non-limit/sl orders? Ignore for now.
             pass
        return v

    @validator('trigger_price', always=True)
    def check_trigger_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in ['SL', 'SL-M'] and v is None:
            raise ValueError(f'Trigger price is required for {order_type} orders')
        return v

    @validator('broker_id', always=True)
    def check_broker_id(cls, v, values):
         # Ensure broker_id isn't mock if is_paper_trade is False (or handle in dependency)
         # Simple check here
         if values.get('is_paper_trade') is False and v == 'mock_broker':
              raise ValueError("Cannot select 'mock_broker' when 'is_paper_trade' is false. Use a live broker ID.")
         return v


class OrderResponse(BaseModel):
    """Response model after placing/cancelling/querying an order."""
    # Fields common to most responses
    status: str = Field(..., example="PLACED") # e.g., PENDING, PLACED, REJECTED, COMPLETE, CANCELLED, ERROR, NOT_FOUND
    message: Optional[str] = None
    broker_order_id: Optional[str] = Field(None, example="25050400000123") # ID from the broker
    internal_order_id: Optional[str] = Field(None, example="mock_xyz") # ID from our system (useful for mock)
    broker: Optional[str] = Field(None, example="AngelOneBroker") # Class name of broker handling it

    # Fields relevant for order status query
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[int] = None
    filled_quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    average_price: Optional[float] = None
    order_type: Optional[str] = None
    product_type: Optional[str] = None
    trigger_price: Optional[float] = None
    price: Optional[float] = None
    order_timestamp: Optional[str] = None # ISO format string preferably