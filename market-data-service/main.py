"""
Market Data Service - Standalone service for streaming market data via NATS
Subscribes to Angel One WebSocket and publishes ticks to NATS
"""

import asyncio
import logging
import os
import sys
import json
import csv
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import nats
from nats.js.api import StreamConfig, RetentionPolicy
from dataclasses import dataclass

# Add parent directory to path to access shared modules
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only what we need directly
from smartapi import SmartConnect
from strategy.AngelWebSocket import SmartWebSocketV2
import pyotp

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
MARKET_DATA_STREAM = "MARKET_DATA"
MARKET_DATA_SUBJECT = "market.data.tick"

# Global instances
market_data_streamer = None

@dataclass
class MarketDataTick:
    """Market data tick structure"""
    symbol: str
    token: str
    ltp: float
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    bid: float
    ask: float
    timestamp: str
    exchange_timestamp: str

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

class MarketDataStreamer:
    """Streams market data from Angel One to NATS"""
    
    def __init__(self):
        self.api_key = os.getenv("ANGEL_ONE_API_KEY")
        self.client_code = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.password = os.getenv("ANGEL_ONE_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET")
        
        # Check if credentials are properly configured
        self.has_credentials = all([self.api_key, self.client_code, self.password, self.totp_secret]) and \
                              self.api_key != "your_api_key_here"
        
        self.smart_api = None
        self.session = None
        self.nats_client = None
        self.jetstream = None
        self.symbols = []
        self.running = False
        self.ws_connected = False
        self.tick_count = 0
        self.last_tick_time = None
        
        # Symbol-token mapping (simplified for now)
        self.symbol_tokens = {
            "RELIANCE": "2881",
            "TCS": "11536", 
            "INFY": "408065"
        }
    
    async def initialize(self):
        """Initialize the streamer"""
        try:
            # Load symbols
            self.symbols = load_symbols_from_csv()
            if not self.symbols:
                logger.warning("No symbols loaded from CSV. Using defaults.")
                self.symbols = ["RELIANCE", "TCS", "INFY"]
            
            # Initialize NATS connection
            logger.info(f"Connecting to NATS at {NATS_URL}...")
            self.nats_client = await nats.connect(NATS_URL)
            logger.info("✅ NATS connected")
            
            # Initialize JetStream
            self.jetstream = self.nats_client.jetstream()
            
            # Create or update stream
            try:
                await self.jetstream.add_stream(
                    name=MARKET_DATA_STREAM,
                    subjects=[f"{MARKET_DATA_SUBJECT}.>"],
                    retention=RetentionPolicy.LIMITS,
                    max_age=300,  # Keep messages for 5 minutes
                    max_msgs=1000000,
                    max_bytes=1024*1024*1024,  # 1GB
                    storage=nats.js.api.StorageType.MEMORY,
                )
                logger.info("✅ NATS JetStream configured")
            except Exception as e:
                logger.warning(f"Stream might already exist: {e}")
            
            # Initialize Angel One API if credentials available
            if self.has_credentials:
                await self._initialize_angel_one()
                # Start WebSocket streaming
                self.start_websocket_stream()
            else:
                logger.warning("⚠️ Angel One API credentials not configured. Using mock data mode.")
                # Start mock data streaming
                asyncio.create_task(self._mock_data_streamer())
            
            logger.info("✅ Market data streamer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize market data streamer: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def _initialize_angel_one(self):
        """Initialize Angel One API connection"""
        try:
            self.smart_api = SmartConnect(self.api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret)
            totp_code = totp.now()
            
            # Login
            self.session = self.smart_api.generateSession(
                self.client_code, 
                self.password, 
                totp_code
            )
            
            if self.session:
                logger.info("✅ Angel One API authenticated successfully")
            else:
                logger.error("❌ Angel One API authentication failed")
                
        except Exception as e:
            logger.error(f"Error initializing Angel One API: {e}")
    
    def start_websocket_stream(self):
        """Start Angel One WebSocket stream"""
        try:
            # Get all tokens for symbols
            tokens = []
            for symbol in self.symbols:
                token = self.symbol_tokens.get(symbol)
                if token:
                    tokens.append(token)
            
            if not tokens:
                logger.warning("No valid tokens found for symbols")
                return
            
            logger.info(f"Starting WebSocket stream for {len(tokens)} tokens...")
            
            # Define tick handler
            def on_tick(tick):
                """Handle incoming tick data from Angel One WebSocket"""
                try:
                    # Publish tick to NATS asynchronously
                    asyncio.create_task(self.publish_tick(tick))
                except Exception as e:
                    logger.error(f"Error in tick handler: {e}")
            
            # Start WebSocket stream
            sws = SmartWebSocketV2(self.session, self.client_code)
            sws.start_websocket(on_tick)
            self.ws_connected = True
            logger.info("✅ WebSocket stream started")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket stream: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _mock_data_streamer(self):
        """Mock data streamer for testing without API credentials"""
        logger.info("Starting mock data streamer...")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    # Generate mock tick data
                    mock_tick = {
                        "symbol": symbol,
                        "token": self.symbol_tokens.get(symbol, "0"),
                        "ltp": 1000.0 + (hash(symbol) % 1000),
                        "change": (hash(symbol) % 100) - 50,
                        "change_percent": ((hash(symbol) % 100) - 50) / 100,
                        "high": 1100.0,
                        "low": 900.0,
                        "volume": hash(symbol) % 10000,
                        "bid": 999.0,
                        "ask": 1001.0,
                        "timestamp": datetime.now().isoformat(),
                        "exchange_timestamp": datetime.now().isoformat()
                    }
                    
                    await self.publish_tick(mock_tick)
                
                # Wait 1 second before next update
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in mock data streamer: {e}")
                await asyncio.sleep(5)
    
    async def publish_tick(self, tick: Dict):
        """Publish tick data to NATS"""
        try:
            if not self.jetstream:
                return
            
            # Extract symbol from tick
            symbol = tick.get('symbol', 'UNKNOWN')
            
            # Create tick message
            tick_message = {
                "symbol": symbol,
                "token": tick.get('token', ''),
                "ltp": tick.get('ltp', 0),
                "change": tick.get('change', 0),
                "change_percent": tick.get('change_percent', 0),
                "high": tick.get('high', 0),
                "low": tick.get('low', 0),
                "volume": tick.get('volume', 0),
                "bid": tick.get('bid', 0),
                "ask": tick.get('ask', 0),
                "timestamp": tick.get('timestamp', datetime.now().isoformat()),
                "exchange_timestamp": tick.get('exchange_timestamp', '')
            }
            
            # Publish to NATS JetStream
            subject = f"{MARKET_DATA_SUBJECT}.{symbol}"
            await self.jetstream.publish(
                subject,
                json.dumps(tick_message).encode()
            )
            
            # Update stats
            self.tick_count += 1
            self.last_tick_time = datetime.now()
            
            if self.tick_count % 100 == 0:
                logger.info(f"📊 Published {self.tick_count} ticks to NATS")
            
        except Exception as e:
            logger.error(f"Error publishing tick to NATS: {e}")
    
    async def close(self):
        """Close the streamer"""
        try:
            self.running = False
            self.ws_connected = False
            
            if self.nats_client:
                await self.nats_client.close()
            
            logger.info("✅ Market data streamer closed")
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
            "has_credentials": self.has_credentials
        }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global market_data_streamer
    
    # Startup
    logger.info("🚀 Starting Market Data Service...")
    try:
        market_data_streamer = MarketDataStreamer()
        success = await market_data_streamer.initialize()
        
        if not success:
            logger.error("❌ Failed to initialize market data streamer")
        else:
            logger.info("✅ Market Data Service started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start market data service: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Market Data Service...")
    if market_data_streamer:
        try:
            await market_data_streamer.close()
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("✅ Market Data Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Market Data Service",
    description="Streams market data from Angel One to NATS",
    version="1.0.0",
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
        "service": "Market Data Service",
        "version": "1.0.0",
        "status": "running",
        "nats_url": NATS_URL,
        "stream": MARKET_DATA_STREAM
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
            "nats_connected": market_data_streamer.nats_client is not None,
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
            "count": len(market_data_streamer.symbols)
        }
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)