#!/usr/bin/env python3
"""
Market Data Handler
Fetches live market data and feeds it to trading strategies
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import aiohttp
from dataclasses import dataclass

from app.strategies.base import MarketData, AssetClass, TimeFrame as StrategyTimeFrame
from app.database import DatabaseManager
from app.models.base import *
from sqlalchemy import select

logger = logging.getLogger(__name__)

@dataclass
class MarketDataConfig:
    """Market data configuration"""
    update_interval: float = 5.0  # seconds
    symbols: List[str] = None
    data_sources: List[str] = None
    enable_websocket: bool = True
    enable_rest_api: bool = True

class MarketDataHandler:
    """
    Market Data Handler
    
    Responsibilities:
    1. Fetch live market data from multiple sources
    2. Normalize data format
    3. Cache recent data
    4. Provide data to strategies
    5. Handle data source failures
    """
    
    def __init__(self, config: Optional[MarketDataConfig] = None):
        self.config = config or MarketDataConfig()
        self.is_running = False
        
        # Data cache
        self.latest_data: Dict[str, MarketData] = {}
        self.historical_cache: Dict[str, List[MarketData]] = {}
        
        # Data sources
        self.websocket_connections: Dict[str, Any] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Performance metrics
        self.total_updates = 0
        self.data_sources_status: Dict[str, bool] = {}
        
    async def initialize(self):
        """Initialize market data handler"""
        logger.info("📡 Initializing Market Data Handler")
        
        try:
            self.session = aiohttp.ClientSession()
            
            # Load symbols from database
            await self.load_symbols_from_database()
            
            # Initialize data sources
            await self.initialize_data_sources()
            
            logger.info("✅ Market Data Handler initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Market Data Handler: {e}")
            raise
    
    async def stop(self):
        """Stop market data handler"""
        logger.info("⏹️ Stopping Market Data Handler")
        self.is_running = False
        
        # Close websocket connections
        for connection in self.websocket_connections.values():
            if hasattr(connection, 'close'):
                await connection.close()
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        logger.info("🏁 Market Data Handler stopped")
    
    async def load_symbols_from_database(self):
        """Load symbols from instrument manager"""
        try:
            from app.core.instrument_manager import get_instrument_manager
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Get instrument manager
            instrument_manager = await get_instrument_manager(db_manager)
            
            # Get all available symbols
            all_symbols = instrument_manager.get_all_symbols()
            
            if all_symbols:
                self.config.symbols = all_symbols[:50]  # Limit for performance
                logger.info(f"📊 Loaded {len(self.config.symbols)} symbols from instrument manager")
            else:
                # Fallback to default symbols
                self.config.symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "TATAMOTORS", "BAJFINANCE", "MARUTI"]
                logger.warning("⚠️ No symbols from instrument manager, using fallback")
            
            await db_manager.close()
            
        except Exception as e:
            logger.error(f"Error loading symbols from instrument manager: {e}")
            # Fallback to default symbols
            self.config.symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "TATAMOTORS", "BAJFINANCE", "MARUTI"]
    
    async def initialize_data_sources(self):
        """Initialize data sources"""
        try:
            # For demo purposes, we'll simulate market data
            # In production, this would connect to real data sources like:
            # - AngelOne API
            # - NSE API
            # - Third-party data providers
            
            logger.info("🔌 Initializing data sources (demo mode)")
            self.data_sources_status['demo_simulator'] = True
            
        except Exception as e:
            logger.error(f"Error initializing data sources: {e}")
    
    async def get_latest_data(self) -> List[MarketData]:
        """Get latest market data for all symbols"""
        try:
            if not self.config.symbols:
                return []
            
            market_data_batch = []
            
            for symbol in self.config.symbols:
                # For demo, generate simulated data
                market_data = await self.generate_demo_data(symbol)
                if market_data:
                    market_data_batch.append(market_data)
                    self.latest_data[symbol] = market_data
            
            self.total_updates += 1
            return market_data_batch
            
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return []
    
    async def generate_demo_data(self, symbol: str) -> Optional[MarketData]:
        """Generate demo market data"""
        try:
            import random
            
            # Get previous price or use base price
            previous_data = self.latest_data.get(symbol)
            base_price = previous_data.close if previous_data else self.get_base_price(symbol)
            
            # Generate realistic price movement
            change_pct = random.uniform(-0.02, 0.02)  # ±2% change
            new_price = base_price * (1 + change_pct)
            
            # Generate OHLC data
            high = new_price * random.uniform(1.001, 1.005)
            low = new_price * random.uniform(0.995, 0.999)
            volume = random.randint(100000, 1000000)
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                open=base_price,
                high=high,
                low=low,
                close=new_price,
                volume=volume,
                asset_class=AssetClass.EQUITY,
                exchange="NSE",
                additional_data={
                    'change': new_price - base_price,
                    'change_pct': change_pct * 100,
                    'previous_close': base_price
                }
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error generating demo data for {symbol}: {e}")
            return None
    
    def get_base_price(self, symbol: str) -> float:
        """Get base price for symbol"""
        base_prices = {
            'RELIANCE': 2500.0,
            'TCS': 3800.0,
            'INFY': 1800.0,
            'HDFC': 1600.0,
            'TATAMOTORS': 900.0,
            'BAJFINANCE': 7000.0,
            'MARUTI': 11000.0
        }
        return base_prices.get(symbol, 1000.0)
    
    async def get_historical_data(self, symbol: str, timeframe: StrategyTimeFrame, 
                                 lookback: int = 100) -> List[MarketData]:
        """Get historical market data"""
        try:
            # For demo, return cached data or generate historical data
            if symbol not in self.historical_cache:
                self.historical_cache[symbol] = await self.generate_historical_data(symbol, lookback)
            
            return self.historical_cache[symbol][-lookback:]
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def generate_historical_data(self, symbol: str, count: int) -> List[MarketData]:
        """Generate historical market data for demo"""
        historical_data = []
        base_price = self.get_base_price(symbol)
        current_price = base_price
        
        for i in range(count):
            import random
            
            # Generate price movement
            change_pct = random.uniform(-0.01, 0.01)
            new_price = current_price * (1 + change_pct)
            
            # Generate OHLC
            high = new_price * random.uniform(1.001, 1.003)
            low = new_price * random.uniform(0.997, 0.999)
            volume = random.randint(50000, 500000)
            
            timestamp = datetime.utcnow() - timedelta(minutes=(count - i) * 5)
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=timestamp,
                open=current_price,
                high=high,
                low=low,
                close=new_price,
                volume=volume,
                asset_class=AssetClass.EQUITY,
                exchange="NSE"
            )
            
            historical_data.append(market_data)
            current_price = new_price
        
        return historical_data
    
    def get_data_status(self) -> Dict[str, Any]:
        """Get market data handler status"""
        return {
            'is_running': self.is_running,
            'total_updates': self.total_updates,
            'symbols_count': len(self.config.symbols or []),
            'symbols': self.config.symbols,
            'data_sources_status': self.data_sources_status,
            'latest_data_count': len(self.latest_data),
            'cache_size': sum(len(data) for data in self.historical_cache.values())
        } 