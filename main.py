#!/usr/bin/env python3
"""
Trading Engine Main Application
Industrial-grade trading backend with Redis queue processing
"""

import asyncio
import logging
import logging.config
import signal
import sys
from pathlib import Path
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import application modules
from app.core.config import settings
from app.database import engine, init_database
from app.engine.trading_engine import TradingEngine
from app.engine.redis_engine import RedisEngine

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging():
    """Setup production logging configuration"""
    log_config_path = Path("config/logging.conf")
    if log_config_path.exists():
        logging.config.fileConfig(log_config_path, disable_existing_loggers=False)
    else:
        # Fallback logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/trading_engine.log')
            ]
        )
    
    # Create logger
    logger = logging.getLogger('trading')
    return logger

class TradingApplication:
    """Main trading application with lifecycle management"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.redis_engine = None
        self.trading_engine = None
        self.shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize application components"""
        try:
            self.logger.info("Starting Trading Engine...")
            
            # Initialize database
            await self.init_database()
            
            # Initialize Redis engine
            self.redis_engine = RedisEngine()
            await self.redis_engine.initialize()
            
            # Initialize trading engine
            self.trading_engine = TradingEngine(redis_engine=self.redis_engine)
            await self.trading_engine.initialize()
            
            self.logger.info("Trading Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Trading Engine: {e}")
            raise
    
    async def init_database(self):
        """Initialize database connection and tables"""
        try:
            self.logger.info("Initializing database...")
            await init_database()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown of application components"""
        try:
            self.logger.info("Shutting down Trading Engine...")
            
            # Stop trading engine
            if self.trading_engine:
                await self.trading_engine.shutdown()
            
            # Stop Redis engine
            if self.redis_engine:
                await self.redis_engine.shutdown()
            
            # Close database connections
            if engine:
                await engine.dispose()
            
            self.logger.info("Trading Engine shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def run(self):
        """Main application run loop"""
        try:
            await self.startup()
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                self.logger.info(f"Received signal {signum}, initiating shutdown...")
                self.shutdown_event.set()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start the trading engine
            engine_task = asyncio.create_task(self.trading_engine.run())
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())
            
            self.logger.info("Trading Engine is running...")
            
            # Wait for shutdown signal or engine completion
            done, pending = await asyncio.wait(
                [engine_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            self.logger.error(f"Critical error in main loop: {e}")
            raise
        finally:
            await self.shutdown()

async def main():
    """Application entry point"""
    app = TradingApplication()
    try:
        await app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Run the application
    asyncio.run(main()) 