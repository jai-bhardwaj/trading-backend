#!/usr/bin/env python3
"""
Advanced Portfolio Manager - P&L tracking, position management, and analytics
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.common.error_handling import with_circuit_breaker, with_retry
from shared.common.security import AuditLogger
from shared.common.monitoring import MetricsCollector
from contextlib import asynccontextmanager

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

class PortfolioManager:
    """Advanced portfolio management system"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.positions = {}
        self.transactions = {}
        self.metrics_collector = MetricsCollector(redis_client)
        self.audit_logger = AuditLogger(redis_client)
        
    async def initialize(self):
        """Initialize portfolio manager"""
        logger.info("✅ Portfolio Manager initialized")
    
    async def add_transaction(self, transaction: Transaction):
        """Add a new transaction"""
        try:
            # Store transaction
            key = f"transaction:{transaction.user_id}:{transaction.transaction_id}"
            transaction_data = {
                "transaction_id": transaction.transaction_id,
                "user_id": transaction.user_id,
                "symbol": transaction.symbol,
                "transaction_type": transaction.transaction_type.value,
                "quantity": transaction.quantity,
                "price": transaction.price,
                "timestamp": transaction.timestamp.isoformat(),
                "order_id": transaction.order_id,
                "fees": transaction.fees,
                "metadata": transaction.metadata
            }
            
            await self.redis_client.setex(
                key,
                86400 * 365,  # 1 year
                json.dumps(transaction_data)
            )
            
            # Update position
            await self._update_position(transaction)
            
            # Record metrics
            await self.metrics_collector.record_metric(
                "portfolio_transaction",
                1,
                {
                    "user_id": transaction.user_id,
                    "symbol": transaction.symbol,
                    "transaction_type": transaction.transaction_type.value,
                    "value": transaction.quantity * transaction.price
                }
            )
            
            # Log transaction
            await self.audit_logger.log_trading_event(
                "transaction",
                transaction.user_id,
                transaction_data
            )
            
            logger.info(f"✅ Transaction added: {transaction.transaction_id}")
            
        except Exception as e:
            logger.error(f"❌ Error adding transaction: {e}")
            raise
    
    async def _update_position(self, transaction: Transaction):
        """Update position based on transaction"""
        try:
            position_key = f"position:{transaction.user_id}:{transaction.symbol}"
            
            # Get current position
            position_data = await self.redis_client.get(position_key)
            current_position = None
            
            if position_data:
                data = json.loads(position_data)
                current_position = Position(
                    symbol=data["symbol"],
                    quantity=data["quantity"],
                    avg_price=data["avg_price"],
                    current_price=data["current_price"],
                    position_type=PositionType(data["position_type"]),
                    unrealized_pnl=data["unrealized_pnl"],
                    realized_pnl=data["realized_pnl"],
                    last_updated=datetime.fromisoformat(data["last_updated"]),
                    metadata=data.get("metadata", {})
                )
            
            # Update position based on transaction
            if transaction.transaction_type == TransactionType.BUY:
                if current_position and current_position.position_type == PositionType.LONG:
                    # Add to existing long position
                    total_quantity = current_position.quantity + transaction.quantity
                    total_value = (current_position.quantity * current_position.avg_price) + \
                                (transaction.quantity * transaction.price)
                    new_avg_price = total_value / total_quantity
                    
                    new_position = Position(
                        symbol=transaction.symbol,
                        quantity=total_quantity,
                        avg_price=new_avg_price,
                        current_price=transaction.price,
                        position_type=PositionType.LONG,
                        unrealized_pnl=0,  # Will be calculated later
                        realized_pnl=current_position.realized_pnl,
                        last_updated=datetime.utcnow(),
                        metadata=current_position.metadata
                    )
                else:
                    # Create new long position
                    new_position = Position(
                        symbol=transaction.symbol,
                        quantity=transaction.quantity,
                        avg_price=transaction.price,
                        current_price=transaction.price,
                        position_type=PositionType.LONG,
                        unrealized_pnl=0,
                        realized_pnl=0,
                        last_updated=datetime.utcnow(),
                        metadata={}
                    )
            
            elif transaction.transaction_type == TransactionType.SELL:
                if current_position and current_position.position_type == PositionType.LONG:
                    # Reduce long position
                    remaining_quantity = current_position.quantity - transaction.quantity
                    
                    if remaining_quantity > 0:
                        # Partial sell
                        realized_pnl = (transaction.price - current_position.avg_price) * transaction.quantity
                        
                        new_position = Position(
                            symbol=transaction.symbol,
                            quantity=remaining_quantity,
                            avg_price=current_position.avg_price,
                            current_price=transaction.price,
                            position_type=PositionType.LONG,
                            unrealized_pnl=0,
                            realized_pnl=current_position.realized_pnl + realized_pnl,
                            last_updated=datetime.utcnow(),
                            metadata=current_position.metadata
                        )
                    else:
                        # Full sell
                        realized_pnl = (transaction.price - current_position.avg_price) * current_position.quantity
                        new_position = None  # Position closed
                else:
                    # Create short position (if supported)
                    new_position = Position(
                        symbol=transaction.symbol,
                        quantity=transaction.quantity,
                        avg_price=transaction.price,
                        current_price=transaction.price,
                        position_type=PositionType.SHORT,
                        unrealized_pnl=0,
                        realized_pnl=0,
                        last_updated=datetime.utcnow(),
                        metadata={}
                    )
            
            # Save updated position
            if new_position:
                position_data = {
                    "symbol": new_position.symbol,
                    "quantity": new_position.quantity,
                    "avg_price": new_position.avg_price,
                    "current_price": new_position.current_price,
                    "position_type": new_position.position_type.value,
                    "unrealized_pnl": new_position.unrealized_pnl,
                    "realized_pnl": new_position.realized_pnl,
                    "last_updated": new_position.last_updated.isoformat(),
                    "metadata": new_position.metadata
                }
                
                await self.redis_client.setex(
                    position_key,
                    86400 * 365,  # 1 year
                    json.dumps(position_data)
                )
            else:
                # Remove position if closed
                await self.redis_client.delete(position_key)
            
        except Exception as e:
            logger.error(f"❌ Error updating position: {e}")
            raise
    
    async def update_position_prices(self, user_id: str, market_data: Dict):
        """Update position prices with current market data"""
        try:
            # Get all user positions
            pattern = f"position:{user_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                position_data = await self.redis_client.get(key)
                if position_data:
                    data = json.loads(position_data)
                    symbol = data["symbol"]
                    
                    if symbol in market_data:
                        current_price = market_data[symbol].get("ltp", data["current_price"])
                        
                        # Calculate unrealized P&L
                        if data["position_type"] == PositionType.LONG.value:
                            unrealized_pnl = (current_price - data["avg_price"]) * data["quantity"]
                        else:  # SHORT
                            unrealized_pnl = (data["avg_price"] - current_price) * data["quantity"]
                        
                        # Update position
                        data["current_price"] = current_price
                        data["unrealized_pnl"] = unrealized_pnl
                        data["last_updated"] = datetime.utcnow().isoformat()
                        
                        await self.redis_client.setex(
                            key,
                            86400 * 365,  # 1 year
                            json.dumps(data)
                        )
            
            logger.info(f"✅ Updated position prices for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating position prices: {e}")
            raise
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        try:
            # Get all positions
            positions = await self.get_positions(user_id)
            
            # Calculate portfolio metrics
            total_value = 0
            total_unrealized_pnl = 0
            total_realized_pnl = 0
            active_positions = 0
            
            for position in positions:
                position_value = position.quantity * position.current_price
                total_value += position_value
                total_unrealized_pnl += position.unrealized_pnl
                total_realized_pnl += position.realized_pnl
                active_positions += 1
            
            # Get historical P&L
            daily_pnl = await self._get_period_pnl(user_id, "daily")
            weekly_pnl = await self._get_period_pnl(user_id, "weekly")
            monthly_pnl = await self._get_period_pnl(user_id, "monthly")
            
            # Calculate performance metrics
            total_pnl = total_unrealized_pnl + total_realized_pnl
            total_return = (total_pnl / total_value) if total_value > 0 else 0
            
            # Get transaction history for additional metrics
            transactions = await self.get_transactions(user_id)
            total_trades = len(transactions)
            winning_trades = len([t for t in transactions if t.price > 0])  # Simplified
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            return {
                "user_id": user_id,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "unrealized_pnl": total_unrealized_pnl,
                "realized_pnl": total_realized_pnl,
                "daily_pnl": daily_pnl,
                "weekly_pnl": weekly_pnl,
                "monthly_pnl": monthly_pnl,
                "total_return": total_return,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "active_positions": active_positions,
                "positions": [
                    {
                        "symbol": p.symbol,
                        "quantity": p.quantity,
                        "avg_price": p.avg_price,
                        "current_price": p.current_price,
                        "position_type": p.position_type.value,
                        "unrealized_pnl": p.unrealized_pnl,
                        "realized_pnl": p.realized_pnl,
                        "position_value": p.quantity * p.current_price
                    }
                    for p in positions
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting portfolio summary: {e}")
            raise
    
    async def get_positions(self, user_id: str) -> List[Position]:
        """Get all positions for user"""
        try:
            positions = []
            pattern = f"position:{user_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                position_data = await self.redis_client.get(key)
                if position_data:
                    data = json.loads(position_data)
                    position = Position(
                        symbol=data["symbol"],
                        quantity=data["quantity"],
                        avg_price=data["avg_price"],
                        current_price=data["current_price"],
                        position_type=PositionType(data["position_type"]),
                        unrealized_pnl=data["unrealized_pnl"],
                        realized_pnl=data["realized_pnl"],
                        last_updated=datetime.fromisoformat(data["last_updated"]),
                        metadata=data.get("metadata", {})
                    )
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []
    
    async def get_transactions(self, user_id: str, limit: int = 100) -> List[Transaction]:
        """Get recent transactions for user"""
        try:
            transactions = []
            pattern = f"transaction:{user_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            # Sort by timestamp (newest first)
            keys.sort(reverse=True)
            
            for key in keys[:limit]:
                transaction_data = await self.redis_client.get(key)
                if transaction_data:
                    data = json.loads(transaction_data)
                    transaction = Transaction(
                        transaction_id=data["transaction_id"],
                        user_id=data["user_id"],
                        symbol=data["symbol"],
                        transaction_type=TransactionType(data["transaction_type"]),
                        quantity=data["quantity"],
                        price=data["price"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        order_id=data.get("order_id"),
                        fees=data.get("fees", 0.0),
                        metadata=data.get("metadata", {})
                    )
                    transactions.append(transaction)
            
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error getting transactions: {e}")
            return []
    
    async def _get_period_pnl(self, user_id: str, period: str) -> float:
        """Get P&L for specific period"""
        try:
            # This is a simplified implementation
            # In production, you'd calculate this from transaction history
            
            if period == "daily":
                return -2500.0  # Mock daily P&L
            elif period == "weekly":
                return -8500.0  # Mock weekly P&L
            elif period == "monthly":
                return -15000.0  # Mock monthly P&L
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"❌ Error getting period P&L: {e}")
            return 0.0
    
    async def get_performance_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get detailed performance analytics"""
        try:
            portfolio_summary = await self.get_portfolio_summary(user_id)
            transactions = await self.get_transactions(user_id, limit=1000)
            
            # Calculate additional metrics
            if transactions:
                # Calculate Sharpe ratio (simplified)
                returns = []
                for i in range(1, len(transactions)):
                    if transactions[i].price > 0 and transactions[i-1].price > 0:
                        returns.append((transactions[i].price - transactions[i-1].price) / transactions[i-1].price)
                
                sharpe_ratio = np.mean(returns) / np.std(returns) if returns and np.std(returns) > 0 else 0
                
                # Calculate max drawdown
                cumulative_pnl = []
                running_pnl = 0
                for transaction in transactions:
                    if transaction.transaction_type in [TransactionType.BUY, TransactionType.SELL]:
                        pnl = (transaction.price - transaction.avg_price) * transaction.quantity if hasattr(transaction, 'avg_price') else 0
                        running_pnl += pnl
                        cumulative_pnl.append(running_pnl)
                
                if cumulative_pnl:
                    peak = max(cumulative_pnl)
                    max_drawdown = min(0, min(cumulative_pnl) - peak)
                else:
                    max_drawdown = 0
            else:
                sharpe_ratio = 0
                max_drawdown = 0
            
            return {
                "user_id": user_id,
                "portfolio_summary": portfolio_summary,
                "performance_metrics": {
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "total_trades": len(transactions),
                    "avg_trade_value": np.mean([t.quantity * t.price for t in transactions]) if transactions else 0,
                    "best_trade": max([t.quantity * t.price for t in transactions]) if transactions else 0,
                    "worst_trade": min([t.quantity * t.price for t in transactions]) if transactions else 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance analytics: {e}")
            raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    global redis_client, portfolio_manager
    
    try:
        logger.info("🚀 Portfolio Manager starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379/8")
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize portfolio manager
        portfolio_manager = PortfolioManager(redis_client)
        await portfolio_manager.initialize()
        
        logger.info("✅ Portfolio Manager ready on port 8008")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Portfolio Manager: {e}")
        raise
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
        logger.info("✅ Portfolio Manager shutdown complete")

# FastAPI app
app = FastAPI(
    title="Portfolio Manager",
    description="Advanced Portfolio Management System",
    version="1.0.0",
    lifespan=lifespan
)

# Global components
redis_client = None
portfolio_manager = None
security = HTTPBearer()

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify user token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/dashboard",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("user_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/transactions")
async def add_transaction(
    transaction_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Add a new transaction"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        transaction = Transaction(
            transaction_id=transaction_data["transaction_id"],
            user_id=current_user,
            symbol=transaction_data["symbol"],
            transaction_type=TransactionType(transaction_data["transaction_type"]),
            quantity=transaction_data["quantity"],
            price=transaction_data["price"],
            timestamp=datetime.fromisoformat(transaction_data["timestamp"]),
            order_id=transaction_data.get("order_id"),
            fees=transaction_data.get("fees", 0.0),
            metadata=transaction_data.get("metadata", {})
        )
        
        await portfolio_manager.add_transaction(transaction)
        return {"message": "Transaction added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to add transaction")

@app.get("/portfolio")
async def get_portfolio_summary(current_user: str = Depends(verify_user_token)):
    """Get portfolio summary"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        result = await portfolio_manager.get_portfolio_summary(current_user)
        return result
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio summary")

@app.get("/positions")
async def get_positions(current_user: str = Depends(verify_user_token)):
    """Get all positions"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        positions = await portfolio_manager.get_positions(current_user)
        return {
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "current_price": p.current_price,
                    "position_type": p.position_type.value,
                    "unrealized_pnl": p.unrealized_pnl,
                    "realized_pnl": p.realized_pnl,
                    "position_value": p.quantity * p.current_price
                }
                for p in positions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get positions")

@app.get("/transactions")
async def get_transactions(
    limit: int = 100,
    current_user: str = Depends(verify_user_token)
):
    """Get recent transactions"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        transactions = await portfolio_manager.get_transactions(current_user, limit)
        return {
            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "symbol": t.symbol,
                    "transaction_type": t.transaction_type.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "timestamp": t.timestamp.isoformat(),
                    "order_id": t.order_id,
                    "fees": t.fees,
                    "value": t.quantity * t.price
                }
                for t in transactions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transactions")

@app.post("/update-prices")
async def update_position_prices(
    market_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Update position prices with current market data"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        await portfolio_manager.update_position_prices(current_user, market_data)
        return {"message": "Position prices updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating position prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to update position prices")

@app.get("/analytics")
async def get_performance_analytics(current_user: str = Depends(verify_user_token)):
    """Get performance analytics"""
    if not portfolio_manager:
        raise HTTPException(status_code=503, detail="Portfolio manager not initialized")
    
    try:
        result = await portfolio_manager.get_performance_analytics(current_user)
        return result
        
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance analytics")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008) 