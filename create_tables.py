#!/usr/bin/env python3
import asyncio
from app.database import get_database_manager
from app.models.base import Base

async def create_tables():
    db = get_database_manager()
    await db.initialize()
    
    # Create all tables using the async engine
    async with db.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print('✅ Database tables created/updated')

if __name__ == "__main__":
    asyncio.run(create_tables()) 