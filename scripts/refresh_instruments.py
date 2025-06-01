#!/usr/bin/env python3
"""
Daily Instrument Refresh Script
Fetches latest instruments from AngelOne and updates strategy symbols
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DatabaseManager
from app.core.instrument_manager import get_instrument_manager
from app.models.base import Strategy, StrategyStatus, AssetClass
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def refresh_instruments():
    """Main function to refresh instruments"""
    logger.info("🔄 Starting daily instrument refresh...")
    
    db_manager = None
    instrument_manager = None
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("✅ Database connected")
        
        # Initialize instrument manager
        instrument_manager = await get_instrument_manager(db_manager)
        logger.info("✅ Instrument manager initialized")
        
        # Refresh instruments from API
        await instrument_manager.refresh_instruments()
        
        # Get status
        status = instrument_manager.get_status()
        logger.info(f"📊 Instrument Status:")
        logger.info(f"   • Total Instruments: {status['total_instruments']}")
        logger.info(f"   • Equity: {status['equity_count']}")
        logger.info(f"   • Derivatives: {status['derivatives_count']}")
        logger.info(f"   • Auth Status: {status['auth_status']}")
        logger.info(f"   • Last Updated: {status['last_updated']}")
        
        # Show strategy updates
        await show_strategy_updates(db_manager)
        
        logger.info("✅ Daily instrument refresh completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during instrument refresh: {e}")
        sys.exit(1)
    
    finally:
        if instrument_manager:
            await instrument_manager.stop()
        if db_manager:
            await db_manager.close()

async def show_strategy_updates(db_manager: DatabaseManager):
    """Show updated strategy symbol counts"""
    try:
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
            )
            strategies = result.scalars().all()
            
            logger.info("📈 Updated Strategy Symbols:")
            for strategy in strategies:
                symbol_count = len(strategy.symbols) if strategy.symbols else 0
                asset_class = strategy.asset_class.value
                logger.info(f"   • {strategy.name} ({asset_class}): {symbol_count} symbols")
    
    except Exception as e:
        logger.error(f"Error showing strategy updates: {e}")

async def test_instrument_fetching():
    """Test function to verify instrument fetching"""
    logger.info("🧪 Testing instrument fetching...")
    
    db_manager = None
    instrument_manager = None
    
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        instrument_manager = await get_instrument_manager(db_manager)
        
        # Test getting instruments by asset class
        equity_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.EQUITY)
        derivatives_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.DERIVATIVES)
        
        logger.info(f"🔍 Test Results:")
        logger.info(f"   • Equity Instruments: {len(equity_instruments)}")
        if equity_instruments:
            logger.info(f"   • Sample Equity: {[inst.symbol for inst in equity_instruments[:5]]}")
        
        logger.info(f"   • Derivatives Instruments: {len(derivatives_instruments)}")
        if derivatives_instruments:
            logger.info(f"   • Sample Derivatives: {[inst.symbol for inst in derivatives_instruments[:5]]}")
        
        # Test getting specific instrument info
        if equity_instruments:
            sample_symbol = equity_instruments[0].symbol
            instrument_info = instrument_manager.get_instrument_info(sample_symbol)
            if instrument_info:
                logger.info(f"   • Sample Instrument Info ({sample_symbol}):")
                logger.info(f"     - Exchange: {instrument_info.exchange}")
                logger.info(f"     - Lot Size: {instrument_info.lot_size}")
                logger.info(f"     - Tick Size: {instrument_info.tick_size}")
        
        logger.info("✅ Test completed successfully")
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    
    finally:
        if instrument_manager:
            await instrument_manager.stop()
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_instrument_fetching())
    else:
        asyncio.run(refresh_instruments()) 