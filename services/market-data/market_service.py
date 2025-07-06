#!/usr/bin/env python3
"""
Market Data Service - Real-time market data with caching
Isolated service for market data fetching, caching, and distribution
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
import redis.asyncio as redis
import httpx
import os
from dataclasses import dataclass
from enum import Enum
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.common.performance import monitor_performance, CacheManager
from shared.common.monitoring import MetricsCollector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class MarketDataConfig:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    ANGEL_ONE_API_KEY: str = os.getenv("ANGEL_ONE_API_KEY", "")
    ANGEL_ONE_CLIENT_ID: str = os.getenv("ANGEL_ONE_CLIENT_ID", "")
    CACHE_TTL_SECONDS: int = 1  # 1 second cache for real-time data
    BATCH_SIZE: int = 50  # Max symbols per batch request
    UPDATE_INTERVAL: float = 0.5  # Update every 500ms

config = MarketDataConfig()

class DataSource(Enum):
    ANGEL_ONE = "angel_one"
    MOCK = "mock"
    CSV = "csv"

class MarketDataCache:
    """Redis-based market data cache with real-time updates"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.subscribed_symbols = set()
        self.is_running = False
        
    async def get_realtime_data(self, symbol: str) -> Optional[Dict]:
        """Get cached real-time data for symbol"""
        cache_key = f"market_data:{symbol}"
        cached_data = await self.redis_client.get(cache_key)
        
        if cached_data:
            data = json.loads(cached_data)
            # Check if data is fresh (within cache TTL)
            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp < config.CACHE_TTL_SECONDS:
                return data
        
        return None
    
    async def set_realtime_data(self, symbol: str, data: Dict):
        """Cache real-time data with TTL"""
        cache_key = f"market_data:{symbol}"
        data["timestamp"] = time.time()
        data["cached_at"] = datetime.utcnow().isoformat()
        
        await self.redis_client.setex(
            cache_key,
            config.CACHE_TTL_SECONDS * 2,  # Cache for 2x TTL
            json.dumps(data)
        )
    
    async def get_multiple_symbols(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get cached data for multiple symbols"""
        result = {}
        pipe = self.redis_client.pipeline()
        
        for symbol in symbols:
            pipe.get(f"market_data:{symbol}")
        
        cached_results = await pipe.execute()
        
        for symbol, cached_data in zip(symbols, cached_results):
            if cached_data:
                try:
                    data = json.loads(cached_data)
                    if time.time() - data.get("timestamp", 0) < config.CACHE_TTL_SECONDS:
                        result[symbol] = data
                except json.JSONDecodeError:
                    continue
        
        return result
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to real-time updates for symbol"""
        self.subscribed_symbols.add(symbol)
        logger.info(f"Subscribed to {symbol}, total: {len(self.subscribed_symbols)}")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from symbol updates"""
        self.subscribed_symbols.discard(symbol)
        logger.info(f"Unsubscribed from {symbol}, total: {len(self.subscribed_symbols)}")

class AngelOneDataProvider:
    """Angel One API integration for real market data"""
    
    def __init__(self):
        self.api_key = config.ANGEL_ONE_API_KEY
        self.client_id = config.ANGEL_ONE_CLIENT_ID
        self.session = None
        self.auth_token = None
        
    async def initialize(self):
        """Initialize Angel One session"""
        if not self.api_key or not self.client_id:
            logger.warning("Angel One credentials not configured, using mock data")
            return False
            
        try:
            # This would be actual Angel One authentication
            self.session = httpx.AsyncClient()
            logger.info("✅ Angel One provider initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Angel One: {e}")
            return False
    
    async def get_live_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch live market data from Angel One API"""
        if not self.session:
            return self._generate_mock_data(symbols)
        
        try:
            # Mock implementation - replace with actual Angel One API calls
            return self._generate_mock_data(symbols)
            
        except Exception as e:
            logger.error(f"Error fetching data from Angel One: {e}")
            return self._generate_mock_data(symbols)
    
    def _generate_mock_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Generate realistic mock market data"""
        import random
        
        base_prices = {
            "RELIANCE": 2800.0,
            "TCS": 3500.0,
            "INFY": 1800.0,
            "HDFC": 1600.0,
            "ICICIBANK": 950.0,
            "WIPRO": 450.0,
            "ITC": 460.0,
            "HDFCBANK": 1550.0,
            "KOTAKBANK": 1750.0,
            "AXISBANK": 1100.0
        }
        
        result = {}
        for symbol in symbols:
            base_price = base_prices.get(symbol, 1000.0)
            # Add realistic price movement
            change_percent = random.uniform(-2.0, 2.0)
            current_price = base_price * (1 + change_percent / 100)
            
            result[symbol] = {
                "symbol": symbol,
                "ltp": round(current_price, 2),
                "open": round(base_price * random.uniform(0.98, 1.02), 2),
                "high": round(current_price * random.uniform(1.0, 1.03), 2),
                "low": round(current_price * random.uniform(0.97, 1.0), 2),
                "volume": random.randint(100000, 5000000),
                "change": round(current_price - base_price, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": time.time(),
                "market_status": "OPEN",
                "data_source": "mock_angel_one"
            }
        
        return result
    
    async def close(self):
        """Close Angel One session"""
        if self.session:
            await self.session.aclose()

class MarketDataEngine:
    """Main engine for market data operations"""
    
    def __init__(self):
        self.cache = None
        self.data_provider = None
        self.is_running = False
        self.update_task = None
        
    async def initialize(self, redis_client):
        """Initialize market data engine"""
        self.cache = MarketDataCache(redis_client)
        self.data_provider = AngelOneDataProvider()
        
        await self.data_provider.initialize()
        logger.info("✅ Market Data Engine initialized")
    
    async def start_real_time_updates(self):
        """Start background task for real-time data updates"""
        if self.is_running:
            return
            
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info("🔄 Real-time market data updates started")
    
    async def stop_real_time_updates(self):
        """Stop real-time updates"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Real-time market data updates stopped")
    
    async def _update_loop(self):
        """Background loop to fetch and cache market data"""
        while self.is_running:
            try:
                if self.cache.subscribed_symbols:
                    symbols = list(self.cache.subscribed_symbols)
                    
                    # Fetch data in batches
                    for i in range(0, len(symbols), config.BATCH_SIZE):
                        batch = symbols[i:i + config.BATCH_SIZE]
                        market_data = await self.data_provider.get_live_market_data(batch)
                        
                        # Cache the data
                        for symbol, data in market_data.items():
                            await self.cache.set_realtime_data(symbol, data)
                
                await asyncio.sleep(config.UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in market data update loop: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def get_symbol_data(self, symbol: str) -> Dict:
        """Get real-time data for a single symbol"""
        # Try cache first
        cached_data = await self.cache.get_realtime_data(symbol)
        if cached_data:
            return cached_data
        
        # If not in cache, fetch fresh data
        market_data = await self.data_provider.get_live_market_data([symbol])
        data = market_data.get(symbol, {})
        
        if data:
            await self.cache.set_realtime_data(symbol, data)
            # Auto-subscribe to this symbol for future updates
            await self.cache.subscribe_symbol(symbol)
        
        return data
    
    async def get_multiple_symbols_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get real-time data for multiple symbols"""
        # Check cache first
        cached_data = await self.cache.get_multiple_symbols(symbols)
        missing_symbols = [s for s in symbols if s not in cached_data]
        
        # Fetch missing symbols
        if missing_symbols:
            fresh_data = await self.data_provider.get_live_market_data(missing_symbols)
            
            # Cache fresh data and auto-subscribe
            for symbol, data in fresh_data.items():
                await self.cache.set_realtime_data(symbol, data)
                await self.cache.subscribe_symbol(symbol)
                cached_data[symbol] = data
        
        return cached_data

# Initialize FastAPI app
app = FastAPI(
    title="Market Data Service",
    description="Real-time Market Data with Caching",
    version="1.0.0",
    lifespan=lifespan
)

# Global components
redis_client = None
market_engine = None
cache_manager = None
metrics_collector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup market data service"""
    global redis_client, market_engine
    
    try:
        logger.info("🚀 Market Data Service starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url(config.REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize market data engine
        market_engine = MarketDataEngine()
        await market_engine.initialize(redis_client)
        
        # Start real-time updates
        await market_engine.start_real_time_updates()
        
        # Initialize performance components
        cache_manager = CacheManager(redis_client)
        metrics_collector = MetricsCollector(redis_client)
        
        logger.info("✅ Market Data Service ready on port 8002")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Market Data Service: {e}")
        raise
    
    yield
    
    # Cleanup
    if market_engine:
        await market_engine.stop_real_time_updates()
    if redis_client:
        await redis_client.close()
    logger.info("🔄 Market Data Service shutting down...")

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "subscribed_symbols": len(market_engine.cache.subscribed_symbols) if market_engine else 0,
            "data_source": "angel_one" if config.ANGEL_ONE_API_KEY else "mock"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.get("/realtime/{symbol}")
@monitor_performance("get_realtime_data")
async def get_realtime_data(symbol: str):
    """Get real-time data for a symbol"""
    if not market_engine:
        raise HTTPException(status_code=503, detail="Market engine not initialized")
    
    try:
        # Use cache manager for better performance
        async def fetch_data():
            return await market_engine.get_symbol_data(symbol.upper())
        
        data = await cache_manager.get_or_set(
            f"market_data:{symbol}",
            fetch_data,
            ttl=1  # 1 second cache for real-time data
        )
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
        
        # Record metrics
        await metrics_collector.record_metric("market_data_requests", 1, {"symbol": symbol})
        
        return {
            "symbol": symbol.upper(),
            "data": data,
            "cached": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data")

@app.post("/realtime/batch")
async def get_batch_data(symbols: List[str]):
    """Get real-time data for multiple symbols"""
    if not market_engine:
        raise HTTPException(status_code=503, detail="Market engine not initialized")
    
    try:
        symbols_upper = [s.upper() for s in symbols]
        data = await market_engine.get_multiple_symbols_data(symbols_upper)
        
        return {
            "symbols": symbols_upper,
            "data": data,
            "count": len(data),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting batch data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data")

@app.post("/subscribe/{symbol}")
async def subscribe_symbol(symbol: str):
    """Subscribe to real-time updates for a symbol"""
    if not market_engine:
        raise HTTPException(status_code=503, detail="Market engine not initialized")
    
    await market_engine.cache.subscribe_symbol(symbol.upper())
    return {"message": f"Subscribed to {symbol.upper()}", "symbol": symbol.upper()}

@app.delete("/subscribe/{symbol}")
async def unsubscribe_symbol(symbol: str):
    """Unsubscribe from symbol updates"""
    if not market_engine:
        raise HTTPException(status_code=503, detail="Market engine not initialized")
    
    await market_engine.cache.unsubscribe_symbol(symbol.upper())
    return {"message": f"Unsubscribed from {symbol.upper()}", "symbol": symbol.upper()}

@app.get("/subscriptions")
async def get_subscriptions():
    """Get list of subscribed symbols"""
    if not market_engine:
        raise HTTPException(status_code=503, detail="Market engine not initialized")
    
    return {
        "subscribed_symbols": list(market_engine.cache.subscribed_symbols),
        "count": len(market_engine.cache.subscribed_symbols)
    }

@app.get("/")
async def service_info():
    """Service information"""
    return {
        "service": "Market Data Service",
        "version": "1.0.0", 
        "status": "operational",
        "data_source": "angel_one" if config.ANGEL_ONE_API_KEY else "mock",
        "cache_ttl": config.CACHE_TTL_SECONDS,
        "update_interval": config.UPDATE_INTERVAL,
        "endpoints": [
            "GET /realtime/{symbol}",
            "POST /realtime/batch",
            "POST /subscribe/{symbol}",
            "DELETE /subscribe/{symbol}",
            "GET /subscriptions",
            "GET /health"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 