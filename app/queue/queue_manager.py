"""
Queue Manager for Trading Engine

Coordinates multiple Redis queues and workers for optimal order processing performance.
"""

import asyncio
import logging
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .redis_client import get_redis_connection, redis_client
from .order_queue import OrderQueue, OrderProcessor, QueuedOrder
from .priority_queue import PriorityOrderQueue, PriorityOrderMetadata

logger = logging.getLogger(__name__)

@dataclass
class WorkerConfig:
    """Configuration for order processing workers"""
    worker_count: int = 4
    max_orders_per_worker: Optional[int] = None
    worker_timeout: int = 300  # 5 minutes
    enable_priority_processing: bool = True
    enable_load_balancing: bool = True
    health_check_interval: int = 30

@dataclass
class QueueConfig:
    """Configuration for queue management"""
    queue_name: str = "trading_orders"
    priority_queue_name: str = "priority_orders"
    enable_retry_processing: bool = True
    retry_check_interval: int = 60
    enable_queue_rebalancing: bool = True
    rebalance_interval: int = 300  # 5 minutes
    max_queue_size: int = 10000

class QueueManager:
    """Manages multiple Redis queues and workers for high-performance order processing"""
    
    def __init__(self, worker_config: Optional[WorkerConfig] = None, queue_config: Optional[QueueConfig] = None):
        self.worker_config = worker_config or WorkerConfig()
        self.queue_config = queue_config or QueueConfig()
        
        # Initialize queues
        self.order_queue = OrderQueue(self.queue_config.queue_name)
        self.priority_queue = PriorityOrderQueue(self.queue_config.priority_queue_name)
        
        # Worker management
        self.workers: List[OrderProcessor] = []
        self.worker_threads: List[threading.Thread] = []
        self.executor = ThreadPoolExecutor(max_workers=self.worker_config.worker_count)
        
        # Control flags
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.total_processed = 0
        self.total_errors = 0
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def start(self):
        """Start the queue manager and all workers"""
        if self.is_running:
            logger.warning("⚠️ Queue manager is already running")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        logger.info(f"🚀 Starting Queue Manager with {self.worker_config.worker_count} workers")
        
        # Check Redis connection
        if not redis_client.is_connected():
            logger.error("❌ Redis connection not available")
            return False
        
        # Start workers
        self._start_workers()
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("✅ Queue Manager started successfully")
        return True
    
    def stop(self):
        """Stop the queue manager and all workers"""
        if not self.is_running:
            logger.warning("⚠️ Queue manager is not running")
            return
        
        logger.info("⏹️ Stopping Queue Manager...")
        
        # Set shutdown flag
        self.shutdown_event.set()
        self.is_running = False
        
        # Stop all workers
        self._stop_workers()
        
        # Cancel background tasks
        self._stop_background_tasks()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("🏁 Queue Manager stopped")
    
    def enqueue_order(self, order: QueuedOrder, priority_metadata: Optional[PriorityOrderMetadata] = None) -> bool:
        """Add order to appropriate queue"""
        try:
            # Check queue capacity
            stats = self.get_comprehensive_stats()
            total_pending = stats.get('queue_summary', {}).get('total_pending', 0)
            
            if total_pending >= self.queue_config.max_queue_size:
                logger.error(f"❌ Queue capacity exceeded ({total_pending}/{self.queue_config.max_queue_size})")
                return False
            
            # Route to appropriate queue
            if priority_metadata or order.priority >= 3:  # High priority or above
                if not priority_metadata:
                    priority_metadata = PriorityOrderMetadata()
                
                success = self.priority_queue.enqueue_priority_order(order, priority_metadata)
                if success:
                    logger.info(f"📈 Order {order.order_id} added to priority queue")
            else:
                success = self.order_queue.enqueue_order(order)
                if success:
                    logger.info(f"📋 Order {order.order_id} added to standard queue")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue order {order.order_id}: {e}")
            return False
    
    def _start_workers(self):
        """Start all order processing workers"""
        for i in range(self.worker_config.worker_count):
            worker_id = f"worker_{i+1}"
            
            # Create worker
            worker = OrderProcessor(
                queue_name=self.queue_config.queue_name,
                worker_id=worker_id
            )
            
            # Start worker in thread
            thread = threading.Thread(
                target=self._run_worker,
                args=(worker,),
                name=f"OrderWorker-{worker_id}",
                daemon=True
            )
            
            self.workers.append(worker)
            self.worker_threads.append(thread)
            thread.start()
            
            logger.info(f"🔄 Started worker {worker_id}")
    
    def _run_worker(self, worker: OrderProcessor):
        """Run a single worker in async context"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run worker
            loop.run_until_complete(
                worker.start_processing(
                    max_orders=self.worker_config.max_orders_per_worker
                )
            )
            
        except Exception as e:
            logger.error(f"❌ Worker {worker.worker_id} error: {e}")
        finally:
            loop.close()
    
    def _stop_workers(self):
        """Stop all workers"""
        logger.info("⏹️ Stopping all workers...")
        
        # Signal workers to stop
        for worker in self.workers:
            worker.stop_processing()
        
        # Wait for threads to finish
        for thread in self.worker_threads:
            thread.join(timeout=30)  # 30 second timeout
            if thread.is_alive():
                logger.warning(f"⚠️ Worker thread {thread.name} did not stop gracefully")
        
        self.workers.clear()
        self.worker_threads.clear()
        
        logger.info("🏁 All workers stopped")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.queue_config.enable_retry_processing:
            task = asyncio.create_task(self._retry_processor())
            self.background_tasks.append(task)
        
        if self.queue_config.enable_queue_rebalancing:
            task = asyncio.create_task(self._queue_rebalancer())
            self.background_tasks.append(task)
        
        # Health monitoring
        task = asyncio.create_task(self._health_monitor())
        self.background_tasks.append(task)
        
        logger.info(f"🔄 Started {len(self.background_tasks)} background tasks")
    
    def _stop_background_tasks(self):
        """Stop all background tasks"""
        for task in self.background_tasks:
            task.cancel()
        
        self.background_tasks.clear()
        logger.info("🏁 Background tasks stopped")
    
    async def _retry_processor(self):
        """Background task to process retry queues"""
        while self.is_running:
            try:
                # Process retry queue
                retry_orders = self.order_queue.process_retry_queue()
                if retry_orders:
                    logger.info(f"🔄 Processed {len(retry_orders)} retry orders")
                
                # Wait before next check
                await asyncio.sleep(self.queue_config.retry_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Retry processor error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _queue_rebalancer(self):
        """Background task to rebalance queues"""
        while self.is_running:
            try:
                # Rebalance priority queues
                rebalanced = self.priority_queue.rebalance_queues()
                if rebalanced:
                    logger.info(f"🔄 Queue rebalancing: {rebalanced}")
                
                # Clean up expired assignments
                cleaned = self.priority_queue.cleanup_expired_assignments()
                if cleaned > 0:
                    logger.info(f"🧹 Cleaned {cleaned} expired assignments")
                
                # Wait before next rebalance
                await asyncio.sleep(self.queue_config.rebalance_interval)
                
            except Exception as e:
                logger.error(f"❌ Queue rebalancer error: {e}")
                await asyncio.sleep(300)  # Wait longer on error
    
    async def _health_monitor(self):
        """Background task to monitor system health"""
        while self.is_running:
            try:
                # Check Redis health
                redis_health = redis_client.health_check()
                if redis_health.get('status') != 'healthy':
                    logger.warning(f"⚠️ Redis health issue: {redis_health}")
                
                # Check queue health
                stats = self.get_comprehensive_stats()
                queue_health = stats.get('health', {})
                
                if queue_health.get('status') == 'critical':
                    logger.warning(f"⚠️ Queue health critical: {queue_health}")
                
                # Check worker health
                active_workers = sum(1 for worker in self.workers if worker.is_running)
                if active_workers < self.worker_config.worker_count:
                    logger.warning(f"⚠️ Only {active_workers}/{self.worker_config.worker_count} workers active")
                
                await asyncio.sleep(self.worker_config.health_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Health monitor error: {e}")
                await asyncio.sleep(60)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all queues and workers"""
        try:
            # Get queue statistics
            order_queue_stats = self.order_queue.get_queue_stats()
            priority_queue_stats = self.priority_queue.get_priority_queue_stats()
            
            # Get worker statistics
            worker_stats = []
            total_processed = 0
            total_errors = 0
            
            for worker in self.workers:
                stats = worker.get_processor_stats()
                worker_stats.append(stats)
                total_processed += stats.get('processed_count', 0)
                total_errors += stats.get('error_count', 0)
            
            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Redis health
            redis_health = redis_client.health_check()
            
            return {
                'manager': {
                    'is_running': self.is_running,
                    'uptime_seconds': uptime_seconds,
                    'worker_count': len(self.workers),
                    'active_workers': sum(1 for w in self.workers if w.is_running),
                    'background_tasks': len(self.background_tasks)
                },
                'queues': {
                    'order_queue': order_queue_stats,
                    'priority_queue': priority_queue_stats
                },
                'workers': {
                    'individual_stats': worker_stats,
                    'total_processed': total_processed,
                    'total_errors': total_errors,
                    'overall_success_rate': (total_processed - total_errors) / max(1, total_processed)
                },
                'queue_summary': {
                    'total_pending': (
                        order_queue_stats.get('queue_lengths', {}).get('total_pending', 0) +
                        priority_queue_stats.get('summary', {}).get('total_pending', 0)
                    ),
                    'total_processing': (
                        order_queue_stats.get('queue_lengths', {}).get('processing', 0) +
                        priority_queue_stats.get('processing_count', 0)
                    ),
                    'total_failed': (
                        order_queue_stats.get('queue_lengths', {}).get('failed', 0)
                    )
                },
                'health': {
                    'status': self._calculate_overall_health(order_queue_stats, priority_queue_stats, worker_stats),
                    'redis': redis_health,
                    'issues': self._identify_health_issues(order_queue_stats, priority_queue_stats, worker_stats)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get comprehensive stats: {e}")
            return {'error': str(e)}
    
    def _calculate_overall_health(self, order_stats: dict, priority_stats: dict, worker_stats: list) -> str:
        """Calculate overall system health status"""
        # Check for critical issues
        total_pending = (
            order_stats.get('queue_lengths', {}).get('total_pending', 0) +
            priority_stats.get('summary', {}).get('total_pending', 0)
        )
        
        active_workers = sum(1 for w in self.workers if w.is_running)
        
        if total_pending > self.queue_config.max_queue_size * 0.9:
            return 'critical'
        elif active_workers < self.worker_config.worker_count * 0.5:
            return 'critical'
        elif total_pending > self.queue_config.max_queue_size * 0.7:
            return 'warning'
        elif active_workers < self.worker_config.worker_count:
            return 'warning'
        else:
            return 'healthy'
    
    def _identify_health_issues(self, order_stats: dict, priority_stats: dict, worker_stats: list) -> List[str]:
        """Identify specific health issues"""
        issues = []
        
        # Queue capacity issues
        total_pending = (
            order_stats.get('queue_lengths', {}).get('total_pending', 0) +
            priority_stats.get('summary', {}).get('total_pending', 0)
        )
        
        if total_pending > self.queue_config.max_queue_size * 0.9:
            issues.append(f"Queue near capacity: {total_pending}/{self.queue_config.max_queue_size}")
        
        # Worker issues
        active_workers = sum(1 for w in self.workers if w.is_running)
        if active_workers < self.worker_config.worker_count:
            issues.append(f"Inactive workers: {self.worker_config.worker_count - active_workers}")
        
        # High error rates
        total_errors = sum(stats.get('error_count', 0) for stats in worker_stats)
        total_processed = sum(stats.get('processed_count', 0) for stats in worker_stats)
        
        if total_processed > 0:
            error_rate = total_errors / total_processed
            if error_rate > 0.1:  # 10% error rate
                issues.append(f"High error rate: {error_rate:.1%}")
        
        # Failed orders
        failed_count = order_stats.get('queue_lengths', {}).get('failed', 0)
        if failed_count > 100:
            issues.append(f"High failed order count: {failed_count}")
        
        return issues
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_worker_by_id(self, worker_id: str) -> Optional[OrderProcessor]:
        """Get worker by ID"""
        for worker in self.workers:
            if worker.worker_id == worker_id:
                return worker
        return None
    
    def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker"""
        try:
            # Find and stop the worker
            worker = self.get_worker_by_id(worker_id)
            if not worker:
                logger.error(f"❌ Worker {worker_id} not found")
                return False
            
            # Stop the worker
            worker.stop_processing()
            
            # Find and stop the thread
            thread_to_remove = None
            for i, thread in enumerate(self.worker_threads):
                if thread.name.endswith(worker_id):
                    thread.join(timeout=30)
                    thread_to_remove = i
                    break
            
            if thread_to_remove is not None:
                self.worker_threads.pop(thread_to_remove)
                self.workers.remove(worker)
            
            # Start new worker
            new_worker = OrderProcessor(
                queue_name=self.queue_config.queue_name,
                worker_id=worker_id
            )
            
            new_thread = threading.Thread(
                target=self._run_worker,
                args=(new_worker,),
                name=f"OrderWorker-{worker_id}",
                daemon=True
            )
            
            self.workers.append(new_worker)
            self.worker_threads.append(new_thread)
            new_thread.start()
            
            logger.info(f"🔄 Restarted worker {worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restart worker {worker_id}: {e}")
            return False 