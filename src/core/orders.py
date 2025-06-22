"""
Multi-User Order Execution System
Handles signal fanout and order placement for multiple users
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

from .signals import TradingSignal, SignalAction
from .cache import EnterpriseUserStrategyCache, UserStrategyMapping  
from .events import EventBus, Event, EventType
from .database import get_db_manager
from .order_sync import get_thread_safe_order_manager, ThreadSafeOrderManager

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class UserOrder:
    """Individual user order"""
    order_id: str
    user_id: str
    strategy_id: str
    signal_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float]
    status: OrderStatus
    created_at: datetime
    broker_order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None
    error_message: Optional[str] = None

class MultiUserOrderExecutor:
    """
    Multi-user order execution engine
    Handles signal fanout to multiple users and order placement
    """
    
    def __init__(self, user_cache: EnterpriseUserStrategyCache, event_bus: EventBus, broker_manager):
        self.user_cache = user_cache
        self.event_bus = event_bus
        self.broker_manager = broker_manager
        self.db_manager = get_db_manager()
        
        # Thread-safe order management
        self.safe_order_manager = get_thread_safe_order_manager()
        
        # Legacy order tracking (for compatibility)
        self.pending_orders: Dict[str, UserOrder] = {}
        self.completed_orders: Dict[str, UserOrder] = {}
        
        # Performance metrics
        self.signals_processed = 0
        self.orders_created = 0
        self.orders_placed = 0
        self.orders_filled = 0
        self.orders_rejected = 0
        
        # Setup event handlers
        self._setup_event_handlers()
        
        logger.info("🎯 Multi-User Order Executor initialized with thread-safe manager")
    
    def _setup_event_handlers(self):
        """Setup event handlers for order lifecycle"""
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.ORDER_REJECTED, self._handle_order_rejected)
    
    async def process_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Process trading signal and fan out to all users with strategy enabled
        This is the CORE multi-user functionality
        """
        try:
            self.signals_processed += 1
            
            logger.info(f"📡 Processing signal: {signal.strategy.strategy_name} - {signal.symbol} {signal.action.value}")
            
            # Get all users with this strategy enabled
            strategy_users = await self.user_cache.get_strategy_users(signal.strategy.strategy_id)
            
            if not strategy_users:
                logger.info(f"⚠️ No users have strategy {signal.strategy.strategy_id} enabled")
                return {
                    'success': True,
                    'signal_id': signal.signal_id,
                    'users_found': 0,
                    'orders_created': 0
                }
            
            logger.info(f"🎯 Fanout: {len(strategy_users)} users have strategy {signal.strategy.strategy_id} enabled")
            
            # Create orders for each user
            user_orders = []
            for user_id in strategy_users:
                try:
                    user_order = await self._create_user_order(user_id, signal)
                    if user_order:
                        user_orders.append(user_order)
                        self.orders_created += 1
                except Exception as e:
                    logger.error(f"❌ Error creating order for user {user_id}: {e}")
            
            # Place orders concurrently for better performance
            if user_orders:
                await self._place_orders_concurrent(user_orders)
            
            return {
                'success': True,
                'signal_id': signal.signal_id,
                'users_found': len(strategy_users),
                'orders_created': len(user_orders),
                'orders_placed': sum(1 for order in user_orders if order.status == OrderStatus.PLACED)
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing signal {signal.signal_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'signal_id': signal.signal_id
            }
    
    async def _create_user_order(self, user_id: str, signal: TradingSignal) -> Optional[UserOrder]:
        """Create order for individual user with user-specific parameters (Thread-Safe)"""
        try:
            # Get user-specific strategy configuration
            user_config = await self.user_cache.get_user_strategy_config(
                user_id, signal.strategy.strategy_id
            )
            
            if not user_config or not user_config.enabled:
                logger.debug(f"⚠️ Strategy not enabled for user {user_id}")
                return None
            
            # Calculate user-specific quantity
            base_quantity = signal.quantity
            user_quantity = int(base_quantity * user_config.quantity_multiplier)
            
            # Apply position size limits
            if user_config.max_position_size:
                max_qty = int(user_config.max_position_size / (signal.order_spec.price or 100))
                user_quantity = min(user_quantity, max_qty)
            
            if user_quantity <= 0:
                logger.warning(f"⚠️ User {user_id} quantity calculated as {user_quantity}, skipping")
                return None
            
            # Create order safely using thread-safe manager
            order_data = {
                'user_id': user_id,
                'strategy_id': signal.strategy.strategy_id,
                'signal_id': signal.signal_id,
                'symbol': signal.symbol,
                'side': signal.action.value,
                'quantity': user_quantity,
                'order_type': signal.order_spec.order_type.value,
                'price': float(signal.order_spec.price) if signal.order_spec.price else None
            }
            
            # Use thread-safe order creation
            order_id = await self.safe_order_manager.create_order_safely(order_data)
            
            if not order_id:
                logger.warning(f"⚠️ Order creation prevented (duplicate/rate limit) for user {user_id}")
                return None
            
            # Create UserOrder object for return (maintaining compatibility)
            user_order = UserOrder(
                order_id=order_id,
                user_id=user_id,
                strategy_id=signal.strategy.strategy_id,
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                side=signal.action.value,
                quantity=user_quantity,
                order_type=signal.order_spec.order_type.value,
                price=float(signal.order_spec.price) if signal.order_spec.price else None,
                status=OrderStatus.PENDING,
                created_at=datetime.now()
            )
            
            # Store in legacy tracking for compatibility
            self.pending_orders[order_id] = user_order
            
            logger.info(f"📋 Created order safely for user {user_id}: {signal.symbol} {signal.action.value} {user_quantity}")
            
            return user_order
            
        except Exception as e:
            logger.error(f"❌ Error creating user order for {user_id}: {e}")
            return None
    
    async def _place_orders_concurrent(self, user_orders: List[UserOrder]):
        """Place multiple orders concurrently for better performance"""
        try:
            # Create tasks for concurrent order placement
            placement_tasks = []
            for order in user_orders:
                task = asyncio.create_task(self._place_single_order(order))
                placement_tasks.append(task)
            
            # Execute all order placements concurrently
            logger.info(f"🚀 Placing {len(user_orders)} orders concurrently...")
            await asyncio.gather(*placement_tasks, return_exceptions=True)
            
            # Log results
            placed_count = sum(1 for order in user_orders if order.status == OrderStatus.PLACED)
            rejected_count = sum(1 for order in user_orders if order.status == OrderStatus.REJECTED)
            
            logger.info(f"📊 Order placement complete: {placed_count} placed, {rejected_count} rejected")
            
        except Exception as e:
            logger.error(f"❌ Error in concurrent order placement: {e}")
    
    async def _place_single_order(self, user_order: UserOrder):
        """Place individual user order through broker (Thread-Safe)"""
        try:
            # Update to PLACING status safely
            placing_success = await self.safe_order_manager.update_order_status_safely(
                user_order.order_id, 'PLACING', {'action': 'starting_order_placement'}
            )
            
            if not placing_success:
                logger.warning(f"⚠️ Failed to update order {user_order.order_id} to PLACING status")
                return
            
            # Convert to broker order format
            broker_order = {
                'order_id': user_order.order_id,
                'user_id': user_order.user_id,
                'symbol': user_order.symbol,
                'side': user_order.side,
                'quantity': user_order.quantity,
                'order_type': user_order.order_type,
                'product_type': 'INTRADAY',  # Default to intraday
                'exchange': 'NSE'
            }
            
            if user_order.price:
                broker_order['price'] = user_order.price
            
            # Send order to broker through event system
            await self.event_bus.publish(Event(
                type=EventType.ORDER_PLACED,
                data=broker_order,
                source='order_executor'
            ))
            
            # Update order status to PLACED safely
            placed_success = await self.safe_order_manager.update_order_status_safely(
                user_order.order_id, 'PLACED', {
                    'action': 'order_sent_to_broker',
                    'broker_order': broker_order,
                    'placed_at': datetime.now()
                }
            )
            
            if placed_success:
                # Update legacy tracking
                user_order.status = OrderStatus.PLACED
                self.orders_placed += 1
                
                logger.info(f"📤 Order placed safely for user {user_order.user_id}: {user_order.symbol} {user_order.side} {user_order.quantity}")
                
                # Store in database for audit
                await self._store_order_in_db(user_order)
            else:
                logger.error(f"❌ Failed to update order {user_order.order_id} to PLACED status")
            
        except Exception as e:
            logger.error(f"❌ Error placing order {user_order.order_id}: {e}")
            
            # Update to REJECTED status safely
            await self.safe_order_manager.update_order_status_safely(
                user_order.order_id, 'REJECTED', {
                    'error_message': str(e),
                    'failed_at': datetime.now()
                }
            )
            
            # Update legacy tracking
            user_order.status = OrderStatus.REJECTED
            user_order.error_message = str(e)
            self.orders_rejected += 1
    
    async def _handle_order_filled(self, event: Event):
        """Handle order fill notification from broker (Thread-Safe)"""
        try:
            fill_data = event.data
            order_id = fill_data.get('order_id')
            
            # Use thread-safe status update
            metadata = {
                'broker_order_id': fill_data.get('broker_order_id'),
                'filled_price': fill_data.get('fill_price'),
                'filled_at': datetime.now()
            }
            
            success = await self.safe_order_manager.update_order_status_safely(
                order_id, 'FILLED', metadata
            )
            
            if success:
                # Update legacy tracking for compatibility
                if order_id in self.pending_orders:
                    user_order = self.pending_orders[order_id]
                    user_order.status = OrderStatus.FILLED
                    user_order.broker_order_id = fill_data.get('broker_order_id')
                    user_order.filled_price = fill_data.get('fill_price')
                    user_order.filled_at = datetime.now()
                    
                    # Move to completed orders
                    self.completed_orders[order_id] = user_order
                    del self.pending_orders[order_id]
                    
                    self.orders_filled += 1
                    
                    logger.info(f"✅ Order filled safely for user {user_order.user_id}: {user_order.symbol} @ ₹{user_order.filled_price:.2f}")
                    
                    # Update database
                    await self._update_order_in_db(user_order)
            else:
                logger.warning(f"⚠️ Failed to update order {order_id} to FILLED status")
                
        except Exception as e:
            logger.error(f"❌ Error handling order fill: {e}")
    
    async def _handle_order_rejected(self, event: Event):
        """Handle order rejection notification from broker (Thread-Safe)"""
        try:
            reject_data = event.data
            order_id = reject_data.get('order_id')
            
            # Use thread-safe status update
            metadata = {
                'error_message': reject_data.get('reason', 'Unknown error'),
                'rejected_at': datetime.now()
            }
            
            success = await self.safe_order_manager.update_order_status_safely(
                order_id, 'REJECTED', metadata
            )
            
            if success:
                # Update legacy tracking for compatibility
                if order_id in self.pending_orders:
                    user_order = self.pending_orders[order_id]
                    user_order.status = OrderStatus.REJECTED
                    user_order.error_message = reject_data.get('reason', 'Unknown error')
                    
                    # Move to completed orders
                    self.completed_orders[order_id] = user_order
                    del self.pending_orders[order_id]
                    
                    self.orders_rejected += 1
                    
                    logger.warning(f"❌ Order rejected safely for user {user_order.user_id}: {user_order.symbol} - {user_order.error_message}")
                    
                    # Update database
                    await self._update_order_in_db(user_order)
            else:
                logger.warning(f"⚠️ Failed to update order {order_id} to REJECTED status")
                
        except Exception as e:
            logger.error(f"❌ Error handling order rejection: {e}")
    
    async def _store_order_in_db(self, user_order: UserOrder):
        """Store order in database for audit trail"""
        try:
            session = self.db_manager.get_session()
            
            # Insert into order_executions table
            insert_sql = """
                INSERT INTO order_executions (
                    order_id, user_id, strategy_id, signal_id, symbol, 
                    side, quantity, order_type, price, status, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            session.execute(insert_sql, (
                user_order.order_id,
                user_order.user_id,
                user_order.strategy_id,
                user_order.signal_id,
                user_order.symbol,
                user_order.side,
                user_order.quantity,
                user_order.order_type,
                user_order.price,
                user_order.status.value,
                user_order.created_at
            ))
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"❌ Error storing order in database: {e}")
    
    async def _update_order_in_db(self, user_order: UserOrder):
        """Update order status in database"""
        try:
            session = self.db_manager.get_session()
            
            update_sql = """
                UPDATE order_executions 
                SET status = %s, broker_order_id = %s, filled_price = %s, 
                    filled_at = %s, error_message = %s
                WHERE order_id = %s
            """
            
            session.execute(update_sql, (
                user_order.status.value,
                user_order.broker_order_id,
                user_order.filled_price,
                user_order.filled_at,
                user_order.error_message,
                user_order.order_id
            ))
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"❌ Error updating order in database: {e}")
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order execution statistics"""
        return {
            'signals_processed': self.signals_processed,
            'orders_created': self.orders_created,
            'orders_placed': self.orders_placed,
            'orders_filled': self.orders_filled,
            'orders_rejected': self.orders_rejected,
            'pending_orders': len(self.pending_orders),
            'completed_orders': len(self.completed_orders),
            'success_rate': (self.orders_filled / max(1, self.orders_placed)) * 100
        }
    
    def get_user_orders(self, user_id: str) -> List[UserOrder]:
        """Get all orders for specific user"""
        user_orders = []
        
        # Add pending orders
        for order in self.pending_orders.values():
            if order.user_id == user_id:
                user_orders.append(order)
        
        # Add completed orders
        for order in self.completed_orders.values():
            if order.user_id == user_id:
                user_orders.append(order)
        
        return sorted(user_orders, key=lambda x: x.created_at, reverse=True)
    
    async def cancel_pending_orders(self, user_id: str = None) -> int:
        """Cancel pending orders (optionally for specific user)"""
        cancelled_count = 0
        
        orders_to_cancel = []
        for order in self.pending_orders.values():
            if user_id is None or order.user_id == user_id:
                orders_to_cancel.append(order)
        
        for order in orders_to_cancel:
            order.status = OrderStatus.CANCELLED
            self.completed_orders[order.order_id] = order
            del self.pending_orders[order.order_id]
            cancelled_count += 1
            
            # Update database
            await self._update_order_in_db(order)
        
        if cancelled_count > 0:
            logger.info(f"🛑 Cancelled {cancelled_count} pending orders" + 
                       (f" for user {user_id}" if user_id else ""))
        
        return cancelled_count

class OrderManager:
    """
    Simple order manager - legacy interface for compatibility
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.orders = {}
        logger.info("📋 Order Manager initialized")
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order through event system"""
        try:
            order_id = str(uuid.uuid4())
            order_data['order_id'] = order_id
            
            # Publish order event
            await self.event_bus.publish(Event(
                type=EventType.ORDER_PLACED,
                data=order_data,
                source='order_manager'
            ))
            
            # Store order
            self.orders[order_id] = {
                **order_data,
                'status': 'PENDING',
                'created_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'order_id': order_id,
                'message': 'Order placed successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_all_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all orders"""
        return self.orders.copy() 