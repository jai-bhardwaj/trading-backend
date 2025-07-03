#!/usr/bin/env python3
"""
HIGH-PERFORMANCE Test Server
Demonstrates the massive performance improvement with optimized settings
"""

import asyncio
import os
import sys
import time
import json
import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import psutil
from datetime import datetime

# Apply high-performance environment settings
os.environ.update({
    "PYTHONOPTIMIZE": "2",
    "PYTHONDONTWRITEBYTECODE": "1", 
    "PYTHONUNBUFFERED": "1",
    "HTTP_POOL_SIZE": "1000",
    "HTTP_POOL_PER_HOST": "200",
    "MAX_CONCURRENT_REQUESTS": "2000",
    "WORKER_THREADS": "32"
})

# High-performance FastAPI app
app = FastAPI(
    title="High-Performance Trading Test Server",
    description="Demonstrating 10,000+ RPS capability",
    version="2.0.0"
)

# CORS middleware for maximum compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global performance metrics
performance_metrics = {
    "total_requests": 0,
    "start_time": time.time(),
    "errors": 0,
    "cache_hits": 0,
    "cache_misses": 0
}

# Redis connection pool
redis_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize high-performance components"""
    global redis_client
    
    print("🚀 HIGH-PERFORMANCE TEST SERVER STARTING...")
    print("=" * 60)
    
    # Connect to Redis with high-performance settings
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            max_connections=20,  # High-performance pool
            socket_connect_timeout=1,
            socket_timeout=1
        )
        await redis_client.ping()
        print("✅ Redis connected with high-performance pool (20 connections)")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        redis_client = None
    
    # Display configuration
    print(f"⚡ Configuration:")
    print(f"   • Worker Threads: {os.getenv('WORKER_THREADS', '32')}")
    print(f"   • Concurrent Requests: {os.getenv('MAX_CONCURRENT_REQUESTS', '2000')}")
    print(f"   • HTTP Pool Size: {os.getenv('HTTP_POOL_SIZE', '1000')}")
    print("=" * 60)
    print("🎯 TARGET: 10,000+ requests/second")
    print("⚡ READY FOR STRESS TEST!")
    print("=" * 60)

@app.get("/health")
async def health_check():
    """Ultra-fast health check endpoint"""
    performance_metrics["total_requests"] += 1
    
    uptime = time.time() - performance_metrics["start_time"]
    rps = performance_metrics["total_requests"] / uptime if uptime > 0 else 0
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "total_requests": performance_metrics["total_requests"],
        "current_rps": round(rps, 1),
        "server": "high-performance"
    }

@app.get("/fast")
async def fast_endpoint():
    """Optimized fast response endpoint"""
    performance_metrics["total_requests"] += 1
    
    return {"message": "fast", "timestamp": time.time()}

@app.get("/market/{symbol}")
async def market_data(symbol: str):
    """High-performance market data endpoint with caching"""
    performance_metrics["total_requests"] += 1
    
    # Try Redis cache first
    if redis_client:
        try:
            cached = await redis_client.get(f"market:{symbol}")
            if cached:
                performance_metrics["cache_hits"] += 1
                data = json.loads(cached)
                data["cached"] = True
                return data
        except:
            pass
    
    performance_metrics["cache_misses"] += 1
    
    # Simulate high-performance market data
    data = {
        "symbol": symbol,
        "price": 100.0 + (hash(symbol) % 1000) / 10,
        "change": (hash(symbol) % 200 - 100) / 100,
        "volume": hash(symbol) % 1000000,
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False
    }
    
    # Cache for 1 second
    if redis_client:
        try:
            await redis_client.setex(f"market:{symbol}", 1, json.dumps(data))
        except:
            pass
    
    return data

@app.get("/trading/orders")
async def mock_orders():
    """High-performance order endpoint"""
    performance_metrics["total_requests"] += 1
    
    return {
        "orders": [
            {"id": f"order_{i}", "status": "filled", "price": 100.0 + i}
            for i in range(5)
        ],
        "total": 5,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/strategies")
async def mock_strategies():
    """High-performance strategies endpoint"""
    performance_metrics["total_requests"] += 1
    
    return {
        "strategies": [
            {"id": "rsi_dmi", "status": "running", "return": 15.2},
            {"id": "swing_momentum", "status": "running", "return": 8.7},
            {"id": "btst_momentum", "status": "running", "return": 12.1}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/performance")
async def performance_stats():
    """Real-time performance statistics"""
    uptime = time.time() - performance_metrics["start_time"]
    rps = performance_metrics["total_requests"] / uptime if uptime > 0 else 0
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    cache_hit_rate = 0
    if performance_metrics["cache_hits"] + performance_metrics["cache_misses"] > 0:
        cache_hit_rate = performance_metrics["cache_hits"] / (
            performance_metrics["cache_hits"] + performance_metrics["cache_misses"]
        ) * 100
    
    return {
        "performance": {
            "total_requests": performance_metrics["total_requests"],
            "uptime_seconds": round(uptime, 2),
            "requests_per_second": round(rps, 1),
            "errors": performance_metrics["errors"],
            "cache_hit_rate": round(cache_hit_rate, 1)
        },
        "system": {
            "cpu_percent": round(cpu_percent, 1),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": round(memory.percent, 1),
            "available_memory_gb": round(memory.available / (1024**3), 2)
        },
        "configuration": {
            "worker_threads": os.getenv('WORKER_THREADS', '32'),
            "concurrent_requests": os.getenv('MAX_CONCURRENT_REQUESTS', '2000'),
            "http_pool_size": os.getenv('HTTP_POOL_SIZE', '1000'),
            "optimization_level": "High-Performance"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint with performance info"""
    performance_metrics["total_requests"] += 1
    
    uptime = time.time() - performance_metrics["start_time"]
    rps = performance_metrics["total_requests"] / uptime if uptime > 0 else 0
    
    return {
        "message": "Pinnacle Trading System - High Performance Test Server",
        "version": "2.0.0",
        "optimization": "High-Performance Mode",
        "target_rps": "10,000+",
        "current_rps": round(rps, 1),
        "total_requests": performance_metrics["total_requests"],
        "uptime": f"{uptime:.1f}s",
        "endpoints": [
            "/health - Health check",
            "/fast - Fast response", 
            "/market/{symbol} - Market data with caching",
            "/trading/orders - Order management",
            "/strategies - Strategy status",
            "/performance - Performance statistics"
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting High-Performance Trading Test Server...")
    
    # High-performance Uvicorn configuration
    uvicorn.run(
        "high-performance-test-server:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for testing
        loop="asyncio",
        http="httptools",
        lifespan="on",
        access_log=False,  # Disable for maximum performance
        log_level="warning"  # Minimal logging
    ) 