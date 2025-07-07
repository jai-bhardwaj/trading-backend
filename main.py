import asyncio
import os
import logging
from strategy.engine import StrategyEngine
from order.manager import OrderManager
from order.subscriber import SignalSubscriber

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("main")

async def main():
    # Load config from environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    paper_trading = os.getenv("PAPER_TRADING", "false").lower() == "true"
    interval = int(os.getenv("STRATEGY_EXECUTION_INTERVAL", 1))  # 1 second for real-time WebSocket trading

    logger.info(f"🚀 Starting trading system with {interval}s execution interval")
    logger.info(f"📊 Paper trading: {paper_trading}")

    # Initialize components
    engine = StrategyEngine(redis_url=redis_url)
    order_manager = OrderManager(paper_trading=paper_trading)
    subscriber = SignalSubscriber(redis_url=redis_url)

    try:
        # Initialize components sequentially to avoid rate limits
        logger.info("🔄 Initializing strategy engine...")
        await engine.initialize()
        
        # Add delay to avoid rate limits
        logger.info("⏳ Waiting 5 seconds before initializing order manager...")
        await asyncio.sleep(5)
        
        logger.info("🔄 Initializing order manager...")
        await order_manager.initialize()
        
        logger.info("🔄 Initializing signal subscriber...")
        await subscriber.initialize(order_manager)
        
        logger.info("✅ All components initialized successfully")
        logger.info(f"⏰ Strategy execution interval: {interval} seconds")
        logger.info("🔄 Starting continuous execution...")

        # Run strategy engine and subscriber concurrently
        async def run_engine():
            await engine.start_continuous_execution(interval_seconds=interval)
        async def run_subscriber():
            await subscriber.start_listening()

        tasks = [
            asyncio.create_task(run_engine()),
            asyncio.create_task(run_subscriber()),
        ]

        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        raise
    finally:
        await engine.stop_continuous_execution()
        await subscriber.stop_listening()
        await engine.close()
        await subscriber.close()
        logger.info("✅ System shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main()) 