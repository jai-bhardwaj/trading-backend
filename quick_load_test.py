#!/usr/bin/env python3
"""
Quick Load Test Script
"""

import asyncio
import json
import uuid
import os
import sys
sys.path.append('/app')

from app.database import DatabaseManager
from sqlalchemy import text

async def create_test_strategies(count=5):
    """Create test strategies and measure impact"""
    print(f"🧪 Creating {count} load test strategies...")
    
    db = DatabaseManager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        for i in range(1, count + 1):
            strategy_id = str(uuid.uuid4())
            query = text('''
                INSERT INTO strategies 
                (id, "userId", name, "strategyType", "assetClass", symbols, timeframe, status, 
                 parameters, "riskParameters", "maxPositions", "capitalAllocated", 
                 "createdAt", "updatedAt")
                VALUES 
                (:id, :user_id, :name, :strategy_type, :asset_class, :symbols, :timeframe, :status,
                 :parameters, :risk_parameters, :max_positions, :capital_allocated,
                 NOW(), NOW())
            ''')
            
            await session.execute(query, {
                'id': strategy_id,
                'user_id': 'load_test_user',
                'name': f'Load Test Strategy #{i}',
                'strategy_type': 'load_test_strategy',
                'asset_class': 'EQUITY',
                'symbols': json.dumps(['RELIANCE', 'TCS', 'INFY']),
                'timeframe': 'MINUTE_1',
                'status': 'ACTIVE',
                'parameters': json.dumps({'strategy_number': i, 'signal_frequency': 0.05}),
                'risk_parameters': json.dumps({'risk_per_trade': 0.01}),
                'max_positions': 3,
                'capital_allocated': 10000
            })
        
        await session.commit()
        print(f'✅ Created {count} load test strategies')
        
        # Count total strategies
        result = await session.execute(text('SELECT COUNT(*) FROM strategies WHERE status = \'ACTIVE\''))
        count_result = result.scalar()
        print(f'📊 Total active strategies: {count_result}')

async def cleanup_test_strategies():
    """Clean up test strategies"""
    print("🧹 Cleaning up load test strategies...")
    
    db = DatabaseManager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        await session.execute(text('''
            DELETE FROM strategies 
            WHERE "strategyType" = 'load_test_strategy'
        '''))
        await session.commit()
        print("✅ Cleanup completed")

async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        await cleanup_test_strategies()
    else:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
        await create_test_strategies(count)

if __name__ == "__main__":
    asyncio.run(main()) 