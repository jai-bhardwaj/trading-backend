"""
Market Data Model
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.utils.timezone_utils import ist_utcnow as datetime_now

class MarketDepth(Base):
    """Market depth/order book model"""
    __tablename__ = "market_depth"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Instrument details
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, index=True)
    
    # Depth data (JSON format for flexibility)
    bids = Column(JSON, nullable=True)  # [{"price": 100, "quantity": 50}, ...]
    asks = Column(JSON, nullable=True)  # [{"price": 101, "quantity": 25}, ...]
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime_now, index=True)
    
    def __repr__(self):
        return f"<MarketDepth(symbol={self.symbol}, time={self.timestamp})>" 