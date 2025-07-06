#!/usr/bin/env python3
"""
Trading Engine - Core trading operations
Modular, high-performance trading system
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    """Trading order"""
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    filled_quantity: int = 0
    filled_price: float = 0.0
    strategy_id: Optional[str] = None
    error_message: str = ""

@dataclass
class Position:
    """Trading position"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

class TradingEngine:
    """Core trading engine - handles all trading operations"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Dict[str, Position]] = {}  # user_id -> {symbol -> Position}
        self.running = False
        
    async def initialize(self):
        """Initialize the trading engine"""
        logger.info("🚀 Initializing Trading Engine...")
        self.running = True
        logger.info("✅ Trading Engine initialized")
    
    async def place_order(self, user_id: str, symbol: str, side: str, 
                         quantity: int, price: float, order_type: str = "MARKET",
                         strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """Place a trading order"""
        try:
            # Create order
            order = Order(
                order_id=f"order_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                symbol=symbol.upper(),
                side=OrderSide(side.upper()),
                order_type=OrderType(order_type.upper()),
                quantity=quantity,
                price=price,
                strategy_id=strategy_id
            )
            
            # Store order
            self.orders[order.order_id] = order
            
            # Process order
            await self._process_order(order)
            
            return {
                "success": True,
                "order_id": order.order_id,
                "status": order.status.value,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "price": order.price,
                "created_at": order.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_order(self, order: Order):
        """Process a trading order"""
        try:
            # Update order status
            order.status = OrderStatus.PLACED
            order.updated_at = datetime.utcnow()
            
            # Execute order based on type
            if order.order_type == OrderType.MARKET:
                await self._execute_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                await self._execute_limit_order(order)
            
            # Update position
            if order.status == OrderStatus.FILLED:
                await self._update_position(order)
                
        except Exception as e:
            logger.error(f"Error processing order {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
    
    async def _execute_market_order(self, order: Order):
        """Execute market order"""
        # Simulate market execution
        execution_price = order.price  # In real system, get from market data
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        logger.info(f"Executed market order: {order.symbol} {order.side.value} {order.quantity} @ {execution_price}")
    
    async def _execute_limit_order(self, order: Order):
        """Execute limit order"""
        # For now, simulate immediate execution
        # In real system, would check market price against limit
        order.filled_price = order.price
        order.filled_quantity = order.quantity
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        logger.info(f"Executed limit order: {order.symbol} {order.side.value} {order.quantity} @ {order.price}")
    
    async def _update_position(self, order: Order):
        """Update position after order execution"""
        if order.status != OrderStatus.FILLED:
            return
        
        user_positions = self.positions.setdefault(order.user_id, {})
        position = user_positions.get(order.symbol)
        
        if not position:
            position = Position(
                symbol=order.symbol,
                quantity=0,
                avg_price=0.0,
                current_price=order.filled_price
            )
            user_positions[order.symbol] = position
        
        # Update position
        if order.side == OrderSide.BUY:
            total_cost = (position.quantity * position.avg_price) + (order.filled_quantity * order.filled_price)
            position.quantity += order.filled_quantity
            position.avg_price = total_cost / position.quantity if position.quantity > 0 else 0
        else:  # SELL
            # Calculate realized P&L
            if position.quantity > 0:
                realized_pnl = (order.filled_price - position.avg_price) * min(order.filled_quantity, position.quantity)
                position.realized_pnl += realized_pnl
            
            position.quantity -= order.filled_quantity
            if position.quantity <= 0:
                position.quantity = 0
                position.avg_price = 0
        
        position.current_price = order.filled_price
        position.last_updated = datetime.utcnow()
    
    async def get_user_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's orders"""
        user_orders = [order for order in self.orders.values() if order.user_id == user_id]
        
        return [
            {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.price,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity,
                "filled_price": order.filled_price,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
                "strategy_id": order.strategy_id,
                "error_message": order.error_message
            }
            for order in user_orders
        ]
    
    async def get_user_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's positions"""
        user_positions = self.positions.get(user_id, {})
        
        return [
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "avg_price": position.avg_price,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "realized_pnl": position.realized_pnl,
                "position_value": position.quantity * position.current_price,
                "last_updated": position.last_updated.isoformat()
            }
            for position in user_positions.values()
        ]
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get specific order"""
        order = self.orders.get(order_id)
        if not order:
            return None
        
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.price,
            "status": order.status.value,
            "filled_quantity": order.filled_quantity,
            "filled_price": order.filled_price,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "strategy_id": order.strategy_id,
            "error_message": order.error_message
        }
    
    async def cancel_order(self, order_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        order = self.orders.get(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}
        
        if order.user_id != user_id:
            return {"success": False, "error": "Access denied"}
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return {"success": False, "error": "Order cannot be cancelled"}
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        return {"success": True, "message": "Order cancelled successfully"}
    
    async def stop(self):
        """Stop the trading engine"""
        self.running = False
        logger.info("🔄 Trading Engine stopped")

# Global trading engine instance
trading_engine = TradingEngine() 