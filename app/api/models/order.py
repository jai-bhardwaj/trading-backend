# app/api/models/order.py
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class OrderCreate(BaseModel):
    """Request model for creating an order via API."""

    user_id: str = Field(..., json_schema_extra={"example": "user123"})
    symbol: str = Field(..., json_schema_extra={"example": "SBIN-EQ"})
    exchange: Literal["NSE", "BSE", "NFO", "MCX", "CDS", "BFO"] = Field(
        ..., json_schema_extra={"example": "NSE"}
    )
    product_type: str = Field(..., json_schema_extra={"example": "INTRADAY"})
    order_type: Literal["MARKET", "LIMIT", "SL", "SL-M"] = Field(
        ..., json_schema_extra={"example": "LIMIT"}
    )
    side: Literal["BUY", "SELL"] = Field(..., json_schema_extra={"example": "BUY"})
    quantity: int = Field(..., gt=0, json_schema_extra={"example": 10})

    price: Optional[float] = Field(None, json_schema_extra={"example": 350.50})
    trigger_price: Optional[float] = Field(None, json_schema_extra={"example": 348.00})

    variety: Optional[str] = Field("NORMAL", json_schema_extra={"example": "NORMAL"})
    tag: Optional[str] = Field(None, json_schema_extra={"example": "my_strategy_tag"})

    # --- Target Broker Selection ---
    broker_id: str = Field(..., json_schema_extra={"example": "angelone"})
    is_paper_trade: bool = Field(
        False,
        description="Set to true to force use of mock_broker, overrides broker_id for execution.",
    )

    # --- Pydantic Validators ---
    @field_validator("price", mode="before")
    @classmethod
    def check_price(cls, v, info):
        order_type = info.data.get("order_type")
        if order_type in ["LIMIT", "SL"] and v is None:
            raise ValueError(f"Price is required for {order_type} orders")
        if order_type not in ["LIMIT", "SL"] and v is not None:
            # Optional: warn or ignore price for non-limit/sl orders? Ignore for now.
            pass
        return v

    @field_validator("trigger_price", mode="before")
    @classmethod
    def check_trigger_price(cls, v, info):
        order_type = info.data.get("order_type")
        if order_type in ["SL", "SL-M"] and v is None:
            raise ValueError(f"Trigger price is required for {order_type} orders")
        return v

    @field_validator("broker_id", mode="before")
    @classmethod
    def check_broker_id(cls, v, info):
        # Ensure broker_id isn't mock if is_paper_trade is False (or handle in dependency)
        # Simple check here
        if info.data.get("is_paper_trade") is False and v == "mock_broker":
            raise ValueError(
                "Cannot select 'mock_broker' when 'is_paper_trade' is false. Use a live broker ID."
            )
        return v


class OrderResponse(BaseModel):
    """Response model after placing/cancelling/querying an order."""

    # Fields common to most responses
    status: str = Field(..., json_schema_extra={"example": "PLACED"})
    message: Optional[str] = None
    broker_order_id: Optional[str] = Field(
        None, json_schema_extra={"example": "25050400000123"}
    )
    internal_order_id: Optional[str] = Field(
        None, json_schema_extra={"example": "mock_xyz"}
    )
    broker: Optional[str] = Field(None, json_schema_extra={"example": "AngelOneBroker"})

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
    order_timestamp: Optional[str] = None  # ISO format string preferably
