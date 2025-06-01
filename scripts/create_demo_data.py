#!/usr/bin/env python3
"""
Create Demo Trading Data
Sets up sample users, strategies, and orders for testing
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.database import DatabaseManager
from app.models.base import *
import uuid
from datetime import datetime, timedelta

async def create_demo_user(db):
    """Create a demo user"""
    user = User(
        id=str(uuid.uuid4()),
        email="demo@tradingengine.com",
        username="demo_trader",
        hashed_password="demo_password_hash",
        first_name="Demo",
        last_name="Trader",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True
    )
    
    db.add(user)
    await db.flush()
    
    # Create user profile
    profile = UserProfile(
        user_id=user.id,
        trading_experience="INTERMEDIATE",
        risk_tolerance="MODERATE",
        investment_goals="GROWTH",
        preferred_assets=["EQUITY", "DERIVATIVES"]
    )
    db.add(profile)
    
    # Create risk profile
    risk_profile = RiskProfile(
        user_id=user.id,
        risk_level=RiskLevel.MODERATE,
        max_daily_loss_pct=2.0,
        max_position_size_pct=10.0,
        max_order_value=50000,
        allowed_asset_classes=["EQUITY", "DERIVATIVES"],
        allowed_exchanges=["NSE", "BSE"]
    )
    db.add(risk_profile)
    
    # Create balance
    balance = Balance(
        user_id=user.id,
        available_cash=100000,
        total_balance=100000,
        buying_power=100000
    )
    db.add(balance)
    
    # Create broker config
    broker_config = BrokerConfig(
        user_id=user.id,
        broker_name=BrokerName.ANGEL_ONE,
        display_name="AngelOne Demo",
        api_key="DEMO_API_KEY",
        client_id="DEMO_CLIENT",
        password="demo_password",
        is_active=True,
        is_connected=True
    )
    db.add(broker_config)
    
    print(f"✅ Created demo user: {user.username} ({user.id})")
    return user

async def create_demo_strategies(db, user):
    """Create demo trading strategies"""
    strategies = []
    
    # Strategy 1: Simple Moving Average Crossover
    strategy1 = Strategy(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name="SMA Crossover Strategy",
        description="Simple moving average crossover strategy for equity trading",
        strategy_type="sma_crossover",
        asset_class=AssetClass.EQUITY,
        symbols=["RELIANCE", "TCS", "INFY", "HDFC"],
        timeframe=TimeFrame.MINUTE_5,
        status=StrategyStatus.ACTIVE,
        parameters={
            "fast_period": 10,
            "slow_period": 20,
            "quantity": 10,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0
        },
        risk_parameters={
            "max_position_size": 10000,
            "max_daily_trades": 5
        },
        is_live=False,
        is_paper_trading=True,
        max_positions=3,
        capital_allocated=50000,
        start_time="09:15",
        end_time="15:30",
        active_days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    )
    db.add(strategy1)
    strategies.append(strategy1)
    
    # Strategy 2: Momentum Strategy
    strategy2 = Strategy(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name="Momentum Breakout",
        description="Momentum-based breakout strategy",
        strategy_type="momentum_breakout",
        asset_class=AssetClass.EQUITY,
        symbols=["TATAMOTORS", "BAJFINANCE", "MARUTI"],
        timeframe=TimeFrame.MINUTE_15,
        status=StrategyStatus.ACTIVE,
        parameters={
            "lookback_period": 20,
            "breakout_threshold": 1.5,
            "volume_threshold": 1.2,
            "quantity": 5
        },
        risk_parameters={
            "max_position_size": 15000,
            "max_daily_trades": 3
        },
        is_live=False,
        is_paper_trading=True,
        max_positions=2,
        capital_allocated=30000,
        start_time="09:15",
        end_time="15:30",
        active_days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    )
    db.add(strategy2)
    strategies.append(strategy2)
    
    print(f"✅ Created {len(strategies)} demo strategies")
    return strategies

async def create_demo_orders(db, user, strategies):
    """Create demo orders"""
    orders = []
    
    # Create some historical orders
    for i, strategy in enumerate(strategies[:2]):
        for j in range(3):
            order = Order(
                id=str(uuid.uuid4()),
                user_id=user.id,
                strategy_id=strategy.id,
                symbol=strategy.symbols[j % len(strategy.symbols)],
                exchange="NSE",
                side=OrderSide.BUY if j % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.LIMIT,
                product_type=ProductType.INTRADAY,
                quantity=10,
                price=100.0 + (j * 10),
                status=OrderStatus.COMPLETE if j < 2 else OrderStatus.PENDING,
                is_paper_trade=True,
                placed_at=datetime.utcnow() - timedelta(hours=j),
                executed_at=datetime.utcnow() - timedelta(hours=j) if j < 2 else None
            )
            db.add(order)
            orders.append(order)
    
    print(f"✅ Created {len(orders)} demo orders")
    return orders

async def create_market_data(db):
    """Create sample market data"""
    symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "TATAMOTORS", "BAJFINANCE", "MARUTI"]
    
    for symbol in symbols:
        market_data = MarketData(
            symbol=symbol,
            exchange="NSE",
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000,
            previous_close=100.0,
            change=3.0,
            change_pct=3.0,
            timestamp=datetime.utcnow(),
            timeframe=TimeFrame.MINUTE_5
        )
        db.add(market_data)
    
    print(f"✅ Created market data for {len(symbols)} symbols")

async def main():
    """Main function to create demo data"""
    print("🚀 Creating Demo Trading Data")
    print("=" * 50)
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_session() as db:
            # Create demo user
            user = await create_demo_user(db)
            
            # Create demo strategies
            strategies = await create_demo_strategies(db, user)
            
            # Create demo orders
            orders = await create_demo_orders(db, user, strategies)
            
            # Create market data
            await create_market_data(db)
            
            # Commit all changes
            await db.commit()
            
            print("\n" + "=" * 50)
            print("🎉 Demo data created successfully!")
            print(f"👤 User: {user.username}")
            print(f"📈 Strategies: {len(strategies)} active")
            print(f"📋 Orders: {len(orders)} created")
            print(f"📊 Market data: Available for trading")
            print("\n🔄 Restart the trading engine to load the new strategies")
            
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        return 1
    
    finally:
        await db_manager.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 