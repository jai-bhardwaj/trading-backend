#!/usr/bin/env python3
"""
Market Data Module - Real-time market data processing
Modular component for market data operations
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Market data for a symbol"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    bid: float = 0.0
    ask: float = 0.0
    high: float = 0.0
    low: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0

class MarketDataModule:
    """Modular market data processing"""
    
    def __init__(self):
        self.market_data: Dict[str, MarketData] = {}
        self.subscribers: List[str] = []
        self.running = False
        self.update_interval = 0.1  # 100ms for real-time
        
    async def initialize(self):
        """Initialize market data module"""
        logger.info("🚀 Initializing Market Data Module...")
        self.running = True
        
        # Start market data updates
        asyncio.create_task(self._market_data_loop())
        
        logger.info("✅ Market Data Module initialized")
    
    async def _market_data_loop(self):
        """Real-time market data update loop"""
        while self.running:
            try:
                await self._update_market_data()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                await asyncio.sleep(1)
    
    async def _update_market_data(self):
        """Update market data for all symbols"""
        symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC"]
        
        for symbol in symbols:
            # Generate realistic market data
            current_price = self._generate_price(symbol)
            volume = random.randint(1000, 10000)
            
            # Calculate bid/ask spread
            spread = current_price * 0.001  # 0.1% spread
            bid = current_price - spread
            ask = current_price + spread
            
            # Calculate high/low
            high = current_price * (1 + random.uniform(0, 0.02))
            low = current_price * (1 - random.uniform(0, 0.02))
            
            # Calculate change
            previous_price = self.market_data.get(symbol, MarketData(symbol, current_price, 0, datetime.utcnow())).price
            change = current_price - previous_price
            change_percent = (change / previous_price) * 100 if previous_price > 0 else 0
            
            # Create market data
            market_data = MarketData(
                symbol=symbol,
                price=current_price,
                volume=volume,
                timestamp=datetime.utcnow(),
                bid=bid,
                ask=ask,
                high=high,
                low=low,
                change=change,
                change_percent=change_percent
            )
            
            self.market_data[symbol] = market_data
    
    def _generate_price(self, symbol: str) -> float:
        """Generate realistic price for symbol"""
        base_prices = {
            "RELIANCE": 2500,
            "TCS": 3800,
            "INFY": 1500,
            "HDFC": 1600,
            "ICICIBANK": 900,
            "SBIN": 600,
            "BHARTIARTL": 800,
            "ITC": 400
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # Add some volatility
        volatility = 0.02  # 2% volatility
        change = random.uniform(-volatility, volatility)
        
        return base_price * (1 + change)
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get market data for symbols"""
        result = {}
        
        for symbol in symbols:
            symbol_upper = symbol.upper()
            data = self.market_data.get(symbol_upper)
            
            if data:
                result[symbol_upper] = {
                    "symbol": data.symbol,
                    "price": data.price,
                    "volume": data.volume,
                    "bid": data.bid,
                    "ask": data.ask,
                    "high": data.high,
                    "low": data.low,
                    "change": data.change,
                    "change_percent": data.change_percent,
                    "timestamp": data.timestamp.isoformat()
                }
        
        return result
    
    async def get_all_market_data(self) -> Dict[str, Dict]:
        """Get market data for all symbols"""
        return await self.get_market_data(list(self.market_data.keys()))
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to symbol updates"""
        symbol_upper = symbol.upper()
        if symbol_upper not in self.subscribers:
            self.subscribers.append(symbol_upper)
            logger.info(f"Subscribed to {symbol_upper}")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from symbol updates"""
        symbol_upper = symbol.upper()
        if symbol_upper in self.subscribers:
            self.subscribers.remove(symbol_upper)
            logger.info(f"Unsubscribed from {symbol_upper}")
    
    async def get_subscribed_symbols(self) -> List[str]:
        """Get list of subscribed symbols"""
        return self.subscribers.copy()
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        symbol_upper = symbol.upper()
        data = self.market_data.get(symbol_upper)
        return data.price if data else None
    
    async def stop(self):
        """Stop market data module"""
        self.running = False
        logger.info("🔄 Market Data Module stopped")

# Global market data module instance
market_data_module = MarketDataModule() 