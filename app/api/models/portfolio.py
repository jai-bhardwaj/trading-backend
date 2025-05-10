# app/api/models/portfolio.py
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Position Models ---
class PositionModel(BaseModel):
    """API model for representing a single position."""
    symbol: str = Field(..., example="RELIANCE-EQ")
    exchange: str = Field(..., example="NSE")
    product_type: str = Field(..., example="DELIVERY")
    quantity: int = Field(..., example=100) # Negative for short
    average_price: float = Field(..., example=2450.50)
    last_traded_price: Optional[float] = Field(None, example=2500.00)
    pnl: Optional[float] = Field(None, example=5000.00)
    # Add other relevant fields

class PositionsResponse(BaseModel):
    """API response model for listing positions."""
    user_id: str
    broker_id: str
    positions: List[PositionModel]

# --- Balance Models ---
class BalanceModel(BaseModel):
    """API model for representing account balance/margins."""
    available_cash: float = Field(..., example=50000.0)
    margin_used: float = Field(..., example=15000.0)
    total_balance: float = Field(..., example=65000.0) # Equity or equivalent
    # Add other relevant fields as needed

class BalanceResponse(BaseModel):
     """API response model for account balance."""
     user_id: str
     broker_id: str
     balance: BalanceModel

# --- Trade History Models ---
class TradeModel(BaseModel):
    """API model for representing a single executed trade."""
    trade_id: Optional[str] = Field(None, example="T12345") # Broker's trade ID if available
    broker_order_id: str = Field(..., example="25050400000123")
    symbol: str = Field(..., example="TCS-EQ")
    exchange: str = Field(..., example="NSE")
    side: str = Field(..., example="BUY")
    quantity: int = Field(..., example=10)
    price: float = Field(..., example=3205.10)
    product_type: str = Field(..., example="INTRADAY")
    order_type: str = Field(..., example="LIMIT")
    trade_timestamp: str = Field(...) # ISO Format string

class TradeHistoryResponse(BaseModel):
    """API response model for trade history."""
    user_id: str
    broker_id: str
    trades: List[TradeModel]