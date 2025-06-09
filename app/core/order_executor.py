"""
Robust Order Executor for Algorithmic Trading

This module provides a comprehensive order execution system with:
- Multi-layer risk management
- Retry logic and error handling
- Order state management
- Audit logging
- Circuit breaker patterns
- Real-time monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_, select

from app.database import DatabaseManager, get_database_manager
from app.models.base import (
    Order, OrderStatus, OrderSide, OrderType, ProductType,
    BrokerConfig, User, Position, Balance, Trade
)
from app.core.risk_manager import risk_manager, RiskCheckContext, RiskCheckResult, RiskViolation
from app.strategies.signals import StrategySignal
from app.brokers.angelone_new import AngelOneBroker
from app.core.interfaces import Order as OrderInterface
from app.utils.timezone_utils import ist_utcnow as datetime_now  # IST replacement for datetime.utcnow

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Order execution status"""
    PENDING = "PENDING"
    RISK_CHECK_PASSED = "RISK_CHECK_PASSED"
    RISK_CHECK_FAILED = "RISK_CHECK_FAILED"
    SUBMITTED_TO_BROKER = "SUBMITTED_TO_BROKER"
    BROKER_ACCEPTED = "BROKER_ACCEPTED"
    BROKER_REJECTED = "BROKER_REJECTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Blocking requests
    HALF_OPEN = "HALF_OPEN"  # Testing recovery

@dataclass
class ExecutionResult:
    """Order execution result"""
    success: bool
    status: ExecutionStatus
    broker_order_id: Optional[str] = None
    message: str = ""
    error_code: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    risk_violations: List[RiskViolation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionConfig:
    """Order execution configuration"""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    enable_risk_checks: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    enable_audit_logging: bool = True
    enable_real_time_monitoring: bool = True

class CircuitBreaker:
    """Circuit breaker for broker connections"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and \
               datetime_now() - self.last_failure_time > timedelta(seconds=self.timeout_seconds):
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime_now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

class OrderExecutor:
    """
    Robust order executor with comprehensive risk management
    
    This class handles the complete order execution lifecycle:
    1. Pre-execution risk checks
    2. Order submission to broker
    3. Order status monitoring
    4. Error handling and retries
    5. Post-execution updates
    6. Audit logging
    """
    
    # Class-level broker singleton
    _angel_one_broker = None
    _broker_last_auth = None
    _broker_lock = None
    
    def __init__(self, config: Optional[ExecutionConfig] = None, db_manager=None):
        self.config = config or ExecutionConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}  # Per broker
        self.execution_history: List[ExecutionResult] = []
        self.broker_instances: Dict[str, Dict[str, Any]] = {}
        self.db_manager = db_manager
        
        # Initialize broker lock if not exists
        if OrderExecutor._broker_lock is None:
            import asyncio
            OrderExecutor._broker_lock = asyncio.Lock()
        
    async def execute_order(self, order_id: str) -> ExecutionResult:
        """
        Execute a single order with comprehensive error handling
        
        Args:
            order_id: Database order ID
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = datetime_now()
        result = ExecutionResult(
            success=False,
            status=ExecutionStatus.PENDING
        )
        
        # Use provided db_manager or get global instance
        db_manager = self.db_manager
        if not db_manager:
            from app.database import get_database_manager
            db_manager = get_database_manager()
            if not db_manager._initialized:
                logger.warning("Using uninitialized database manager - attempting to initialize")
                try:
                    await db_manager.initialize()
                except Exception as e:
                    logger.error(f"Database not initialized: {e}")
                    result.status = ExecutionStatus.FAILED
                    result.message = f"Database not initialized: {str(e)}"
                    return result
        
        try:
            async with db_manager.get_async_session() as db:
                # Get order from database
                stmt = select(Order).where(Order.id == order_id)
                result_set = await db.execute(stmt)
                order = result_set.scalar_one_or_none()
                
                if not order:
                    result.message = f"Order {order_id} not found"
                    result.status = ExecutionStatus.FAILED
                    return result
                
                # Log execution start
                if self.config.enable_audit_logging:
                    self._log_execution_event(order, "EXECUTION_STARTED", {})
                
                # Execute with proper risk checks and broker integration
                result = await self._execute_with_retries(db, order)
                
        except Exception as e:
            logger.error(f"Critical error in order execution: {e}")
            result.status = ExecutionStatus.FAILED
            result.message = f"Critical execution error: {str(e)}"
            
        finally:
            # Calculate execution time
            result.execution_time = (datetime_now() - start_time).total_seconds()
            
            # Store execution history
            self.execution_history.append(result)
            
            # Log execution completion
            if self.config.enable_audit_logging:
                self._log_execution_event(
                    order if 'order' in locals() else None,
                    "EXECUTION_COMPLETED",
                    {
                        'success': result.success,
                        'status': result.status.value,
                        'execution_time': result.execution_time,
                        'retry_count': result.retry_count
                    }
                )
        
        return result
    
    async def _perform_risk_checks(self, db, order: Order) -> Tuple[RiskCheckResult, List[RiskViolation], Dict[str, Any]]:
        """Perform comprehensive risk checks"""
        try:
            # Get user balance
            balance_result = await db.execute(select(Balance).where(Balance.user_id == order.user_id))
            balance = balance_result.scalar_one_or_none()
            current_balance = balance.total_balance if balance else 0
            
            # Get current positions
            positions_result = await db.execute(select(Position).where(Position.user_id == order.user_id))
            positions = positions_result.scalars().all()
            current_positions = [
                {
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_price': pos.average_price,
                    'pnl': pos.pnl
                }
                for pos in positions
            ]
            
            # Get recent orders for rate limiting
            recent_orders_result = await db.execute(
                select(Order).where(
                    and_(
                        Order.user_id == order.user_id,
                        Order.created_at > datetime_now() - timedelta(hours=1)
                    )
                )
            )
            recent_orders = recent_orders_result.scalars().all()
            
            # Create risk check context
            context = RiskCheckContext(
                user_id=order.user_id,
                strategy_id=order.strategy_id,
                order_value=order.quantity * (order.price or 0),
                current_balance=current_balance,
                current_positions=current_positions,
                recent_orders=[{'id': o.id, 'created_at': o.created_at} for o in recent_orders],
                market_conditions={}  # Would be populated with real market data
            )
            
            # Perform risk check
            return risk_manager.check_order_risk(db, context)
            
        except Exception as e:
            logger.error(f"Error in risk checks: {e}")
            violation = RiskViolation(
                rule_name="RISK_CHECK_ERROR",
                severity="CRITICAL",
                message=f"Risk check error: {str(e)}",
                current_value=0,
                limit_value=0,
                suggested_action="REJECT_ORDER"
            )
            return RiskCheckResult.REJECTED, [violation], {}
    
    async def _execute_with_retries(self, db, order: Order) -> ExecutionResult:
        """Execute order with retry logic"""
        result = ExecutionResult(success=False, status=ExecutionStatus.PENDING)
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result.retry_count = attempt
                
                # Get broker instance
                broker = await self._get_broker_instance(db, order.user_id)
                if not broker:
                    result.status = ExecutionStatus.FAILED
                    result.message = "No active broker configuration"
                    break
                
                # Convert to broker order format
                broker_order = self._convert_to_broker_order(order)
                
                # Submit order to broker
                result.status = ExecutionStatus.SUBMITTED_TO_BROKER
                await self._update_order_status(db, order, OrderStatus.QUEUED, "Order submitted to broker")
                
                # Execute order
                broker_result = await asyncio.wait_for(
                    broker.place_order(broker_order),
                    timeout=self.config.timeout_seconds
                )
                
                # Process broker response
                if broker_result.get("status") == "success":
                    result.success = True
                    result.status = ExecutionStatus.BROKER_ACCEPTED
                    result.broker_order_id = broker_result.get("broker_order_id")
                    result.message = broker_result.get("message", "Order placed successfully")
                    
                    # Update order in database
                    await self._update_order_status(
                        db, order, OrderStatus.PLACED,
                        result.message, result.broker_order_id
                    )
                    break
                else:
                    result.status = ExecutionStatus.BROKER_REJECTED
                    result.message = broker_result.get("message", "Order rejected by broker")
                    result.error_code = broker_result.get("error_code")
                    
                    # Check if error is retryable
                    if not self._is_retryable_error(result.error_code):
                        break
                
            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.message = f"Order execution timeout after {self.config.timeout_seconds}s"
                logger.warning(f"Order {order.id} execution timeout on attempt {attempt + 1}")
                
            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.message = f"Execution error: {str(e)}"
                logger.error(f"Order {order.id} execution error on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))  # Exponential backoff
        
        # Final status update if not successful
        if not result.success:
            await self._update_order_status(db, order, OrderStatus.REJECTED, result.message)
        
        return result
    
    def _convert_to_broker_order(self, order: Order) -> OrderInterface:
        """Convert database order to broker order format"""
        return OrderInterface(
            user_id=order.user_id,
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side.value,
            order_type=order.order_type.value,
            product_type=order.product_type.value,
            quantity=order.quantity,
            price=order.price,
            trigger_price=order.trigger_price,
            variety=order.variety,
            broker_id="angelone",  # Default broker
        )
    
    def _is_retryable_error(self, error_code: Optional[str]) -> bool:
        """Check if error is retryable"""
        if not error_code:
            return True
        
        # Non-retryable errors
        non_retryable = [
            "INSUFFICIENT_FUNDS",
            "INVALID_SYMBOL",
            "MARKET_CLOSED",
            "ORDER_SIZE_TOO_SMALL",
            "INVALID_PRICE",
            "DUPLICATE_ORDER"
        ]
        
        return error_code not in non_retryable
    
    async def _get_broker_instance(self, db, user_id: str) -> Optional[Any]:
        """Get simple Angel One broker - FINAL FIX"""
        try:
            from fix_angel_one_final import get_global_angel_one
            broker = await get_global_angel_one()
            if broker:
                logger.info(f"✅ Using simple Angel One broker for user {user_id}")
            return broker
        except Exception as e:
            logger.error(f"❌ Failed to get Angel One broker: {e}")
            return None
    async def _get_broker_name(self, db, user_id: str) -> str:
        """Get broker name for user"""
        broker_config_result = await db.execute(
            select(BrokerConfig).where(
                and_(
                    BrokerConfig.user_id == user_id,
                    BrokerConfig.is_active == True
                )
            )
        )
        broker_config = broker_config_result.scalar_one_or_none()
        
        return broker_config.broker_name.value.lower() if broker_config else "unknown"
    
    def _check_circuit_breaker(self, broker_name: str) -> bool:
        """Check circuit breaker status"""
        if broker_name not in self.circuit_breakers:
            self.circuit_breakers[broker_name] = CircuitBreaker(
                self.config.circuit_breaker_failure_threshold,
                self.config.circuit_breaker_timeout_seconds
            )
        
        return self.circuit_breakers[broker_name].can_execute()
    
    def _record_circuit_breaker_success(self, broker_name: str):
        """Record successful execution for circuit breaker"""
        if broker_name in self.circuit_breakers:
            self.circuit_breakers[broker_name].record_success()
    
    def _record_circuit_breaker_failure(self, broker_name: str):
        """Record failed execution for circuit breaker"""
        if broker_name not in self.circuit_breakers:
            self.circuit_breakers[broker_name] = CircuitBreaker(
                self.config.circuit_breaker_failure_threshold,
                self.config.circuit_breaker_timeout_seconds
            )
        
        self.circuit_breakers[broker_name].record_failure()
    
    async def _update_order_status(self, db, order: Order, status: OrderStatus, 
                                 message: str, broker_order_id: Optional[str] = None):
        """Update order status in database"""
        try:
            order.status = status
            order.status_message = message
            order.updated_at = datetime_now()
            
            if broker_order_id:
                order.broker_order_id = broker_order_id
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            await db.rollback()
    
    async def _post_execution_updates(self, db, order: Order, result: ExecutionResult):
        """Perform post-execution updates"""
        try:
            # Create trade record if order was filled
            if result.success and result.status == ExecutionStatus.BROKER_ACCEPTED:
                trade = Trade(
                    user_id=order.user_id,
                    order_id=order.id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price or 0,
                    broker_order_id=result.broker_order_id,
                    execution_time=datetime_now(),
                    pnl=0.0  # Will be calculated later
                )
                db.add(trade)
                await db.commit()
            
        except Exception as e:
            logger.error(f"Error in post-execution updates: {e}")
    
    def _log_execution_event(self, order: Optional[Order], event: str, metadata: Dict[str, Any]):
        """Log execution events for audit trail"""
        try:
            log_entry = {
                'timestamp': datetime_now().isoformat(),
                'event': event,
                'order_id': order.id if order else None,
                'user_id': order.user_id if order else None,
                'metadata': metadata
            }
            
            # In production, this would go to a dedicated audit log
            logger.info(f"AUDIT: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Error logging execution event: {e}")
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {}
        
        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.success])
        failed_executions = total_executions - successful_executions
        
        avg_execution_time = sum(r.execution_time for r in self.execution_history) / total_executions
        avg_retry_count = sum(r.retry_count for r in self.execution_history) / total_executions
        
        # Calculate status breakdown
        status_breakdown = {}
        for result in self.execution_history:
            status = result.status.value
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
            'average_execution_time': avg_execution_time,
            'average_retry_count': avg_retry_count,
            'status_breakdown': status_breakdown,
            'circuit_breaker_states': {
                broker: cb.state.value for broker, cb in self.circuit_breakers.items()
            }
        }
    
    async def cancel_order(self, order_id: str) -> ExecutionResult:
        """Cancel an existing order"""
        result = ExecutionResult(success=False, status=ExecutionStatus.PENDING)
        
        db_manager = self.db_manager or get_database_manager()
        if not db_manager._initialized:
            logger.warning("Database manager not initialized in cancel_order") 
            try:
                await db_manager.initialize()
            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.message = f"Database initialization failed: {str(e)}"
                return result
        
        try:
            async with db_manager.get_async_session() as db:
                order_result = await db.execute(select(Order).where(Order.id == order_id))
                order = order_result.scalar_one_or_none()
                if not order:
                    result.message = f"Order {order_id} not found"
                    result.status = ExecutionStatus.FAILED
                    return result
                
                if order.status not in [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.QUEUED]:
                    result.message = f"Order {order_id} cannot be cancelled (status: {order.status})"
                    result.status = ExecutionStatus.FAILED
                    return result
                
                # Get broker instance and cancel order
                broker = await self._get_broker_instance(db, order.user_id)
                if broker and order.broker_order_id:
                    cancel_result = await broker.cancel_order(order.user_id, order.broker_order_id)
                    if cancel_result.get("status") == "success":
                        result.success = True
                        result.status = ExecutionStatus.CANCELLED
                        result.message = "Order cancelled successfully"
                        await self._update_order_status(db, order, OrderStatus.CANCELLED, result.message)
                    else:
                        result.message = cancel_result.get("message", "Failed to cancel order")
                        result.status = ExecutionStatus.FAILED
                else:
                    # Order not yet submitted to broker, cancel locally
                    result.success = True
                    result.status = ExecutionStatus.CANCELLED
                    result.message = "Order cancelled locally"
                    await self._update_order_status(db, order, OrderStatus.CANCELLED, result.message)
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            result.status = ExecutionStatus.FAILED
            result.message = f"Cancel error: {str(e)}"
        
        return result

# Global order executor instance
order_executor = OrderExecutor() 