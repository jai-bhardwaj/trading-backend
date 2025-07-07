"""
Market Data Provider - Live data from Angel One broker
"""

import os
import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from dotenv import load_dotenv
import json

import pyotp
from shared.config import ConfigLoader

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    ltp: float  # Last traded price
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    bid: float
    ask: float
    timestamp: datetime

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls_per_minute = max_calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            now = time.time()
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls if now - call_time < 60]
            
            if len(self.calls) >= self.max_calls_per_minute:
                # Wait until we can make another call
                wait_time = 60 - (now - self.calls[0]) + 1
                logger.warning(f"⚠️ Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                # Recursive call after waiting
                return await self.wait_if_needed()
            
            self.calls.append(now)

class MarketDataProvider:
    """Live market data provider using Angel One API"""
    
    def __init__(self):
        self.api_key = os.getenv("ANGEL_ONE_API_KEY")
        self.client_code = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.password = os.getenv("ANGEL_ONE_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET")
        
        if not all([self.api_key, self.client_code, self.password, self.totp_secret]):
            raise ValueError("Missing Angel One environment variables. Please set ANGEL_ONE_API_KEY, ANGEL_ONE_CLIENT_CODE, ANGEL_ONE_PASSWORD, ANGEL_ONE_TOTP_SECRET")
        
        self.smart_api = None
        self.session = None
        self.symbol_configs = self._load_symbol_configs_from_json()
        self.rate_limiter = RateLimiter(max_calls_per_minute=10)  # Conservative for LTP fallback
        self._last_login_time = 0
        self._session_valid_until = 0
        
    def _load_symbol_configs_from_json(self):
        """Load symbol-token mapping from instruments_latest.json"""
        symbol_configs = {}
        try:
            with open("data/instruments_latest.json", "r") as f:
                instruments = json.load(f)
                for inst in instruments:
                    symbol = inst.get("symbol")
                    token = inst.get("token")
                    exchange = inst.get("exch_seg")
                    lot_size = int(float(inst.get("lotsize", 1)))
                    enabled = True
                    if symbol and token:
                        symbol_configs[symbol] = {
                            "token": token,
                            "exchange": exchange,
                            "lot_size": lot_size,
                            "enabled": enabled
                        }
            logger.info(f"✅ Loaded {len(symbol_configs)} symbol-token mappings from instruments_latest.json")
        except Exception as e:
            logger.error(f"❌ Error loading symbol-token mapping from instruments_latest.json: {e}")
        return symbol_configs
    
    async def initialize(self):
        """Initialize the market data provider with retry logic"""
        max_retries = 3
        retry_delay = 30  # Start with 30 seconds
        
        for attempt in range(max_retries):
            try:
                await self._initialize_with_rate_limit()
                logger.info("✅ Market data provider initialized successfully")
                return
            except Exception as e:
                error_msg = str(e)
                if "Access denied because of exceeding access rate" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("❌ Max retries reached for rate limit")
                        raise
                else:
                    logger.error(f"❌ Failed to initialize market data provider: {e}")
                    raise
        
        raise Exception("Failed to initialize market data provider after all retries")
    
    async def _initialize_with_rate_limit(self):
        """Initialize with rate limiting"""
        logger.info("🔐 Waiting for rate limit before login...")
        await self.rate_limiter.wait_if_needed()
        
        # Initialize SmartAPI
        logger.info("🔐 Initializing SmartAPI...")
        self.smart_api = SmartConnect(api_key=self.api_key)
        
        # Generate TOTP
        logger.info("🔐 Generating TOTP...")
        totp = pyotp.TOTP(self.totp_secret).now()
        
        # Login
        logger.info("🔐 Logging in to Angel One...")
        loop = asyncio.get_running_loop()
        self.session = await loop.run_in_executor(
            None, 
            lambda: self.smart_api.generateSession(self.client_code, self.password, totp)
        )
        
        # Set session validity (Angel One sessions typically last 24 hours)
        self._last_login_time = time.time()
        self._session_valid_until = self._last_login_time + (23 * 3600)  # 23 hours
    
    async def _ensure_session_valid(self):
        """Ensure session is still valid, re-login if needed - WebSocket only mode"""
        # In WebSocket-only mode, we only need session for order placement
        # Market data comes from WebSocket
        if time.time() > self._session_valid_until:
            logger.info("🔄 Session expired, re-logging in")
            await self._initialize_with_rate_limit()
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get LTP market data for symbols using ltpData (REST) - DISABLED for WebSocket-only mode."""
        logger.warning("⚠️ REST API market data disabled - using WebSocket only")
        return {}
    
    async def get_ltp_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get LTP market data for symbols using ltpData (REST) - for market closed scenarios."""
        try:
            await self._ensure_session_valid()

            loop = asyncio.get_running_loop()
            result = {}
            for symbol in symbols:
                token = self._get_symbol_token(symbol)
                if not token:
                    continue
                
                # Wait for rate limit before each API call
                await self.rate_limiter.wait_if_needed()
                
                # Fetch LTP for each symbol
                ltp_resp = await loop.run_in_executor(
                    None,
                    lambda: self.smart_api.ltpData(exchange="NSE", tradingsymbol=symbol, symboltoken=token)
                )
                data = ltp_resp.get("data", {})
                if data:
                    result[symbol] = MarketData(
                        symbol=symbol,
                        ltp=float(data.get("ltp", 0)),
                        change=0.0,  # Not available in ltpData
                        change_percent=0.0,  # Not available in ltpData
                        high=0.0,  # Not available in ltpData
                        low=0.0,   # Not available in ltpData
                        volume=0,  # Not available in ltpData
                        bid=0.0,   # Not available in ltpData
                        ask=0.0,   # Not available in ltpData
                        timestamp=datetime.now()
                    )
            logger.info(f"✅ Fetched LTP data for {len(result)} symbols")
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching LTP data: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, interval: str = "1D", days: int = 30) -> List[Dict]:
        """Get historical data for a symbol - DISABLED due to API issues"""
        logger.warning(f"⚠️ Historical data API disabled for {symbol} - using live data only")
        return []
        
        # DISABLED: This method causes rate limit issues
        # try:
        #     await self._ensure_session_valid()
        #     
        #     symbol_token = self._get_symbol_token(symbol)
        #     if not symbol_token:
        #         logger.error(f"❌ Symbol token not found for {symbol}")
        #         return []
        #     
        #     # Wait for rate limit
        #     await self.rate_limiter.wait_if_needed()
        #     
        #     # Fetch historical data
        #     loop = asyncio.get_running_loop()
        #     historical_data = await loop.run_in_executor(
        #         None,
        #         lambda: self.smart_api.getCandleData({
        #             "exchange": "NSE",
        #             "symboltoken": symbol_token,
        #             "interval": interval,
        #             "fromdate": f"{datetime.now().strftime('%Y-%m-%d')} 00:00",
        #             "todate": f"{datetime.now().strftime('%Y-%m-%d')} 23:59"
        #         })
        #     )
        #     
        #     return historical_data.get("data", [])
        #     
        # except Exception as e:
        #     logger.error(f"❌ Error fetching historical data: {e}")
        #     return []
    
    def _get_symbol_tokens(self, symbols: List[str]) -> List[str]:
        """Get symbol tokens for symbols from instruments_latest.json mapping"""
        tokens = []
        for symbol in symbols:
            token = self._get_symbol_token(symbol)
            if token:
                tokens.append(token)
        return tokens
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for a symbol from instruments_latest.json mapping"""
        symbol_config = self.symbol_configs.get(symbol)
        if symbol_config:
            return symbol_config["token"]
        else:
            logger.error(f"❌ Symbol token not found for {symbol}")
            return ""
    
    async def close(self):
        """Close the market data provider (no logout needed)"""
        pass

    def start_websocket_stream(self, tokens, on_tick_callback):
        """Start SmartAPI WebSocket client and stream live market data for given tokens."""
        import pyotp
        
        # Ensure SmartAPI session is initialized
        if not self.smart_api or not self.session:
            totp = pyotp.TOTP(self.totp_secret).now()
            self.session = self.smart_api.generateSession(self.client_code, self.password, totp)
        
        # Get the correct tokens from session
        jwt_token = self.session["data"]["jwtToken"]  # Use jwtToken as auth_token
        feed_token = self.session["data"]["feedToken"]  # Use feedToken as feed_token
        client_code = self.client_code  # Use clientcode as client_code
        api_key = self.api_key
        
        def on_tick(ws, tick):
            on_tick_callback(tick)
        def on_connect(ws, response):
            logger.info("🔌 WebSocket connected, subscribing to tokens...")
            # Subscribe with correlation ID and mode
            ws.subscribe("correlation_001", 1, [{"exchangeType": 1, "tokens": tokens}])  # 1 for NSE, mode 1 for LTP
        def on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        # Initialize with correct tokens: SmartWebSocketV2(auth_token, api_key, client_code, feed_token)
        logger.info(f"🔌 Initializing WebSocket with {len(tokens)} tokens...")
        sws = SmartWebSocketV2(jwt_token, api_key, client_code, feed_token)
        sws.on_ticks = on_tick
        sws.on_connect = on_connect
        sws.on_close = on_close
        sws.on_error = on_error
        sws.connect()
        logger.info("✅ WebSocket connection initiated") 