#!/usr/bin/env python3
"""
Industrial Trading Engine - Main Entry Point
High-Performance Multi-User Trading System
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
import uvicorn

# Setup logging with Docker-friendly configuration
import os
log_handlers = [logging.StreamHandler()]

# Only add file handler if we can write to logs directory
try:
    os.makedirs('logs', exist_ok=True)
    # Test write permissions
    test_file = 'logs/test_write.tmp'
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    log_handlers.append(logging.FileHandler('logs/trading_engine.log'))
except (PermissionError, OSError):
    # If we can't write to logs, just use console logging
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)

logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.engine.production_engine import ProductionTradingEngine, app, set_production_engine

class TradingSystemManager:
    """Main trading system manager"""
    
    def __init__(self):
        self.trading_engine = None
        self.is_running = False
    
    async def initialize(self):
        """Initialize the trading system"""
        try:
            logger.info("🚀 Initializing Industrial Trading System")
            logger.info("=" * 60)
            
            # Create logs directory
            Path("logs").mkdir(exist_ok=True)
            
            # Initialize the production trading engine
            logger.info("🔄 Initializing production trading engine...")
            self.trading_engine = ProductionTradingEngine()
            
            # Initialize the engine
            await self.trading_engine.initialize()
            
            # Connect engine to FastAPI
            set_production_engine(self.trading_engine)
            
            self.is_running = True
            logger.info("✅ Industrial Trading System initialized successfully")
            logger.info("=" * 60)
            
            # Log final status
            self._log_startup_summary()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trading System: {e}")
            await self.cleanup()
            raise
    
    def _log_startup_summary(self):
        """Log startup summary"""
        summary = [
            f"🎯 Trading System Status: {'RUNNING' if self.is_running else 'STOPPED'}",
            f"🏢 Engine Type: Industrial Production Engine",
            f"📊 Multi-User Support: ENABLED",
            f"🔗 Real Broker Integration: ENABLED",
            f"🌐 API Server: ENABLED",
            f"📧 Email Notifications: ENABLED"
        ]
        
        logger.info("📋 STARTUP SUMMARY:")
        for item in summary:
            logger.info(f"   {item}")
        
        logger.info("🎉 Industrial Trading System is ready for production!")
    
    async def run(self):
        """Main run loop"""
        if not self.is_running:
            raise RuntimeError("System not initialized")
        
        logger.info("🔄 Starting production execution loop...")
        
        try:
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Create tasks for both the FastAPI server and trading engine
            server_task = asyncio.create_task(self._run_fastapi_server())
            engine_task = asyncio.create_task(self.trading_engine.start_execution_loop())
            
            logger.info("🚀 Both API server and trading engine started!")
            
            # Wait for both tasks
            await asyncio.gather(server_task, engine_task)
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Unexpected error in main loop: {e}")
        finally:
            await self.cleanup()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"📡 Received {signal_name} signal - initiating graceful shutdown...")
            self.is_running = False
            if self.trading_engine:
                self.trading_engine.stop_execution_loop()
        
        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("🧹 Starting cleanup process...")
        
        # Stop trading engine
        if self.trading_engine:
            try:
                logger.info("⏹️ Stopping trading engine...")
                self.trading_engine.stop_execution_loop()
                logger.info("✅ Trading engine stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping trading engine: {e}")
        
        self.is_running = False
        logger.info("🏁 Cleanup completed")

    async def _run_fastapi_server(self):
        """Run FastAPI server"""
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()

async def main():
    """Main entry point"""
    manager = TradingSystemManager()
    
    try:
        # Initialize all components
        await manager.initialize()
        
        # Run the main loop
        await manager.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    finally:
        await manager.cleanup()
    
    return 0

if __name__ == "__main__":
    # Print startup banner
    print("\n" + "=" * 60)
    print("🚀 INDUSTRIAL TRADING SYSTEM STARTING")
    print("=" * 60)
    
    # Run the application
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        sys.exit(1) 