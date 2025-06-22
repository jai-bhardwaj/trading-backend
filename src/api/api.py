#!/usr/bin/env python3
"""
Lightweight Trading Engine - Web API
Simple monitoring and control interface
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn
import json

from core.engine import LightweightTradingEngine, EngineConfig
from core.strategy_manager import StrategyConfig

logger = logging.getLogger(__name__)

# Global engine instance
engine: Optional[LightweightTradingEngine] = None

# Create FastAPI app
app = FastAPI(
    title="Lightweight Trading Engine API",
    description="Ultra-efficient trading system for 100+ strategies",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize the trading engine"""
    global engine
    
    config = EngineConfig(
        max_strategies=1000,
        max_orders_per_second=10,
        data_refresh_interval=1,
        strategy_execution_interval=5,
        memory_limit_mb=400,
        enable_paper_trading=True
    )
    
    engine = LightweightTradingEngine(config)
    
    # Start engine in background
    asyncio.create_task(engine.start())
    
    logger.info("🚀 Trading Engine API started")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the trading engine"""
    global engine
    if engine:
        await engine.stop()
        logger.info("🛑 Trading Engine API stopped")

@app.get("/")
async def root():
    """Root endpoint with HTML dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lightweight Trading Engine</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .stat { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 6px; }
            .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
            .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
            .status-running { color: #28a745; }
            .status-stopped { color: #dc3545; }
            h1 { color: #333; text-align: center; }
            h2 { color: #555; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #0056b3; }
        </style>
        <script>
            async function refreshStats() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    document.getElementById('stats-content').innerHTML = JSON.stringify(data, null, 2);
                } catch (error) {
                    console.error('Error fetching stats:', error);
                }
            }
            
            setInterval(refreshStats, 5000); // Auto-refresh every 5 seconds
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Lightweight Trading Engine</h1>
            <div class="card">
                <h2>📊 System Overview</h2>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">100+</div>
                        <div class="stat-label">Strategies Supported</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">~150MB</div>
                        <div class="stat-label">Memory Usage</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">3GB</div>
                        <div class="stat-label">System Requirement</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value status-running">RUNNING</div>
                        <div class="stat-label">Engine Status</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔧 Quick Actions</h2>
                <button class="refresh-btn" onclick="refreshStats()">Refresh Stats</button>
                <a href="/status" class="refresh-btn" style="text-decoration: none; margin-left: 10px;">View JSON Status</a>
                <a href="/docs" class="refresh-btn" style="text-decoration: none; margin-left: 10px;">API Documentation</a>
            </div>
            
            <div class="card">
                <h2>📈 Live Statistics</h2>
                <pre id="stats-content" style="background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto;">
Loading...
                </pre>
            </div>
        </div>
        
        <script>
            // Load initial stats
            refreshStats();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get engine status and statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return engine.get_status()

@app.get("/strategies")
async def get_strategies() -> Dict[str, Any]:
    """Get strategy statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return engine.strategy_manager.get_stats()

@app.get("/orders")
async def get_orders() -> Dict[str, Any]:
    """Get order statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return engine.order_manager.get_stats()

@app.get("/market-data")
async def get_market_data() -> Dict[str, Any]:
    """Get market data statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return engine.data_manager.get_stats()

@app.get("/broker")
async def get_broker_stats() -> Dict[str, Any]:
    """Get broker statistics"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    return engine.broker_manager.get_stats()

@app.post("/strategies/add")
async def add_strategy(strategy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new strategy"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        config = StrategyConfig(
            strategy_id=strategy_data['strategy_id'],
            name=strategy_data['name'],
            symbols=strategy_data['symbols'],
            enabled=strategy_data.get('enabled', True),
            execution_interval=strategy_data.get('execution_interval', 5),
            parameters=strategy_data.get('parameters', {})
        )
        
        success = engine.add_strategy(config.__dict__)
        
        return {
            "success": success,
            "message": f"Strategy {config.name} {'added' if success else 'failed to add'}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/strategies/{strategy_id}")
async def remove_strategy(strategy_id: str) -> Dict[str, Any]:
    """Remove a strategy"""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    success = engine.remove_strategy(strategy_id)
    
    return {
        "success": success,
        "message": f"Strategy {strategy_id} {'removed' if success else 'not found'}"
    }

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy" if engine and engine.is_running else "unhealthy",
        "service": "lightweight-trading-engine"
    }

if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    ) 