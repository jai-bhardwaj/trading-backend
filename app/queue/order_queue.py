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
        """Get next order from queue (blocking)"""
        try:
            redis_client = get_redis_connection()
            
            # Try priority queue first, then regular queue
            result = redis_client.blpop([
                self.priority_queue_name,
                self.queue_name
            ], timeout=timeout)
            
            if result:
                queue_name, order_data = result
                order_dict = json.loads(order_data.decode('utf-8'))
                order = QueuedOrder(**order_dict)
                
                # Move to processing queue
                processing_data = {
                    'order': asdict(order),
                    'started_at': datetime.utcnow().isoformat(),
                    'worker_id': f"worker_{uuid.uuid4().hex[:8]}"
                }
                redis_client.hset(
                    self.processing_queue_name,
                    order.order_id,
                    json.dumps(processing_data)
                )
                
                # Update statistics
                self._update_stats("dequeued")
                
                logger.info(f"🔄 Dequeued order {order.order_id} from {queue_name.decode('utf-8')}")
                return order
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue order: {e}")
            return None
    
    def complete_order(self, order_id: str, result: ExecutionResult):
        """Mark order as completed and remove from processing"""
        try:
            redis_client = get_redis_connection()
            
            # Remove from processing queue
            redis_client.hdel(self.processing_queue_name, order_id)
            
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
    
    def __init__(self, queue_name: str = "trading_orders", worker_id: Optional[str] = None):
        self.queue = OrderQueue(queue_name)
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.order_executor = OrderExecutor()
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        
    async def start_processing(self, max_orders: Optional[int] = None):
        """Start processing orders from the queue"""
        self.is_running = True
        logger.info(f"🚀 Order processor {self.worker_id} started")
        
        try:
            while self.is_running:
                # Process retry queue first
                retry_orders = self.queue.process_retry_queue()
                if retry_orders:
                    logger.info(f"🔄 Processed {len(retry_orders)} retry orders")
                
                # Get next order from queue
                order = self.queue.dequeue_order(timeout=5)
                
                if order:
                    await self._process_order(order)
                    self.processed_count += 1
                    
                    # Check if we've reached max orders
                    if max_orders and self.processed_count >= max_orders:
                        logger.info(f"🎯 Processed {max_orders} orders, stopping")
                        break
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Order processor stopped by user")
        except Exception as e:
            logger.error(f"❌ Order processor error: {e}")
        finally:
            self.is_running = False
            logger.info(f"🏁 Order processor {self.worker_id} stopped. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    async def _process_order(self, order: QueuedOrder):
        """Process a single order"""
        try:
            logger.info(f"🔄 Processing order {order.order_id} ({order.symbol} {order.side} {order.quantity})")
            
            # Execute the order
            result = await self.order_executor.execute_order(order.order_id)
            
            if result.success:
                # Mark as completed
                self.queue.complete_order(order.order_id, result)
                logger.info(f"✅ Order {order.order_id} executed successfully")
            else:
                # Retry if possible
                if not self.queue.retry_order(order):
                    logger.error(f"❌ Order {order.order_id} failed permanently")
                self.error_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error processing order {order.order_id}: {e}")
            self.error_count += 1
            
            # Try to retry the order
            try:
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