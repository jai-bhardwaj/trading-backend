#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.database import get_database_manager
from sqlalchemy import text

async def fix_enum():
    print("🔧 FIXING OrderStatus ENUM IN DATABASE")
    print("=" * 50)
    
    db = get_database_manager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        # Check current enum values
        result = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'OrderStatus')")
        )
        current_values = [v[0] for v in result.fetchall()]
        
        print("Current database enum values:")
        for v in current_values:
            print(f"  • {v}")
        
        # Required values from Python enum
        required_values = ['PENDING', 'QUEUED', 'PLACED', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED', 'ERROR', 'UNKNOWN']
        missing_values = [v for v in required_values if v not in current_values]
        
        if missing_values:
            print(f"\nMissing values: {missing_values}")
            
            for value in missing_values:
                print(f"Adding {value} to OrderStatus enum...")
                try:
                    await session.execute(
                        text(f"ALTER TYPE \"OrderStatus\" ADD VALUE '{value}'")
                    )
                    await session.commit()
                    print(f"✅ Added {value}")
                except Exception as e:
                    print(f"❌ Failed to add {value}: {e}")
                    await session.rollback()
        else:
            print("✅ All required enum values are present")
        
        # Verify final state
        result = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'OrderStatus')")
        )
        final_values = [v[0] for v in result.fetchall()]
        
        print(f"\nFinal database enum values:")
        for v in final_values:
            print(f"  • {v}")
    
    await db.close()
    print("\n🎉 ENUM FIX COMPLETE!")

if __name__ == "__main__":
    asyncio.run(fix_enum()) 