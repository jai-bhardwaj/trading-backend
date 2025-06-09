"""
Redis-based Order Queue System

Provides high-performance order queuing and processing using Redis.
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .redis_client import get_redis_connection
from app.models.base import Order, OrderStatus, OrderSide, OrderType
from app.core.order_executor import OrderExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    """Order queue priorities"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

@dataclass
class QueuedOrder:
    """Order data structure for queue processing"""
    order_id: str
    user_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    price: Optional[float] = None
    priority: int = QueuePriority.NORMAL.value
    created_at: str = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}

class OrderQueue:
    """Redis-based order queue with priority support"""
    
    def __init__(self, queue_name: str = "trading_orders"):
        self.queue_name = queue_name
        self.priority_queue_name = f"{queue_name}:priority"
        self.processing_queue_name = f"{queue_name}:processing"
        self.failed_queue_name = f"{queue_name}:failed"
        self.retry_queue_name = f"{queue_name}:retry"
        
        # Queue statistics
        self.stats_key = f"{queue_name}:stats"
        
    def enqueue_order(self, order: QueuedOrder) -> bool:
        """Add order to the queue"""
        try:
            redis_client = get_redis_connection()
            
            # Serialize order data
            order_data = json.dumps(asdict(order))
            
            # Add to appropriate queue based on priority
            if order.priority >= QueuePriority.HIGH.value:
                # High priority orders go to priority queue
                redis_client.lpush(self.priority_queue_name, order_data)
                logger.info(f"📈 High priority order {order.order_id} added to priority queue")
            else:
                # Normal orders go to regular queue
                redis_client.lpush(self.queue_name, order_data)
                logger.info(f"📋 Order {order.order_id} added to queue")
            
            # Update statistics
            self._update_stats("enqueued")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue order {order.order_id}: {e}")
            return False
    
    def dequeue_order(self, timeout: int = 5) -> Optional[QueuedOrder]:
        """Get next order from queue (non-blocking with intelligent polling)"""
        try:
            redis_client = get_redis_connection()
            
            # First try non-blocking operations to avoid timeout errors
            # Try priority queue first
            result = redis_client.lpop(self.priority_queue_name)
            if result:
                order_dict = json.loads(result.decode('utf-8'))
                order = QueuedOrder(**order_dict)
                return self._process_dequeued_order(order, "priority_queue")
            
            # Then try regular queue
            result = redis_client.lpop(self.queue_name)
            if result:
                order_dict = json.loads(result.decode('utf-8'))
                order = QueuedOrder(**order_dict)
                return self._process_dequeued_order(order, "regular_queue")
            
            # If no orders found, return None immediately (no blocking)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue order: {e}")
            return None
    
    def _process_dequeued_order(self, order: QueuedOrder, queue_type: str) -> QueuedOrder:
        """Process a dequeued order and move it to processing queue"""
        try:
            redis_client = get_redis_connection()
            
            # Move to processing queue
            processing_data = {
                'order': asdict(order),
                'started_at': datetime.utcnow().isoformat(),
                'worker_id': f"worker_{uuid.uuid4().hex[:8]}",
                'queue_type': queue_type
            }
            redis_client.hset(
                self.processing_queue_name,
                order.order_id,
                json.dumps(processing_data)
            )
            
            # Update statistics
            self._update_stats("dequeued")
            
            logger.info(f"🔄 Dequeued order {order.order_id} from {queue_type}")
            return order
            
        except Exception as e:
            logger.error(f"❌ Failed to process dequeued order {order.order_id}: {e}")
            return order
    
    def complete_order(self, order_id: str, result: ExecutionResult):
        """Mark order as completed and remove from processing"""
        try:
            redis_client = get_redis_connection()
            
            # Remove from processing queue
            redis_client.hdel(self.processing_queue_name, order_id)
            
            # Mark order as dirty for DB sync
            redis_client.sadd("orders:pending_sync", order_id)
            
            # Update statistics
            if result.success:
                self._update_stats("completed")
                logger.info(f"✅ Order {order_id} completed successfully")
            else:
                self._update_stats("failed")
                logger.error(f"❌ Order {order_id} failed: {result.message}")
            
        except Exception as e:
            logger.error(f"❌ Failed to complete order {order_id}: {e}")
    
    def retry_order(self, order: QueuedOrder) -> bool:
        """Retry failed order with exponential backoff"""
        try:
            if order.retry_count >= order.max_retries:
                # Mark order as dirty for DB sync
                redis_client = get_redis_connection()
                redis_client.sadd("orders:pending_sync", order.order_id)
                return self._move_to_failed_queue(order)
            
            redis_client = get_redis_connection()
            
            # Increment retry count
            order.retry_count += 1
            
            # Calculate delay (exponential backoff)
            delay_seconds = min(300, 2 ** order.retry_count)  # Max 5 minutes
            retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            
            # Add to retry queue with delay
            retry_data = {
                'order': asdict(order),
                'retry_at': retry_at.isoformat(),
                'delay_seconds': delay_seconds
            }
            
            redis_client.zadd(
                self.retry_queue_name,
                {json.dumps(retry_data): retry_at.timestamp()}
            )
            
            # Remove from processing queue
            redis_client.hdel(self.processing_queue_name, order.order_id)
            
            # Update statistics
            self._update_stats("retried")
            
            logger.info(f"🔄 Order {order.order_id} scheduled for retry #{order.retry_count} in {delay_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to retry order {order.order_id}: {e}")
            return False
    
    def process_retry_queue(self) -> List[QueuedOrder]:
        """Process orders ready for retry"""
        try:
            redis_client = get_redis_connection()
            current_time = datetime.utcnow().timestamp()
            
            # Get orders ready for retry
            retry_items = redis_client.zrangebyscore(
                self.retry_queue_name,
                0,
                current_time,
                withscores=True
            )
            
            retried_orders = []
            
            for item_data, score in retry_items:
                try:
                    retry_data = json.loads(item_data.decode('utf-8'))
                    order = QueuedOrder(**retry_data['order'])
                    
                    # Re-enqueue the order
                    if self.enqueue_order(order):
                        retried_orders.append(order)
                        
                        # Remove from retry queue
                        redis_client.zrem(self.retry_queue_name, item_data)
                        
                        logger.info(f"🔄 Order {order.order_id} moved from retry queue back to main queue")
                
                except Exception as e:
                    logger.error(f"❌ Failed to process retry item: {e}")
                    # Remove corrupted item
                    redis_client.zrem(self.retry_queue_name, item_data)
            
            return retried_orders
            
        except Exception as e:
            logger.error(f"❌ Failed to process retry queue: {e}")
            return []
    
    def _move_to_failed_queue(self, order: QueuedOrder) -> bool:
        """Move order to failed queue after max retries"""
        try:
            redis_client = get_redis_connection()
            
            failed_data = {
                'order': asdict(order),
                'failed_at': datetime.utcnow().isoformat(),
                'reason': f"Max retries ({order.max_retries}) exceeded"
            }
            
            redis_client.lpush(self.failed_queue_name, json.dumps(failed_data))
            redis_client.hdel(self.processing_queue_name, order.order_id)
            
            # Update statistics
            self._update_stats("max_retries_exceeded")
            
            logger.error(f"💀 Order {order.order_id} moved to failed queue after {order.retry_count} retries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to move order {order.order_id} to failed queue: {e}")
            return False
    
    def _update_stats(self, metric: str):
        """Update queue statistics"""
        try:
            redis_client = get_redis_connection()
            
            # Increment counter
            redis_client.hincrby(self.stats_key, metric, 1)
            redis_client.hincrby(self.stats_key, "total", 1)
            
            # Update timestamp
            redis_client.hset(self.stats_key, "last_updated", datetime.utcnow().isoformat())
            
        except Exception as e:
            logger.error(f"❌ Failed to update stats: {e}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics and health metrics"""
        try:
            redis_client = get_redis_connection()
            
            # Get queue lengths
            queue_length = redis_client.llen(self.queue_name)
            priority_queue_length = redis_client.llen(self.priority_queue_name)
            processing_count = redis_client.hlen(self.processing_queue_name)
            failed_count = redis_client.llen(self.failed_queue_name)
            retry_count = redis_client.zcard(self.retry_queue_name)
            
            # Get statistics
            stats = redis_client.hgetall(self.stats_key)
            stats = {k.decode('utf-8'): v.decode('utf-8') for k, v in stats.items()}
            
            return {
                'queue_lengths': {
                    'normal': queue_length,
                    'priority': priority_queue_length,
                    'processing': processing_count,
                    'failed': failed_count,
                    'retry': retry_count,
                    'total_pending': queue_length + priority_queue_length
                },
                'statistics': stats,
                'health': {
                    'status': 'healthy' if processing_count < 1000 else 'warning',
                    'total_orders': queue_length + priority_queue_length + processing_count
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {'error': str(e)}

class OrderProcessor:
    """High-performance order processor using Redis queues"""
    
    def __init__(self, queue_name: str = "trading_orders", worker_id: Optional[str] = None, db_manager=None):
        self.queue = OrderQueue(queue_name)
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        # No order_executor or db_manager - workers only use Redis!
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        
    async def start_processing(self, max_orders: Optional[int] = None):
        """Start processing orders from the queue"""
        self.is_running = True
        logger.info(f"🚀 Order processor {self.worker_id} started")
        
        consecutive_empty_polls = 0
        
        try:
            while self.is_running:
                # Process retry queue first
                retry_orders = self.queue.process_retry_queue()
                if retry_orders:
                    logger.info(f"🔄 Processed {len(retry_orders)} retry orders")
                    consecutive_empty_polls = 0  # Reset counter
                
                # Get next order from queue
                order = self.queue.dequeue_order(timeout=5)
                
                if order:
                    await self._process_order(order)
                    self.processed_count += 1
                    consecutive_empty_polls = 0  # Reset counter
                    
                    # Check if we've reached max orders
                    if max_orders and self.processed_count >= max_orders:
                        logger.info(f"🎯 Processed {max_orders} orders, stopping")
                        break
                else:
                    # No orders found - implement intelligent backoff
                    consecutive_empty_polls += 1
                    
                    # Gradually increase sleep time when no orders are found
                    if consecutive_empty_polls < 10:
                        sleep_time = 0.1  # Fast polling for first 10 attempts
                    elif consecutive_empty_polls < 50:
                        sleep_time = 1.0  # Medium polling for next 40 attempts
                    else:
                        sleep_time = 5.0  # Slow polling after 50 empty attempts
                    
                    await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Order processor stopped by user")
        except Exception as e:
            logger.error(f"❌ Order processor error: {e}")
        finally:
            self.is_running = False
            logger.info(f"🏁 Order processor {self.worker_id} stopped. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    async def _process_order(self, order: QueuedOrder):
        """Process a single order (Redis-only, no DB access)"""
        try:
            logger.info(f"🔄 Processing order {order.order_id} ({order.symbol} {order.side} {order.quantity})")
            
            # Update order status in Redis only
            redis_client = get_redis_connection()
            order_key = f"order:{order.order_id}"
            
            # Simulate order processing (replace with actual broker logic)
            redis_client.hset(order_key, mapping={
                "status": "PROCESSING",
                "updated_at": datetime.utcnow().isoformat(),
                "worker_id": self.worker_id
            })
            
            # Mark order as dirty for DB sync
            redis_client.sadd("orders:pending_sync", order.order_id)
            
            # Simulate successful execution (you can replace this with real broker calls)
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Update final status in Redis
            redis_client.hset(order_key, mapping={
                "status": "COMPLETED",
                "executed_at": datetime.utcnow().isoformat(),
                "filled_quantity": str(order.quantity)
            })
            
            # Mark as completed (Redis only)
            from app.core.order_executor import ExecutionResult
            result = ExecutionResult(success=True, status="COMPLETED", message="Order executed via Redis")
            self.queue.complete_order(order.order_id, result)
            logger.info(f"✅ Order {order.order_id} executed successfully (Redis-only)")
                
        except Exception as e:
            logger.error(f"❌ Error processing order {order.order_id}: {e}")
            self.error_count += 1
            
            # Update error status in Redis
            try:
                redis_client = get_redis_connection()
                order_key = f"order:{order.order_id}"
                redis_client.hset(order_key, mapping={
                    "status": "ERROR",
                    "error_message": str(e),
                    "updated_at": datetime.utcnow().isoformat()
                })
                redis_client.sadd("orders:pending_sync", order.order_id)
                
                # Try to retry the order
                self.queue.retry_order(order)
            except Exception as retry_error:
                logger.error(f"❌ Failed to retry order {order.order_id}: {retry_error}")
    
    def stop_processing(self):
        """Stop the order processor"""
        self.is_running = False
        logger.info(f"⏹️ Stop signal sent to processor {self.worker_id}")
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'worker_id': self.worker_id,
            'is_running': self.is_running,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'success_rate': (self.processed_count - self.error_count) / max(1, self.processed_count)
        } 