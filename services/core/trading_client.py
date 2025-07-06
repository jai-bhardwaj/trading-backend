#!/usr/bin/env python3
"""
Trading Client - Direct Python interface to trading core
No HTTP overhead, direct function calls for maximum performance
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingClient:
    """High-performance trading client with direct function calls"""
    
    def __init__(self, trading_core):
        self.core = trading_core
    
    async def place_order(self, user_id: str, symbol: str, side: str, 
                         quantity: int, price: float, order_type: str = "MARKET",
                         strategy_id: Optional[str] = None) -> Dict:
        """Place a trading order - direct function call, no HTTP"""
        order_data = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "strategy_id": strategy_id
        }
        
        return await self.core.place_order(user_id, order_data)
    
    async def get_positions(self, user_id: str) -> Dict:
        """Get user positions - direct function call"""
        return await self.core.get_user_positions(user_id)
    
    async def get_orders(self, user_id: str) -> Dict:
        """Get user orders - direct function call"""
        return await self.core.get_user_orders(user_id)
    
    async def get_market_data(self, symbols: List[str]) -> Dict:
        """Get market data - direct function call"""
        return await self.core.get_market_data(symbols)
    
    async def get_portfolio_summary(self, user_id: str) -> Dict:
        """Get portfolio summary - direct function call"""
        positions = await self.core.get_user_positions(user_id)
        
        total_value = 0
        total_pnl = 0
        
        for position in positions["positions"]:
            position_value = position["quantity"] * position["current_price"]
            total_value += position_value
            total_pnl += position["unrealized_pnl"] + position["realized_pnl"]
        
        return {
            "user_id": user_id,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "positions_count": len(positions["positions"]),
            "timestamp": datetime.utcnow().isoformat()
        }

# Example usage functions
async def example_trading_session():
    """Example of how to use the trading client"""
    from services.core.trading_core import trading_core
    
    # Initialize trading core
    await trading_core.initialize()
    
    # Create client
    client = TradingClient(trading_core)
    
    # Place an order
    result = await client.place_order(
        user_id="trader_001",
        symbol="RELIANCE",
        side="BUY",
        quantity=100,
        price=2500.0,
        order_type="MARKET"
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

if __name__ == "__main__":
    asyncio.run(example_trading_session()) 