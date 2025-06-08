#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.database import get_database_manager
from sqlalchemy import text

async def check_enum():
    db = get_database_manager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        # Check database enum values
        result = await session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'OrderStatus')")
        )
        values = result.fetchall()
        
        print("Database OrderStatus enum values:")
        for v in values:
            print(f"  • {v[0]}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(check_enum()) 