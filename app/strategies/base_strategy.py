"""
Enhanced Base Strategy Class for Live Trading
Works with the new cleaned schema and enhanced strategy execution system.
"""

# Standard library imports
import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

# Third-party imports
import redis.asyncio as aioredis
from sqlalchemy import text

# Local imports
from app.core.notification_service import NotificationService
from app.database import get_database_manager, RedisKeys
from app.models.base import (
    AssetClass, OrderSide, OrderType, ProductType, OrderStatus
)
from app.strategies.signals import StrategySignal
from app.utils.timezone_utils import ist_now as datetime_now

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a trading position from the new schema"""
    id: str
    user_id: str
    symbol: str
    exchange: str
    product_type: ProductType
    quantity: int
    average_price: float
    last_traded_price: float
    pnl: float
    realized_pnl: float
    market_value: float
    day_change: float
    day_change_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['product_type'] = self.product_type.value
        return data

@dataclass
class Order:
    """Represents a trading order from the new schema"""
    id: str
    user_id: str
    strategy_id: Optional[str]
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    product_type: ProductType
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    broker_order_id: Optional[str]
    status: OrderStatus
    status_message: Optional[str]
    filled_quantity: int
    average_price: Optional[float]
    tags: List[str]
    notes: Optional[str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['side'] = self.side.value
        data['order_type'] = self.order_type.value
        data['product_type'] = self.product_type.value
        data['status'] = self.status.value
        return data

class BaseStrategy(ABC):
    """
    Enhanced base class for all trading strategies.
    Works with the new cleaned schema and microservices architecture.
    """
    
    def __init__(self, config_id: str, user_id: str, strategy_id: Optional[str],
                 config: Dict[str, Any]):
        # Strategy identification
        self.config_id = config_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.config = config
        
        # Core services
        self.redis_client: Optional[aioredis.Redis] = None
        self.notification_service: Optional[NotificationService] = None
        
        # Strategy state
        self.is_running = False
        self.is_paused = False
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        
        # Performance tracking
        self.total_pnl = Decimal('0')
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = Decimal('0')
        self.peak_pnl = Decimal('0')
        
        # Strategy metrics for the new schema
        self.metrics = {
            'start_time': None,
            'last_update': None,
            'total_signals': 0,
            'executed_trades': 0,
            'portfolio_value': 0,
            'success_rate': 0,
            'positions_count': 0,
            'orders_count': 0,
            'custom_metrics': {}
        }
        
        # Subscribed instruments
        self.subscribed_symbols: List[str] = []
        
        # Execution settings
        self.execution_interval = config.get('execution_interval', 5)  # seconds
        self.capital_allocated = config.get('capital_allocated', 100000)  # ₹1,00,000
        self.max_positions = config.get('max_positions', 5)
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # 2%
        
        # Strategy parameters (for compatibility with existing strategies)
        self.parameters = config.get('parameters', {})
        
    async def initialize(self):
        """Initialize strategy with new schema components"""
        try:
            # Get Redis client
            self.redis_client = await get_database_manager().get_redis()
            
            # Initialize notification service
            self.notification_service = NotificationService()
            await self.notification_service.initialize()
            
            # Load existing positions and orders from database
            await self._load_existing_positions()
            await self._load_existing_orders()
            
            # Strategy-specific initialization
            await self.on_initialize()
            
            logger.info(f"Strategy {self.__class__.__name__} initialized successfully")
            
        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            raise
    
    @abstractmethod
    async def on_initialize(self):
        """Strategy-specific initialization - implement in subclass"""
        pass
    
    @abstractmethod
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Handle market data updates - implement in subclass"""
        pass
    
    @abstractmethod
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals - implement in subclass"""
        pass
    
    async def execute(self):
        """Main execution method called by the strategy executor"""
        try:
            if self.is_paused:
                return
                
            # Update market data
            await self.update_market_data()
            
            # Generate trading signals
            signals = await self.generate_signals()
            
            # Execute signals
            for signal in signals:
                await self.execute_signal(signal)
            
            # Update performance metrics
            await self.update_metrics()
            
            # Custom strategy logic hook
            await self.on_strategy_iteration()
            
            # Update last execution time
            self.metrics['last_update'] = datetime_now()
            
        except Exception as e:
            logger.error(f"Strategy execution error: {e}")
            await self._handle_execution_error(e)
    
    async def update_market_data(self):
        """Update market data for subscribed instruments"""
        for symbol in self.subscribed_symbols:
            try:
                # Get market data from Redis
                market_key = RedisKeys.MARKET_DATA.format(symbol=symbol, exchange="NSE")
                market_data = await self.redis_client.get(market_key)
                
                if market_data:
                    data = json.loads(market_data)
                    await self.on_market_data(symbol, data)
                    
            except Exception as e:
                logger.error(f"Market data update error for {symbol}: {e}")
    
    async def execute_signal(self, signal: Dict[str, Any]):
        """Execute a trading signal using the new schema"""
        try:
            signal_type = signal.get('type')
            symbol = signal.get('symbol')
            exchange = signal.get('exchange', 'NSE')
            quantity = signal.get('quantity', 0)
            price = signal.get('price')
            order_type = signal.get('order_type', 'MARKET')
            product_type = signal.get('product_type', 'INTRADAY')
            
            if signal_type == 'BUY':
                await self.place_buy_order(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    price=price,
                    order_type=order_type,
                    product_type=product_type
                )
                
            elif signal_type == 'SELL':
                await self.place_sell_order(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    price=price,
                    order_type=order_type,
                    product_type=product_type
                )
                
            elif signal_type == 'EXIT':
                await self.exit_position(symbol, exchange)
            
            self.metrics['total_signals'] += 1
            
        except Exception as e:
            logger.error(f"Signal execution error: {e}")
            raise
    
    async def place_buy_order(self, symbol: str, exchange: str, quantity: int,
                            price: Optional[float] = None, 
                            order_type: str = 'MARKET',
                            product_type: str = 'INTRADAY') -> str:
        """Place a buy order using the new schema"""
        try:
            order_id = f"ord_{int(datetime_now().timestamp() * 1000)}"
            
            # Insert order into database
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    INSERT INTO orders 
                    (id, user_id, strategy_id, symbol, exchange, side, order_type, 
                     product_type, quantity, price, status, filled_quantity, 
                     tags, created_at, updated_at)
                    VALUES (:id, :user_id, :strategy_id, :symbol, :exchange, :side, 
                            :order_type, :product_type, :quantity, :price, :status, 
                            :filled_quantity, :tags, NOW(), NOW())
                """), {
                    "id": order_id,
                    "user_id": self.user_id,
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "side": "BUY",
                    "order_type": order_type,
                    "product_type": product_type,
                    "quantity": quantity,
                    "price": price,
                    "status": "PENDING",
                    "filled_quantity": 0,
                    "tags": json.dumps([f"strategy_{self.config_id}"])
                })
                await session.commit()
            
            # Create order object
            order = Order(
                id=order_id,
                user_id=self.user_id,
                strategy_id=self.strategy_id,
                symbol=symbol,
                exchange=exchange,
                side=OrderSide.BUY,
                order_type=OrderType(order_type),
                product_type=ProductType(product_type),
                quantity=quantity,
                price=price,
                trigger_price=None,
                broker_order_id=None,
                status=OrderStatus.PENDING,
                status_message=None,
                filled_quantity=0,
                average_price=None,
                tags=[f"strategy_{self.config_id}"],
                notes=None,
                created_at=datetime_now()
            )
            
            self.orders[order_id] = order
            
            # Send notification
            await self.notification_service.send_realtime_notification(
                user_id=self.user_id,
                type="ORDER_PLACED",
                title="Buy Order Placed",
                message=f"Buy order for {quantity} shares of {symbol} placed",
                data={
                    "order_id": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "strategy_id": self.strategy_id
                }
            )
            
            # Simulate order execution for now
            await self.simulate_order_execution(order)
            
            return order_id
            
        except Exception as e:
            logger.error(f"Buy order placement failed: {e}")
            raise
    
    async def place_sell_order(self, symbol: str, exchange: str, quantity: int,
                             price: Optional[float] = None, 
                             order_type: str = 'MARKET',
                             product_type: str = 'INTRADAY') -> str:
        """Place a sell order using the new schema"""
        try:
            order_id = f"ord_{int(datetime_now().timestamp() * 1000)}"
            
            # Insert order into database
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    INSERT INTO orders 
                    (id, user_id, strategy_id, symbol, exchange, side, order_type, 
                     product_type, quantity, price, status, filled_quantity, 
                     tags, created_at, updated_at)
                    VALUES (:id, :user_id, :strategy_id, :symbol, :exchange, :side, 
                            :order_type, :product_type, :quantity, :price, :status, 
                            :filled_quantity, :tags, NOW(), NOW())
                """), {
                    "id": order_id,
                    "user_id": self.user_id,
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "side": "SELL",
                    "order_type": order_type,
                    "product_type": product_type,
                    "quantity": quantity,
                    "price": price,
                    "status": "PENDING",
                    "filled_quantity": 0,
                    "tags": json.dumps([f"strategy_{self.config_id}"])
                })
                await session.commit()
            
            # Create order object
            order = Order(
                id=order_id,
                user_id=self.user_id,
                strategy_id=self.strategy_id,
                symbol=symbol,
                exchange=exchange,
                side=OrderSide.SELL,
                order_type=OrderType(order_type),
                product_type=ProductType(product_type),
                quantity=quantity,
                price=price,
                trigger_price=None,
                broker_order_id=None,
                status=OrderStatus.PENDING,
                status_message=None,
                filled_quantity=0,
                average_price=None,
                tags=[f"strategy_{self.config_id}"],
                notes=None,
                created_at=datetime_now()
            )
            
            self.orders[order_id] = order
            
            # Send notification
            await self.notification_service.send_realtime_notification(
                user_id=self.user_id,
                type="ORDER_PLACED",
                title="Sell Order Placed",
                message=f"Sell order for {quantity} shares of {symbol} placed",
                data={
                    "order_id": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "strategy_id": self.strategy_id
                }
            )
            
            # Simulate order execution for now
            await self.simulate_order_execution(order)
            
            return order_id
            
        except Exception as e:
            logger.error(f"Sell order placement failed: {e}")
            raise
    
    async def simulate_order_execution(self, order: Order):
        """Simulate order execution (replace with actual broker integration)"""
        try:
            # Simulate execution delay
            await asyncio.sleep(1)
            
            # Get current price from market data
            current_price = await self.get_current_price(order.symbol, order.exchange)
            if not current_price:
                current_price = order.price or 100.0  # Fallback price
            
            # Update order status
            order.status = OrderStatus.COMPLETE
            order.filled_quantity = order.quantity
            order.average_price = current_price
            
            # Update in database
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    UPDATE orders 
                    SET status = :status, filled_quantity = :filled_quantity, 
                        average_price = :average_price, executed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :order_id
                """), {
                    "status": order.status.value,
                    "filled_quantity": order.filled_quantity,
                    "average_price": order.average_price,
                    "order_id": order.id
                })
                await session.commit()
            
            # Update position
            await self.update_position(order)
            
            # Send execution notification
            await self.notification_service.send_realtime_notification(
                user_id=self.user_id,
                type="ORDER_EXECUTED",
                title="Order Executed",
                message=f"{order.side.value} order for {order.quantity} shares of {order.symbol} executed at ₹{current_price}",
                data={
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "quantity": order.quantity,
                    "price": current_price,
                    "strategy_id": self.strategy_id
                }
            )
            
            self.metrics['executed_trades'] += 1
            
        except Exception as e:
            logger.error(f"Order execution simulation failed: {e}")
            raise
    
    async def update_position(self, order: Order):
        """Update position based on order execution"""
        try:
            position_key = f"{order.symbol}_{order.exchange}_{order.product_type.value}"
            
            if position_key in self.positions:
                # Update existing position
                position = self.positions[position_key]
                
                if order.side == OrderSide.BUY:
                    # Add to position
                    total_cost = (position.quantity * position.average_price) + (order.quantity * order.average_price)
                    total_quantity = position.quantity + order.quantity
                    position.average_price = total_cost / total_quantity if total_quantity > 0 else 0
                    position.quantity = total_quantity
                    
                else:  # SELL
                    # Reduce position
                    if order.quantity >= position.quantity:
                        # Position closed
                        realized_pnl = (order.average_price - position.average_price) * position.quantity
                        position.realized_pnl += realized_pnl
                        position.quantity = 0
                        self.total_pnl += Decimal(str(realized_pnl))
                        
                        if realized_pnl > 0:
                            self.winning_trades += 1
                        else:
                            self.losing_trades += 1
                    else:
                        # Partial exit
                        realized_pnl = (order.average_price - position.average_price) * order.quantity
                        position.realized_pnl += realized_pnl
                        position.quantity -= order.quantity
                        self.total_pnl += Decimal(str(realized_pnl))
                
            else:
                # Create new position (only for BUY orders)
                if order.side == OrderSide.BUY:
                    position_id = f"pos_{int(datetime_now().timestamp() * 1000)}"
                    
                    position = Position(
                        id=position_id,
                        user_id=self.user_id,
                        symbol=order.symbol,
                        exchange=order.exchange,
                        product_type=order.product_type,
                        quantity=order.quantity,
                        average_price=order.average_price,
                        last_traded_price=order.average_price,
                        pnl=0,
                        realized_pnl=0,
                        market_value=order.quantity * order.average_price,
                        day_change=0,
                        day_change_pct=0
                    )
                    
                    self.positions[position_key] = position
            
            # Update position in database
            if position_key in self.positions:
                await self._update_position_in_db(self.positions[position_key])
            
        except Exception as e:
            logger.error(f"Position update failed: {e}")
            raise
    
    async def _update_position_in_db(self, position: Position):
        """Update position in database"""
        try:
            async with get_database_manager().get_async_session() as session:
                # Check if position exists
                result = await session.execute(text("""
                    SELECT id FROM positions 
                    WHERE user_id = :user_id AND symbol = :symbol 
                    AND exchange = :exchange AND product_type = :product_type
                """), {
                    "user_id": position.user_id,
                    "symbol": position.symbol,
                    "exchange": position.exchange,
                    "product_type": position.product_type.value
                })
                
                existing = result.fetchone()
                
                if existing:
                    # Update existing position
                    await session.execute(text("""
                        UPDATE positions 
                        SET quantity = :quantity, average_price = :average_price,
                            last_traded_price = :last_traded_price, pnl = :pnl,
                            realized_pnl = :realized_pnl, market_value = :market_value,
                            updated_at = NOW()
                        WHERE id = :id
                    """), {
                        "quantity": position.quantity,
                        "average_price": position.average_price,
                        "last_traded_price": position.last_traded_price,
                        "pnl": position.pnl,
                        "realized_pnl": position.realized_pnl,
                        "market_value": position.market_value,
                        "id": existing.id
                    })
                else:
                    # Insert new position
                    await session.execute(text("""
                        INSERT INTO positions 
                        (id, user_id, symbol, exchange, product_type, quantity, 
                         average_price, last_traded_price, pnl, realized_pnl, 
                         market_value, day_change, day_change_pct, created_at, updated_at)
                        VALUES (:id, :user_id, :symbol, :exchange, :product_type, 
                                :quantity, :average_price, :last_traded_price, :pnl, 
                                :realized_pnl, :market_value, :day_change, 
                                :day_change_pct, NOW(), NOW())
                    """), {
                        "id": position.id,
                        "user_id": position.user_id,
                        "symbol": position.symbol,
                        "exchange": position.exchange,
                        "product_type": position.product_type.value,
                        "quantity": position.quantity,
                        "average_price": position.average_price,
                        "last_traded_price": position.last_traded_price,
                        "pnl": position.pnl,
                        "realized_pnl": position.realized_pnl,
                        "market_value": position.market_value,
                        "day_change": position.day_change,
                        "day_change_pct": position.day_change_pct
                    })
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Database position update failed: {e}")
            raise
    
    async def get_current_price(self, symbol: str, exchange: str) -> Optional[float]:
        """Get current market price from Redis"""
        try:
            market_key = RedisKeys.MARKET_DATA.format(symbol=symbol, exchange=exchange)
            market_data = await self.redis_client.get(market_key)
            
            if market_data:
                data = json.loads(market_data)
                return data.get('ltp') or data.get('close') or data.get('last_price')
            
            return None
            
        except Exception as e:
            logger.error(f"Price fetch error for {symbol}: {e}")
            return None
    
    async def _load_existing_positions(self):
        """Load existing positions from database"""
        try:
            async with get_database_manager().get_async_session() as session:
                result = await session.execute(text("""
                    SELECT * FROM positions 
                    WHERE "userId" = :user_id AND quantity > 0
                """), {"user_id": self.user_id})
                
                for row in result.fetchall():
                    position = Position(
                        id=row.id,
                        user_id=row.user_id,
                        symbol=row.symbol,
                        exchange=row.exchange,
                        product_type=ProductType(row.product_type),
                        quantity=row.quantity,
                        average_price=row.average_price,
                        last_traded_price=row.last_traded_price,
                        pnl=row.pnl,
                        realized_pnl=row.realized_pnl,
                        market_value=row.market_value,
                        day_change=row.day_change,
                        day_change_pct=row.day_change_pct
                    )
                    
                    position_key = f"{position.symbol}_{position.exchange}_{position.product_type.value}"
                    self.positions[position_key] = position
                    
        except Exception as e:
            logger.error(f"Failed to load existing positions: {e}")
    
    async def _load_existing_orders(self):
        """Load existing open orders from database"""
        try:
            async with get_database_manager().get_async_session() as session:
                result = await session.execute(text("""
                    SELECT * FROM orders 
                    WHERE "userId" = :user_id AND "strategyId" = :strategy_id
                    AND status IN ('PENDING', 'PLACED', 'OPEN')
                """), {"user_id": self.user_id, "strategy_id": self.strategy_id})
                
                for row in result.fetchall():
                    order = Order(
                        id=row.id,
                        user_id=row.user_id,
                        strategy_id=row.strategy_id,
                        symbol=row.symbol,
                        exchange=row.exchange,
                        side=OrderSide(row.side),
                        order_type=OrderType(row.order_type),
                        product_type=ProductType(row.product_type),
                        quantity=row.quantity,
                        price=row.price,
                        trigger_price=row.trigger_price,
                        broker_order_id=row.broker_order_id,
                        status=OrderStatus(row.status),
                        status_message=row.status_message,
                        filled_quantity=row.filled_quantity,
                        average_price=row.average_price,
                        tags=json.loads(row.tags) if row.tags else [],
                        notes=row.notes,
                        created_at=row.created_at
                    )
                    
                    self.orders[order.id] = order
                    
        except Exception as e:
            logger.error(f"Failed to load existing orders: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get strategy metrics for reporting to database"""
        portfolio_value = self.get_portfolio_value()
        total_trades = self.winning_trades + self.losing_trades
        success_rate = (self.winning_trades / total_trades) if total_trades > 0 else 0
        
        self.metrics.update({
            'portfolio_value': portfolio_value,
            'total_pnl': float(self.total_pnl),
            'success_rate': success_rate,
            'positions_count': len([p for p in self.positions.values() if p.quantity > 0]),
            'orders_count': len(self.orders),
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_trades': total_trades
        })
        
        return self.metrics
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        total_value = 0
        for position in self.positions.values():
            if position.quantity > 0:
                total_value += position.market_value
        return total_value
    
    async def exit_position(self, symbol: str, exchange: str):
        """Exit a position"""
        position_key = f"{symbol}_{exchange}_INTRADAY"  # Assuming INTRADAY
        
        if position_key in self.positions:
            position = self.positions[position_key]
            if position.quantity > 0:
                await self.place_sell_order(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=position.quantity,
                    order_type='MARKET',
                    product_type='INTRADAY'
                )
    
    async def subscribe_to_instruments(self, symbols: List[str]):
        """Subscribe to market data for instruments"""
        self.subscribed_symbols.extend(symbols)
        logger.info(f"Subscribed to instruments: {symbols}")
    
    async def update_metrics(self):
        """Update strategy metrics"""
        self.metrics['last_update'] = datetime_now()
        
        # Update P&L for open positions
        for position in self.positions.values():
            if position.quantity > 0:
                current_price = await self.get_current_price(position.symbol, position.exchange)
                if current_price:
                    position.last_traded_price = current_price
                    position.pnl = (current_price - position.average_price) * position.quantity
                    position.market_value = current_price * position.quantity
                    position.day_change = current_price - position.average_price
                    position.day_change_pct = (position.day_change / position.average_price) * 100
    
    async def _handle_execution_error(self, error: Exception):
        """Handle strategy execution errors"""
        await self.notification_service.send_realtime_notification(
            user_id=self.user_id,
            type="STRATEGY_ERROR",
            title="Strategy Execution Error",
            message=f"Strategy {self.__class__.__name__} encountered an error: {str(error)}",
            data={
                "strategy_id": self.strategy_id,
                "config_id": self.config_id,
                "error": str(error)
            }
        )
    
    async def pause(self):
        """Pause strategy execution"""
        self.is_paused = True
        logger.info(f"Strategy {self.__class__.__name__} paused")
    
    async def resume(self):
        """Resume strategy execution"""
        self.is_paused = False
        logger.info(f"Strategy {self.__class__.__name__} resumed")
    
    async def cleanup(self):
        """Cleanup strategy resources"""
        try:
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info(f"Strategy {self.__class__.__name__} cleanup completed")
            
        except Exception as e:
            logger.error(f"Strategy cleanup error: {e}")
    
    # Abstract methods that subclasses can override
    async def on_strategy_iteration(self):
        """Called after each strategy iteration - override in subclass"""
        pass
    
    async def on_order_filled(self, order: Order):
        """Called when an order is filled - override in subclass"""
        pass
    
    async def on_position_opened(self, position: Position):
        """Called when a new position is opened - override in subclass"""
        pass
    
    async def on_position_closed(self, position: Position, pnl: float):
        """Called when a position is closed - override in subclass"""
        pass 