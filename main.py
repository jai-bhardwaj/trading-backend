#!/usr/bin/env python3
"""
Trading Engine Main Entry Point
Centralized startup with proper configuration management and error handling
"""

import asyncio
import signal
import sys
import logging
import time
from datetime import datetime
from app.utils.timezone_utils import ist_now as datetime_now
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings, validate_configuration, setup_logging
from app.database import initialize_database, get_database_manager
from app.engine.redis_engine import RedisBasedTradingEngine

# Setup logging early
logger = logging.getLogger(__name__)

class TradingEngineManager:
    """Main trading engine manager with proper lifecycle management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = None
        self.trading_engine = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("🚀 Initializing Trading Engine")
            logger.info("=" * 60)
            
            # Validate configuration
            validation = validate_configuration(self.settings)
            if not validation["valid"]:
                logger.error("❌ Configuration validation failed:")
                for error in validation["errors"]:
                    logger.error(f"  • {error}")
                raise ValueError("Invalid configuration")
            
            # Log configuration info
            for info in validation["info"]:
                logger.info(f"⚙️ {info}")
            
            # Log warnings if any
            for warning in validation["warnings"]:
                logger.warning(f"⚠️ {warning}")
            
            # Initialize database
            logger.info("📊 Initializing database connections...")
            self.db_manager = await initialize_database()
            
            # Test database connection
            health = await self.db_manager.health_check()
            if not health["overall_healthy"]:
                logger.error("❌ Database health check failed:")
                if not health["database"]["healthy"]:
                    logger.error(f"  • PostgreSQL: {health['database']['error']}")
                if not health["redis"]["healthy"]:
                    logger.error(f"  • Redis: {health['redis']['error']}")
                raise ConnectionError("Database connections failed")
            
            logger.info("✅ Database connections healthy")
            
            # Initialize trading engine
            logger.info("🔄 Initializing trading engine...")
            engine_config = self.settings.trading_engine
            self.trading_engine = RedisBasedTradingEngine(
                worker_count=engine_config.worker_count,
                max_queue_size=engine_config.max_queue_size,
                db_manager=self.db_manager
            )
            
            # Start trading engine
            success = await self.trading_engine.start()
            if not success:
                raise RuntimeError("Failed to start trading engine")
            
            self.is_running = True
            logger.info("✅ Trading Engine initialized successfully")
            logger.info("=" * 60)
            
            # Log final status
            self._log_startup_summary()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trading Engine: {e}")
            await self.cleanup()
            raise
    
    def _log_startup_summary(self):
        """Log startup summary"""
        summary = [
            f"🎯 Trading Engine Status: {'RUNNING' if self.is_running else 'STOPPED'}",
            f"🏢 Environment: {self.settings.environment.upper()}",
            f"🔧 Debug Mode: {'ON' if self.settings.debug else 'OFF'}",
            f"👥 Workers: {self.settings.trading_engine.worker_count}",
            f"📊 Queue Size: {self.settings.trading_engine.max_queue_size}",
            f"🔗 Database Pool: {self.settings.database.pool_size}",
        ]
        
        logger.info("📋 STARTUP SUMMARY:")
        for item in summary:
            logger.info(f"   {item}")
        
        logger.info("🎉 Trading Engine is ready for trading!")
    
    async def run(self):
        """Main run loop"""
        if not self.is_running:
            raise RuntimeError("Engine not initialized")
        
        logger.info("🔄 Starting main event loop...")
        
        try:
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Main loop - keep running until interrupted
            while self.is_running:
                await asyncio.sleep(self.settings.trading_engine.loop_interval)
                
                # Periodic health checks
                if hasattr(self, '_last_health_check'):
                    if time.time() - self._last_health_check > 300:  # Every 5 minutes
                        await self._periodic_health_check()
                else:
                    self._last_health_check = time.time()
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Unexpected error in main loop: {e}")
        finally:
            await self.cleanup()
    
    async def _periodic_health_check(self):
        """Perform periodic health checks"""
        try:
            health = await self.db_manager.health_check()
            if not health["overall_healthy"]:
                logger.warning("⚠️ Health check warning - some components unhealthy")
            
            # Update last health check time
            self._last_health_check = time.time()
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"📡 Received {signal_name} signal - initiating graceful shutdown...")
            self.is_running = False
        
        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Handle SIGUSR1 for reload (if needed in future)
        def reload_handler(signum, frame):
            logger.info("📡 Received SIGUSR1 - reload requested")
            # Future: implement configuration reload
        
        signal.signal(signal.SIGUSR1, reload_handler)
    
    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("🧹 Starting cleanup process...")
        
        cleanup_tasks = []
        
        # Stop trading engine
        if self.trading_engine:
            try:
                logger.info("⏹️ Stopping trading engine...")
                await self.trading_engine.stop()
                logger.info("✅ Trading engine stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping trading engine: {e}")
        
        # Close database connections
        if self.db_manager:
            try:
                logger.info("🔒 Closing database connections...")
                await self.db_manager.close()
                logger.info("✅ Database connections closed")
            except Exception as e:
                logger.error(f"❌ Error closing database: {e}")
        
        self.is_running = False
        logger.info("🏁 Cleanup completed")

async def main():
    """Main entry point"""
    manager = TradingEngineManager()
    
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
    # Setup logging before anything else
    settings = get_settings()
    setup_logging(settings)
    
    # Print startup banner
    print("\n" + "=" * 60)
    print("🚀 TRADING ENGINE STARTING")
    print("=" * 60)
    
    # Run the application
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        sys.exit(1) 