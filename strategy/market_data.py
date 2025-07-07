"""
Market Data Provider - Live data from Angel One broker
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from SmartApi import SmartConnect
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
        """Initialize the market data provider"""
        try:
            # Initialize SmartAPI
            self.smart_api = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            
            # Login
            loop = asyncio.get_running_loop()
            self.session = await loop.run_in_executor(
                None, 
                lambda: self.smart_api.generateSession(self.client_code, self.password, totp)
            )
            
            logger.info("✅ Market data provider initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize market data provider: {e}")
            raise
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get LTP market data for symbols using ltpData (REST)."""
        try:
            if not self.smart_api:
                await self.initialize()

            loop = asyncio.get_running_loop()
            result = {}
            for symbol in symbols:
                token = self._get_symbol_token(symbol)
                if not token:
                    continue
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
            logger.info(f"✅ Fetched LTP market data for {len(result)} symbols")
            return result
        except Exception as e:
            logger.error(f"❌ Error fetching LTP market data: {e}")
            return {}
    
    async def get_historical_data(self, symbol: str, interval: str = "1D", days: int = 30) -> List[Dict]:
        """Get historical data for a symbol"""
        try:
            if not self.smart_api:
                await self.initialize()
            
            symbol_token = self._get_symbol_token(symbol)
            if not symbol_token:
                logger.error(f"❌ Symbol token not found for {symbol}")
                return []
            
            # Fetch historical data
            loop = asyncio.get_running_loop()
            historical_data = await loop.run_in_executor(
                None,
                lambda: self.smart_api.getCandleData({
                    "exchange": "NSE",
                    "symboltoken": symbol_token,
                    "interval": interval,
                    "fromdate": f"{datetime.now().strftime('%Y-%m-%d')} 00:00",
                    "todate": f"{datetime.now().strftime('%Y-%m-%d')} 23:59"
                })
            )
            
            return historical_data.get("data", [])
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data: {e}")
            return []
    
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
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2
        import pyotp
        
        # Ensure SmartAPI session is initialized
        if not self.smart_api or not self.session:
            totp = pyotp.TOTP(self.totp_secret).now()
            self.session = self.smart_api.generateSession(self.client_code, self.password, totp)
        feed_token = self.session["data"]["feedToken"]
        client_id = self.client_code
        api_key = self.api_key
        
        def on_tick(ws, tick):
            on_tick_callback(tick)
        def on_connect(ws, response):
            ws.subscribe([{"exchangeType": 1, "tokens": tokens}])  # 1 for NSE
        def on_close(ws, code, reason):
            print("WebSocket closed:", code, reason)
        def on_error(ws, code, reason):
            print("WebSocket error:", code, reason)
        
        sws = SmartWebSocketV2(api_key, client_id, feed_token, client_id)
        sws.on_ticks = on_tick
        sws.on_connect = on_connect
        sws.on_close = on_close
        sws.on_error = on_error
        sws.connect() 