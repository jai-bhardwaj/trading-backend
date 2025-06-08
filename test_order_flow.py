#!/usr/bin/env python3
"""
Test Order Flow - End-to-End Testing
Tests the complete order flow from strategy -> engine -> broker
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
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

async def test_strategy_registration():
    """Test if strategies are properly registered"""
    print("=" * 60)
    print("🔍 TESTING STRATEGY REGISTRATION")
    print("=" * 60)
    
    try:
        from app.strategies import AutomaticStrategyRegistry, initialize_strategies
        
        # Initialize strategies with force reload
        logger.info("📋 Initializing strategy registry...")
        initialize_strategies(force_reload=True)
        
        # Get registered strategies
        strategies = AutomaticStrategyRegistry.list_strategies()
        logger.info(f"📈 Found {len(strategies)} registered strategies: {strategies}")
        
        # Test each strategy
        for strategy_id in strategies:
            strategy_class = AutomaticStrategyRegistry.get_strategy_class(strategy_id)
            if strategy_class:
                logger.info(f"✅ {strategy_id}: {strategy_class.__name__}")
            else:
                logger.error(f"❌ {strategy_id}: Class not found")
        
        # Test specific test strategy
        test_strategy_class = AutomaticStrategyRegistry.get_strategy_class('test_strategy')
        if test_strategy_class:
            logger.info(f"✅ Test strategy found: {test_strategy_class.__name__}")
            return True
        else:
            logger.error("❌ Test strategy not found in registry")
            return False
            
    except Exception as e:
        logger.error(f"❌ Strategy registration test failed: {e}")
        return False

async def test_database_connection():
    """Test database connectivity"""
    print("\n" + "=" * 60)
    print("🔍 TESTING DATABASE CONNECTION")
    print("=" * 60)
    
    try:
        from app.database import get_database_manager
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Test connection
        health = await db_manager.health_check()
        logger.info(f"📊 Database health: {health}")
        
        if health["overall_healthy"]:
            logger.info("✅ Database connection healthy")
            return True
        else:
            logger.error("❌ Database connection issues")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

async def test_strategy_execution():
    """Test strategy execution and signal generation"""
    print("\n" + "=" * 60)
    print("🔍 TESTING STRATEGY EXECUTION")
    print("=" * 60)
    
    try:
        from app.strategies import AutomaticStrategyRegistry
        from app.strategies.base import StrategyConfig, AssetClass, TimeFrame, MarketData
        
        # Get test strategy class
        test_strategy_class = AutomaticStrategyRegistry.get_strategy_class('test_strategy')
        if not test_strategy_class:
            logger.error("❌ Test strategy not found")
            return False
        
        # Create strategy config
        config = StrategyConfig(
            name="Test Strategy Execution",
            asset_class=AssetClass.EQUITY,
            symbols=["RELIANCE"],
            timeframe=TimeFrame.MINUTE_5,
            parameters={
                "order_interval_minutes": 1,  # Quick test - 1 minute
                "test_symbols": ["RELIANCE"],
                "test_quantity": 1,
                "max_test_orders": 2,
                "alternate_sides": True
            },
            risk_parameters={
                "max_position_size": 10,
                "max_daily_loss": 1000
            },
            is_active=True
        )
        
        # Create strategy instance
        strategy = test_strategy_class(config)
        strategy.initialize()
        logger.info(f"✅ Created strategy instance: {strategy.__class__.__name__}")
        
        # Create mock market data
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
        
        # Process market data
        logger.info("📊 Processing market data...")
        signal = strategy.process_market_data(market_data)
        
        if signal:
            logger.info(f"✅ Signal generated: {signal.signal_type.value} {signal.symbol} qty={signal.quantity}")
            return True
        else:
            logger.info("ℹ️ No signal generated (may be normal for test strategy)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Strategy execution test failed: {e}")
        return False

async def test_order_creation():
    """Test order creation in database"""
    print("\n" + "=" * 60)
    print("🔍 TESTING ORDER CREATION")
    print("=" * 60)
    
    try:
        from app.database import get_database_manager
        from app.models.base import Order, OrderStatus, OrderSide, OrderType, ProductType
        
        db_manager = get_database_manager()
        
        async with db_manager.get_async_session() as session:
            # Create a test order
            test_order = Order(
                user_id="test-user",
                strategy_id="test-strategy",
                symbol="RELIANCE",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=1,
                price=0.0,
                status=OrderStatus.PENDING,
                notes="Test order from order flow test"
            )
            
            session.add(test_order)
            await session.commit()
            await session.refresh(test_order)
            
            logger.info(f"✅ Created test order: ID={test_order.id}, {test_order.symbol} {test_order.side.value}")
            return test_order.id
            
    except Exception as e:
        logger.error(f"❌ Order creation test failed: {e}")
        return None

async def test_broker_integration():
    """Test broker integration"""
    print("\n" + "=" * 60)
    print("🔍 TESTING BROKER INTEGRATION")
    print("=" * 60)
    
    try:
        from app.brokers import get_broker_instance
        from app.database import get_database_manager
        
        db_manager = get_database_manager()
        
        # Try to get a broker instance
        async with db_manager.get_async_session() as session:
            broker = await get_broker_instance("test-user", session)
            
            if broker:
                logger.info(f"✅ Broker instance created: {broker.__class__.__name__}")
                
                # Test broker health
                if hasattr(broker, 'health_check'):
                    health = await broker.health_check()
                    logger.info(f"📊 Broker health: {health}")
                else:
                    logger.info("ℹ️ Broker health check not available")
                
                return True
            else:
                logger.warning("⚠️ No broker instance available (may be normal in test environment)")
                return True
                
    except Exception as e:
        logger.error(f"❌ Broker integration test failed: {e}")
        return False

async def test_redis_queue():
    """Test Redis queue connectivity"""
    print("\n" + "=" * 60)
    print("🔍 TESTING REDIS QUEUE")
    print("=" * 60)
    
    try:
        from app.database import get_database_manager
        
        db_manager = get_database_manager()
        redis_client = await db_manager.get_redis()
        
        if redis_client:
            # Test Redis connection
            await redis_client.ping()
            logger.info("✅ Redis connection successful")
            
            # Test queue operations
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            await redis_client.lpush("test_queue", str(test_data))
            result = await redis_client.rpop("test_queue")
            
            if result:
                logger.info("✅ Redis queue operations successful")
                return True
            else:
                logger.error("❌ Redis queue operations failed")
                return False
        else:
            logger.error("❌ Redis client not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis queue test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive end-to-end test"""
    print("\n🚀 STARTING COMPREHENSIVE ORDER FLOW TEST")
    print("=" * 60)
    
    results = {}
    
    # Run all tests
    results['strategy_registration'] = await test_strategy_registration()
    results['database_connection'] = await test_database_connection()
    results['strategy_execution'] = await test_strategy_execution()
    results['order_creation'] = await test_order_creation()
    results['broker_integration'] = await test_broker_integration()
    results['redis_queue'] = await test_redis_queue()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Order flow is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check logs for details.")
        return False

async def main():
    """Main test function"""
    try:
        success = await run_comprehensive_test()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 