#!/usr/bin/env python3
"""
Lightweight Trading Engine - Main Application
Ultra-efficient trading system for 100+ strategies on 3GB RAM
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import LightweightTradingEngine, EngineConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_engine.log')
    ]
)

logger = logging.getLogger(__name__)

class TradingEngineApp:
    """Main application class"""
    
    def __init__(self):
        self.engine = None
        self.shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the trading engine"""
        try:
            # Create engine configuration
            config = EngineConfig(
                max_strategies=1000,
                max_orders_per_second=10,
                data_refresh_interval=1,
                strategy_execution_interval=5,
                memory_limit_mb=400,  # Leave 100MB for system
                enable_paper_trading=True
            )
            
            # Create and start engine
            self.engine = LightweightTradingEngine(config)
            
            logger.info("🚀 Starting Lightweight Trading Engine...")
            logger.info(f"📊 Configuration: {config.max_strategies} strategies, {config.memory_limit_mb}MB limit")
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start engine
            await self.engine.start()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Shutdown requested by user")
        except Exception as e:
            logger.error(f"❌ Engine startup error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the engine gracefully"""
        if self.engine:
            logger.info("🛑 Shutting down trading engine...")
            await self.engine.stop()
            logger.info("✅ Engine shutdown complete")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point"""
    app = TradingEngineApp()
    await app.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1) 