#!/usr/bin/env python3
"""
Simple Trading Engine - Main Entry Point
"""

import asyncio
import logging
import sys
from pathlib import Path
import uvicorn

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.engine.production_engine import ProductionTradingEngine, app, set_production_engine

# Create and set the engine on import so FastAPI startup can use it
async def setup_engine():
    """Setup the trading engine"""
    try:
        logger.info("🚀 Initializing Simple Trading System")
        logger.info("=" * 50)
        
        # Initialize the production trading engine
        logger.info("🔄 Initializing production trading engine...")
        trading_engine = ProductionTradingEngine()
        
        # Initialize the engine
        await trading_engine.initialize()
        
        # Connect engine to FastAPI
        set_production_engine(trading_engine)
        
        logger.info("✅ Simple Trading System initialized successfully")
        logger.info("🌐 API server ready on http://0.0.0.0:8000")
        logger.info("📖 Documentation available at http://0.0.0.0:8000/docs")
        logger.info("=" * 50)
        
        return trading_engine
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Trading System: {e}")
        raise

if __name__ == "__main__":
    # Print startup banner
    print("\n" + "=" * 60)
    print("🚀 SIMPLE TRADING SYSTEM STARTING")
    print("=" * 60)
    
    # Run the FastAPI application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 