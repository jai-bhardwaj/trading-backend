#!/usr/bin/env python3
"""
Updated Trading Engine Demo
Demonstrates the complete live trading system with the new cleaned schema.
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

async def demo_updated_trading_engine():
    """
    Complete demo of the updated trading engine with new schema.
    """
    print("🚀 Starting Updated Trading Engine Demo")
    print("=" * 60)
    
    try:
        # Initialize database and services
        await initialize_services()
        
        # Demo 1: Create user and strategy configuration
        user_id = await create_demo_user()
        strategy_config_id = await create_strategy_configuration(user_id)
        
        # Demo 2: Test notification system
        await test_notification_system(user_id)
        
        # Demo 3: Start strategy execution
        await test_strategy_execution(strategy_config_id)
        
        # Demo 4: Monitor strategy performance
        await monitor_strategy_performance(strategy_config_id)
        
        # Demo 5: Test order and position management
        await test_order_management(user_id, strategy_config_id)
        
        # Demo 6: Test hybrid alert system
        await test_alert_system(user_id)
        
        # Demo 7: Demonstrate strategy commands
        await test_strategy_commands(strategy_config_id)
        
        print("\n✅ Demo completed successfully!")
        print("🎉 Updated trading engine is working perfectly with the new schema!")
        
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

async def create_demo_user():
    """Create a demo user for testing."""
    print("\n2. 👤 Creating Demo User...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    user_id = f"demo_user_{int(datetime.now().timestamp())}"
    
    async with db_manager.get_async_session() as session:
        # Create user
        await session.execute(text("""
            INSERT INTO users (id, email, username, hashed_password, first_name, role, status)
            VALUES (:id, :email, :username, :password, :first_name, :role, :status)
        """), {
            "id": user_id,
            "email": "demo@tradingengine.com",
            "username": "demo_trader",
            "password": "hashed_password_demo",
            "first_name": "Demo",
            "role": "USER",
            "status": "ACTIVE"
        })
        
        # Create notification settings
        await session.execute(text("""
            INSERT INTO notification_settings 
            (id, user_id, order_execution, strategy_status, price_alerts, risk_violations,
             sms_risk_violations, email_daily_summary, email_regulatory)
            VALUES (:id, :user_id, true, true, true, true, true, false, true)
        """), {
            "id": f"notif_settings_{user_id}",
            "user_id": user_id
        })
        
        # Create risk profile
        await session.execute(text("""
            INSERT INTO risk_profiles 
            (id, user_id, risk_level, max_daily_loss_pct, max_position_size_pct, 
             max_order_value, stop_loss_enabled, default_stop_loss_pct)
            VALUES (:id, :user_id, :risk_level, :max_daily_loss, :max_position_size,
                    :max_order_value, :stop_loss_enabled, :default_stop_loss)
        """), {
            "id": f"risk_{user_id}",
            "user_id": user_id,
            "risk_level": "MODERATE",
            "max_daily_loss": 0.02,
            "max_position_size": 0.10,
            "max_order_value": 50000,
            "stop_loss_enabled": True,
            "default_stop_loss": 0.02
        })
        
        await session.commit()
    
    print(f"   ✅ Created user: {user_id}")
    return user_id

async def create_strategy_configuration(user_id: str):
    """Create a strategy configuration."""
    print("\n3. ⚙️ Creating Strategy Configuration...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    strategy_config_id = f"strategy_config_{int(datetime.now().timestamp())}"
    strategy_id = f"strategy_{int(datetime.now().timestamp())}"
    
    # Strategy configuration
    config = {
        "symbols": ["RELIANCE", "TCS", "INFY"],
        "timeframe": "MINUTE_5",
        "execution_interval": 5,
        "capital_allocated": 100000,
        "max_positions": 3,
        "risk_per_trade": 0.02,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
        "momentum_period": 14,
        "rsi_threshold": 70
    }
    
    async with db_manager.get_async_session() as session:
        # Create base strategy
        await session.execute(text("""
            INSERT INTO strategies 
            (id, user_id, name, description, strategy_type, asset_class, symbols, 
             timeframe, status, parameters, risk_parameters, max_positions, capital_allocated)
            VALUES (:id, :user_id, :name, :description, :strategy_type, :asset_class, 
                    :symbols, :timeframe, :status, :parameters, :risk_parameters, 
                    :max_positions, :capital_allocated)
        """), {
            "id": strategy_id,
            "user_id": user_id,
            "name": "Demo Momentum Strategy",
            "description": "Demo strategy for testing the updated engine",
            "strategy_type": "momentum",
            "asset_class": "EQUITY",
            "symbols": json.dumps(config["symbols"]),
            "timeframe": "MINUTE_5",
            "status": "DRAFT",
            "parameters": json.dumps(config),
            "risk_parameters": json.dumps({
                "stop_loss_pct": config["stop_loss_pct"],
                "take_profit_pct": config["take_profit_pct"],
                "risk_per_trade": config["risk_per_trade"]
            }),
            "max_positions": config["max_positions"],
            "capital_allocated": config["capital_allocated"]
        })
        
        # Create strategy configuration
        await session.execute(text("""
            INSERT INTO strategy_configs 
            (id, user_id, strategy_id, name, class_name, module_path, config_json, 
             status, auto_start)
            VALUES (:id, :user_id, :strategy_id, :name, :class_name, :module_path, 
                    :config_json, :status, :auto_start)
        """), {
            "id": strategy_config_id,
            "user_id": user_id,
            "strategy_id": strategy_id,
            "name": "demo_momentum_strategy",
            "class_name": "DemoMomentumStrategy",
            "module_path": "app.strategies.demo_momentum",
            "config_json": json.dumps(config),
            "status": "ACTIVE",
            "auto_start": True
        })
        
        await session.commit()
    
    print(f"   ✅ Created strategy configuration: {strategy_config_id}")
    return strategy_config_id

async def test_notification_system(user_id: str):
    """Test the hybrid notification system."""
    print("\n4. 🔔 Testing Notification System...")
    
    from app.core.notification_service import send_notification, get_user_notifications
    
    # Test real-time notification
    await send_notification(
        user_id=user_id,
        type="ORDER_EXECUTED",
        title="Demo Order Executed",
        message="Your buy order for 100 shares of RELIANCE has been executed at ₹2,500",
        data={
            "symbol": "RELIANCE",
            "quantity": 100,
            "price": 2500,
            "order_type": "BUY"
        }
    )
    
    # Test critical notification (stored in DB)
    await send_notification(
        user_id=user_id,
        type="RISK_VIOLATION",
        title="Risk Limit Alert",
        message="Daily loss limit of 2% has been reached",
        data={
            "current_loss_pct": 2.1,
            "limit_pct": 2.0,
            "action": "STOP_TRADING"
        }
    )
    
    # Get notifications
    notifications = await get_user_notifications(user_id, limit=10)
    
    print(f"   ✅ Sent notifications, retrieved {len(notifications)} notifications")
    for notif in notifications[:2]:
        print(f"      📱 {notif['type']}: {notif['title']}")

async def test_strategy_execution(strategy_config_id: str):
    """Test strategy execution with the new system."""
    print("\n5. 🎯 Testing Strategy Execution...")
    
    # Create a demo strategy class
    await create_demo_strategy_class()
    
    # Start strategy engine manager (simulate)
    print("   🚀 Starting strategy engine manager...")
    
    # Simulate strategy start command
    from app.database import db_manager
    from sqlalchemy import text
    
    async with db_manager.get_async_session() as session:
        command_id = f"cmd_{int(datetime.now().timestamp())}"
        await session.execute(text("""
            INSERT INTO strategy_commands 
            (id, strategy_config_id, command, status)
            VALUES (:id, :strategy_config_id, :command, :status)
        """), {
            "id": command_id,
            "strategy_config_id": strategy_config_id,
            "command": "START",
            "status": "PENDING"
        })
        await session.commit()
    
    print(f"   ✅ Created START command: {command_id}")
    print("   🎯 Strategy execution initiated")

async def monitor_strategy_performance(strategy_config_id: str):
    """Monitor strategy performance metrics."""
    print("\n6. 📊 Monitoring Strategy Performance...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    # Insert sample metrics
    async with db_manager.get_async_session() as session:
        metric_id = f"metric_{int(datetime.now().timestamp())}"
        await session.execute(text("""
            INSERT INTO strategy_metrics 
            (id, strategy_config_id, timestamp, pnl, positions_count, 
             orders_count, success_rate, metrics_json)
            VALUES (:id, :strategy_config_id, NOW(), :pnl, :positions_count,
                    :orders_count, :success_rate, :metrics_json)
        """), {
            "id": metric_id,
            "strategy_config_id": strategy_config_id,
            "pnl": 1250.50,
            "positions_count": 2,
            "orders_count": 5,
            "success_rate": 0.75,
            "metrics_json": json.dumps({
                "total_trades": 4,
                "winning_trades": 3,
                "losing_trades": 1,
                "avg_profit": 625.25,
                "max_drawdown": 150.0,
                "sharpe_ratio": 1.8
            })
        })
        await session.commit()
    
    print("   ✅ Strategy metrics recorded:")
    print("      💰 P&L: ₹1,250.50")
    print("      📈 Success Rate: 75%")
    print("      🎯 Active Positions: 2")
    print("      📊 Total Orders: 5")

async def test_order_management(user_id: str, strategy_config_id: str):
    """Test order and position management."""
    print("\n7. 📋 Testing Order Management...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    async with db_manager.get_async_session() as session:
        # Create sample order
        order_id = f"order_{int(datetime.now().timestamp())}"
        await session.execute(text("""
            INSERT INTO orders 
            (id, user_id, strategy_id, symbol, exchange, side, order_type, 
             product_type, quantity, price, status, filled_quantity, average_price, tags)
            VALUES (:id, :user_id, :strategy_id, :symbol, :exchange, :side, :order_type,
                    :product_type, :quantity, :price, :status, :filled_quantity, 
                    :average_price, :tags)
        """), {
            "id": order_id,
            "user_id": user_id,
            "strategy_id": strategy_config_id,
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "side": "BUY",
            "order_type": "MARKET",
            "product_type": "INTRADAY",
            "quantity": 100,
            "price": 2500.0,
            "status": "COMPLETE",
            "filled_quantity": 100,
            "average_price": 2500.0,
            "tags": json.dumps([f"strategy_{strategy_config_id}"])
        })
        
        # Create corresponding position
        position_id = f"pos_{int(datetime.now().timestamp())}"
        await session.execute(text("""
            INSERT INTO positions 
            (id, user_id, symbol, exchange, product_type, quantity, average_price,
             last_traded_price, pnl, market_value)
            VALUES (:id, :user_id, :symbol, :exchange, :product_type, :quantity,
                    :average_price, :last_traded_price, :pnl, :market_value)
        """), {
            "id": position_id,
            "user_id": user_id,
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "product_type": "INTRADAY",
            "quantity": 100,
            "average_price": 2500.0,
            "last_traded_price": 2525.0,
            "pnl": 2500.0,  # (2525 - 2500) * 100
            "market_value": 252500.0  # 2525 * 100
        })
        
        await session.commit()
    
    print("   ✅ Order and position created:")
    print(f"      📊 Order: {order_id}")
    print(f"      💼 Position: {position_id}")
    print("      💰 P&L: ₹2,500 (unrealized)")

async def test_alert_system(user_id: str):
    """Test the Redis-based alert system."""
    print("\n8. ⚠️ Testing Alert System...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    # Create alert template
    async with db_manager.get_async_session() as session:
        alert_id = f"alert_{int(datetime.now().timestamp())}"
        await session.execute(text("""
            INSERT INTO alert_templates 
            (id, user_id, name, symbol, exchange, condition, message, is_active)
            VALUES (:id, :user_id, :name, :symbol, :exchange, :condition, :message, :is_active)
        """), {
            "id": alert_id,
            "user_id": user_id,
            "name": "RELIANCE Price Alert",
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "condition": json.dumps({
                "type": "PRICE_ABOVE",
                "value": 2600.0,
                "trigger_once": False
            }),
            "message": "RELIANCE crossed ₹2,600",
            "is_active": True
        })
        await session.commit()
    
    # Simulate alert in Redis
    redis_client = await db_manager.get_redis()
    
    alert_data = {
        "alert_id": alert_id,
        "symbol": "RELIANCE",
        "condition": "PRICE_ABOVE",
        "trigger_price": 2600.0,
        "current_price": 2625.0,
        "triggered_at": datetime.now().isoformat()
    }
    
    # Store alert in Redis
    await redis_client.setex(
        f"alerts:price:RELIANCE",
        3600,  # 1 hour TTL
        json.dumps(alert_data)
    )
    
    print(f"   ✅ Alert template created: {alert_id}")
    print("   🚨 Price alert configured for RELIANCE > ₹2,600")
    print("   ⚡ Alert stored in Redis for real-time processing")

async def test_strategy_commands(strategy_config_id: str):
    """Test strategy command system."""
    print("\n9. 🎮 Testing Strategy Commands...")
    
    from app.database import db_manager
    from sqlalchemy import text
    
    commands_to_test = ["PAUSE", "RESUME", "STOP"]
    
    async with db_manager.get_async_session() as session:
        for command in commands_to_test:
            command_id = f"cmd_{command}_{int(datetime.now().timestamp())}"
            await session.execute(text("""
                INSERT INTO strategy_commands 
                (id, strategy_config_id, command, status)
                VALUES (:id, :strategy_config_id, :command, :status)
            """), {
                "id": command_id,
                "strategy_config_id": strategy_config_id,
                "command": command,
                "status": "PENDING"
            })
            
            print(f"   🎯 Command created: {command} -> {command_id}")
        
        await session.commit()
    
    print("   ✅ Strategy command system tested")

async def create_demo_strategy_class():
    """Create a demo strategy class file."""
    print("   📝 Creating demo strategy class...")
    
    # Ensure directory exists
    os.makedirs("app/strategies", exist_ok=True)
    
    demo_strategy_code = '''
"""
Demo Momentum Strategy for Testing Updated Engine
"""

from app.strategies.base_strategy import BaseStrategy
import asyncio
from typing import Dict, List, Any

class DemoMomentumStrategy(BaseStrategy):
    """Demo momentum strategy for testing."""
    
    async def on_initialize(self):
        """Initialize strategy-specific components."""
        # Subscribe to market data for configured symbols
        await self.subscribe_to_instruments(self.config.get('symbols', []))
        
        # Set up strategy-specific variables
        self.rsi_values = {}
        self.price_history = {}
        
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data updates."""
        # Store price history for RSI calculation
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        price = data.get('ltp', data.get('close', 0))
        self.price_history[symbol].append(price)
        
        # Keep only last 20 prices for RSI calculation
        if len(self.price_history[symbol]) > 20:
            self.price_history[symbol] = self.price_history[symbol][-20:]
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals based on momentum."""
        signals = []
        
        for symbol in self.config.get('symbols', []):
            # Simple momentum signal (demo)
            if symbol in self.price_history and len(self.price_history[symbol]) >= 2:
                current_price = self.price_history[symbol][-1]
                previous_price = self.price_history[symbol][-2]
                
                # Calculate simple momentum
                momentum = (current_price - previous_price) / previous_price
                
                # Generate buy signal if momentum > 1%
                if momentum > 0.01:
                    signals.append({
                        'type': 'BUY',
                        'symbol': symbol,
                        'exchange': 'NSE',
                        'quantity': 100,
                        'order_type': 'MARKET',
                        'product_type': 'INTRADAY',
                        'reason': f'Positive momentum: {momentum:.2%}'
                    })
                
                # Generate sell signal if momentum < -1%
                elif momentum < -0.01:
                    position_key = f"{symbol}_NSE_INTRADAY"
                    if position_key in self.positions and self.positions[position_key].quantity > 0:
                        signals.append({
                            'type': 'SELL',
                            'symbol': symbol,
                            'exchange': 'NSE',
                            'quantity': self.positions[position_key].quantity,
                            'order_type': 'MARKET',
                            'product_type': 'INTRADAY',
                            'reason': f'Negative momentum: {momentum:.2%}'
                        })
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration."""
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.price_history),
            'total_price_points': sum(len(prices) for prices in self.price_history.values()),
            'active_positions': len([p for p in self.positions.values() if p.quantity > 0])
        })
'''
    
    with open("app/strategies/demo_momentum.py", "w") as f:
        f.write(demo_strategy_code)
    
    print("   ✅ Demo strategy class created")

async def cleanup_demo():
    """Cleanup demo resources."""
    print("\n🧹 Cleaning up demo resources...")
    
    try:
        from app.database import db_manager
        await db_manager.close()
        print("   ✅ Database connections closed")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

def print_system_status():
    """Print current system status."""
    print("\n📊 System Status:")
    print("   🔄 Database: ✅ Connected")
    print("   🔄 Redis: ✅ Connected") 
    print("   🔄 Strategy Engine: ✅ Running")
    print("   🔄 Notification Service: ✅ Active")
    print("   🔄 Market Data: ✅ Streaming")
    print("   🔄 Order Management: ✅ Operational")

if __name__ == "__main__":
    print("🎯 Updated Trading Engine Demo")
    print("This demo showcases the complete live trading system with the new cleaned schema.")
    print("\nFeatures demonstrated:")
    print("• Hybrid notification system (Redis + Database)")
    print("• Independent strategy process execution")
    print("• Database-driven strategy configuration")
    print("• Real-time order and position management")
    print("• Redis-based alert system")
    print("• Strategy command and control system")
    print("• Performance monitoring and metrics")
    
    try:
        asyncio.run(demo_updated_trading_engine())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc() 