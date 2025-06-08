"""
Live Trading Adapter - Unified interface for live trading operations

This adapter provides a high-level interface for live trading that abstracts
the complexity of broker interactions and provides a consistent API for
strategy execution with Angel One integration.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from app.models.base import (
    BrokerConfig, BrokerName, User, Order as DBOrder, Trade as DBTrade,
    Position as DBPosition, Balance as DBBalance, OrderSide, OrderType,
    ProductType, OrderStatus
)
from app.brokers.base import (
    BrokerRegistry, BrokerInterface, BrokerOrder, BrokerPosition, 
    BrokerBalance, BrokerTrade, MarketData, BrokerError,
    AuthenticationError, OrderError, InsufficientFundsError
)
from app.database import get_database_manager
from app.core.config import get_settings
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@dataclass
class TradingResult:
    """Result of a trading operation"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    broker_response: Optional[Dict] = None

@dataclass
class LiveOrderRequest:
    """Live order request structure"""
    symbol: str
    exchange: str = "NSE"
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    product_type: ProductType = ProductType.DELIVERY
    quantity: int = 1
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    variety: str = "NORMAL"
    strategy_id: Optional[str] = None
    user_id: Optional[str] = None

class LiveTradingAdapter:
    """
    Live Trading Adapter - Main interface for live trading operations
    
    This adapter provides a unified interface for:
    - Broker authentication and management
    - Order placement and management
    - Position and balance monitoring
    - Market data retrieval
    - Real-time trading operations
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        self._broker_instances: Dict[str, BrokerInterface] = {}
        self._authenticated_users: set = set()
        self._market_data_cache: Dict[str, MarketData] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        
    async def initialize(self) -> bool:
        """Initialize the live trading adapter"""
        try:
            await self.db_manager.initialize()
            logger.info("✅ Live Trading Adapter initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Live Trading Adapter: {e}")
            return False
    
    async def get_broker_for_user(self, user_id: str) -> Optional[BrokerInterface]:
        """Get authenticated broker instance for user"""
        if user_id in self._broker_instances:
            return self._broker_instances[user_id]
        
        async with self.db_manager.get_async_session() as session:
            # Get active broker config for user
            result = await session.execute(
                select(BrokerConfig).where(
                    and_(
                        BrokerConfig.user_id == user_id,
                        BrokerConfig.is_active == True
                    )
                )
            )
            broker_config = result.scalar_one_or_none()
            
            if not broker_config:
                logger.warning(f"No active broker configuration found for user {user_id}")
                return None
            
            try:
                # Get broker instance from registry
                broker = BrokerRegistry.get_broker(broker_config)
                
                # Authenticate if not already authenticated
                if not broker.is_authenticated:
                    auth_success = await broker.authenticate()
                    if not auth_success:
                        logger.error(f"Failed to authenticate broker for user {user_id}")
                        return None
                
                # Cache the authenticated broker
                self._broker_instances[user_id] = broker
                self._authenticated_users.add(user_id)
                
                logger.info(f"✅ Broker authenticated and cached for user {user_id}")
                return broker
                
            except Exception as e:
                logger.error(f"❌ Error setting up broker for user {user_id}: {e}")
                return None
    
    async def place_live_order(self, order_request: LiveOrderRequest) -> TradingResult:
        """
        Place a live order through the broker
        
        Args:
            order_request: Order details
            
        Returns:
            TradingResult: Result of the order placement
        """
        try:
            # Get broker instance
            broker = await self.get_broker_for_user(order_request.user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            # Create broker order
            broker_order = BrokerOrder(
                symbol=order_request.symbol,
                exchange=order_request.exchange,
                side=order_request.side,
                order_type=order_request.order_type,
                product_type=order_request.product_type,
                quantity=order_request.quantity,
                price=order_request.price,
                trigger_price=order_request.trigger_price,
                variety=order_request.variety
            )
            
            # Validate order before placing
            if not broker.validate_order(broker_order):
                return TradingResult(
                    success=False,
                    message="Order validation failed",
                    error_code="INVALID_ORDER"
                )
            
            # Place order with broker
            broker_order_id = await broker.place_order(broker_order)
            
            # Save order to database
            async with self.db_manager.get_async_session() as session:
                db_order = DBOrder(
                    user_id=order_request.user_id,
                    strategy_id=order_request.strategy_id,
                    symbol=order_request.symbol,
                    exchange=order_request.exchange,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    product_type=order_request.product_type,
                    quantity=order_request.quantity,
                    price=order_request.price,
                    trigger_price=order_request.trigger_price,
                    variety=order_request.variety,
                    broker_order_id=broker_order_id,
                    status=OrderStatus.PLACED,
                    placed_at=datetime.utcnow()
                )
                
                session.add(db_order)
                await session.commit()
                await session.refresh(db_order)
                
                logger.info(f"✅ Order placed successfully: {broker_order_id}")
                
                return TradingResult(
                    success=True,
                    message="Order placed successfully",
                    data={
                        "order_id": db_order.id,
                        "broker_order_id": broker_order_id,
                        "symbol": order_request.symbol,
                        "quantity": order_request.quantity,
                        "side": order_request.side.value
                    }
                )
                
        except InsufficientFundsError as e:
            logger.warning(f"Insufficient funds for order: {e}")
            return TradingResult(
                success=False,
                message="Insufficient funds",
                error_code="INSUFFICIENT_FUNDS",
                broker_response=e.broker_response
            )
            
        except OrderError as e:
            logger.error(f"Order error: {e}")
            return TradingResult(
                success=False,
                message=str(e),
                error_code="ORDER_ERROR",
                broker_response=e.broker_response
            )
            
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            return TradingResult(
                success=False,
                message=f"Unexpected error: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def cancel_live_order(self, user_id: str, broker_order_id: str) -> TradingResult:
        """Cancel a live order"""
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            # Cancel order with broker
            cancel_success = await broker.cancel_order(broker_order_id)
            
            if cancel_success:
                # Update order status in database
                async with self.db_manager.get_async_session() as session:
                    result = await session.execute(
                        select(DBOrder).where(DBOrder.broker_order_id == broker_order_id)
                    )
                    db_order = result.scalar_one_or_none()
                    
                    if db_order:
                        db_order.status = OrderStatus.CANCELLED
                        db_order.cancelled_at = datetime.utcnow()
                        await session.commit()
                
                return TradingResult(
                    success=True,
                    message="Order cancelled successfully",
                    data={"broker_order_id": broker_order_id}
                )
            else:
                return TradingResult(
                    success=False,
                    message="Failed to cancel order",
                    error_code="CANCEL_FAILED"
                )
                
        except Exception as e:
            logger.error(f"Error cancelling order {broker_order_id}: {e}")
            return TradingResult(
                success=False,
                message=f"Error cancelling order: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def get_live_positions(self, user_id: str) -> TradingResult:
        """Get current positions from broker"""
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            positions = await broker.get_positions()
            
            # Convert to dictionary format
            positions_data = [pos.to_dict() for pos in positions]
            
            return TradingResult(
                success=True,
                message="Positions retrieved successfully",
                data={"positions": positions_data}
            )
            
        except Exception as e:
            logger.error(f"Error getting positions for user {user_id}: {e}")
            return TradingResult(
                success=False,
                message=f"Error getting positions: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def get_live_balance(self, user_id: str) -> TradingResult:
        """Get current balance from broker"""
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            balance = await broker.get_balance()
            
            return TradingResult(
                success=True,
                message="Balance retrieved successfully",
                data=balance.to_dict()
            )
            
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return TradingResult(
                success=False,
                message=f"Error getting balance: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def get_live_market_data(self, user_id: str, symbol: str, exchange: str = "NSE") -> TradingResult:
        """Get live market data for a symbol"""
        try:
            # Check cache first
            cache_key = f"{symbol}:{exchange}"
            if cache_key in self._market_data_cache:
                cached_data = self._market_data_cache[cache_key]
                cache_time = self._cache_expiry.get(cache_key, datetime.min)
                
                # Use cached data if less than 30 seconds old
                if datetime.utcnow() - cache_time < timedelta(seconds=30):
                    return TradingResult(
                        success=True,
                        message="Market data retrieved from cache",
                        data=cached_data.to_dict()
                    )
            
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            market_data = await broker.get_market_data(symbol, exchange)
            
            if market_data:
                # Cache the data
                self._market_data_cache[cache_key] = market_data
                self._cache_expiry[cache_key] = datetime.utcnow()
                
                return TradingResult(
                    success=True,
                    message="Market data retrieved successfully",
                    data=market_data.to_dict()
                )
            else:
                return TradingResult(
                    success=False,
                    message="Market data not available",
                    error_code="NO_DATA"
                )
                
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return TradingResult(
                success=False,
                message=f"Error getting market data: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def sync_orders_status(self, user_id: str) -> TradingResult:
        """Sync order status with broker"""
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No authenticated broker available",
                    error_code="NO_BROKER"
                )
            
            updated_orders = 0
            
            async with self.db_manager.get_async_session() as session:
                # Get pending orders
                result = await session.execute(
                    select(DBOrder).where(
                        and_(
                            DBOrder.user_id == user_id,
                            DBOrder.status.in_([OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.OPEN])
                        )
                    )
                )
                pending_orders = result.scalars().all()
                
                for db_order in pending_orders:
                    if db_order.broker_order_id:
                        try:
                            # Get order status from broker
                            broker_order = await broker.get_order_status(db_order.broker_order_id)
                            
                            # Update database if status changed
                            if broker_order.status and broker_order.status != db_order.status:
                                db_order.status = broker_order.status
                                db_order.filled_quantity = broker_order.filled_quantity
                                db_order.average_price = broker_order.average_price
                                db_order.status_message = broker_order.status_message
                                
                                if broker_order.status == OrderStatus.COMPLETE:
                                    db_order.executed_at = datetime.utcnow()
                                elif broker_order.status == OrderStatus.CANCELLED:
                                    db_order.cancelled_at = datetime.utcnow()
                                
                                updated_orders += 1
                                
                        except Exception as e:
                            logger.warning(f"Failed to sync order {db_order.broker_order_id}: {e}")
                
                await session.commit()
            
            return TradingResult(
                success=True,
                message=f"Order sync completed. Updated {updated_orders} orders",
                data={"updated_orders": updated_orders}
            )
            
        except Exception as e:
            logger.error(f"Error syncing orders for user {user_id}: {e}")
            return TradingResult(
                success=False,
                message=f"Error syncing orders: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            now = datetime.now()
            # Simple market hours check (9:15 AM to 3:30 PM IST on weekdays)
            if now.weekday() >= 5:  # Weekend
                return False
            
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    async def get_broker_health(self, user_id: str) -> TradingResult:
        """Check broker connection health"""
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                return TradingResult(
                    success=False,
                    message="No broker available",
                    error_code="NO_BROKER"
                )
            
            health_status = await broker.health_check()
            
            return TradingResult(
                success=True,
                message="Broker health check completed",
                data=health_status
            )
            
        except Exception as e:
            logger.error(f"Error checking broker health for user {user_id}: {e}")
            return TradingResult(
                success=False,
                message=f"Error checking broker health: {e}",
                error_code="SYSTEM_ERROR"
            )
    
    @asynccontextmanager
    async def trading_session(self, user_id: str):
        """Context manager for trading session with automatic cleanup"""
        broker = None
        try:
            broker = await self.get_broker_for_user(user_id)
            if not broker:
                raise Exception("Failed to get authenticated broker")
            
            logger.info(f"📈 Trading session started for user {user_id}")
            yield broker
            
        except Exception as e:
            logger.error(f"Error in trading session for user {user_id}: {e}")
            raise
        finally:
            if broker:
                try:
                    # Optional: Perform any cleanup
                    logger.info(f"🏁 Trading session ended for user {user_id}")
                except Exception as e:
                    logger.warning(f"Error during trading session cleanup: {e}")
    
    async def cleanup(self):
        """Cleanup adapter resources"""
        try:
            # Disconnect all broker instances
            for user_id, broker in self._broker_instances.items():
                try:
                    await broker.disconnect()
                    logger.info(f"Disconnected broker for user {user_id}")
                except Exception as e:
                    logger.warning(f"Error disconnecting broker for user {user_id}: {e}")
            
            self._broker_instances.clear()
            self._authenticated_users.clear()
            self._market_data_cache.clear()
            self._cache_expiry.clear()
            
            # Close database connections
            if self.db_manager:
                await self.db_manager.close()
            
            logger.info("✅ Live Trading Adapter cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during adapter cleanup: {e}")

# Global instance
live_trading_adapter = LiveTradingAdapter()

# Convenience functions for easy access
async def place_order(order_request: LiveOrderRequest) -> TradingResult:
    """Place a live order"""
    return await live_trading_adapter.place_live_order(order_request)

async def cancel_order(user_id: str, broker_order_id: str) -> TradingResult:
    """Cancel a live order"""
    return await live_trading_adapter.cancel_live_order(user_id, broker_order_id)

async def get_positions(user_id: str) -> TradingResult:
    """Get current positions"""
    return await live_trading_adapter.get_live_positions(user_id)

async def get_balance(user_id: str) -> TradingResult:
    """Get current balance"""
    return await live_trading_adapter.get_live_balance(user_id)

async def get_market_data(user_id: str, symbol: str, exchange: str = "NSE") -> TradingResult:
    """Get live market data"""
    return await live_trading_adapter.get_live_market_data(user_id, symbol, exchange) 