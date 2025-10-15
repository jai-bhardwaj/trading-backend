"""
Market Data Redis Streamer - Clean implementation using AngelOneWebSocketClient
Streams real-time market data from Angel One to Redis Streams
"""

import asyncio
import logging
import os
import sys
import csv
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
import redis.asyncio as redis
import sys
import os
sys.path.insert(0, '/app')
from shared.timezone import get_ist_now, get_ist_timestamp

# Add parent directory to path
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our Angel One client
from angel_one_client import AngelOneWebSocketClient

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://trading-redis:6379")
MARKET_DATA_STREAM = "market_data_stream"

# Global instances
market_data_streamer = None

def load_symbols_from_csv():
    """Load symbols from symbols_to_trade.csv"""
    symbols = []
    csv_path = "/app/data/symbols_to_trade.csv"
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('enabled', '').lower() == 'true':
                    symbol = row['symbol_name']
                    symbols.append(symbol)
        logger.info(f"Loaded {len(symbols)} symbols from CSV: {symbols}")
        return symbols
    except Exception as e:
        logger.error(f"Error loading symbols from CSV: {e}")
        return []

class MarketDataRedisStreamer:
    """Streams market data from Angel One to Redis Streams"""
    
    def __init__(self):
        self.redis_client = None
        self.symbols = []
        self.running = False
        self.ws_connected = False
        self.tick_count = 0
        self.last_tick_time = None
        
        # Angel One WebSocket client
        self.angel_client = None
        
        # Event loop reference for scheduling async tasks from sync context
        self.event_loop = None
        
        # Symbol-token mapping
        self.symbol_tokens = {
            "RELIANCE": "2881",
            "TCS": "11536", 
            "INFY": "408065",
            "HDFC": "1333",
            "ICICIBANK": "4963",
            "SBIN": "3045",
            "BHARTIARTL": "2714625",
            "ITC": "424",
            "KOTAKBANK": "4920",
            "LT": "11483",
            "MARUTI": "10999",
            "ASIANPAINT": "1660",
            "NESTLEIND": "459",
            "BAJFINANCE": "81153",
            "HINDUNILVR": "1394"
        }
    
    async def _initialize_angel_one(self):
        """Initialize Angel One WebSocket client"""
        try:
            logger.info("🔐 Initializing Angel One WebSocket client...")
            
            # Create Angel One client instance
            self.angel_client = AngelOneWebSocketClient()
            
            # Set up callbacks
            self.angel_client.set_callbacks(
                on_data=self._handle_tick_data,
                on_error=self._handle_websocket_error,
                on_close=self._handle_websocket_close,
                on_open=self._handle_websocket_open
            )
            
            logger.info("✅ Angel One WebSocket client initialized")
                
        except Exception as e:
            logger.error(f"Error initializing Angel One client: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def start(self):
        """Start the market data streamer"""
        try:
            logger.info("🚀 Starting Market Data Service...")
            
            # Store the current event loop for later use
            self.event_loop = asyncio.get_running_loop()
            
            # Load symbols from CSV
            self.symbols = load_symbols_from_csv()
            if not self.symbols:
                logger.warning("No symbols loaded from CSV. Using defaults.")
                self.symbols = ["RELIANCE", "TCS", "INFY"]
            
            # Connect to Redis
            logger.info(f"Connecting to Redis at {REDIS_URL}...")
            self.redis_client = redis.from_url(REDIS_URL)
            await self.redis_client.ping()
            logger.info("✅ Redis connected")
            
            # Initialize Angel One client
            await self._initialize_angel_one()
            
            # Start WebSocket stream
            self.start_websocket_stream()
            
            # Set running flag
            self.running = True
            
            logger.info("✅ Market Data Service started successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to start Market Data Service: {e}")
            self.running = False
            raise
    
    def start_websocket_stream(self):
        """Start Angel One WebSocket stream"""
        try:
            # Get tokens for symbols
            tokens = []
            nse_tokens = []
            
            for symbol in self.symbols:
                token = self.symbol_tokens.get(symbol)
                if token:
                    nse_tokens.append(token)
            
            # Create token list in the format expected by Angel One
            if nse_tokens:
                tokens.append({
                    "exchangeType": 1,  # NSE CM (Cash Market)
                    "tokens": nse_tokens
                })
            
            if not tokens:
                logger.warning("No valid tokens found for symbols")
                return
            
            logger.info(f"Starting WebSocket stream for {len(tokens)} token groups...")
            
            # Connect using the Angel One client
            success = self.angel_client.connect(tokens)
            
            if success:
                self.ws_connected = True
                logger.info("✅ WebSocket stream started")
            else:
                logger.error("❌ Failed to start WebSocket stream")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket stream: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _handle_tick_data(self, wsapp, msg):
        """Handle incoming tick data from Angel One WebSocket"""
        try:
            logger.info(f"Received tick: {msg}")
            
            # Process tick data and publish to Redis
            if self.event_loop and not self.event_loop.is_closed():
                # Schedule the coroutine to run in the stored event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.process_and_publish_tick(msg), 
                    self.event_loop
                )
                logger.debug(f"Scheduled tick processing task: {future}")
            else:
                logger.error("No valid event loop available for scheduling tick processing")
            
        except Exception as e:
            logger.error(f"Error in tick handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _handle_websocket_error(self, wsapp, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def _handle_websocket_close(self, wsapp, *args):
        """Handle WebSocket connection close"""
        logger.warning("WebSocket connection closed")
        self.ws_connected = False
    
    def _handle_websocket_open(self, wsapp):
        """Handle WebSocket connection open"""
        logger.info("✅ WebSocket connection opened")
        self.ws_connected = True
    
    async def process_and_publish_tick(self, tick_data: Dict):
        """Process tick data and publish to Redis Stream"""
        try:
            if not self.redis_client:
                return
            
            # Extract data from Angel One tick format
            token = tick_data.get('token', '')
            ltp = tick_data.get('last_traded_price', 0) / 100  # Angel One sends price * 100
            volume = tick_data.get('volume_trade_for_the_day', 0)
            high = tick_data.get('high_price_of_the_day', 0) / 100
            low = tick_data.get('low_price_of_the_day', 0) / 100
            open_price = tick_data.get('open_price_of_the_day', 0) / 100
            close_price = tick_data.get('closed_price', 0) / 100
            
            # Calculate change
            change = ltp - close_price if close_price > 0 else 0
            change_percent = (change / close_price * 100) if close_price > 0 else 0
            
            # Get best bid/ask from order book
            best_buy_data = tick_data.get('best_5_buy_data', [])
            best_sell_data = tick_data.get('best_5_sell_data', [])
            
            bid = best_buy_data[0]['price'] / 100 if best_buy_data else ltp
            ask = best_sell_data[0]['price'] / 100 if best_sell_data else ltp
            
            # Find symbol from token
            symbol = self._get_symbol_from_token(token)
            
            # Create tick message
            tick_message = {
                "symbol": symbol,
                "token": token,
                "ltp": ltp,
                "change": change,
                "change_percent": change_percent,
                "high": high,
                "low": low,
                "volume": volume,
                "bid": bid,
                "ask": ask,
                "open": open_price,
                "close": close_price,
                "timestamp": get_ist_timestamp(),
                "exchange_timestamp": datetime.fromtimestamp(tick_data.get('exchange_timestamp', 0) / 1000).isoformat() if tick_data.get('exchange_timestamp') else get_ist_timestamp()
            }
            
            # Publish to Redis Stream
            stream_key = f"{MARKET_DATA_STREAM}:{symbol}"
            await self.redis_client.xadd(
                stream_key,
                tick_message,
                maxlen=1000  # Keep last 1000 messages per symbol
            )
            
            # Update stats
            self.tick_count += 1
            self.last_tick_time = get_ist_now()
            
            if self.tick_count % 100 == 0:
                logger.info(f"📊 Published {self.tick_count} ticks to Redis")
            
        except Exception as e:
            logger.error(f"Error processing and publishing tick: {e}")
    
    def _get_symbol_from_token(self, token: str) -> str:
        """Get symbol name from token"""
        for symbol, token_val in self.symbol_tokens.items():
            if token_val == token:
                return symbol
        return f"TOKEN_{token}"  # Fallback if symbol not found
    
    async def close(self):
        """Close the streamer"""
        try:
            self.running = False
            self.ws_connected = False
            
            # Close WebSocket connection using the Angel One client
            if self.angel_client:
                self.angel_client.disconnect()
            
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ Market data Redis streamer closed")
        except Exception as e:
            logger.error(f"Error closing streamer: {e}")
    
    def get_stats(self) -> Dict:
        """Get streaming statistics"""
        return {
            "symbols_tracked": len(self.symbols),
            "symbols": self.symbols,
            "ws_connected": self.ws_connected,
            "tick_count": self.tick_count,
            "last_tick_time": self.last_tick_time.isoformat() if self.last_tick_time else None,
            "running": self.running,
            "has_credentials": True,
            "redis_connected": self.redis_client is not None
        }
    
    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to additional symbols"""
        try:
            if not self.angel_client or not self.ws_connected:
                logger.error("❌ Cannot subscribe - not connected")
                return False
            
            # Get tokens for new symbols
            new_tokens = []
            for symbol in symbols:
                token = self.symbol_tokens.get(symbol)
                if token:
                    new_tokens.append(token)
            
            if not new_tokens:
                logger.warning("No valid tokens found for new symbols")
                return False
            
            # Add to existing symbols
            self.symbols.extend(symbols)
            
            # Subscribe to new tokens
            token_group = [{
                "exchangeType": 1,  # NSE CM
                "tokens": new_tokens
            }]
            
            success = self.angel_client.subscribe(token_group)
            if success:
                logger.info(f"✅ Subscribed to {len(symbols)} new symbols: {symbols}")
            return success
            
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application"""
    global market_data_streamer
    
    # Startup
    try:
        logger.info("🚀 Starting market data streamer...")
        market_data_streamer = MarketDataRedisStreamer()
        await market_data_streamer.start()
        logger.info("✅ Market data streamer started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start market data streamer: {e}")
    
    yield
    
    # Shutdown
    if market_data_streamer:
        try:
            await market_data_streamer.close()
            logger.info("✅ Market data streamer stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping market data streamer: {e}")

# Create FastAPI app
app = FastAPI(
    title="Market Data Redis Streamer",
    description="Streams market data from Angel One to Redis Streams",
    version="4.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Market Data Redis Streamer",
        "version": "4.0.0",
        "status": "running",
        "redis_url": REDIS_URL,
        "stream": MARKET_DATA_STREAM,
        "implementation": "AngelOneWebSocketClient + Redis Streams"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if not market_data_streamer:
            return {
                "status": "unhealthy",
                "error": "Streamer not initialized"
            }
        
        stats = market_data_streamer.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "redis_connected": stats["redis_connected"],
            "ws_connected": stats["ws_connected"],
            "symbols_tracked": stats["symbols_tracked"],
            "tick_count": stats["tick_count"],
            "last_tick_time": stats["last_tick_time"],
            "has_credentials": stats["has_credentials"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/stats")
async def get_stats():
    """Get streaming statistics"""
    try:
        if not market_data_streamer:
            raise HTTPException(status_code=503, detail="Streamer not initialized")
        
        return market_data_streamer.get_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/symbols")
async def get_symbols():
    """Get list of tracked symbols"""
    try:
        if not market_data_streamer:
            raise HTTPException(status_code=503, detail="Streamer not initialized")
        
        return {
            "symbols": market_data_streamer.symbols,
            "count": len(market_data_streamer.symbols),
            "symbol_tokens": market_data_streamer.symbol_tokens
        }
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/subscribe")
async def subscribe_symbols(symbols: List[str]):
    """Subscribe to additional symbols"""
    try:
        if not market_data_streamer:
            raise HTTPException(status_code=503, detail="Streamer not initialized")
        
        success = await market_data_streamer.subscribe_to_symbols(symbols)
        
        if success:
            return {
                "message": f"Successfully subscribed to {len(symbols)} symbols",
                "symbols": symbols,
                "total_symbols": len(market_data_streamer.symbols)
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to subscribe to symbols")
            
    except Exception as e:
        logger.error(f"Error subscribing to symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
