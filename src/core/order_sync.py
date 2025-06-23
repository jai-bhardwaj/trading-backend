"""
Thread-Safe Order Management System

This module provides thread-safe order management to prevent race conditions
in concurrent order operations. It includes:
- Order state machine with valid transitions
- Thread-safe operations with proper locking
- Duplicate order prevention
- Rate limiting between orders
- Atomic operations with consistent lock ordering
"""

import threading
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class OrderState(Enum):
    """Valid order states with controlled transitions"""
    PENDING = "pending"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class OrderRequest:
    """Thread-safe order request structure"""
    user_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    signal_id: Optional[str] = None
    strategy_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Generate unique signal_id if not provided"""
        if not self.signal_id:
            # Create deterministic signal_id based on order details
            content = f"{self.user_id}:{self.symbol}:{self.side}:{self.quantity}:{self.timestamp}"
            self.signal_id = hashlib.md5(content.encode()).hexdigest()[:16]

@dataclass
class Order:
    """Thread-safe order object"""
    order_id: str
    request: OrderRequest
    state: OrderState = OrderState.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error_message: Optional[str] = None
    broker_order_id: Optional[str] = None
    
    def update_state(self, new_state: OrderState, error_message: Optional[str] = None):
        """Update order state with timestamp"""
        self.state = new_state
        self.updated_at = time.time()
        if error_message:
            self.error_message = error_message

class OrderSyncManager:
    """
    Thread-safe order management system that prevents race conditions
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        OrderState.PENDING: [OrderState.VALIDATED, OrderState.REJECTED, OrderState.ERROR],
        OrderState.VALIDATED: [OrderState.SUBMITTED, OrderState.REJECTED, OrderState.ERROR],
        OrderState.SUBMITTED: [OrderState.FILLED, OrderState.PARTIALLY_FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.ERROR],
        OrderState.PARTIALLY_FILLED: [OrderState.FILLED, OrderState.CANCELLED, OrderState.ERROR],
        OrderState.FILLED: [],  # Terminal state
        OrderState.CANCELLED: [],  # Terminal state
        OrderState.REJECTED: [],  # Terminal state
        OrderState.EXPIRED: [],  # Terminal state
        OrderState.ERROR: []  # Terminal state
    }
    
    def __init__(self, min_order_interval: float = 1.0, max_orders_per_minute: int = 60):
        """
        Initialize thread-safe order manager
        
        Args:
            min_order_interval: Minimum seconds between orders from same user
            max_orders_per_minute: Maximum orders per minute per user
        """
        # Thread synchronization
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._order_locks: Dict[str, threading.Lock] = {}  # Per-order locks
        
        # Order storage
        self._orders: Dict[str, Order] = {}  # order_id -> Order
        self._user_orders: Dict[str, List[str]] = defaultdict(list)  # user_id -> [order_ids]
        self._signal_orders: Dict[str, str] = {}  # signal_id -> order_id
        
        # Rate limiting
        self.min_order_interval = min_order_interval
        self.max_orders_per_minute = max_orders_per_minute
        self._user_last_order: Dict[str, float] = {}  # user_id -> timestamp
        self._user_order_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_orders_per_minute))
        
        # Transaction log for audit
        self._transaction_log: List[Dict[str, Any]] = []
        self._log_lock = threading.Lock()
        
        # Order ID counter
        self._order_counter = 0
        self._counter_lock = threading.Lock()
        
    def _generate_order_id(self) -> str:
        """Generate unique order ID in thread-safe manner"""
        with self._counter_lock:
            self._order_counter += 1
            return f"ORD_{int(time.time())}_{self._order_counter:06d}"
    
    def _get_order_lock(self, order_id: str) -> threading.Lock:
        """Get or create thread lock for specific order"""
        with self._lock:
            if order_id not in self._order_locks:
                self._order_locks[order_id] = threading.Lock()
            return self._order_locks[order_id]
    
    def _log_transaction(self, action: str, order_id: str, details: Dict[str, Any]):
        """Log transaction for audit trail"""
        with self._log_lock:
            self._transaction_log.append({
                'timestamp': time.time(),
                'action': action,
                'order_id': order_id,
                'details': details,
                'thread_id': threading.get_ident()
            })
            
            # Keep only last 10000 transactions to prevent memory growth
            if len(self._transaction_log) > 10000:
                self._transaction_log = self._transaction_log[-5000:]
    
    def _check_rate_limits(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user can place order based on rate limits
        
        Returns:
            (can_place_order, error_message)
        """
        current_time = time.time()
        
        # Check minimum interval between orders
        if user_id in self._user_last_order:
            time_since_last = current_time - self._user_last_order[user_id]
            if time_since_last < self.min_order_interval:
                return False, f"Must wait {self.min_order_interval - time_since_last:.1f} seconds between orders"
        
        # Check orders per minute limit
        user_history = self._user_order_history[user_id]
        # Remove orders older than 1 minute
        while user_history and current_time - user_history[0] > 60:
            user_history.popleft()
        
        if len(user_history) >= self.max_orders_per_minute:
            return False, f"Maximum {self.max_orders_per_minute} orders per minute exceeded"
        
        return True, ""
    
    def _validate_order_request(self, request: OrderRequest) -> Tuple[bool, str]:
        """
        Validate order request
        
        Returns:
            (is_valid, error_message)
        """
        # Basic validation
        if not request.user_id:
            return False, "User ID is required"
        
        if not request.symbol:
            return False, "Symbol is required"
        
        if request.side not in ['buy', 'sell']:
            return False, "Side must be 'buy' or 'sell'"
        
        if request.quantity <= 0:
            return False, "Quantity must be positive"
        
        if request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not request.price:
            return False, f"{request.order_type.value} orders require price"
        
        if request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not request.stop_price:
            return False, f"{request.order_type.value} orders require stop_price"
        
        if request.price and request.price <= 0:
            return False, "Price must be positive"
        
        if request.stop_price and request.stop_price <= 0:
            return False, "Stop price must be positive"
        
        return True, ""
    
    def _check_duplicate_order(self, request: OrderRequest) -> Tuple[bool, str]:
        """
        Check for duplicate orders based on signal_id
        
        Returns:
            (is_duplicate, existing_order_id)
        """
        if request.signal_id and request.signal_id in self._signal_orders:
            existing_order_id = self._signal_orders[request.signal_id]
            existing_order = self._orders.get(existing_order_id)
            
            if existing_order and existing_order.state not in [OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED]:
                return True, existing_order_id
        
        return False, ""
    
    def create_order(self, request: OrderRequest) -> Tuple[Optional[str], str]:
        """
        Create new order in thread-safe manner
        
        Args:
            request: OrderRequest object
            
        Returns:
            (order_id, error_message) - order_id is None if creation failed
        """
        try:
            with self._lock:
                # Validate order request
                is_valid, validation_error = self._validate_order_request(request)
                if not is_valid:
                    logger.warning(f"Order validation failed for user {request.user_id}: {validation_error}")
                    return None, validation_error
                
                # Check rate limits
                can_place, rate_limit_error = self._check_rate_limits(request.user_id)
                if not can_place:
                    logger.warning(f"Rate limit exceeded for user {request.user_id}: {rate_limit_error}")
                    return None, rate_limit_error
                
                # Check for duplicate orders
                is_duplicate, existing_order_id = self._check_duplicate_order(request)
                if is_duplicate:
                    error_msg = f"Duplicate order detected. Existing order: {existing_order_id}"
                    logger.warning(f"Duplicate order attempt by user {request.user_id}: {error_msg}")
                    return None, error_msg
                
                # Generate order ID and create order
                order_id = self._generate_order_id()
                order = Order(order_id=order_id, request=request)
                
                # Store order with all mappings
                self._orders[order_id] = order
                self._user_orders[request.user_id].append(order_id)
                if request.signal_id:
                    self._signal_orders[request.signal_id] = order_id
                
                # Update rate limiting
                current_time = time.time()
                self._user_last_order[request.user_id] = current_time
                self._user_order_history[request.user_id].append(current_time)
                
                # Log transaction
                self._log_transaction('ORDER_CREATED', order_id, {
                    'user_id': request.user_id,
                    'symbol': request.symbol,
                    'side': request.side,
                    'quantity': request.quantity,
                    'order_type': request.order_type.value,
                    'signal_id': request.signal_id
                })
                
                logger.info(f"Order created successfully: {order_id} for user {request.user_id}")
                return order_id, ""
                
        except Exception as e:
            error_msg = f"Failed to create order: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def update_order_state(self, order_id: str, new_state: OrderState, 
                          filled_quantity: Optional[float] = None,
                          average_price: Optional[float] = None,
                          broker_order_id: Optional[str] = None,
                          error_message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update order state in thread-safe manner
        
        Returns:
            (success, error_message)
        """
        try:
            order_lock = self._get_order_lock(order_id)
            with order_lock:
                order = self._orders.get(order_id)
                if not order:
                    return False, f"Order {order_id} not found"
                
                # Check if state transition is valid
                current_state = order.state
                if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
                    if current_state != new_state:  # Allow same state updates
                        return False, f"Invalid state transition from {current_state.value} to {new_state.value}"
                
                # Update order
                order.update_state(new_state, error_message)
                
                if filled_quantity is not None:
                    order.filled_quantity = filled_quantity
                
                if average_price is not None:
                    order.average_price = average_price
                
                if broker_order_id is not None:
                    order.broker_order_id = broker_order_id
                
                # Log transaction
                self._log_transaction('ORDER_UPDATED', order_id, {
                    'old_state': current_state.value,
                    'new_state': new_state.value,
                    'filled_quantity': filled_quantity,
                    'average_price': average_price,
                    'broker_order_id': broker_order_id,
                    'error_message': error_message
                })
                
                logger.info(f"Order {order_id} state updated: {current_state.value} -> {new_state.value}")
                return True, ""
                
        except Exception as e:
            error_msg = f"Failed to update order {order_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID in thread-safe manner"""
        with self._lock:
            return self._orders.get(order_id)
    
    def get_user_orders(self, user_id: str, states: Optional[List[OrderState]] = None) -> List[Order]:
        """Get all orders for user, optionally filtered by states"""
        with self._lock:
            order_ids = self._user_orders.get(user_id, [])
            orders = [self._orders[oid] for oid in order_ids if oid in self._orders]
            
            if states:
                orders = [order for order in orders if order.state in states]
            
            return sorted(orders, key=lambda x: x.created_at, reverse=True)
    
    def get_active_orders(self, user_id: Optional[str] = None) -> List[Order]:
        """Get all active (non-terminal) orders"""
        active_states = [OrderState.PENDING, OrderState.VALIDATED, OrderState.SUBMITTED, OrderState.PARTIALLY_FILLED]
        
        with self._lock:
            if user_id:
                return self.get_user_orders(user_id, active_states)
            else:
                return [order for order in self._orders.values() if order.state in active_states]
    
    def cancel_order(self, order_id: str, reason: str = "User cancellation") -> Tuple[bool, str]:
        """Cancel order if possible"""
        return self.update_order_state(order_id, OrderState.CANCELLED, error_message=reason)
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order management statistics"""
        with self._lock:
            state_counts = defaultdict(int)
            for order in self._orders.values():
                state_counts[order.state.value] += 1
            
            return {
                'total_orders': len(self._orders),
                'state_distribution': dict(state_counts),
                'active_orders': len(self.get_active_orders()),
                'users_with_orders': len(self._user_orders),
                'transaction_log_size': len(self._transaction_log),
                'rate_limit_config': {
                    'min_order_interval': self.min_order_interval,
                    'max_orders_per_minute': self.max_orders_per_minute
                }
            }
    
    def cleanup_old_orders(self, older_than_hours: int = 24) -> int:
        """Clean up old completed orders to prevent memory growth"""
        if older_than_hours <= 0:
            return 0
        
        cutoff_time = time.time() - (older_than_hours * 3600)
        terminal_states = [OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED]
        
        with self._lock:
            orders_to_remove = []
            
            for order_id, order in self._orders.items():
                if (order.state in terminal_states and 
                    order.updated_at < cutoff_time):
                    orders_to_remove.append(order_id)
            
            # Remove old orders
            for order_id in orders_to_remove:
                order = self._orders[order_id]
                
                # Remove from all mappings
                del self._orders[order_id]
                
                # Remove from user orders
                user_orders = self._user_orders.get(order.request.user_id, [])
                if order_id in user_orders:
                    user_orders.remove(order_id)
                
                # Remove from signal mapping
                if order.request.signal_id in self._signal_orders:
                    del self._signal_orders[order.request.signal_id]
                
                # Remove order lock
                if order_id in self._order_locks:
                    del self._order_locks[order_id]
            
            logger.info(f"Cleaned up {len(orders_to_remove)} old orders")
            return len(orders_to_remove)

# Global thread-safe order manager instance
order_manager = OrderSyncManager()

def get_thread_safe_order_manager() -> OrderSyncManager:
    """Get global thread-safe order manager instance"""
    return order_manager

# Async wrapper methods for compatibility
class AsyncOrderManagerWrapper:
    """Async wrapper for thread-safe order manager"""
    
    def __init__(self, sync_manager: OrderSyncManager):
        self.sync_manager = sync_manager
    
    async def create_order_safely(self, order_data: dict) -> Optional[str]:
        """Create order safely (async wrapper)"""
        try:
            from .type_definitions import OrderType
            
            # Convert dict to OrderRequest
            order_type = OrderType.MARKET
            if order_data.get('order_type'):
                order_type = OrderType(order_data['order_type'].lower())
            
            request = OrderRequest(
                user_id=order_data['user_id'],
                symbol=order_data['symbol'],
                side=order_data['side'].lower(),
                quantity=float(order_data['quantity']),
                order_type=order_type,
                price=order_data.get('price'),
                signal_id=order_data.get('signal_id'),
                strategy_id=order_data.get('strategy_id')
            )
            
            order_id, error = self.sync_manager.create_order(request)
            return order_id
            
        except Exception as e:
            logger.error(f"Error in create_order_safely: {e}")
            return None
    
    async def update_order_status_safely(self, order_id: str, status: str, metadata: dict = None) -> bool:
        """Update order status safely (async wrapper)"""
        try:
            # Map status strings to OrderState
            status_mapping = {
                'PLACING': OrderState.SUBMITTED,
                'PLACED': OrderState.SUBMITTED,  
                'FILLED': OrderState.FILLED,
                'REJECTED': OrderState.REJECTED,
                'CANCELLED': OrderState.CANCELLED
            }
            
            new_state = status_mapping.get(status.upper(), OrderState.PENDING)
            
            success, error = self.sync_manager.update_order_state(
                order_id, new_state,
                filled_quantity=metadata.get('filled_quantity') if metadata else None,
                average_price=metadata.get('filled_price') if metadata else None,
                broker_order_id=metadata.get('broker_order_id') if metadata else None,
                error_message=metadata.get('error_message') if metadata else None
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error in update_order_status_safely: {e}")
            return False
    
    async def get_order_safely(self, order_id: str) -> Optional[Order]:
        """Get order safely (async wrapper)"""
        try:
            return self.sync_manager.get_order(order_id)
        except Exception as e:
            logger.error(f"Error in get_order_safely: {e}")
            return None

# Add async methods to the global manager
def _patch_order_manager():
    """Add async methods to the order manager"""
    global order_manager
    
    # Add async wrapper methods
    async_wrapper = AsyncOrderManagerWrapper(order_manager)
    order_manager.create_order_safely = async_wrapper.create_order_safely
    order_manager.update_order_status_safely = async_wrapper.update_order_status_safely
    order_manager.get_order_safely = async_wrapper.get_order_safely

# Patch the manager on import
_patch_order_manager() 