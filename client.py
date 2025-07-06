#!/usr/bin/env python3
"""
Trading Client - Simple interface for the trading system
Direct Python calls - no HTTP overhead
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import modules
from core.trading_engine import trading_engine
from modules.market_data import market_data_module
from modules.risk_management import risk_management_module
from modules.strategy_engine import strategy_engine_module
from modules.portfolio_manager import portfolio_manager_module

logger = logging.getLogger(__name__)

class TradingClient:
    """Simple trading client interface"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        """Initialize the client"""
        if not self.initialized:
            await trading_engine.initialize()
            await market_data_module.initialize()
            await risk_management_module.initialize()
            await strategy_engine_module.initialize()
            await portfolio_manager_module.initialize()
            self.initialized = True
            logger.info("✅ Trading client initialized")
    
    # Trading Operations
    async def place_order(self, user_id: str, symbol: str, side: str, 
                         quantity: int, price: float, order_type: str = "MARKET",
                         strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """Place a trading order"""
        await self.initialize()
        
        # Check risk limits first
        order_data = {"symbol": symbol, "quantity": quantity, "price": price}
        risk_check = await risk_management_module.check_order_risk(user_id, order_data)
        
        if not risk_check["approved"]:
            return {
                "success": False,
                "error": "Risk check failed",
                "violations": risk_check["violations"]
            }
        
        # Place order
        result = await trading_engine.place_order(user_id, symbol, side, quantity, price, order_type, strategy_id)
        
        if result["success"]:
            # Add transaction to portfolio
            transaction = {
                "transaction_id": f"txn_{int(datetime.utcnow().timestamp() * 1000)}",
                "user_id": user_id,
                "symbol": symbol,
                "transaction_type": side.upper(),
                "quantity": quantity,
                "price": price,
                "timestamp": datetime.utcnow(),
                "order_id": result["order_id"]
            }
            
            await portfolio_manager_module.add_transaction(transaction)
            
            # Update order count
            await risk_management_module.increment_order_count(user_id)
        
        return result
    
    async def get_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user orders"""
        await self.initialize()
        return await trading_engine.get_user_orders(user_id)
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get specific order"""
        await self.initialize()
        return await trading_engine.get_order(order_id)
    
    async def cancel_order(self, order_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        await self.initialize()
        return await trading_engine.cancel_order(order_id, user_id)
    
    # Portfolio Operations
    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user positions"""
        await self.initialize()
        return await portfolio_manager_module.get_positions(user_id)
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary"""
        await self.initialize()
        return await portfolio_manager_module.get_portfolio_summary(user_id)
    
    async def get_transactions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user transactions"""
        await self.initialize()
        return await portfolio_manager_module.get_transactions(user_id, limit)
    
    async def get_performance_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get performance analytics"""
        await self.initialize()
        return await portfolio_manager_module.get_performance_analytics(user_id)
    
    # Market Data Operations
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get market data for symbols"""
        await self.initialize()
        return await market_data_module.get_market_data(symbols)
    
    async def get_all_market_data(self) -> Dict[str, Dict]:
        """Get market data for all symbols"""
        await self.initialize()
        return await market_data_module.get_all_market_data()
    
    async def subscribe_symbol(self, symbol: str):
        """Subscribe to symbol updates"""
        await self.initialize()
        await market_data_module.subscribe_symbol(symbol)
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from symbol updates"""
        await self.initialize()
        await market_data_module.unsubscribe_symbol(symbol)
    
    # Risk Management Operations
    async def get_risk_summary(self, user_id: str) -> Dict[str, Any]:
        """Get risk summary"""
        await self.initialize()
        return await risk_management_module.get_risk_summary(user_id)
    
    async def check_portfolio_risk(self, user_id: str) -> Dict[str, Any]:
        """Check portfolio risk"""
        await self.initialize()
        positions = await self.get_positions(user_id)
        return await risk_management_module.check_portfolio_risk(user_id, positions)
    
    # Strategy Operations
    async def get_strategies(self) -> List[Dict[str, Any]]:
        """Get all strategies"""
        await self.initialize()
        return await strategy_engine_module.get_strategies()
    
    async def run_strategy(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Run a specific strategy"""
        await self.initialize()
        market_data = await self.get_all_market_data()
        signals = await strategy_engine_module.run_strategy(strategy_id, market_data)
        
        return [
            {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "confidence": signal.confidence,
                "price": signal.price,
                "quantity": signal.quantity,
                "timestamp": signal.timestamp.isoformat(),
                "metadata": signal.metadata
            }
            for signal in signals
        ]
    
    async def enable_strategy(self, strategy_id: str):
        """Enable a strategy"""
        await self.initialize()
        await strategy_engine_module.enable_strategy(strategy_id)
    
    async def disable_strategy(self, strategy_id: str):
        """Disable a strategy"""
        await self.initialize()
        await strategy_engine_module.disable_strategy(strategy_id)

# Example usage
async def example_usage():
    """Example of how to use the trading client"""
    client = TradingClient()
    
    # Initialize
    await client.initialize()
    
    # Place an order
    result = await client.place_order(
        user_id="trader_001",
        symbol="RELIANCE",
        side="BUY",
        quantity=100,
        price=2500.0
    )
    print(f"Order result: {result}")
    
    # Get positions
    positions = await client.get_positions("trader_001")
    print(f"Positions: {positions}")
    
    # Get market data
    market_data = await client.get_market_data(["RELIANCE", "TCS"])
    print(f"Market data: {market_data}")
    
    # Get portfolio summary
    portfolio = await client.get_portfolio_summary("trader_001")
    print(f"Portfolio: {portfolio}")
    
    # Get risk summary
    risk = await client.get_risk_summary("trader_001")
    print(f"Risk summary: {risk}")
    
    # Run strategies
    strategies = await client.get_strategies()
    print(f"Strategies: {strategies}")
    
    signals = await client.run_strategy("ma_crossover")
    print(f"Signals: {signals}")

if __name__ == "__main__":
    asyncio.run(example_usage()) 