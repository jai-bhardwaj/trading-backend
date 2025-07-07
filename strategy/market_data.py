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

import pyotp
from shared.config import ConfigLoader

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
        self.config_loader = ConfigLoader()
        self.symbol_configs = {}
        
    async def initialize(self):
        """Initialize the market data provider"""
        try:
            # Load symbol configurations
            self.symbol_configs = self.config_loader.load_symbols()
            logger.info(f"✅ Loaded {len(self.symbol_configs)} symbol configurations")
            
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
        """Get live market data for symbols"""
        try:
            if not self.smart_api:
                await self.initialize()
            
            # Load symbol token map
            symbol_tokens = self._get_symbol_tokens(symbols)
            
            # Fetch quotes
            loop = asyncio.get_running_loop()
            quotes = await loop.run_in_executor(
                None,
                lambda: self.smart_api.getQuotes("NSE", symbol_tokens)
            )
            
            result = {}
            for quote in quotes.get("data", {}).get("fetched", []):
                symbol = quote.get("tradingSymbol", "")
                if symbol in symbols:
                    result[symbol] = MarketData(
                        symbol=symbol,
                        ltp=float(quote.get("ltp", 0)),
                        change=float(quote.get("netChange", 0)),
                        change_percent=float(quote.get("pChange", 0)),
                        high=float(quote.get("high", 0)),
                        low=float(quote.get("low", 0)),
                        volume=int(quote.get("totalTradedVolume", 0)),
                        bid=float(quote.get("bid", 0)),
                        ask=float(quote.get("ask", 0)),
                        timestamp=datetime.now()
                    )
            
            logger.info(f"✅ Fetched market data for {len(result)} symbols")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching market data: {e}")
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
        """Get symbol tokens for symbols"""
        tokens = []
        for symbol in symbols:
            token = self._get_symbol_token(symbol)
            if token:
                tokens.append(token)
        return tokens
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for a symbol from CSV configuration"""
        symbol_config = self.symbol_configs.get(symbol)
        if symbol_config:
            return symbol_config.token
        else:
            logger.error(f"❌ Symbol token not found for {symbol}")
            return ""
    
    async def close(self):
        """Close the market data provider"""
        if self.smart_api:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.smart_api.logout)
                logger.info("✅ Market data provider closed")
            except Exception as e:
                logger.error(f"❌ Error closing market data provider: {e}") 