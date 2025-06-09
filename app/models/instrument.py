"""
Instrument and Exchange Models
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from app.models.base import Base
import enum

class Exchange(enum.Enum):
    """Stock exchange enums"""
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NCDEX = "NCDEX"

class InstrumentType(enum.Enum):
    """Instrument type enums"""
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"

class Instrument(Base):
    """Financial instrument model"""
    __tablename__ = "instruments"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    exchange = Column(Enum(Exchange), nullable=False, index=True)
    instrument_type = Column(Enum(InstrumentType), nullable=False, index=True)
    
    # Trading details
    lot_size = Column(Integer, default=1)
    tick_size = Column(Float, default=0.05)
    
    # Options specific
    strike_price = Column(Float, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    option_type = Column(String(2), nullable=True)  # CE/PE
    
    # Futures specific
    contract_size = Column(Integer, nullable=True)
    
    # Market data
    last_price = Column(Float, nullable=True)
    volume = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=True)
    
    # Metadata
    token = Column(String(50), nullable=True, index=True)  # Broker specific token
    isin = Column(String(12), nullable=True)
    
    def __repr__(self):
        return f"<Instrument(symbol={self.symbol}, exchange={self.exchange})>" 