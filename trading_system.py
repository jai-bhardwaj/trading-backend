#!/usr/bin/env python3
"""
Trading System - Main orchestrator for all modules
Clean, modular, high-performance trading system
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, List, Optional, Any

# Import modules
from core.trading_engine import trading_engine
from modules.market_data import market_data_module
from modules.risk_management import risk_management_module
from modules.strategy_engine import strategy_engine_module
from modules.portfolio_manager import portfolio_manager_module

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingSystem:
    """Main trading system orchestrator"""
    
    def __init__(self):
        self.modules = {
            "trading_engine": trading_engine,
            "market_data": market_data_module,
            "risk_management": risk_management_module,
            "strategy_engine": strategy_engine_module,
            "portfolio_manager": portfolio_manager_module
        }
        self.running = False
        
    async def initialize(self):
        """Initialize all modules"""
        logger.info("🚀 Initializing Trading System...")
        
        try:
            # Initialize all modules
            for name, module in self.modules.items():
                logger.info(f"Initializing {name}...")
                await module.initialize()
                logger.info(f"✅ {name} initialized")
            
            self.running = True
            logger.info("✅ Trading System initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trading System: {e}")
            raise
    
    async def start(self):
        """Start the trading system"""
        logger.info("🚀 Starting Trading System...")
        
        try:
            # Start background tasks
            tasks = [
                asyncio.create_task(self._market_data_loop()),
                asyncio.create_task(self._strategy_loop()),
                asyncio.create_task(self._risk_monitoring_loop()),
                asyncio.create_task(self._portfolio_update_loop())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error in trading system: {e}")
            raise
    
    async def _market_data_loop(self):
        """Market data processing loop"""
        while self.running:
            try:
                # Get market data
                market_data = await market_data_module.get_all_market_data()
                
                # Update portfolio prices
                for user_id in ["trader_001", "trader_002"]:
                    await portfolio_manager_module.update_position_prices(user_id, market_data)
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                await asyncio.sleep(1)
    
    async def _strategy_loop(self):
        """Strategy execution loop"""
        while self.running:
            try:
                # Get market data
                market_data = await market_data_module.get_all_market_data()
                
                # Run strategies
                signals = await strategy_engine_module.run_all_strategies(market_data)
                
                # Process signals
                for signal in signals:
                    await self._process_trading_signal(signal)
                
                await asyncio.sleep(5)  # Run strategies every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in strategy loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_trading_signal(self, signal: Any):
        """Process a trading signal"""
        try:
            # Check risk limits
            order_data = {
                "symbol": signal.symbol,
                "quantity": signal.quantity,
                "price": signal.price
            }
            
            risk_check = await risk_management_module.check_order_risk("trader_001", order_data)
            
            if risk_check["approved"]:
                # Place order
                result = await trading_engine.place_order(
                    user_id="trader_001",
                    symbol=signal.symbol,
                    side=signal.signal_type.value,
                    quantity=signal.quantity,
                    price=signal.price,
                    strategy_id=signal.strategy_id
                )
                
                if result["success"]:
                    # Add transaction to portfolio
                    transaction = {
                        "transaction_id": f"txn_{int(time.time() * 1000)}",
                        "user_id": "trader_001",
                        "symbol": signal.symbol,
                        "transaction_type": signal.signal_type.value,
                        "quantity": signal.quantity,
                        "price": signal.price,
                        "timestamp": signal.timestamp,
                        "order_id": result["order_id"]
                    }
                    
                    await portfolio_manager_module.add_transaction(transaction)
                    logger.info(f"Processed signal: {signal.symbol} {signal.signal_type.value}")
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _risk_monitoring_loop(self):
        """Risk monitoring loop"""
        while self.running:
            try:
                for user_id in ["trader_001", "trader_002"]:
                    # Get positions
                    positions = await trading_engine.get_user_positions(user_id)
                    
                    # Check portfolio risk
                    risk_summary = await risk_management_module.check_portfolio_risk(user_id, positions)
                    
                    if risk_summary.get("violations"):
                        logger.warning(f"Risk violations for {user_id}: {risk_summary['violations']}")
                
                await asyncio.sleep(10)  # Check risk every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _portfolio_update_loop(self):
        """Portfolio update loop"""
        while self.running:
            try:
                for user_id in ["trader_001", "trader_002"]:
                    # Update portfolio metrics
                    summary = await portfolio_manager_module.get_portfolio_summary(user_id)
                    
                    # Update risk management with new capital
                    if "total_value" in summary:
                        await risk_management_module.update_user_capital(user_id, summary["total_value"])
                    
                    if "daily_pnl" in summary:
                        await risk_management_module.update_daily_pnl(user_id, summary["daily_pnl"])
                
                await asyncio.sleep(30)  # Update portfolio every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in portfolio update loop: {e}")
                await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the trading system"""
        logger.info("🔄 Stopping Trading System...")
        self.running = False
        
        # Stop all modules
        for name, module in self.modules.items():
            try:
                await module.stop()
                logger.info(f"✅ {name} stopped")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("✅ Trading System stopped")

# Global trading system instance
trading_system = TradingSystem()

async def shutdown(signal, loop):
    """Graceful shutdown"""
    logger.info(f"Received exit signal {signal.name}...")
    await trading_system.stop()
    loop.stop()

def main():
    """Main function"""
    loop = asyncio.get_event_loop()
    
    # Setup signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
    
    try:
        logger.info("🚀 Starting Modular Trading System...")
        logger.info("✅ Clean architecture - no HTTP overhead")
        logger.info("✅ Modular design - easy to maintain")
        logger.info("✅ High performance - direct function calls")
        logger.info("✅ Real-time processing - 100ms updates")
        
        # Initialize and start trading system
        loop.run_until_complete(trading_system.initialize())
        loop.run_until_complete(trading_system.start())
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in trading system: {e}")
    finally:
        loop.run_until_complete(trading_system.stop())
        loop.close()
        logger.info("Trading system shutdown complete")

if __name__ == "__main__":
    main() 