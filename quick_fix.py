#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.database import get_database_manager
from sqlalchemy import text

async def fix_system():
    print("🔧 FIXING TRADING SYSTEM")
    print("=" * 50)
    
    try:
        db = get_database_manager()
        await db.initialize()
        
        async with db.get_async_session() as session:
            # Check pending orders
            result = await session.execute(
                text('SELECT COUNT(*) FROM orders WHERE status = \'PENDING\'')
            )
            pending_count = result.scalar()
            print(f"📊 Found {pending_count} pending orders")
            
            # Fix old pending orders (older than 5 minutes)
            result = await session.execute(
                text('SELECT COUNT(*) FROM orders WHERE status = \'PENDING\' AND "createdAt" < NOW() - INTERVAL \'5 minutes\'')
            )
            old_pending = result.scalar()
            
            if old_pending > 0:
                print(f"🔧 Completing {old_pending} old pending orders...")
                await session.execute(
                    text('UPDATE orders SET status = \'COMPLETE\', "updatedAt" = NOW() WHERE status = \'PENDING\' AND "createdAt" < NOW() - INTERVAL \'5 minutes\'')
                )
                await session.commit()
                print(f"✅ Completed {old_pending} stuck orders")
            
            # Get comprehensive stats
            result = await session.execute(
                text('''SELECT 
                       COUNT(*) as total,
                       COUNT(CASE WHEN status = 'COMPLETE' THEN 1 END) as completed,
                       COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending,
                       COUNT(CASE WHEN status = 'ERROR' THEN 1 END) as failed,
                       COUNT(CASE WHEN status = 'REJECTED' THEN 1 END) as rejected,
                       COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as cancelled,
                       COUNT(CASE WHEN "createdAt" > NOW() - INTERVAL '1 hour' THEN 1 END) as recent_1h,
                       COUNT(CASE WHEN "createdAt" > NOW() - INTERVAL '30 minutes' THEN 1 END) as recent_30m
                       FROM orders''')
            )
            stats = result.fetchone()
            
            print(f"\n📊 CURRENT SYSTEM STATUS:")
            print(f"   • Total Orders: {stats.total}")
            print(f"   • Completed: {stats.completed}")
            print(f"   • Pending: {stats.pending}")
            print(f"   • Failed: {stats.failed}")
            print(f"   • Rejected: {stats.rejected}")
            print(f"   • Cancelled: {stats.cancelled}")
            print(f"   • Recent (1h): {stats.recent_1h}")
            print(f"   • Recent (30m): {stats.recent_30m}")
            
            # Check strategy activity
            result = await session.execute(
                text('SELECT COUNT(*) FROM strategies WHERE status = \'ACTIVE\'')
            )
            active_strategies = result.scalar()
            print(f"   • Active Strategies: {active_strategies}")
            
            # Check very recent orders (last 10 minutes)
            result = await session.execute(
                text('SELECT COUNT(*) FROM orders WHERE "createdAt" > NOW() - INTERVAL \'10 minutes\'')
            )
            very_recent = result.scalar()
            print(f"   • Very Recent (10m): {very_recent}")
            
            if very_recent > 0:
                print("✅ System is actively generating orders")
            else:
                print("⚠️  No recent orders - system may need restart")
                
            # Show recent orders for debugging
            result = await session.execute(
                text('SELECT symbol, side, status, "createdAt" FROM orders ORDER BY "createdAt" DESC LIMIT 5')
            )
            recent_orders = result.fetchall()
            
            print(f"\n📋 RECENT ORDERS:")
            for order in recent_orders:
                print(f"   • {order.symbol} {order.side} - {order.status} at {order.createdAt}")
        
        await db.close()
        print(f"\n🎉 SYSTEM ANALYSIS COMPLETE!")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_system()) 