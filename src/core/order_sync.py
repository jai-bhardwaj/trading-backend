"""
Thread-Safe Order Management System
Prevents race conditions in order placement and status updates
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import uuid
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class OrderState(Enum):
    """Detailed order states for tracking"""
    CREATED = "CREATED"
    PENDING = "PENDING"
    PLACING = "PLACING"
    PLACED = "PLACED"
    FILLING = "FILLING"
    FILLED = "FILLED"
    REJECTING = "REJECTING"
    REJECTED = "REJECTED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"

@dataclass
class OrderTransaction:
    """Atomic order transaction record"""
    transaction_id: str
    order_id: str
    user_id: str
    action: str
    from_state: OrderState
    to_state: OrderState
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

class OrderStateMachine:
    """Thread-safe order state machine with transitions"""
    
    VALID_TRANSITIONS = {
        OrderState.CREATED: [OrderState.PENDING, OrderState.REJECTED],
        OrderState.PENDING: [OrderState.PLACING, OrderState.REJECTED, OrderState.CANCELLING],
        OrderState.PLACING: [OrderState.PLACED, OrderState.REJECTED],
        OrderState.PLACED: [OrderState.FILLING, OrderState.CANCELLING],
        OrderState.FILLING: [OrderState.FILLED, OrderState.REJECTED],
        OrderState.FILLED: [],  # Terminal state
        OrderState.REJECTING: [OrderState.REJECTED],
        OrderState.REJECTED: [],  # Terminal state
        OrderState.CANCELLING: [OrderState.CANCELLED],
        OrderState.CANCELLED: []  # Terminal state
    }
    
    def __init__(self):
        self.lock = threading.RLock()
        self.order_states: Dict[str, OrderState] = {}
        self.order_locks: Dict[str, asyncio.Lock] = {}
        self.transitions: List[OrderTransaction] = []
        
    async def get_order_lock(self, order_id: str) -> asyncio.Lock:
        """Get or create a lock for specific order"""
        if order_id not in self.order_locks:
            self.order_locks[order_id] = asyncio.Lock()
        return self.order_locks[order_id]
    
    def is_valid_transition(self, order_id: str, new_state: OrderState) -> bool:
        """Check if state transition is valid"""
        with self.lock:
            current_state = self.order_states.get(order_id, OrderState.CREATED)
            valid_next_states = self.VALID_TRANSITIONS.get(current_state, [])
            return new_state in valid_next_states
    
    async def transition_state(self, order_id: str, new_state: OrderState, 
                              user_id: str = "", metadata: Dict[str, Any] = None) -> bool:
        """Atomically transition order state"""
        async with await self.get_order_lock(order_id):
            with self.lock:
                current_state = self.order_states.get(order_id, OrderState.CREATED)
                
                if not self.is_valid_transition(order_id, new_state):
                    logger.warning(f"⚠️ Invalid state transition for order {order_id}: "
                                 f"{current_state} -> {new_state}")
                    return False
                
                # Record transition
                transaction = OrderTransaction(
                    transaction_id=str(uuid.uuid4()),
                    order_id=order_id,
                    user_id=user_id,
                    action=f"transition_{current_state.value}_to_{new_state.value}",
                    from_state=current_state,
                    to_state=new_state,
                    timestamp=datetime.now(),
                    metadata=metadata or {}
                )
                
                # Update state
                self.order_states[order_id] = new_state
                self.transitions.append(transaction)
                
                logger.debug(f"🔄 Order {order_id} transitioned: {current_state} -> {new_state}")
                return True
    
    def get_current_state(self, order_id: str) -> OrderState:
        """Get current state of order"""
        with self.lock:
            return self.order_states.get(order_id, OrderState.CREATED)
    
    def get_order_history(self, order_id: str) -> List[OrderTransaction]:
        """Get complete history of order state changes"""
        with self.lock:
            return [t for t in self.transitions if t.order_id == order_id]

class ThreadSafeOrderManager:
    """
    Thread-safe order manager that prevents race conditions
    Uses locks, state machines, and atomic operations
    """
    
    def __init__(self):
        # Thread synchronization
        self.global_lock = threading.RLock()
        self.user_locks: Dict[str, asyncio.Lock] = {}
        self.symbol_locks: Dict[str, asyncio.Lock] = {}
        
        # Order tracking with state machine
        self.state_machine = OrderStateMachine()
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.completed_orders: Dict[str, Dict[str, Any]] = {}
        
        # Duplicate prevention
        self.signal_order_tracking: Dict[str, Set[str]] = defaultdict(set)  # signal_id -> order_ids
        self.user_pending_orders: Dict[str, Set[str]] = defaultdict(set)   # user_id -> order_ids
        
        # Rate limiting and throttling
        self.user_last_order: Dict[str, float] = {}
        self.min_order_interval = 1.0  # Minimum 1 second between orders per user
        
        # Performance metrics
        self.race_conditions_prevented = 0
        self.duplicate_orders_prevented = 0
        self.concurrent_operations = 0
        
        logger.info("🔒 Thread-Safe Order Manager initialized")
    
    async def get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create lock for specific user"""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]
    
    async def get_symbol_lock(self, symbol: str) -> asyncio.Lock:
        """Get or create lock for specific symbol"""
        if symbol not in self.symbol_locks:
            self.symbol_locks[symbol] = asyncio.Lock()
        return self.symbol_locks[symbol]
    
    @asynccontextmanager
    async def atomic_order_operation(self, order_id: str, user_id: str = "", symbol: str = ""):
        """Context manager for atomic order operations"""
        # Acquire locks in consistent order to prevent deadlocks
        locks_to_acquire = []
        
        if order_id:
            locks_to_acquire.append(('order', await self.state_machine.get_order_lock(order_id)))
        if user_id:
            locks_to_acquire.append(('user', await self.get_user_lock(user_id)))
        if symbol:
            locks_to_acquire.append(('symbol', await self.get_symbol_lock(symbol)))
        
        # Sort locks to ensure consistent ordering
        locks_to_acquire.sort(key=lambda x: x[0])
        
        # Acquire all locks
        acquired_locks = []
        try:
            for lock_type, lock in locks_to_acquire:
                await lock.acquire()
                acquired_locks.append(lock)
            
            self.concurrent_operations += 1
            yield
            
        finally:
            # Release locks in reverse order
            for lock in reversed(acquired_locks):
                lock.release()
            self.concurrent_operations -= 1
    
    async def check_duplicate_order(self, signal_id: str, user_id: str, symbol: str, side: str) -> bool:
        """Check if this order would be a duplicate"""
        # Create unique order signature
        order_signature = f"{signal_id}:{user_id}:{symbol}:{side}"
        
        with self.global_lock:
            # Check if we already have orders for this signal from this user
            existing_orders = self.signal_order_tracking.get(signal_id, set())
            for order_id in existing_orders:
                if order_id in self.active_orders:
                    order = self.active_orders[order_id]
                    if (order['user_id'] == user_id and 
                        order['symbol'] == symbol and 
                        order['side'] == side):
                        
                        self.duplicate_orders_prevented += 1
                        logger.warning(f"🚫 Duplicate order prevented: {order_signature}")
                        return True
            
            return False
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        with self.global_lock:
            last_order_time = self.user_last_order.get(user_id, 0)
            if current_time - last_order_time < self.min_order_interval:
                logger.warning(f"🚫 Rate limit hit for user {user_id}")
                return False
            
            self.user_last_order[user_id] = current_time
            return True
    
    async def create_order_safely(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Create order with full race condition protection"""
        order_id = str(uuid.uuid4())
        user_id = order_data['user_id']
        symbol = order_data['symbol']
        signal_id = order_data.get('signal_id', '')
        
        async with self.atomic_order_operation(order_id, user_id, symbol):
            try:
                # Check for duplicates
                if await self.check_duplicate_order(signal_id, user_id, symbol, order_data['side']):
                    return None
                
                # Check rate limiting
                if not await self.check_rate_limit(user_id):
                    return None
                
                # Initialize order state
                if not await self.state_machine.transition_state(
                    order_id, OrderState.PENDING, user_id, 
                    metadata={'action': 'create_order'}
                ):
                    logger.error(f"❌ Failed to initialize order state for {order_id}")
                    return None
                
                # Add to tracking structures
                with self.global_lock:
                    self.active_orders[order_id] = {
                        'order_id': order_id,
                        'user_id': user_id,
                        'signal_id': signal_id,
                        'symbol': symbol,
                        'side': order_data['side'],
                        'quantity': order_data['quantity'],
                        'order_type': order_data.get('order_type', 'MARKET'),
                        'price': order_data.get('price'),
                        'created_at': datetime.now(),
                        'last_updated': datetime.now()
                    }
                    
                    # Track for duplicate prevention
                    if signal_id:
                        self.signal_order_tracking[signal_id].add(order_id)
                    self.user_pending_orders[user_id].add(order_id)
                
                logger.info(f"✅ Order created safely: {order_id} for user {user_id}")
                return order_id
                
            except Exception as e:
                logger.error(f"❌ Error creating order safely: {e}")
                return None
    
    async def update_order_status_safely(self, order_id: str, new_status: str, 
                                        metadata: Dict[str, Any] = None) -> bool:
        """Update order status with race condition protection"""
        
        # Map string status to OrderState
        status_mapping = {
            'PLACING': OrderState.PLACING,
            'PLACED': OrderState.PLACED,
            'FILLING': OrderState.FILLING,
            'FILLED': OrderState.FILLED,
            'REJECTED': OrderState.REJECTED,
            'CANCELLED': OrderState.CANCELLED
        }
        
        new_state = status_mapping.get(new_status)
        if not new_state:
            logger.error(f"❌ Invalid status: {new_status}")
            return False
        
        async with self.atomic_order_operation(order_id):
            try:
                # Update state machine
                if not await self.state_machine.transition_state(
                    order_id, new_state, 
                    metadata=metadata or {'action': f'update_status_to_{new_status}'}
                ):
                    self.race_conditions_prevented += 1
                    return False
                
                # Update order data
                with self.global_lock:
                    if order_id in self.active_orders:
                        self.active_orders[order_id]['status'] = new_status
                        self.active_orders[order_id]['last_updated'] = datetime.now()
                        
                        if metadata:
                            self.active_orders[order_id].update(metadata)
                        
                        # Move to completed if terminal state
                        if new_state in [OrderState.FILLED, OrderState.REJECTED, OrderState.CANCELLED]:
                            order_data = self.active_orders.pop(order_id)
                            self.completed_orders[order_id] = order_data
                            
                            # Clean up tracking
                            user_id = order_data['user_id']
                            signal_id = order_data.get('signal_id', '')
                            
                            self.user_pending_orders[user_id].discard(order_id)
                            if signal_id and signal_id in self.signal_order_tracking:
                                self.signal_order_tracking[signal_id].discard(order_id)
                
                logger.info(f"✅ Order status updated safely: {order_id} -> {new_status}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error updating order status: {e}")
                return False
    
    def get_order_safely(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order data safely"""
        with self.global_lock:
            return self.active_orders.get(order_id) or self.completed_orders.get(order_id)
    
    def get_user_orders_safely(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all orders for user safely"""
        with self.global_lock:
            orders = []
            
            # Active orders
            for order in self.active_orders.values():
                if order['user_id'] == user_id:
                    orders.append(order.copy())
            
            # Completed orders
            for order in self.completed_orders.values():
                if order['user_id'] == user_id:
                    orders.append(order.copy())
            
            return orders
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get thread safety statistics"""
        with self.global_lock:
            return {
                'active_orders': len(self.active_orders),
                'completed_orders': len(self.completed_orders),
                'race_conditions_prevented': self.race_conditions_prevented,
                'duplicate_orders_prevented': self.duplicate_orders_prevented,
                'concurrent_operations': self.concurrent_operations,
                'unique_signals_tracked': len(self.signal_order_tracking),
                'users_with_pending_orders': len([u for u in self.user_pending_orders.values() if u])
            }

# Global thread-safe order manager instance
_thread_safe_order_manager = None

def get_thread_safe_order_manager() -> ThreadSafeOrderManager:
    """Get global thread-safe order manager instance"""
    global _thread_safe_order_manager
    if _thread_safe_order_manager is None:
        _thread_safe_order_manager = ThreadSafeOrderManager()
    return _thread_safe_order_manager 