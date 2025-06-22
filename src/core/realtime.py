# Angel One Real-time Market Data Manager
import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from .instrument_manager import get_instrument_manager, Instrument

logger = logging.getLogger(__name__)

@dataclass
class TickData:
    token: str
    symbol: str
    ltp: float
    volume: int
    timestamp: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None

class AngelOneRealTimeManager:
    def __init__(self):
        self.instrument_manager = None
        self.all_instruments = {}
        self.auto_subscribe_tokens = []
        self.tick_data = {}
        self.ticks_received = 0
        self.connection_status = "demo"
        self.last_tick_time = 0
        self.is_running = False

    async def initialize(self):
        logger.info("🚀 Initializing Angel One Real-time Data Manager...")
        
        # Initialize instrument manager
        self.instrument_manager = await get_instrument_manager()
        
        # Get all instruments
        instruments = self.instrument_manager.get_all_instruments()
        self.all_instruments = {inst.token: inst for inst in instruments}
        
        # Get auto-subscribe instruments
        auto_subscribe_instruments = self.instrument_manager.get_auto_subscribe_instruments()
        self.auto_subscribe_tokens = [inst.token for inst in auto_subscribe_instruments]
        
        # Start demo mode
        await self._start_demo_mode()
        
        logger.info("✅ Angel One Real-time Data Manager initialized successfully")
        return True

    async def _start_demo_mode(self):
        logger.info(f"📊 Starting Angel One Demo Mode with {len(self.auto_subscribe_tokens)} auto-subscribe instruments")
        self.connection_status = "demo"
        self.is_running = True
        
        # Start generating ticks
        asyncio.create_task(self._generate_demo_ticks())

    async def _generate_demo_ticks(self):
        # Initialize base prices for different instrument types
        base_prices = {}
        
        for token, instrument in self.all_instruments.items():
            base_symbol = instrument.base_symbol
            instrument_type = instrument.instrumenttype
            exchange = instrument.exch_seg
            
            if instrument_type == 'EQ':
                # Equity prices
                if base_symbol in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]:
                    equity_prices = {
                        "RELIANCE": 2454.81, "TCS": 3103.67, "INFY": 1421.35, 
                        "HDFCBANK": 1587.23, "ICICIBANK": 912.78
                    }
                    base_prices[token] = equity_prices.get(base_symbol, 1000)
                else:
                    base_prices[token] = random.uniform(100, 3000)
                    
            elif 'FUT' in instrument_type:
                # Futures pricing
                if exchange == 'MCX':
                    # Commodity futures
                    if base_symbol == 'GOLD':
                        base_prices[token] = random.uniform(76000, 78000)
                    elif base_symbol == 'SILVER':
                        base_prices[token] = random.uniform(89000, 92000)
                    elif base_symbol == 'CRUDEOIL':
                        base_prices[token] = random.uniform(6700, 6900)
                    else:
                        base_prices[token] = random.uniform(500, 2000)
                elif exchange == 'CDS':
                    # Currency futures
                    if base_symbol == 'USDINR':
                        base_prices[token] = random.uniform(84.50, 85.50)
                    else:
                        base_prices[token] = random.uniform(80, 100)
                else:
                    # Index and stock futures
                    if base_symbol == 'NIFTY':
                        base_prices[token] = random.uniform(23900, 24100)
                    elif base_symbol == 'BANKNIFTY':
                        base_prices[token] = random.uniform(51800, 52200)
                    else:
                        base_prices[token] = random.uniform(100, 3000) * 1.02
                        
            elif 'OPT' in instrument_type:
                # Options pricing
                strike_price = instrument.strike or 100
                option_type = instrument.option_type
                
                if base_symbol == 'NIFTY':
                    spot_price = random.uniform(23950, 24050)
                elif base_symbol == 'BANKNIFTY':
                    spot_price = random.uniform(51900, 52100)
                else:
                    spot_price = strike_price * random.uniform(0.95, 1.05)
                
                # Simple option pricing
                if option_type == 'CE':  # Call option
                    if spot_price > strike_price:
                        base_prices[token] = max(1, (spot_price - strike_price) + random.uniform(5, 50))
                    else:
                        base_prices[token] = random.uniform(1, 20)
                else:  # Put option
                    if spot_price < strike_price:
                        base_prices[token] = max(1, (strike_price - spot_price) + random.uniform(5, 50))
                    else:
                        base_prices[token] = random.uniform(1, 20)
            else:
                base_prices[token] = random.uniform(100, 1000)
        
        while self.is_running:
            try:
                # Prioritize auto-subscribe instruments (80% of the time)
                if self.auto_subscribe_tokens and random.random() < 0.8:
                    token = random.choice(self.auto_subscribe_tokens)
                else:
                    token = random.choice(list(self.all_instruments.keys()))
                
                instrument = self.all_instruments[token]
                base_price = base_prices.get(token, 100)
                
                # Instrument-specific volatility
                if 'OPT' in instrument.instrumenttype:
                    # Options are more volatile
                    price_change = random.uniform(-0.15, 0.15)
                elif 'FUT' in instrument.instrumenttype:
                    # Futures moderate volatility
                    price_change = random.uniform(-0.008, 0.008)
                else:
                    # Equity volatility based on priority
                    if instrument.priority == 1:
                        price_change = random.uniform(-0.002, 0.002)
                    elif instrument.priority == 2:
                        price_change = random.uniform(-0.004, 0.004)
                    else:
                        price_change = random.uniform(-0.008, 0.008)
                
                new_price = max(0.05, base_price * (1 + price_change))
                
                # Format price based on instrument type
                if instrument.exch_seg == 'CDS':
                    # Currency - 4 decimal places
                    new_price = round(new_price, 4)
                elif 'OPT' in instrument.instrumenttype and new_price < 10:
                    # Options under 10 - 2 decimal places
                    new_price = round(new_price, 2)
                else:
                    # Others - 2 decimal places
                    new_price = round(new_price, 2)
                
                tick = TickData(
                    token=token,
                    symbol=instrument.symbol,
                    ltp=new_price,
                    volume=random.randint(100, 10000),
                    timestamp=datetime.now().isoformat(),
                    bid=round(new_price - abs(new_price * 0.001), 4),
                    ask=round(new_price + abs(new_price * 0.001), 4),
                    change=round(new_price - base_price, 4),
                    change_pct=round(price_change * 100, 2)
                )
                
                self.tick_data[token] = tick
                self.ticks_received += 1
                self.last_tick_time = time.time()
                base_prices[token] = new_price
                
                if self.ticks_received % 500 == 0:
                    logger.info(f"📊 ANGEL ONE DEMO: {instrument.base_symbol} {instrument.instrumenttype} ({instrument.exch_seg}) = ₹{tick.ltp} (Total: {self.ticks_received})")
                
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Demo tick generation error: {e}")
                await asyncio.sleep(1)

    def get_all_instruments(self):
        """Get all available instruments"""
        return list(self.all_instruments.values())

    def get_auto_subscribe_instruments(self):
        """Get auto-subscribe instruments"""
        return [self.all_instruments[token] for token in self.auto_subscribe_tokens if token in self.all_instruments]

    def search_instruments(self, query, limit=50):
        """Search instruments"""
        if not self.instrument_manager:
            return []
        return self.instrument_manager.search_instruments(query, limit)

    def get_instruments_by_base_symbol(self, base_symbol):
        """Get all instruments for a base symbol"""
        if not self.instrument_manager:
            return []
        return self.instrument_manager.get_instruments_by_base_symbol(base_symbol)

    async def subscribe_to_symbols(self, tokens):
        """Subscribe to specific instrument tokens"""
        valid_tokens = [token for token in tokens if token in self.all_instruments]
        if valid_tokens:
            logger.info(f"📡 Subscribed to {len(valid_tokens)} instruments")
        return valid_tokens

    def get_all_ticks(self):
        """Get all current tick data"""
        return self.tick_data.copy()

    def get_market_data_dict(self):
        """Get market data in dictionary format"""
        market_data = {}
        for token, tick in self.tick_data.items():
            instrument = self.all_instruments.get(token)
            if instrument:
                market_data[instrument.symbol] = {
                    "token": token,
                    "ltp": tick.ltp,
                    "volume": tick.volume,
                    "timestamp": tick.timestamp,
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "change": tick.change,
                    "change_pct": tick.change_pct,
                    "base_symbol": instrument.base_symbol,
                    "instrument_type": instrument.instrumenttype,
                    "exchange": instrument.exch_seg
                }
        return market_data

    def get_stats(self):
        """Get comprehensive statistics"""
        if not self.instrument_manager:
            return {"error": "Instrument manager not initialized"}
        
        instrument_stats = self.instrument_manager.get_stats()
        
        return {
            "connection_status": self.connection_status,
            "total_instruments": len(self.all_instruments),
            "auto_subscribe_instruments": len(self.auto_subscribe_tokens),
            "instruments_with_data": len(self.tick_data),
            "ticks_received": self.ticks_received,
            "last_tick_time": self.last_tick_time,
            "data_source": "angel_one_instrument_api_comprehensive",
            "tick_frequency": "10 ticks/second",
            "auth_status": "demo_mode",
            "config_file": "config/subscribed_symbols.csv",
            **instrument_stats
        }

_angel_one_manager = None

async def get_angel_one_manager():
    global _angel_one_manager
    if _angel_one_manager is None:
        _angel_one_manager = AngelOneRealTimeManager()
        await _angel_one_manager.initialize()
    return _angel_one_manager
