# Angel One Real-time Market Data Manager
import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from .instruments import get_instrument_manager, Instrument

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
        
        # Check for Angel One API credentials
        import os
        api_key = os.getenv('ANGEL_ONE_API_KEY', '')
        secret_key = os.getenv('ANGEL_ONE_SECRET_KEY', '')
        client_id = os.getenv('ANGEL_ONE_CLIENT_ID', '')
        pin = os.getenv('ANGEL_ONE_PIN', '')
        totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET', '')
        
        # Check if we're in production environment
        environment = os.getenv('ENVIRONMENT', os.getenv('TRADING_ENV', 'production')).lower()
        is_production = environment == 'production'
        
        if all([api_key, secret_key, client_id, pin]):
            logger.info("📡 Angel One API credentials found - attempting live connection...")
            live_success = await self._connect_to_live_api(api_key, secret_key, client_id, pin, totp_secret)
            if live_success:
                logger.info("✅ Angel One Live API connected successfully")
                return True
            else:
                if is_production:
                    logger.error("❌ PRODUCTION MODE: Angel One API connection failed - cannot start without live data")
                    raise Exception("Production mode requires live Angel One API connection")
                else:
                    logger.warning("⚠️ Angel One Live API connection failed - falling back to demo mode")
        else:
            if is_production:
                logger.error("❌ PRODUCTION MODE: Angel One API credentials missing - cannot start without live data")
                raise Exception("Production mode requires Angel One API credentials")
            else:
                logger.warning("⚠️ Angel One API credentials not found - using demo mode")
        
        # Fallback to demo mode (only in development)
        if not is_production:
            await self._start_demo_mode()
        else:
            logger.error("❌ Cannot start in production mode without live Angel One API")
        
        logger.info("✅ Angel One Real-time Data Manager initialized successfully")
        return True

    async def _connect_to_live_api(self, api_key: str, secret_key: str, client_id: str, pin: str, totp_secret: str = '') -> bool:
        """Connect to Angel One live API"""
        try:
            import requests
            import json
            import os
            
            # Step 1: Login to Angel One API
            login_url = "https://smartapi.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': api_key
            }
            
            payload = {
                "clientcode": client_id,
                "password": pin
            }
            
            # Add TOTP if available
            if totp_secret:
                try:
                    import pyotp
                    totp = pyotp.TOTP(totp_secret)
                    payload["totp"] = totp.now()
                    logger.info("🔐 TOTP added to login request")
                except Exception as e:
                    logger.warning(f"⚠️ TOTP generation failed: {e}")
            
            logger.info("🔑 Attempting Angel One API login...")
            response = requests.post(login_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📊 Angel One API Response: {data}")
                
                if data.get('status') and data.get('data'):
                    access_token = data['data'].get('jwtToken')
                    feed_token = data['data'].get('feedToken')
                    
                    if access_token and feed_token:
                        logger.info("✅ Angel One API login successful - starting live data stream")
                        self.connection_status = "connected"
                        self.is_running = True
                        
                        # Start live data fetching
                        asyncio.create_task(self._fetch_live_data_periodically(access_token, api_key))
                        return True
                    else:
                        logger.error(f"❌ Invalid response: missing tokens. Response: {data}")
                        return False
                else:
                    error_msg = data.get('message', 'Unknown error')
                    error_code = data.get('errorcode', 'Unknown')
                    logger.error(f"❌ Angel One login failed: {error_msg} (Code: {error_code})")
                    return False
            else:
                logger.error(f"❌ Angel One login failed with status: {response.status_code}, response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to Angel One API: {e}")
            return False

    async def _fetch_live_data_periodically(self, access_token: str, api_key: str):
        """Fetch live market data periodically using Angel One API"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '127.0.0.1',
            'X-ClientPublicIP': '127.0.0.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': api_key
        }
        
        # Get sample symbols for live data
        sample_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        
        while self.is_running:
            try:
                # Use Angel One LTP API for live data
                ltp_url = "https://smartapi.angelbroking.com/rest/secure/angelbroking/order/v1/getLTP"
                
                for symbol in sample_symbols:
                    try:
                        payload = {
                            "exchange": "NSE",
                            "tradingsymbol": symbol,
                            "symboltoken": str(hash(symbol) % 100000)  # Simplified token
                        }
                        
                        response = requests.post(ltp_url, json=payload, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('status') and data.get('data'):
                                ltp_data = data['data']
                                
                                # Create tick data from Angel One response
                                token = payload["symboltoken"]
                                
                                tick = TickData(
                                    token=token,
                                    symbol=symbol,
                                    ltp=float(ltp_data.get('ltp', 0)),
                                    volume=int(ltp_data.get('volume', 0)),
                                    timestamp=datetime.now().isoformat(),
                                    bid=float(ltp_data.get('bid', 0)),
                                    ask=float(ltp_data.get('ask', 0)),
                                    change=float(ltp_data.get('change', 0)),
                                    change_pct=float(ltp_data.get('pChange', 0))
                                )
                                
                                self.tick_data[token] = tick
                                self.ticks_received += 1
                                self.last_tick_time = time.time()
                                
                                if self.ticks_received % 50 == 0:
                                    logger.info(f"📈 LIVE: {symbol} = ₹{tick.ltp} (Total: {self.ticks_received})")
                        
                        await asyncio.sleep(1)  # Rate limiting
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error fetching live data for {symbol}: {e}")
                        continue
                
                await asyncio.sleep(5)  # Wait before next round of all symbols
                
            except Exception as e:
                logger.error(f"❌ Error in live data fetching: {e}")
                await asyncio.sleep(10)  # Wait longer on error

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
            "data_source": "angel_one_live_api" if self.connection_status == "connected" else "angel_one_demo",
            "tick_frequency": "real-time" if self.connection_status == "connected" else "10 ticks/second",
            "auth_status": "live_authenticated" if self.connection_status == "connected" else "demo_mode",
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
