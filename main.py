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
from app.database import DatabaseManager
from app.engine.redis_engine import RedisBasedTradingEngine
from app.strategies.manager import StrategyManager
from app.queue import QueueManager

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
        self.db_manager = None
        self.trading_engine = None
        self.strategy_manager = None
        self.shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize application components"""
        try:
            self.logger.info("🚀 Starting Trading Engine...")
            
            # Initialize database
            await self.init_database()
            
            # Initialize instrument manager
            await self.init_instrument_manager()
            
            # Initialize strategy manager
            await self.init_strategy_manager()
            
            # Initialize Redis-based trading engine
            await self.init_trading_engine()
            
            # Create database tables if they don't exist
            await self.ensure_database_tables()
            
            self.logger.info("✅ Trading Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Trading Engine: {e}")
            raise
    
    async def init_database(self):
        """Initialize database connection and tables"""
        try:
            self.logger.info("📊 Initializing database...")
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def init_instrument_manager(self):
        """Initialize instrument manager"""
        try:
            self.logger.info("📊 Initializing instrument manager...")
            from app.core.instrument_manager import get_instrument_manager
            
            # Initialize and fetch instruments
            self.instrument_manager = await get_instrument_manager(self.db_manager)
            
            # Update strategy symbols with fresh instruments
            await self.instrument_manager.update_strategy_symbols()
            
            self.logger.info("✅ Instrument manager initialized")
        except Exception as e:
            self.logger.error(f"❌ Instrument manager initialization failed: {e}")
            # Don't raise - continue with demo mode
    
    async def init_strategy_manager(self):
        """Initialize strategy manager"""
        try:
            self.logger.info("🧠 Initializing strategy manager...")
            self.strategy_manager = StrategyManager(max_workers=settings.worker_count)
            self.logger.info("✅ Strategy manager initialized")
        except Exception as e:
            self.logger.error(f"❌ Strategy manager initialization failed: {e}")
            raise
    
    async def init_trading_engine(self):
        """Initialize Redis-based trading engine"""
        try:
            self.logger.info("⚡ Initializing Redis trading engine...")
            self.trading_engine = RedisBasedTradingEngine(
                worker_count=settings.worker_count,
                max_queue_size=settings.max_queue_size,
                db_manager=self.db_manager
            )
            
            # Start the trading engine
            engine_started = await self.trading_engine.start()
            if not engine_started:
                raise Exception("Failed to start Redis trading engine")
            
            self.logger.info("✅ Redis trading engine started")
        except Exception as e:
            self.logger.error(f"❌ Trading engine initialization failed: {e}")
            raise
    
    async def ensure_database_tables(self):
        """Ensure all database tables are created"""
        try:
            from app.database import Base
            
            # Create all tables
            async with self.db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.logger.info("✅ Database tables verified/created")
        except Exception as e:
            self.logger.error(f"❌ Database table creation failed: {e}")
            # Don't raise - this might fail if tables already exist
    
    async def load_active_strategies(self):
        """Load and start active strategies from database"""
        try:
            self.logger.info("🎯 Loading active strategies...")
            
            async with self.db_manager.get_session() as db:
                from app.models.base import Strategy, StrategyStatus
                from sqlalchemy import select
                
                # Get active strategies
                result = await db.execute(
                    select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
                )
                active_strategies = result.scalars().all()
                
                strategies_loaded = 0
                for strategy in active_strategies:
                    try:
                        # Create strategy configuration
                        from app.strategies.base import StrategyConfig, AssetClass, TimeFrame as StrategyTimeFrame
                        
                        # Convert TimeFrame from database enum to strategy enum
                        timeframe_mapping = {
                            "MINUTE_1": StrategyTimeFrame.MINUTE_1,
                            "MINUTE_5": StrategyTimeFrame.MINUTE_5,
                            "MINUTE_15": StrategyTimeFrame.MINUTE_15,
                            "HOUR_1": StrategyTimeFrame.HOUR_1,
                            "HOUR_4": StrategyTimeFrame.HOUR_4,
                            "DAY_1": StrategyTimeFrame.DAILY,
                            "WEEK_1": StrategyTimeFrame.WEEKLY
                        }
                        
                        strategy_timeframe = timeframe_mapping.get(strategy.timeframe.value, StrategyTimeFrame.MINUTE_5)
                        
                        config = StrategyConfig(
                            name=strategy.name,
                            asset_class=AssetClass(strategy.asset_class.value),
                            symbols=strategy.symbols or [],
                            timeframe=strategy_timeframe,
                            parameters=strategy.parameters or {},
                            risk_parameters=strategy.risk_parameters or {},
                            is_active=True,
                            paper_trade=strategy.is_paper_trading
                        )
                        
                        # Create strategy in manager
                        if self.strategy_manager.create_strategy(strategy.strategy_type, config):
                            strategies_loaded += 1
                            self.logger.info(f"✅ Loaded strategy: {strategy.name} ({strategy.strategy_type})")
                        else:
                            self.logger.warning(f"⚠️ Failed to load strategy: {strategy.name}")
                    
                    except Exception as e:
                        self.logger.error(f"❌ Error loading strategy {strategy.name}: {e}")
                
                self.logger.info(f"📈 Loaded {strategies_loaded} active strategies")
        
        except Exception as e:
            self.logger.error(f"❌ Failed to load strategies: {e}")
    
    async def start_market_data_feed(self):
        """Start market data feed and processing"""
        try:
            self.logger.info("📡 Starting market data feed...")
            
            # This would typically connect to a market data provider
            # For now, we'll start a placeholder task
            async def market_data_simulator():
                """Simulate market data updates"""
                while self.trading_engine and self.trading_engine.is_running:
                    try:
                        # In a real implementation, this would fetch real market data
                        # and call self.strategy_manager.process_market_data(market_data)
                        await asyncio.sleep(settings.engine_loop_interval)
                    except Exception as e:
                        self.logger.error(f"❌ Market data error: {e}")
                        await asyncio.sleep(5)
            
            # Start market data task
            asyncio.create_task(market_data_simulator())
            self.logger.info("✅ Market data feed started")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start market data feed: {e}")
    
    async def shutdown(self):
        """Graceful shutdown of application components"""
        try:
            self.logger.info("⏹️ Shutting down Trading Engine...")
            
            # Stop trading engine
            if self.trading_engine:
                await self.trading_engine.stop()
            
            # Shutdown strategy manager
            if self.strategy_manager:
                self.strategy_manager.shutdown()
            
            # Close database connections
            if self.db_manager:
                await self.db_manager.close()
            
            self.logger.info("🏁 Trading Engine shutdown completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
    
    async def run(self):
        """Main application run loop"""
        try:
            await self.startup()
            
            # Load active strategies
            await self.load_active_strategies()
            
            # Start market data feed
            await self.start_market_data_feed()
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                self.logger.info(f"🛑 Received signal {signum}, initiating shutdown...")
                self.shutdown_event.set()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            self.logger.info("🎯 Trading Engine is now fully operational!")
            self.logger.info("📊 Engine Status:")
            self.logger.info(f"   • Workers: {settings.worker_count}")
            self.logger.info(f"   • Max Queue Size: {settings.max_queue_size}")
            self.logger.info(f"   • Loop Interval: {settings.engine_loop_interval}s")
            
            # Main loop - wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"💥 Critical error in main loop: {e}")
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
        logging.error(f"💥 Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Run the application
    asyncio.run(main()) 