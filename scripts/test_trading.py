#!/usr/bin/env python3
"""
Test Trading Engine
Submit test orders to verify the trading engine is working
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
from datetime import datetime

async def submit_test_order():
    """Submit a test order to the trading engine"""
    print("🧪 Testing Trading Engine")
    print("=" * 40)
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_session() as db:
            # Get the demo user
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.username == "demo_trader"))
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ Demo user not found. Run create_demo_data.py first.")
                return 1
            
            # Create a test order
            test_order = Order(
                id=str(uuid.uuid4()),
                user_id=user.id,
                symbol="RELIANCE",
                exchange="NSE",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                product_type=ProductType.INTRADAY,
                quantity=5,
                price=2500.0,
                status=OrderStatus.PENDING,
                is_paper_trade=True
            )
            
            db.add(test_order)
            await db.commit()
            
            print(f"✅ Test order created: {test_order.id}")
            print(f"📊 Order details:")
            print(f"   • Symbol: {test_order.symbol}")
            print(f"   • Side: {test_order.side.value}")
            print(f"   • Quantity: {test_order.quantity}")
            print(f"   • Price: ₹{test_order.price}")
            print(f"   • Status: {test_order.status.value}")
            
            print("\n🔄 Order will be processed by the trading engine automatically")
            print("📋 Check the logs with: pm2 logs trading-engine")
            
    except Exception as e:
        print(f"❌ Error creating test order: {e}")
        return 1
    
    finally:
        await db_manager.close()
    
    return 0

async def check_order_status():
    """Check status of recent orders"""
    print("\n📊 Recent Order Status")
    print("=" * 40)
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    try:
        async with db_manager.get_session() as db:
            from sqlalchemy import select, desc
            
            # Get recent orders
            result = await db.execute(
                select(Order)
                .order_by(desc(Order.created_at))
                .limit(5)
            )
            orders = result.scalars().all()
            
            if not orders:
                print("No orders found")
                return
            
            for order in orders:
                status_emoji = "✅" if order.status == OrderStatus.COMPLETE else "⏳" if order.status == OrderStatus.PENDING else "🔄"
                print(f"{status_emoji} {order.symbol} {order.side.value} {order.quantity} @ ₹{order.price} - {order.status.value}")
                if order.executed_at:
                    print(f"   Executed: {order.executed_at}")
                print()
    
    except Exception as e:
        print(f"❌ Error checking orders: {e}")
    
    finally:
        await db_manager.close()

async def main():
    """Main function"""
    # Submit test order
    result = await submit_test_order()
    
    # Wait a moment for processing
    await asyncio.sleep(2)
    
    # Check order status
    await check_order_status()
    
    return result

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 