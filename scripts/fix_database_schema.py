#!/usr/bin/env python3
"""
Fix Database Schema Issues
Comprehensive script to align database schema with current model definitions
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import DatabaseManager
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_enum_types(db):
    """Fix all enum types in the database"""
    logger.info("🔧 Fixing database enum types...")
    
    # Define all enum fixes
    enum_fixes = [
        {
            'name': 'OrderStatus',
            'values': ['PENDING', 'QUEUED', 'PLACED', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED', 'ERROR', 'UNKNOWN', 'SUBMITTED']
        },
        {
            'name': 'OrderSide', 
            'values': ['BUY', 'SELL']
        },
        {
            'name': 'OrderType',
            'values': ['MARKET', 'LIMIT', 'SL', 'SL_M']
        },
        {
            'name': 'ProductType',
            'values': ['DELIVERY', 'INTRADAY', 'MARGIN', 'NORMAL', 'CARRYFORWARD', 'BO', 'CO']
        },
        {
            'name': 'UserRole',
            'values': ['USER', 'ADMIN', 'SUPER_ADMIN']
        },
        {
            'name': 'UserStatus',
            'values': ['ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION']
        },
        {
            'name': 'BrokerName',
            'values': ['ANGEL_ONE', 'ZERODHA', 'UPSTOX', 'FYERS', 'ALICE_BLUE']
        },
        {
            'name': 'RiskLevel',
            'values': ['CONSERVATIVE', 'MODERATE', 'AGGRESSIVE', 'CUSTOM']
        },
        {
            'name': 'StrategyStatus',
            'values': ['DRAFT', 'ACTIVE', 'PAUSED', 'STOPPED', 'ERROR', 'BACKTESTING']
        },
        {
            'name': 'AssetClass',
            'values': ['EQUITY', 'DERIVATIVES', 'CRYPTO', 'COMMODITIES', 'FOREX']
        },
        {
            'name': 'TimeFrame',
            'values': ['SECOND_1', 'SECOND_5', 'SECOND_15', 'SECOND_30', 'MINUTE_1', 'MINUTE_3', 'MINUTE_5', 'MINUTE_15', 'MINUTE_30', 'HOUR_1', 'HOUR_4', 'DAY_1', 'WEEK_1', 'MONTH_1']
        },
        {
            'name': 'NotificationType',
            'values': ['ORDER_EXECUTED', 'ORDER_CANCELLED', 'STRATEGY_STARTED', 'STRATEGY_STOPPED', 'RISK_VIOLATION', 'SYSTEM_ALERT', 'PRICE_ALERT']
        },
        {
            'name': 'NotificationStatus',
            'values': ['UNREAD', 'READ', 'ARCHIVED']
        },
        {
            'name': 'AuditAction',
            'values': ['LOGIN', 'LOGOUT', 'ORDER_PLACED', 'ORDER_CANCELLED', 'STRATEGY_CREATED', 'STRATEGY_UPDATED', 'STRATEGY_STARTED', 'STRATEGY_STOPPED', 'SETTINGS_CHANGED', 'PASSWORD_CHANGED', 'API_KEY_CREATED', 'API_KEY_DELETED']
        },
        {
            'name': 'StrategyConfigStatus',
            'values': ['ACTIVE', 'STOPPED', 'ERROR', 'PAUSED']
        },
        {
            'name': 'StrategyCommandType',
            'values': ['START', 'STOP', 'RESTART', 'PAUSE', 'RESUME', 'UPDATE_CONFIG']
        },
        {
            'name': 'CommandStatus',
            'values': ['PENDING', 'EXECUTED', 'FAILED']
        }
    ]
    
    for enum_def in enum_fixes:
        await fix_single_enum(db, enum_def['name'], enum_def['values'])

async def fix_single_enum(db, enum_name, values):
    """Fix a single enum type"""
    try:
        logger.info(f"  📝 Updating {enum_name} enum...")
        
        # First, check if enum exists
        check_enum_sql = f"""
        SELECT 1 FROM pg_type WHERE typname = '{enum_name.lower()}';
        """
        result = await db.execute(text(check_enum_sql))
        enum_exists = result.fetchone() is not None
        
        if not enum_exists:
            # Create new enum
            values_str = "', '".join(values)
            create_enum_sql = f"CREATE TYPE \"{enum_name}\" AS ENUM ('{values_str}');"
            await db.execute(text(create_enum_sql))
            logger.info(f"    ✅ Created new enum {enum_name}")
        else:
            # Get existing values
            get_values_sql = f"""
            SELECT unnest(enum_range(NULL::{enum_name}))::text as enum_value;
            """
            result = await db.execute(text(get_values_sql))
            existing_values = {row[0] for row in result.fetchall()}
            
            # Add missing values
            for value in values:
                if value not in existing_values:
                    try:
                        add_value_sql = f"ALTER TYPE \"{enum_name}\" ADD VALUE '{value}';"
                        await db.execute(text(add_value_sql))
                        logger.info(f"    ➕ Added '{value}' to {enum_name}")
                    except Exception as e:
                        if "already exists" not in str(e):
                            logger.warning(f"    ⚠️ Could not add '{value}' to {enum_name}: {e}")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"    ❌ Error updating {enum_name}: {e}")
        await db.rollback()

async def fix_table_columns(db):
    """Fix any missing table columns"""
    logger.info("🔧 Checking table columns...")
    
    # Add any missing columns with proper defaults
    column_fixes = [
        {
            'table': 'orders',
            'column': 'status',
            'type': '"OrderStatus"',
            'default': "'PENDING'"
        },
        {
            'table': 'orders', 
            'column': 'updatedAt',
            'type': 'TIMESTAMP',
            'default': 'now()'
        }
    ]
    
    for fix in column_fixes:
        await add_column_if_missing(db, fix['table'], fix['column'], fix['type'], fix.get('default'))

async def add_column_if_missing(db, table_name, column_name, column_type, default_value=None):
    """Add a column if it doesn't exist"""
    try:
        # Check if column exists
        check_sql = f"""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = '{column_name}';
        """
        result = await db.execute(text(check_sql))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            # Add column
            default_clause = f" DEFAULT {default_value}" if default_value else ""
            add_column_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause};"
            await db.execute(text(add_column_sql))
            logger.info(f"  ✅ Added column {column_name} to {table_name}")
            await db.commit()
        
    except Exception as e:
        logger.error(f"  ❌ Error adding column {column_name} to {table_name}: {e}")
        await db.rollback()

async def update_existing_data(db):
    """Update any existing data that might have invalid enum values"""
    logger.info("🔧 Updating existing data...")
    
    try:
        # Fix any orders with invalid status
        update_sql = """
        UPDATE orders 
        SET status = 'PENDING'::\"OrderStatus\"
        WHERE status NOT IN ('PENDING', 'QUEUED', 'PLACED', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED', 'ERROR', 'UNKNOWN', 'SUBMITTED');
        """
        result = await db.execute(text(update_sql))
        if result.rowcount > 0:
            logger.info(f"  ✅ Updated {result.rowcount} orders with invalid status")
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"  ❌ Error updating existing data: {e}")
        await db.rollback()

async def vacuum_and_analyze(db):
    """Vacuum and analyze tables for better performance"""
    logger.info("🔧 Optimizing database...")
    
    try:
        # Vacuum analyze key tables
        tables = ['orders', 'strategies', 'users', 'trades', 'positions']
        
        for table in tables:
            await db.execute(text(f"VACUUM ANALYZE {table};"))
            logger.info(f"  ✅ Optimized {table} table")
        
    except Exception as e:
        logger.error(f"  ❌ Error optimizing database: {e}")

async def main():
    """Main function to fix all database issues"""
    logger.info("🚀 Starting Database Schema Fix")
    logger.info("=" * 50)
    
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.initialize()
    
    try:
        async with db_manager.get_async_session() as db:
            # Fix enum types
            await fix_enum_types(db)
            
            # Fix table columns
            await fix_table_columns(db)
            
            # Update existing data
            await update_existing_data(db)
            
            # Optimize database
            await vacuum_and_analyze(db)
            
            logger.info("\n" + "=" * 50)
            logger.info("🎉 Database schema fixes completed successfully!")
            logger.info("✅ All enum types updated")
            logger.info("✅ Missing columns added")
            logger.info("✅ Data integrity restored")
            logger.info("✅ Database optimized")
            logger.info("\n🔄 Restart the trading engine to apply changes")
            
    except Exception as e:
        logger.error(f"❌ Error fixing database schema: {e}")
        return 1
    
    finally:
        await db_manager.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 