#!/usr/bin/env python3
"""
Portfolio Manager Module - Position and portfolio management
Modular component for portfolio operations
"""

import asyncio
import logging
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"

@dataclass
class Position:
    """Portfolio position"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    position_type: PositionType
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime
    metadata: Dict = field(default_factory=dict)

@dataclass
class Transaction:
    """Portfolio transaction"""
    transaction_id: str
    user_id: str
    symbol: str
    transaction_type: TransactionType
    quantity: int
    price: float
    timestamp: datetime
    order_id: Optional[str] = None
    fees: float = 0.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    active_positions: int

class PortfolioManagerModule:
    """Modular portfolio management system"""
    
    def __init__(self):
        self.positions: Dict[str, Dict[str, Position]] = {}  # user_id -> {symbol -> Position}
        self.transactions: Dict[str, List[Transaction]] = {}  # user_id -> [Transaction]
        self.portfolio_history: Dict[str, List[Dict]] = {}  # user_id -> [portfolio_snapshots]
        
    async def initialize(self):
        """Initialize portfolio manager module"""
        logger.info("🚀 Initializing Portfolio Manager Module...")
        logger.info("✅ Portfolio Manager Module initialized")
    
    async def add_transaction(self, transaction: Transaction):
        """Add a new transaction"""
        try:
            user_id = transaction.user_id
            
            # Initialize user data if not exists
            if user_id not in self.transactions:
                self.transactions[user_id] = []
            if user_id not in self.positions:
                self.positions[user_id] = {}
            
            # Add transaction
            self.transactions[user_id].append(transaction)
            
            # Update position
            await self._update_position(transaction)
            
            # Update portfolio history
            await self._update_portfolio_history(user_id)
            
            logger.info(f"Added transaction: {transaction.symbol} {transaction.transaction_type.value} {transaction.quantity}")
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
    
    async def _update_position(self, transaction: Transaction):
        """Update position based on transaction"""
        user_id = transaction.user_id
        symbol = transaction.symbol
        user_positions = self.positions[user_id]
        
        position = user_positions.get(symbol)
        
        if not position:
            position = Position(
                symbol=symbol,
                quantity=0,
                avg_price=0.0,
                current_price=transaction.price,
                position_type=PositionType.LONG,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                last_updated=transaction.timestamp
            )
            user_positions[symbol] = position
        
        # Update position based on transaction type
        if transaction.transaction_type == TransactionType.BUY:
            # Calculate new average price
            total_cost = (position.quantity * position.avg_price) + (transaction.quantity * transaction.price)
            position.quantity += transaction.quantity
            position.avg_price = total_cost / position.quantity if position.quantity > 0 else 0
            
        elif transaction.transaction_type == TransactionType.SELL:
            if position.quantity > 0:
                # Calculate realized P&L
                realized_pnl = (transaction.price - position.avg_price) * min(transaction.quantity, position.quantity)
                position.realized_pnl += realized_pnl
            
            position.quantity -= transaction.quantity
            if position.quantity <= 0:
                position.quantity = 0
                position.avg_price = 0
        
        position.current_price = transaction.price
        position.last_updated = transaction.timestamp
    
    async def update_position_prices(self, user_id: str, market_data: Dict):
        """Update position prices with current market data"""
        try:
            user_positions = self.positions.get(user_id, {})
            
            for symbol, position in user_positions.items():
                if symbol in market_data:
                    new_price = market_data[symbol]["price"]
                    position.current_price = new_price
                    position.unrealized_pnl = (new_price - position.avg_price) * position.quantity
                    position.last_updated = datetime.utcnow()
            
            # Update portfolio history
            await self._update_portfolio_history(user_id)
            
        except Exception as e:
            logger.error(f"Error updating position prices: {e}")
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary"""
        try:
            user_positions = self.positions.get(user_id, {})
            user_transactions = self.transactions.get(user_id, [])
            
            # Calculate portfolio metrics
            total_value = 0
            total_unrealized_pnl = 0
            total_realized_pnl = 0
            active_positions = 0
            
            for position in user_positions.values():
                position_value = position.quantity * position.current_price
                total_value += position_value
                total_unrealized_pnl += position.unrealized_pnl
                total_realized_pnl += position.realized_pnl
                
                if position.quantity > 0:
                    active_positions += 1
            
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            # Calculate daily P&L
            today = datetime.utcnow().date()
            daily_transactions = [
                t for t in user_transactions 
                if t.timestamp.date() == today
            ]
            daily_pnl = sum(
                (t.price - t.price) * t.quantity  # Simplified for demo
                for t in daily_transactions
            )
            
            return {
                "user_id": user_id,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "unrealized_pnl": total_unrealized_pnl,
                "realized_pnl": total_realized_pnl,
                "daily_pnl": daily_pnl,
                "active_positions": active_positions,
                "total_transactions": len(user_transactions),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {"error": str(e)}
    
    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user positions"""
        try:
            user_positions = self.positions.get(user_id, {})
            
            return [
                {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "avg_price": position.avg_price,
                    "current_price": position.current_price,
                    "position_type": position.position_type.value,
                    "unrealized_pnl": position.unrealized_pnl,
                    "realized_pnl": position.realized_pnl,
                    "position_value": position.quantity * position.current_price,
                    "return_percent": ((position.current_price - position.avg_price) / position.avg_price * 100) if position.avg_price > 0 else 0,
                    "last_updated": position.last_updated.isoformat()
                }
                for position in user_positions.values()
                if position.quantity > 0
            ]
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_transactions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user transactions"""
        try:
            user_transactions = self.transactions.get(user_id, [])
            
            # Sort by timestamp (newest first)
            sorted_transactions = sorted(user_transactions, key=lambda x: x.timestamp, reverse=True)
            
            return [
                {
                    "transaction_id": t.transaction_id,
                    "symbol": t.symbol,
                    "transaction_type": t.transaction_type.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "value": t.quantity * t.price,
                    "fees": t.fees,
                    "timestamp": t.timestamp.isoformat(),
                    "order_id": t.order_id
                }
                for t in sorted_transactions[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    async def get_performance_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get performance analytics"""
        try:
            user_transactions = self.transactions.get(user_id, [])
            user_positions = self.positions.get(user_id, {})
            
            # Calculate basic metrics
            total_trades = len(user_transactions)
            winning_trades = 0
            total_profit = 0
            
            # Calculate win rate (simplified)
            for transaction in user_transactions:
                if transaction.transaction_type == TransactionType.SELL:
                    # Find corresponding buy transaction
                    buy_transactions = [
                        t for t in user_transactions 
                        if t.symbol == transaction.symbol and t.transaction_type == TransactionType.BUY
                    ]
                    
                    if buy_transactions:
                        avg_buy_price = sum(t.price for t in buy_transactions) / len(buy_transactions)
                        profit = (transaction.price - avg_buy_price) * transaction.quantity
                        total_profit += profit
                        
                        if profit > 0:
                            winning_trades += 1
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate portfolio metrics
            total_value = sum(pos.quantity * pos.current_price for pos in user_positions.values())
            total_pnl = sum(pos.unrealized_pnl + pos.realized_pnl for pos in user_positions.values())
            
            return {
                "user_id": user_id,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "active_positions": len([p for p in user_positions.values() if p.quantity > 0]),
                "avg_position_size": total_value / len(user_positions) if user_positions else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            return {"error": str(e)}
    
    async def _update_portfolio_history(self, user_id: str):
        """Update portfolio history"""
        try:
            if user_id not in self.portfolio_history:
                self.portfolio_history[user_id] = []
            
            summary = await self.get_portfolio_summary(user_id)
            
            self.portfolio_history[user_id].append({
                **summary,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep only last 1000 snapshots
            if len(self.portfolio_history[user_id]) > 1000:
                self.portfolio_history[user_id] = self.portfolio_history[user_id][-1000:]
                
        except Exception as e:
            logger.error(f"Error updating portfolio history: {e}")
    
    async def get_portfolio_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get portfolio history"""
        try:
            history = self.portfolio_history.get(user_id, [])
            
            # Filter by days
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filtered_history = [
                h for h in history 
                if datetime.fromisoformat(h["timestamp"]) > cutoff_date
            ]
            
            return filtered_history
            
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return []
    
    async def stop(self):
        """Stop portfolio manager module"""
        logger.info("🔄 Portfolio Manager Module stopped")

# Global portfolio manager module instance
portfolio_manager_module = PortfolioManagerModule() 