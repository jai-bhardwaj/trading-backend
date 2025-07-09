"""
Market Data Provider - Live data from Angel One broker
"""

import os
import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from SmartApi import SmartConnect
from strategy.AngelWebSocket import SmartWebSocketV2  # Use V2 as per official docs
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
        self.rate_limiter = RateLimiter(max_calls_per_minute=3)  # Very conservative for API calls
        self._last_login_time = 0
        self._session_valid_until = 0
        self._historical_data_cache = {}  # (symbol, interval, from_date, to_date) -> data
        self._ltp_cache = {}  # symbol -> (MarketData, timestamp)
        self._ltp_cache_ttl = 60  # seconds

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
                
                # Test API connection and token mapping - REMOVED to avoid warnings
                # await self._test_api_connection()
                
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

    async def _test_api_connection(self):
        """Test API connection and token mapping"""
        try:
            logger.info("🔍 Testing API connection and token mapping...")
            
            # Test with a single symbol
            test_symbols = ["RELIANCE-EQ", "TCS-EQ"]
            for symbol in test_symbols:
                token = self._get_symbol_token(symbol)
                if token:
                    logger.info(f"✅ Token mapping OK: {symbol} -> {token}")
                else:
                    logger.error(f"❌ No token found for {symbol}")
            
            # Test a simple LTP call
            if test_symbols:
                test_result = await self.get_ltp_data([test_symbols[0]])
                if test_result:
                    logger.info(f"✅ API connection test successful: {test_symbols[0]} LTP = {list(test_result.values())[0].ltp}")
                else:
                    logger.warning("⚠️ API connection test failed - no LTP data received")
                    
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
    
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
        """Get LTP market data for symbols using WebSocket data with REST API fallback (throttled)."""
        result = {}
        now = time.time()
        for symbol in symbols:
            token = self._get_symbol_token(symbol)
            if not token:
                continue
            # Try to get data from live_market_data (WebSocket)
            market_data = None
            if hasattr(self, 'live_market_data'):
                live_data = getattr(self, 'live_market_data')
                if token in live_data:
                    market_data = live_data[token]
            if market_data:
                result[symbol] = market_data
                # Update cache
                self._ltp_cache[symbol] = (market_data, now)
            else:
                # Check cache before REST fallback
                cached = self._ltp_cache.get(symbol)
                if cached and now - cached[1] < self._ltp_cache_ttl:
                    logger.info(f"📦 Serving cached REST LTP for {symbol}")
                    result[symbol] = cached[0]
                else:
                    logger.warning(f"⚠️ No WebSocket data for {symbol}, trying REST fallback (throttled)...")
                    try:
                        await self._ensure_session_valid()
                        rest_result = await self._get_ltp_data_individual([symbol])
                        if rest_result and symbol in rest_result:
                            logger.info(f"✅ REST API fallback successful for {symbol}")
                            result[symbol] = rest_result[symbol]
                            self._ltp_cache[symbol] = (rest_result[symbol], now)
                        else:
                            logger.warning(f"⚠️ REST API fallback failed for {symbol}")
                    except Exception as e:
                        logger.error(f"❌ REST API fallback failed for {symbol}: {e}")
        logger.info(f"✅ LTP fetch completed for {len(result)} symbols")
        return result

    def _safe_json_loads(self, response):
        import json
        if isinstance(response, bytes):
            try:
                response = response.decode('utf-8')
            except Exception as e:
                logger.error(f"❌ Failed to decode bytes response: {e}")
                return None
        if not response:
            logger.error("❌ Empty response received from API.")
            return None
        try:
            return json.loads(response)
        except Exception as e:
            logger.error(f"❌ Failed to parse JSON response: {e} | Raw: {response}")
            return None

    async def _get_ltp_data_individual(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Fallback method: Get LTP data for symbols using individual ltpData calls"""
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
                
                try:
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
                            change=0.0,
                            change_percent=0.0,
                            high=0.0,
                            low=0.0,
                            volume=0,
                            bid=0.0,
                            ask=0.0,
                            timestamp=datetime.now()
                        )
                except Exception as e:
                    logger.error(f"❌ Error fetching LTP for {symbol}: {e}")
                    continue
                    
            logger.info(f"✅ Individual LTP fetch completed for {len(result)} symbols")
            return result
        except Exception as e:
            logger.error(f"❌ Error in individual LTP fetch: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, interval: str = "1D", days: int = 30) -> List[Dict]:
        """Get historical data for a symbol from Angel One API, with in-memory caching"""
        # Temporarily disabled to prevent rate limit blocking
        logger.info(f"📊 Historical data temporarily disabled for {symbol} to prevent rate limits")
        return []
        
        try:
            # Skip historical data for test strategy to avoid rate limits
            import inspect
            frame = inspect.currentframe()
            while frame:
                if 'test_strategy' in str(frame.f_code.co_name):
                    logger.info(f"📊 Skipping historical data for test strategy - {symbol}")
                    return []
                frame = frame.f_back
            
            await self._ensure_session_valid()
            
            # Get symbol token
            token = self._get_symbol_token(symbol)
            if not token:
                logger.error(f"❌ Symbol token not found for {symbol}")
                return []
            
            # Map interval to Angel One format
            interval_map = {
                "1minute": "ONE_MINUTE",
                "5minute": "FIVE_MINUTE", 
                "15minute": "FIFTEEN_MINUTE",
                "30minute": "THIRTY_MINUTE",
                "1hour": "ONE_HOUR",
                "1D": "ONE_DAY",
                "1W": "ONE_WEEK",
                "1M": "ONE_MONTH"
            }
            angel_interval = interval_map.get(interval, "ONE_DAY")
            
            # Calculate date range
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            from_date = start_date.strftime("%Y-%m-%d %H:%M")
            to_date = end_date.strftime("%Y-%m-%d %H:%M")
            
            # Use cache key
            cache_key = (symbol, angel_interval, from_date, to_date)
            if cache_key in self._historical_data_cache:
                logger.info(f"📦 Returning cached historical data for {symbol} {angel_interval} {from_date} - {to_date}")
                return self._historical_data_cache[cache_key]
            
            # Wait for rate limit before API call
            await self.rate_limiter.wait_if_needed()
            
            logger.info(f"📊 Fetching historical data for {symbol} from {from_date} to {to_date}")
            
            # Call Angel One API
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.smart_api.getCandleData({
                    "exchange": "NSE",
                    "symboltoken": token,
                    "interval": angel_interval,
                    "fromdate": from_date,
                    "todate": to_date,
                    "tradingsymbol": symbol
                })
            )
            
            if not response or "data" not in response:
                logger.error(f"❌ No data received for {symbol}")
                return []
            
            # Parse the response
            candles = response["data"]
            if not candles:
                logger.warning(f"⚠️ No candle data received for {symbol}")
                return []
            
            # Convert to standard format
            historical_data = []
            for candle in candles:
                try:
                    # Angel One candle format: [timestamp, open, high, low, close, volume]
                    timestamp_str = candle[0]  # "2024-01-15T09:15:00"
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    historical_data.append({
                        'time': timestamp,
                        'o': float(candle[1]),  # open
                        'h': float(candle[2]),  # high
                        'l': float(candle[3]),  # low
                        'c': float(candle[4]),  # close
                        'v': int(candle[5])     # volume
                    })
                except Exception as e:
                    logger.error(f"❌ Error parsing candle data: {e}")
                    continue
            
            logger.info(f"✅ Fetched {len(historical_data)} candles for {symbol}")
            # Store in cache
            self._historical_data_cache[cache_key] = historical_data
            return historical_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
            # Return mock data as fallback
            logger.info(f"📊 Returning mock historical data for {symbol} as fallback")
            return self._get_mock_historical_data(symbol)
    
    def _get_mock_historical_data(self, symbol: str) -> List[Dict]:
        """Generate mock historical data as fallback"""
        mock_data = []
        base_price = 1000.0  # Base price for mock data
        
        for i in range(50):  # Generate 50 candles
            timestamp = datetime.now() - timedelta(minutes=50-i)
            open_price = base_price + (i * 0.5)
            high_price = open_price + 2.0
            low_price = open_price - 1.0
            close_price = open_price + (0.5 if i % 2 == 0 else -0.3)
            volume = 1000 + (i * 10)
            
            mock_data.append({
                'time': timestamp,
                'o': open_price,
                'h': high_price,
                'l': low_price,
                'c': close_price,
                'v': volume
            })
        
        return mock_data
    
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
    
    def _get_token_symbol(self, token: str) -> str:
        """Get symbol for a token from instruments_latest.json mapping"""
        for symbol, config in self.symbol_configs.items():
            if config.get("token") == token:
                return symbol
        logger.error(f"❌ Symbol not found for token {token}")
        return ""
    
    async def close(self):
        """Close the market data provider (no logout needed)"""
        pass

    def start_websocket_stream(self, tokens, on_tick_callback):
        """Start Angel One WebSocket 2.0 client and stream live market data for given tokens."""
        import json
        import struct
        import threading
        import time
        import websocket  # websocket-client
        import logging

        logger = logging.getLogger(__name__)

        # Prepare the subscription message
        correlation_id = "sub_" + str(int(time.time()))
        mode = 1  # LTP mode
        token_list = [
            {
                "exchangeType": 1,  # NSE_CM
                "tokens": tokens
            }
        ]
        subscribe_msg = json.dumps({
            "correlationID": correlation_id,
            "action": 1,
            "params": {
                "mode": mode,
                "tokenList": token_list
            }
        })

        ws_url = (
            f"wss://smartapisocket.angelone.in/smart-stream"
            f"?clientCode={self.client_code}&feedToken={self.session['data']['feedToken']}&apiKey={self.api_key}"
        )

        def on_open(ws):
            logger.info("[WS] WebSocket opened")
            ws.send(subscribe_msg)
            logger.info(f"[WS] Sent subscription message: {subscribe_msg}")

        def on_message(ws, message):
            # Heartbeat (text)
            if isinstance(message, str):
                if message == "ping":
                    ws.send("pong")
                    logger.debug("[WS] Received ping, sent pong")
                    return
                try:
                    # Try to parse as JSON (error message)
                    data = json.loads(message)
                    logger.error(f"[WS] WebSocket error message: {data}")
                    return
                except Exception:
                    logger.warning(f"[WS] Unknown text message: {message}")
                    return

            # Binary tick data
            if isinstance(message, bytes):
                try:
                    if len(message) >= 51:
                        # Unpack: mode(1), exch(1), token(25), seq(8), ts(8), ltp(4)
                        mode, exch = struct.unpack("<BB", message[0:2])
                        token_bytes = message[2:27]
                        token = token_bytes.split(b'\x00', 1)[0].decode()
                        seq, ts = struct.unpack("<qq", message[27:43])
                        ltp = struct.unpack("<i", message[43:47])[0] / 100.0
                        tick = {
                            "mode": mode,
                            "exchange": exch,
                            "token": token,
                            "sequence": seq,
                            "timestamp": ts,
                            "ltp": ltp,
                        }
                        logger.debug(f"[WS] Parsed tick: {tick}")
                        if on_tick_callback:
                            on_tick_callback(tick)
                    else:
                        logger.warning(f"[WS] Received binary message of unexpected length: {len(message)}")
                except Exception as e:
                    logger.error(f"[WS] Error parsing binary tick: {e}")

        def on_error(ws, error):
            logger.error(f"[WS] WebSocket error: {error}")

        def on_close(ws, *args):
            logger.info("[WS] WebSocket closed")

        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            header=[
                f"Authorization: {self.session['data']['jwtToken']}",
                f"x-api-key: {self.api_key}",
                f"x-client-code: {self.client_code}",
                f"x-feed-token: {self.session['data']['feedToken']}",
            ]
        )

        # Run in a thread
        threading.Thread(target=ws.run_forever, daemon=True).start()
        logger.info("[WS] WebSocket connection initiated in background thread") 