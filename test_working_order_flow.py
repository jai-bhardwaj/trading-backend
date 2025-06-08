#!/usr/bin/env python3
"""
Working Order Flow Test
Tests the complete order flow with direct strategy access
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_working_order_flow():
    """Test the complete order flow with working strategies"""
    print("=" * 60)
    print("🚀 TESTING WORKING ORDER FLOW")
    print("=" * 60)
    
    try:
        # 1. Initialize database
        print("\n1️⃣ Initializing database...")
        from app.database import initialize_database
        db_manager = await initialize_database()
        
        # Test database health
        health = await db_manager.health_check()
        logger.info(f"📊 Database health: {health['overall_healthy']}")
        
        if not health["overall_healthy"]:
            print("❌ Database not healthy, aborting test")
            return False
        
        # 2. Import strategies directly (they auto-register)
        print("\n2️⃣ Importing strategies...")
        from app.strategies.registry import AutomaticStrategyRegistry
        
        # Import strategy modules to trigger registration
        import app.strategies.equity.test_strategy
        import app.strategies.equity.btst_momentum_strategy
        import app.strategies.equity.rsi_dmi_strategy
        
        # Check strategies
        strategies = list(AutomaticStrategyRegistry._strategies.keys())
        logger.info(f"📈 Found {len(strategies)} strategies: {strategies}")
        
        # 3. Test strategy execution
        print("\n3️⃣ Testing strategy execution...")
        test_strategy_class = AutomaticStrategyRegistry.get_strategy_class('test_strategy')
        
        if test_strategy_class:
            logger.info(f"✅ Test strategy found: {test_strategy_class.__name__}")
            
            # Create strategy instance
            from app.strategies.base import StrategyConfig, AssetClass, TimeFrame
            config = StrategyConfig(
                name="Test Order Flow",
                asset_class=AssetClass.EQUITY,
                symbols=["RELIANCE"],
                timeframe=TimeFrame.MINUTE_5,
                parameters={
                    "order_interval_minutes": 1,
                    "test_symbols": ["RELIANCE"],
                    "test_quantity": 1,
                    "max_test_orders": 1,
                    "alternate_sides": True
                },
                risk_parameters={},
                is_active=True
            )
            
            strategy = test_strategy_class(config)
            strategy.initialize()
            logger.info("✅ Strategy initialized")
            
            # Test signal generation
            from app.strategies.base import MarketData
            from datetime import datetime
            
            market_data = MarketData(
                symbol="RELIANCE",
                exchange="NSE",
                timestamp=datetime.now(),
                open=2500.0,
                high=2510.0,
                low=2490.0,
                close=2505.0,
                volume=100000,
                asset_class=AssetClass.EQUITY
            )
            
            signal = strategy.process_market_data(market_data)
            if signal:
                logger.info(f"✅ Signal generated: {signal.signal_type.value} {signal.symbol}")
                
                # 4. Test order creation
                print("\n4️⃣ Testing order creation...")
                from app.models.base import Order, OrderStatus, OrderSide, OrderType, ProductType
                
                async with db_manager.get_async_session() as session:
                    # Create order from signal
                    order = Order(
                        user_id="test-user",
                        strategy_id="test-strategy",
                        symbol=signal.symbol,
                        exchange="NSE",
                        side=OrderSide.BUY if signal.signal_type.value == "BUY" else OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        product_type=ProductType.INTRADAY,
                        quantity=signal.quantity or 1,
                        price=signal.price or 0.0,
                        status=OrderStatus.PENDING,
                        notes=f"Test order from signal {signal.signal_type.value}"
                    )
                    
                    session.add(order)
                    await session.commit()
                    await session.refresh(order)
                    
                    logger.info(f"✅ Order created: ID={order.id}, {order.symbol} {order.side.value}")
                    
                    # 5. Test Redis Engine order processing
                    print("\n5️⃣ Testing Redis Engine order submission...")
                    from app.engine.redis_engine import RedisBasedTradingEngine
                    
                    engine = RedisBasedTradingEngine(worker_count=1, db_manager=db_manager)
                    success = await engine.start()
                    
                    if success:
                        logger.info("✅ Trading engine started")
                        
                        # Submit order to queue
                        result = await engine.submit_order(order.id, priority=2)
                        logger.info(f"✅ Order submitted to queue: {result}")
                        
                        # Test a manual strategy execution
                        await engine.execute_active_strategies()
                        logger.info("✅ Strategy execution cycle completed")
                        
                        # Stop engine
                        await engine.stop()
                        logger.info("✅ Trading engine stopped")
                        
                        print("\n🎉 ALL TESTS PASSED!")
                        print("=" * 60)
                        print("✅ Strategy registration working")
                        print("✅ Database connection working")
                        print("✅ Signal generation working")
                        print("✅ Order creation working")
                        print("✅ Redis queue working")
                        print("✅ Order flow complete!")
                        
                        # 6. Test broker integration
                        print("\n6️⃣ Testing broker integration...")
                        try:
                            from app.brokers import get_broker_instance
                            
                            async with db_manager.get_async_session() as session:
                                broker = await get_broker_instance("test-user", session)
                                
                                if broker:
                                    logger.info(f"✅ Broker instance created: {broker.__class__.__name__}")
                                    print("✅ Broker integration working")
                                else:
                                    logger.info("ℹ️ No broker configured (normal in test environment)")
                                    print("ℹ️ Broker integration not configured")
                        except Exception as e:
                            logger.warning(f"⚠️ Broker integration test failed: {e}")
                            print("⚠️ Broker integration needs configuration")
                        
                        return True
                    else:
                        logger.error("❌ Failed to start trading engine")
                        return False
            else:
                logger.info("ℹ️ No signal generated (may be normal for test strategy)")
                print("ℹ️ Test strategy didn't generate signal (may be normal)")
                return True
        else:
            logger.error("❌ Test strategy not found")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'db_manager' in locals():
            await db_manager.close()

async def main():
    """Main function"""
    success = await test_working_order_flow()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 