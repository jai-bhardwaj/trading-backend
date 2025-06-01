#!/usr/bin/env python3
"""
Instrument Manager Status
Shows current instrument status and strategy integration
"""

import asyncio
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
    print("📊 INSTRUMENT MANAGER STATUS")
    print("=" * 60)
    
    db_manager = None
    instrument_manager = None
    
    try:
        # Initialize
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        instrument_manager = await get_instrument_manager(db_manager)
        
        # Get status
        status = instrument_manager.get_status()
        
        print(f"🔗 API Status: {status['auth_status']}")
        print(f"🕐 Last Updated: {status['last_updated']}")
        print(f"📈 Total Instruments: {status['total_instruments']}")
        print(f"   • Equity: {status['equity_count']}")
        print(f"   • Derivatives: {status['derivatives_count']}")
        print()
        
        # Show sample instruments
        print("📋 SAMPLE INSTRUMENTS")
        print("-" * 40)
        
        equity_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.EQUITY)
        if equity_instruments:
            print("💼 Equity (Top 10):")
            for i, inst in enumerate(equity_instruments[:10], 1):
                print(f"   {i:2d}. {inst.symbol} ({inst.exchange}) - Lot: {inst.lot_size}")
        
        derivatives_instruments = instrument_manager.get_instruments_by_asset_class(AssetClass.DERIVATIVES)
        if derivatives_instruments:
            print("\n📊 Derivatives (Top 5):")
            for i, inst in enumerate(derivatives_instruments[:5], 1):
                expiry_info = f" Exp: {inst.expiry}" if inst.expiry else ""
                print(f"   {i}. {inst.symbol} ({inst.exchange}){expiry_info} - Lot: {inst.lot_size}")
        
        print()
        
        # Show strategy integration
        print("🎯 STRATEGY INTEGRATION")
        print("-" * 40)
        
        async with db_manager.get_session() as db:
            result = await db.execute(
                select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
            )
            strategies = result.scalars().all()
            
            for strategy in strategies:
                asset_class = strategy.asset_class.value
                symbol_count = len(strategy.symbols) if strategy.symbols else 0
                
                print(f"📈 {strategy.name}")
                print(f"   • Asset Class: {asset_class}")
                print(f"   • Symbols: {symbol_count}")
                
                if strategy.symbols:
                    print(f"   • Sample Symbols: {', '.join(strategy.symbols[:5])}")
                    if len(strategy.symbols) > 5:
                        print(f"     ... and {len(strategy.symbols) - 5} more")
                print()
        
        # Configuration info
        print("⚙️ CONFIGURATION")
        print("-" * 40)
        print("For real AngelOne data, set these environment variables:")
        print("• ANGELONE_API_KEY_INSTRUMENTS=your_api_key")
        print("• ANGELONE_CLIENT_ID_INSTRUMENTS=your_client_id")
        print("• ANGELONE_PASSWORD_INSTRUMENTS=your_password")
        print("• ANGELONE_TOTP_SECRET_INSTRUMENTS=your_totp_secret")
        print()
        print("📅 Run daily: python3 scripts/refresh_instruments.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if instrument_manager:
            await instrument_manager.stop()
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_instrument_status()) 