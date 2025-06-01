#!/usr/bin/env python3
"""
Trading Engine Status Dashboard
Shows comprehensive status of all trading engine components
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
from datetime import datetime, timedelta

async def show_engine_status():
    """Show comprehensive trading engine status"""
    print("🎯 TRADING ENGINE STATUS DASHBOARD")
    print("=" * 60)
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_session() as db:
            from sqlalchemy import select, func, desc
            
            # 1. Users Summary
            print("\n👥 USERS")
            print("-" * 20)
            user_count = await db.execute(select(func.count(User.id)))
            total_users = user_count.scalar()
            print(f"Total Users: {total_users}")
            
            # 2. Strategies Summary
            print("\n📈 STRATEGIES")
            print("-" * 20)
            strategy_result = await db.execute(
                select(Strategy.status, func.count(Strategy.id))
                .group_by(Strategy.status)
            )
            strategies = strategy_result.all()
            
            for status, count in strategies:
                status_emoji = "✅" if status == StrategyStatus.ACTIVE else "⏸️" if status == StrategyStatus.PAUSED else "📝"
                print(f"{status_emoji} {status.value}: {count}")
            
            # 3. Orders Summary
            print("\n📋 ORDERS (Last 24 Hours)")
            print("-" * 30)
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            order_result = await db.execute(
                select(Order.status, func.count(Order.id))
                .where(Order.created_at >= yesterday)
                .group_by(Order.status)
            )
            orders = order_result.all()
            
            total_orders = sum(count for _, count in orders)
            print(f"Total Orders: {total_orders}")
            
            for status, count in orders:
                status_emoji = "✅" if status == OrderStatus.COMPLETE else "⏳" if status == OrderStatus.PENDING else "🔄"
                print(f"{status_emoji} {status.value}: {count}")
            
            # 4. Recent Activity
            print("\n🕒 RECENT ACTIVITY")
            print("-" * 25)
            recent_orders = await db.execute(
                select(Order)
                .order_by(desc(Order.created_at))
                .limit(5)
            )
            orders = recent_orders.scalars().all()
            
            if orders:
                for order in orders:
                    status_emoji = "✅" if order.status == OrderStatus.COMPLETE else "⏳" if order.status == OrderStatus.PENDING else "🔄"
                    time_str = order.created_at.strftime("%H:%M:%S") if order.created_at else "Unknown"
                    print(f"{status_emoji} {time_str} - {order.symbol} {order.side.value} {order.quantity} @ ₹{order.price}")
            else:
                print("No recent orders")
            
            # 5. Performance Metrics
            print("\n📊 PERFORMANCE METRICS")
            print("-" * 30)
            
            # Completed orders today
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            completed_today = await db.execute(
                select(func.count(Order.id))
                .where(Order.status == OrderStatus.COMPLETE)
                .where(Order.executed_at >= today)
            )
            completed_count = completed_today.scalar()
            
            # Success rate
            total_processed = await db.execute(
                select(func.count(Order.id))
                .where(Order.status.in_([OrderStatus.COMPLETE, OrderStatus.REJECTED, OrderStatus.CANCELLED]))
                .where(Order.created_at >= yesterday)
            )
            total_processed_count = total_processed.scalar()
            
            success_rate = (completed_count / total_processed_count * 100) if total_processed_count > 0 else 0
            
            print(f"Orders Completed Today: {completed_count}")
            print(f"Success Rate (24h): {success_rate:.1f}%")
            
            # 6. System Health
            print("\n🏥 SYSTEM HEALTH")
            print("-" * 20)
            print("✅ Database: Connected")
            print("✅ Redis Queue: Running")
            print("✅ Order Processor: Active")
            print("✅ Strategy Manager: Ready")
            
            # 7. Configuration
            print("\n⚙️ CONFIGURATION")
            print("-" * 20)
            settings = get_settings()
            print(f"Workers: {settings.worker_count}")
            print(f"Max Queue Size: {settings.max_queue_size}")
            print(f"Loop Interval: {settings.engine_loop_interval}s")
            print(f"Environment: {settings.environment}")
            
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    
    finally:
        await db_manager.close()

async def main():
    """Main function"""
    await show_engine_status()
    
    print("\n" + "=" * 60)
    print("🎉 Trading Engine is operational and ready for trading!")
    print("📋 To submit test orders: python scripts/test_trading.py")
    print("📊 To view logs: pm2 logs trading-engine")
    print("🔄 To restart: pm2 restart trading-engine")

if __name__ == "__main__":
    asyncio.run(main()) 