#!/usr/bin/env python3

logger = logging.getLogger(__name__)

"""
Instrument Manager Status
Shows current instrument status and strategy integration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DatabaseManager
from app.core.instrument_manager import get_instrument_manager
from app.models.base import Strategy, StrategyStatus, AssetClass
from sqlalchemy import select

async def show_instrument_status():
    """Show comprehensive instrument manager status"""
    logger.info("📊 INSTRUMENT MANAGER STATUS")
    logger.info("=" * 60)
    
    db_manager = None
    instrument_manager = None
    
    try:
        # Initialize
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        instrument_manager = await get_instrument_manager(db_manager)
        
        # Get status
        status = instrument_manager.get_status()
        
        logger.info(f"🔗 API Status: {status['auth_status']}")
        logger.info(f"🕐 Last Updated: {status['last_updated']}")
        logger.info(f"📈 Total Instruments: {status['total_instruments']}")
        logger.info(f"   • Equity: {status['equity_count']}")
        logger.info(f"   • Derivatives: {status['derivatives_count']}")
        print()
        
        # Show sample instruments
        logger.info("📋 SAMPLE INSTRUMENTS")
        logger.info("-" * 40)
        
        equity_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.EQUITY)
        if equity_instruments:
            logger.info("💼 Equity (Top 10):")
            for i, inst in enumerate(equity_instruments[:10], 1):
                logger.info(f"   {i:2d}. {inst.symbol} ({inst.exchange}) - Lot: {inst.lot_size}")
        
        derivatives_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.DERIVATIVES)
        if derivatives_instruments:
            logger.info("\n📊 Derivatives (Top 5):")
            for i, inst in enumerate(derivatives_instruments[:5], 1):
                expiry_info = f" Exp: {inst.expiry}" if inst.expiry else ""
                logger.info(f"   {i}. {inst.symbol} ({inst.exchange}){expiry_info} - Lot: {inst.lot_size}")
        
        print()
        
        # Show strategy integration
        logger.info("🎯 STRATEGY INTEGRATION")
        logger.info("-" * 40)
        
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
            )
            strategies = result.scalars().all()
            
            for strategy in strategies:
                asset_class = strategy.asset_class.value
                symbol_count = len(strategy.symbols) if strategy.symbols else 0
                
                logger.info(f"📈 {strategy.name}")
                logger.info(f"   • Asset Class: {asset_class}")
                logger.info(f"   • Symbols: {symbol_count}")
                
                if strategy.symbols:
                    logger.info(f"   • Sample Symbols: {', '.join(strategy.symbols[:5])}")
                    if len(strategy.symbols) > 5:
                        logger.info(f"     ... and {len(strategy.symbols) - 5} more")
                print()
        
        # Configuration info
        logger.info("⚙️ CONFIGURATION")
        logger.info("-" * 40)
        logger.info("For real AngelOne data, set these environment variables:")
        logger.info("• ANGELONE_API_KEY_INSTRUMENTS=your_api_key")
        logger.info("• ANGELONE_CLIENT_ID_INSTRUMENTS=your_client_id")
        logger.info("• ANGELONE_PASSWORD_INSTRUMENTS=your_password")
        logger.info("• ANGELONE_TOTP_SECRET_INSTRUMENTS=your_totp_secret")
        print()
        logger.info("📅 Run daily: python3 scripts/refresh_instruments.py")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    
    finally:
        if instrument_manager:
            await instrument_manager.stop()
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_instrument_status()) 