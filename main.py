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
    interval = int(os.getenv("STRATEGY_EXECUTION_INTERVAL", 1))  # 1 second for testing

    # Initialize components
    engine = StrategyEngine(redis_url=redis_url)
    order_manager = OrderManager(paper_trading=paper_trading)
    subscriber = SignalSubscriber(redis_url=redis_url)

    await engine.initialize()
    await order_manager.initialize()
    await subscriber.initialize(order_manager)

    # Run strategy engine and subscriber concurrently
    async def run_engine():
        await engine.start_continuous_execution(interval_seconds=interval)
    async def run_subscriber():
        await subscriber.start_listening()

    tasks = [
        asyncio.create_task(run_engine()),
        asyncio.create_task(run_subscriber()),
    ]

    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Shutting down...")
    finally:
        await engine.stop_continuous_execution()
        await subscriber.stop_listening()
        await engine.close()
        await subscriber.close()
        logger.info("✅ System shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main()) 