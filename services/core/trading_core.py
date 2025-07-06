#!/usr/bin/env python3
"""
Trading Core - High-Performance Trading System
Direct Python communication without HTTP overhead
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import redis.asyncio as redis
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    """Trading system configuration"""
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    TRADING_MODE: str = os.getenv("TRADING_MODE", "PAPER")  # PAPER or LIVE
    MAX_POSITION_SIZE: float = 100000.0
    RISK_TOLERANCE: str = "MEDIUM"
    UPDATE_INTERVAL: float = 0.1  # 100ms for real-time trading

@dataclass
class MarketData:
    """Real-time market data"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    bid: float = 0.0
    ask: float = 0.0
    high: float = 0.0
    low: float = 0.0

@dataclass
class Order:
    """Trading order"""
    order_id: str
    user_id: str
    symbol: str
    side: str  # BUY/SELL
    quantity: int
    price: float
    order_type: str  # MARKET/LIMIT
    status: str = "PENDING"
    filled_quantity: int = 0
    filled_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    strategy_id: Optional[str] = None

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

class TradingCore:
    """High-performance trading core without HTTP overhead"""
    
    def __init__(self):
        self.config = TradingConfig()
        self.redis_client = None
        self.running = False
        self.orders = {}  # order_id -> Order
        self.positions = {}  # user_id -> {symbol -> Position}
        self.market_data = {}  # symbol -> MarketData
        self.users = {}  # user_id -> user_data
        self.strategies = {}  # strategy_id -> strategy_config
        
    async def initialize(self):
        """Initialize trading core"""
        logger.info("🚀 Initializing Trading Core...")
        
        # Connect to Redis
        self.redis_client = redis.from_url(self.config.REDIS_URL)
        await self.redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Load initial data
        await self._load_users()
        await self._load_strategies()
        await self._load_positions()
        
        logger.info("✅ Trading Core initialized")
        
    async def start(self):
        """Start the trading core"""
        self.running = True
        logger.info("🚀 Trading Core started")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._market_data_loop()),
            asyncio.create_task(self._order_processing_loop()),
            asyncio.create_task(self._risk_monitoring_loop()),
            asyncio.create_task(self._position_update_loop())
        ]
        
        await asyncio.gather(*tasks)
        
    async def stop(self):
        """Stop the trading core"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("🔄 Trading Core stopped")
    
    # Market Data Management
    async def _market_data_loop(self):
        """Real-time market data processing loop"""
        while self.running:
            try:
                # Get market data from Redis
                market_data_raw = await self.redis_client.get("market_data")
                if market_data_raw:
                    data = json.loads(market_data_raw)
                    for symbol, price_data in data.items():
                        self.market_data[symbol] = MarketData(
                            symbol=symbol,
                            price=price_data["price"],
                            volume=price_data.get("volume", 0),
                            timestamp=datetime.fromisoformat(price_data["timestamp"]),
                            bid=price_data.get("bid", price_data["price"]),
                            ask=price_data.get("ask", price_data["price"]),
                            high=price_data.get("high", price_data["price"]),
                            low=price_data.get("low", price_data["price"])
                        )
                
                await asyncio.sleep(self.config.UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in market data loop: {e}")
                await asyncio.sleep(1)
    
    # Order Management
    async def place_order(self, user_id: str, order_data: Dict) -> Dict:
        """Place a trading order (direct function call, no HTTP)"""
        try:
            # Validate order
            if not self._validate_order(order_data):
                return {"success": False, "error": "Invalid order data"}
            
            # Create order
            order = Order(
                order_id=f"order_{int(time.time() * 1000)}",
                user_id=user_id,
                symbol=order_data["symbol"],
                side=order_data["side"],
                quantity=order_data["quantity"],
                price=order_data["price"],
                order_type=order_data["order_type"],
                strategy_id=order_data.get("strategy_id")
            )
            
            # Store order
            self.orders[order.order_id] = order
            
            # Process order immediately
            await self._process_order(order)
            
            return {
                "success": True,
                "order_id": order.order_id,
                "status": order.status
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_order(self, order: Order):
        """Process a trading order"""
        try:
            # Check risk limits
            if not await self._check_risk_limits(order):
                order.status = "REJECTED"
                return
            
            # Execute order
            if order.order_type == "MARKET":
                await self._execute_market_order(order)
            else:
                await self._execute_limit_order(order)
                
            # Update position
            await self._update_position(order)
            
            # Log order
            await self._log_order(order)
            
        except Exception as e:
            logger.error(f"Error processing order {order.order_id}: {e}")
            order.status = "REJECTED"
    
    async def _execute_market_order(self, order: Order):
        """Execute market order"""
        symbol_data = self.market_data.get(order.symbol)
        if not symbol_data:
            order.status = "REJECTED"
            return
        
        # Execute at current market price
        execution_price = symbol_data.ask if order.side == "BUY" else symbol_data.bid
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.status = "FILLED"
        
        logger.info(f"Executed market order: {order.symbol} {order.side} {order.quantity} @ {execution_price}")
    
    async def _execute_limit_order(self, order: Order):
        """Execute limit order"""
        symbol_data = self.market_data.get(order.symbol)
        if not symbol_data:
            order.status = "PENDING"
            return
        
        # Check if limit price is met
        if order.side == "BUY" and symbol_data.ask <= order.price:
            order.filled_price = order.price
            order.filled_quantity = order.quantity
            order.status = "FILLED"
        elif order.side == "SELL" and symbol_data.bid >= order.price:
            order.filled_price = order.price
            order.filled_quantity = order.quantity
            order.status = "FILLED"
        else:
            order.status = "PENDING"
    
    async def _order_processing_loop(self):
        """Process pending orders"""
        while self.running:
            try:
                # Process pending limit orders
                for order in self.orders.values():
                    if order.status == "PENDING" and order.order_type == "LIMIT":
                        await self._process_order(order)
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                logger.error(f"Error in order processing loop: {e}")
                await asyncio.sleep(1)
    
    # Position Management
    async def _update_position(self, order: Order):
        """Update position after order execution"""
        if order.status != "FILLED":
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
        if order.side == "BUY":
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
    
    async def _position_update_loop(self):
        """Update position P&L based on current market prices"""
        while self.running:
            try:
                for user_id, user_positions in self.positions.items():
                    for symbol, position in user_positions.items():
                        market_data = self.market_data.get(symbol)
                        if market_data:
                            position.current_price = market_data.price
                            position.unrealized_pnl = (position.current_price - position.avg_price) * position.quantity
                            position.last_updated = datetime.utcnow()
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in position update loop: {e}")
                await asyncio.sleep(1)
    
    # Risk Management
    async def _risk_monitoring_loop(self):
        """Monitor risk limits"""
        while self.running:
            try:
                for user_id, user_positions in self.positions.items():
                    # Check position limits
                    total_exposure = sum(abs(p.quantity * p.current_price) for p in user_positions.values())
                    if total_exposure > self.config.MAX_POSITION_SIZE:
                        logger.warning(f"Risk limit exceeded for user {user_id}: {total_exposure}")
                        # Could trigger position reduction here
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _check_risk_limits(self, order: Order) -> bool:
        """Check if order meets risk limits"""
        # Simple risk check - can be expanded
        user_positions = self.positions.get(order.user_id, {})
        current_exposure = sum(abs(p.quantity * p.current_price) for p in user_positions.values())
        new_exposure = current_exposure + (order.quantity * order.price)
        
        return new_exposure <= self.config.MAX_POSITION_SIZE
    
    # Data Loading
    async def _load_users(self):
        """Load user data"""
        try:
            users_data = await self.redis_client.get("users")
            if users_data:
                self.users = json.loads(users_data)
            else:
                # Default users for development
                self.users = {
                    "trader_001": {
                        "user_id": "trader_001",
                        "name": "Trader 1",
                        "capital": 100000.0,
                        "risk_tolerance": "MEDIUM"
                    },
                    "trader_002": {
                        "user_id": "trader_002", 
                        "name": "Trader 2",
                        "capital": 500000.0,
                        "risk_tolerance": "HIGH"
                    }
                }
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    async def _load_strategies(self):
        """Load strategy configurations"""
        try:
            strategies_data = await self.redis_client.get("strategies")
            if strategies_data:
                self.strategies = json.loads(strategies_data)
            else:
                # Default strategies
                self.strategies = {
                    "ma_crossover": {
                        "strategy_id": "ma_crossover",
                        "type": "MOVING_AVERAGE",
                        "symbols": ["RELIANCE", "TCS", "INFY"],
                        "parameters": {"short_period": 10, "long_period": 20}
                    }
                }
        except Exception as e:
            logger.error(f"Error loading strategies: {e}")
    
    async def _load_positions(self):
        """Load existing positions"""
        try:
            positions_data = await self.redis_client.get("positions")
            if positions_data:
                positions_dict = json.loads(positions_data)
                for user_id, user_positions in positions_dict.items():
                    self.positions[user_id] = {}
                    for symbol, pos_data in user_positions.items():
                        self.positions[user_id][symbol] = Position(
                            symbol=symbol,
                            quantity=pos_data["quantity"],
                            avg_price=pos_data["avg_price"],
                            current_price=pos_data["current_price"],
                            unrealized_pnl=pos_data.get("unrealized_pnl", 0.0),
                            realized_pnl=pos_data.get("realized_pnl", 0.0)
                        )
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
    
    # Utility Functions
    def _validate_order(self, order_data: Dict) -> bool:
        """Validate order data"""
        required_fields = ["symbol", "side", "quantity", "price", "order_type"]
        return all(field in order_data for field in required_fields)
    
    async def _log_order(self, order: Order):
        """Log order for audit"""
        log_data = {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": order.price,
            "status": order.status,
            "timestamp": order.created_at.isoformat()
        }
        await self.redis_client.lpush("order_logs", json.dumps(log_data))
    
    # Public API (direct function calls, no HTTP)
    async def get_user_positions(self, user_id: str) -> Dict:
        """Get user positions"""
        user_positions = self.positions.get(user_id, {})
        return {
            "user_id": user_id,
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "realized_pnl": pos.realized_pnl
                }
                for pos in user_positions.values()
            ]
        }
    
    async def get_user_orders(self, user_id: str) -> Dict:
        """Get user orders"""
        user_orders = [order for order in self.orders.values() if order.user_id == user_id]
        return {
            "user_id": user_id,
            "orders": [
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "price": order.price,
                    "status": order.status,
                    "filled_quantity": order.filled_quantity,
                    "filled_price": order.filled_price,
                    "created_at": order.created_at.isoformat()
                }
                for order in user_orders
            ]
        }
    
    async def get_market_data(self, symbols: List[str]) -> Dict:
        """Get market data for symbols"""
        return {
            symbol: {
                "price": data.price,
                "volume": data.volume,
                "bid": data.bid,
                "ask": data.ask,
                "high": data.high,
                "low": data.low,
                "timestamp": data.timestamp.isoformat()
            }
            for symbol, data in self.market_data.items()
            if symbol in symbols
        }

# Global trading core instance
trading_core = TradingCore()

async def main():
    """Main function to run the trading core"""
    try:
        await trading_core.initialize()
        await trading_core.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await trading_core.stop()

if __name__ == "__main__":
    asyncio.run(main()) 