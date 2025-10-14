"""
Market Data Service Client - HTTP client for market data service
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Callable
from datetime import datetime
import httpx
import websockets
from dataclasses import dataclass

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

class MarketDataClient:
    """HTTP client for market data service"""
    
    def __init__(self, base_url: str = "http://market-data-service:8001"):
        self.base_url = base_url.rstrip('/')
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()
    
    async def health_check(self) -> Dict:
        """Check if the market data service is healthy"""
        try:
            response = await self.http_client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_ltp_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get Last Traded Price data for symbols"""
        try:
            symbols_str = ",".join(symbols)
            response = await self.http_client.get(
                f"{self.base_url}/api/market-data/ltp",
                params={"symbols": symbols_str}
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert dict data back to MarketData objects
            result = {}
            for symbol, market_data_dict in data.items():
                result[symbol] = MarketData(
                    symbol=market_data_dict["symbol"],
                    ltp=market_data_dict["ltp"],
                    change=market_data_dict["change"],
                    change_percent=market_data_dict["change_percent"],
                    high=market_data_dict["high"],
                    low=market_data_dict["low"],
                    volume=market_data_dict["volume"],
                    bid=market_data_dict["bid"],
                    ask=market_data_dict["ask"],
                    timestamp=datetime.fromisoformat(market_data_dict["timestamp"])
                )
            
            return result
        except Exception as e:
            logger.error(f"Error getting LTP data: {e}")
            return {}
    
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: str = "1minute",
        from_date: str = None,
        to_date: str = None
    ) -> Dict:
        """Get historical market data"""
        try:
            params = {
                "symbol": symbol,
                "interval": interval
            }
            if from_date:
                params["from_date"] = from_date
            if to_date:
                params["to_date"] = to_date
            
            response = await self.http_client.get(
                f"{self.base_url}/api/market-data/historical",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {}
    
    async def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        try:
            response = await self.http_client.get(f"{self.base_url}/api/market-data/symbols")
            response.raise_for_status()
            data = response.json()
            return data.get("symbols", [])
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []

class MarketDataWebSocketClient:
    """WebSocket client for real-time market data"""
    
    def __init__(self, ws_url: str = "ws://market-data-service:8001/ws/market-data"):
        self.ws_url = ws_url
        self.websocket = None
        self.subscribed_symbols = set()
        self.message_handlers = []
        self.running = False
    
    def add_message_handler(self, handler: Callable[[Dict], None]):
        """Add a message handler function"""
        self.message_handlers.append(handler)
    
    async def connect(self):
        """Connect to the WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.running = True
            logger.info("Connected to market data WebSocket")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the WebSocket"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from market data WebSocket")
    
    async def subscribe(self, symbol: str):
        """Subscribe to a symbol"""
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        message = {
            "action": "subscribe",
            "symbol": symbol
        }
        await self.websocket.send(json.dumps(message))
        self.subscribed_symbols.add(symbol)
        logger.info(f"Subscribed to {symbol}")
    
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from a symbol"""
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        message = {
            "action": "unsubscribe",
            "symbol": symbol
        }
        await self.websocket.send(json.dumps(message))
        self.subscribed_symbols.discard(symbol)
        logger.info(f"Unsubscribed from {symbol}")
    
    async def listen(self):
        """Listen for messages from the WebSocket"""
        if not self.websocket:
            raise Exception("WebSocket not connected")
        
        try:
            while self.running:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Call all message handlers
                for handler in self.message_handlers:
                    try:
                        handler(data)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening to WebSocket: {e}")
            raise

# Convenience function to create a client
def create_market_data_client(base_url: str = "http://market-data-service:8001") -> MarketDataClient:
    """Create a market data client"""
    return MarketDataClient(base_url)

def create_market_data_websocket_client(ws_url: str = "ws://market-data-service:8001/ws/market-data") -> MarketDataWebSocketClient:
    """Create a market data WebSocket client"""
    return MarketDataWebSocketClient(ws_url)
