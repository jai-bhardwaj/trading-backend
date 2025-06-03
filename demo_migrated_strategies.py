#!/usr/bin/env python3
"""
Demo Script for Migrated Equity Strategies
Shows how to use the updated strategies with the new schema and execution system.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_migrated_strategies():
    """
    Demonstrate the migrated equity strategies working with the new system.
    """
    print("🚀 Migrated Equity Strategies Demo")
    print("=" * 50)
    
    try:
        # Initialize services
        await initialize_services()
        
        # Demo 1: List available strategies
        list_available_strategies()
        
        # Demo 2: Create and test each strategy type
        user_id = await create_demo_user()
        
        await demo_test_strategy(user_id)
        await demo_technical_strategies(user_id)
        await demo_momentum_strategies(user_id)
        await demo_swing_and_btst_strategies(user_id)
        
        print("\n✅ All migrated strategies demonstrated successfully!")
        print("🎉 Strategies are ready for production use with the new system!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        await cleanup_demo()

async def initialize_services():
    """Initialize all required services."""
    print("\n1. 🔧 Initializing Services...")
    
    # Set environment variables for demo
    os.environ['DATABASE_URL'] = 'postgresql+asyncpg://trading:password@localhost:5432/trading_db'
    os.environ['REDIS_URL'] = 'redis://localhost:6379'
    
    from app.database import init_database
    init_database()
    
    print("   ✅ Database and Redis connections initialized")

def list_available_strategies():
    """List all available migrated strategies."""
    print("\n2. 📋 Available Migrated Strategies:")
    
    from app.strategies.equity import get_strategy_info, list_available_strategies
    
    strategies = get_strategy_info()
    strategy_names = list_available_strategies()
    
    print(f"   📊 Total strategies: {len(strategy_names)}")
    
    for strategy_name in strategy_names:
        info = strategies[strategy_name]
        print(f"   • {info['name']} ({strategy_name})")
        print(f"     Type: {info['type']}, Timeframe: {info['timeframe']}, Risk: {info['risk_level']}")

async def create_demo_user():
    """Create a demo user for testing."""
    print("\n3. 👤 Creating Demo User...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    user_id = f"migrated_demo_user_{int(datetime.now().timestamp())}"
    
    async with db_manager.get_async_session() as session:
        # Create user
        await session.execute(text("""
            INSERT INTO users (id, email, username, hashed_password, first_name, role, status)
            VALUES (:id, :email, :username, :password, :first_name, :role, :status)
        """), {
            "id": user_id,
            "email": "migrated@tradingengine.com",
            "username": "migrated_trader",
            "password": "hashed_password_demo",
            "first_name": "Migrated",
            "role": "USER",
            "status": "ACTIVE"
        })
        await session.commit()
    
    print(f"   ✅ Created user: {user_id}")
    return user_id

async def demo_test_strategy(user_id: str):
    """Demo the test strategy."""
    print("\n4. 🧪 Testing Test Strategy...")
    
    from app.strategies.equity import TestStrategy2Min
    
    # Configuration for test strategy
    config = {
        "order_interval_minutes": 1,  # Faster for demo
        "test_symbols": ["RELIANCE", "TCS"],
        "max_position_size": 0.005,  # Very small for testing
        "auto_close_minutes": 2
    }
    
    # Create strategy instance
    strategy = TestStrategy2Min(
        config_id=f"test_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=config
    )
    
    # Initialize strategy
    await strategy.initialize()
    
    # Simulate market data
    await strategy.on_market_data("RELIANCE", {
        "ltp": 2500.0,
        "close": 2500.0,
        "open": 2480.0
    })
    
    # Generate signals
    signals = await strategy.generate_signals()
    
    print(f"   ✅ Test strategy initialized and generated {len(signals)} signals")
    
    # Show metrics
    metrics = await strategy.get_metrics()
    print(f"   📊 Strategy metrics: {json.dumps(metrics['custom_metrics'], indent=2)}")

async def demo_technical_strategies(user_id: str):
    """Demo technical analysis strategies."""
    print("\n5. 📈 Testing Technical Strategies...")
    
    from app.strategies.equity import RSIDMIStrategy, RSIDMIIntradayDelayedStrategy
    
    # Test RSI DMI Strategy
    print("   Testing RSI DMI Strategy...")
    
    config = {
        "symbols": ["RELIANCE", "TCS", "INFY"],
        "upper_limit": 70,
        "lower_limit": 30,
        "di_upper_limit": 25,
        "rsi_period": 10  # Shorter for demo
    }
    
    rsi_strategy = RSIDMIStrategy(
        config_id=f"rsi_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=config
    )
    
    await rsi_strategy.initialize()
    
    # Simulate market data updates
    for i in range(15):  # Generate enough data for RSI calculation
        price = 2500 + (i * 5)  # Trending up
        await rsi_strategy.on_market_data("RELIANCE", {
            "ltp": price,
            "close": price
        })
    
    signals = await rsi_strategy.generate_signals()
    print(f"   ✅ RSI DMI strategy generated {len(signals)} signals")
    
    # Test RSI DMI Delayed Strategy
    print("   Testing RSI DMI Delayed Strategy...")
    
    delayed_config = config.copy()
    delayed_config.update({
        "signal_delay_minutes": 1,  # Faster for demo
        "signal_confirmation_count": 2
    })
    
    delayed_strategy = RSIDMIIntradayDelayedStrategy(
        config_id=f"delayed_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=delayed_config
    )
    
    await delayed_strategy.initialize()
    
    # Simulate market data
    await delayed_strategy.on_market_data("TCS", {
        "ltp": 3200.0,
        "close": 3200.0
    })
    
    delayed_signals = await delayed_strategy.generate_signals()
    print(f"   ✅ RSI DMI delayed strategy initialized with pending signal system")

async def demo_momentum_strategies(user_id: str):
    """Demo momentum-based strategies."""
    print("\n6. 🚀 Testing Momentum Strategies...")
    
    from app.strategies.equity import SimpleMovingAverageStrategy, RSIMeanReversionStrategy
    
    # Test Simple Moving Average Strategy
    print("   Testing Moving Average Crossover...")
    
    ma_config = {
        "symbols": ["RELIANCE", "TCS"],
        "short_period": 5,
        "long_period": 10,
        "min_confidence": 0.5
    }
    
    ma_strategy = SimpleMovingAverageStrategy(
        config_id=f"ma_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=ma_config
    )
    
    await ma_strategy.initialize()
    
    # Simulate price trend for MA crossover
    prices = [2480, 2485, 2490, 2495, 2505, 2515, 2520, 2525, 2530, 2535, 2540]
    for price in prices:
        await ma_strategy.on_market_data("RELIANCE", {
            "ltp": price,
            "close": price
        })
    
    ma_signals = await ma_strategy.generate_signals()
    print(f"   ✅ MA strategy generated {len(ma_signals)} signals")
    
    # Test RSI Mean Reversion Strategy
    print("   Testing RSI Mean Reversion...")
    
    rsi_config = {
        "symbols": ["TCS"],
        "rsi_period": 8,
        "oversold_threshold": 25,
        "overbought_threshold": 75
    }
    
    rsi_mean_strategy = RSIMeanReversionStrategy(
        config_id=f"rsi_mean_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=rsi_config
    )
    
    await rsi_mean_strategy.initialize()
    
    # Simulate oversold condition
    base_price = 3200
    for i in range(10):
        price = base_price - (i * 10)  # Declining prices
        await rsi_mean_strategy.on_market_data("TCS", {
            "ltp": price,
            "close": price
        })
    
    rsi_signals = await rsi_mean_strategy.generate_signals()
    print(f"   ✅ RSI mean reversion strategy generated {len(rsi_signals)} signals")

async def demo_swing_and_btst_strategies(user_id: str):
    """Demo swing and BTST strategies."""
    print("\n7. 📊 Testing Swing & BTST Strategies...")
    
    from app.strategies.equity import SwingMomentumGain4Strategy, BTSTMomentumGain4Strategy
    
    # Test Swing Momentum Strategy
    print("   Testing Swing Momentum Strategy...")
    
    swing_config = {
        "symbols": ["RELIANCE", "TCS"],
        "momentum_percentage": 3.0,  # Lower for demo
        "exit_days": 1,  # Shorter for demo
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.06
    }
    
    swing_strategy = SwingMomentumGain4Strategy(
        config_id=f"swing_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=swing_config
    )
    
    await swing_strategy.initialize()
    
    # Simulate momentum conditions
    await swing_strategy.on_market_data("RELIANCE", {
        "ltp": 2580.0,  # 4% up from day open
        "close": 2580.0,
        "open": 2500.0
    })
    
    swing_signals = await swing_strategy.generate_signals()
    print(f"   ✅ Swing momentum strategy generated {len(swing_signals)} signals")
    
    # Test BTST Strategy
    print("   Testing BTST Strategy...")
    
    btst_config = {
        "symbols": ["TCS"],
        "momentum_percentage": 3.5,
        "exit_days": 1,
        "stop_loss_pct": 0.015,
        "take_profit_pct": 0.05
    }
    
    btst_strategy = BTSTMomentumGain4Strategy(
        config_id=f"btst_config_{int(datetime.now().timestamp())}",
        user_id=user_id,
        strategy_id=None,
        config=btst_config
    )
    
    await btst_strategy.initialize()
    
    # Simulate BTST conditions
    await btst_strategy.on_market_data("TCS", {
        "ltp": 3312.0,  # 3.5% up from day open
        "close": 3312.0,
        "open": 3200.0
    })
    
    btst_signals = await btst_strategy.generate_signals()
    print(f"   ✅ BTST momentum strategy generated {len(btst_signals)} signals")

async def cleanup_demo():
    """Cleanup demo resources."""
    print("\n🧹 Cleaning up demo resources...")
    
    try:
        from app.database import db_manager
        await db_manager.close()
        print("   ✅ Database connections closed")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

def print_migration_summary():
    """Print summary of the migration."""
    print("\n📊 Migration Summary:")
    print("=" * 50)
    print("✅ Successfully migrated all equity strategies to new system:")
    print("   • TestStrategy2Min")
    print("   • SimpleMovingAverageStrategy") 
    print("   • RSIMeanReversionStrategy")
    print("   • RSIDMIStrategy")
    print("   • RSIDMIIntradayDelayedStrategy")
    print("   • SwingMomentumGain4Strategy")
    print("   • BTSTMomentumGain4Strategy")
    
    print("\n🔧 Key Changes Made:")
    print("   • Updated to use new BaseStrategy class")
    print("   • Integrated with cleaned database schema")
    print("   • Async/await pattern implementation")
    print("   • Redis-based market data access")
    print("   • Enhanced notification system")
    print("   • Improved error handling and logging")
    print("   • Database-driven order and position management")
    
    print("\n🚀 Production Ready Features:")
    print("   • Independent strategy processes")
    print("   • Real-time market data processing")
    print("   • Hybrid notification system")
    print("   • Comprehensive metrics tracking")
    print("   • Graceful error handling")
    print("   • Database persistence")

if __name__ == "__main__":
    print("🎯 Migrated Equity Strategies Demo")
    print("This demo shows all equity strategies working with the new system.")
    
    print_migration_summary()
    
    try:
        asyncio.run(demo_migrated_strategies())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc() 