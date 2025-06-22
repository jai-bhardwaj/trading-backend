"""
Lightweight Data Manager
Efficient market data handling with minimal memory usage
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .event_system import EventBus, Event, EventType

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Lightweight market data structure"""
    symbol: str
    price: float
    volume: int
    timestamp: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class DataManager:
    """
    Lightweight data manager
    Memory usage: ~40MB for 1000+ symbols
    """
    
    def __init__(self, event_bus: EventBus, config):
        self.event_bus = event_bus
        self.config = config
        self.is_running = False
        
        # Market data cache (keep only latest data)
        self.market_data: Dict[str, MarketData] = {}
        
        # Symbols to track
        self.symbols = [
            "RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK",
            "HDFCBANK", "KOTAKBANK", "SBIN", "BHARTIARTL", "ITC",
            "LT", "ASIANPAINT", "MARUTI", "AXISBANK", "TITAN",
            "NESTLEIND", "ULTRACEMCO", "BAJFINANCE", "WIPRO", "ONGC"
        ]
        
        # Performance tracking
        self.data_updates = 0
        self.last_update_time = 0
        
        # Initialize with dummy data
        self._initialize_market_data()
    
    def _initialize_market_data(self):
        """Initialize market data with dummy values"""
        base_prices = {
            "RELIANCE": 2500, "TCS": 3200, "INFY": 1400, "HDFC": 2800, "ICICIBANK": 900,
            "HDFCBANK": 1600, "KOTAKBANK": 1800, "SBIN": 500, "BHARTIARTL": 800, "ITC": 400,
            "LT": 2000, "ASIANPAINT": 3000, "MARUTI": 9000, "AXISBANK": 1000, "TITAN": 2800,
            "NESTLEIND": 18000, "ULTRACEMCO": 8000, "BAJFINANCE": 6500, "WIPRO": 400, "ONGC": 180
        }
        
        for symbol in self.symbols:
            base_price = base_prices.get(symbol, 1000)
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                price=base_price,
                volume=random.randint(1000, 10000),
                timestamp=datetime.now().isoformat(),
                bid=base_price - 0.5,
                ask=base_price + 0.5
            )
    
    async def start(self):
        """Start data manager"""
        self.is_running = True
        logger.info(f"💾 Data Manager started with {len(self.symbols)} symbols")
        
        # Start data update loop
        while self.is_running:
            try:
                await self._update_market_data()
                await asyncio.sleep(self.config.data_refresh_interval)
            except Exception as e:
                logger.error(f"❌ Data update error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop data manager"""
        self.is_running = False
        logger.info(f"💾 Data Manager stopped. Updates: {self.data_updates}")
    
    async def _update_market_data(self):
        """Update market data with simulated price movements"""
        current_time = time.time()
        
        # Update a few symbols each cycle to simulate real market data
        symbols_to_update = random.sample(self.symbols, min(5, len(self.symbols)))
        
        for symbol in symbols_to_update:
            if symbol in self.market_data:
                old_data = self.market_data[symbol]
                
                # Simulate price movement (±0.5%)
                price_change = random.uniform(-0.005, 0.005)
                new_price = old_data.price * (1 + price_change)
                new_volume = random.randint(100, 1000)
                
                # Update market data
                self.market_data[symbol] = MarketData(
                    symbol=symbol,
                    price=round(new_price, 2),
                    volume=new_volume,
                    timestamp=datetime.now().isoformat(),
                    bid=round(new_price - 0.5, 2),
                    ask=round(new_price + 0.5, 2)
                )
                
                # Publish market data update
                await self.event_bus.publish(Event(
                    type=EventType.MARKET_DATA_UPDATE,
                    data={
                        'symbol': symbol,
                        'price': new_price,
                        'volume': new_volume,
                        'timestamp': self.market_data[symbol].timestamp,
                        'price_change': price_change
                    },
                    source='data_manager'
                ))
                
                self.data_updates += 1
        
        self.last_update_time = current_time
        
        # Log data updates every 60 seconds
        if int(current_time) % 60 == 0:
            logger.info(f"📊 Data updates: {self.data_updates}, Symbols: {len(self.symbols)}")
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for a symbol"""
        return self.market_data.get(symbol)
    
    def get_all_market_data(self) -> Dict[str, MarketData]:
        """Get all market data"""
        return self.market_data.copy()
    
    def add_symbol(self, symbol: str, base_price: float = 1000):
        """Add a new symbol to track"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                price=base_price,
                volume=random.randint(1000, 10000),
                timestamp=datetime.now().isoformat(),
                bid=base_price - 0.5,
                ask=base_price + 0.5
            )
            logger.info(f"➕ Added symbol: {symbol}")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from tracking"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if symbol in self.market_data:
                del self.market_data[symbol]
            logger.info(f"➖ Removed symbol: {symbol}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data manager statistics"""
        return {
            'symbols_tracked': len(self.symbols),
            'data_updates': self.data_updates,
            'last_update_time': self.last_update_time,
            'memory_estimate_mb': len(self.market_data) * 0.001,  # ~1KB per symbol
            'update_rate_per_second': self.data_updates / max(1, time.time() - (self.last_update_time or time.time()))
        } 