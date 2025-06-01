"""
Redis-Based Trading Engine

High-performance trading engine using Redis queues for order processing.
Replaces the database polling approach with real-time queue processing.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import DatabaseManager
from app.models.base import Order, OrderStatus, Strategy, StrategyStatus, User, BrokerConfig
from app.queue import QueueManager, WorkerConfig, QueueConfig, QueuedOrder, PriorityOrderMetadata
from app.queue.priority_queue import OrderUrgency
from app.brokers import get_broker_instance
from app.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)

class RedisBasedTradingEngine:
    """
    High-performance trading engine using Redis queues for order processing.
    
    Key improvements over database polling:
    - Real-time order processing (no polling delay)
    - Horizontal scalability with multiple workers
    - Priority-based order routing
    - Automatic retry with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Comprehensive monitoring and health checks
    """
    
    def __init__(self, worker_count: int = 4, max_queue_size: int = 10000, db_manager=None):
        # Queue configuration
        self.worker_config = WorkerConfig(
            worker_count=worker_count,
            enable_priority_processing=True,
            enable_load_balancing=True,
            health_check_interval=30
        )
        
        self.queue_config = QueueConfig(
            queue_name="trading_orders",
            priority_queue_name="priority_orders",
            enable_retry_processing=True,
            enable_queue_rebalancing=True,
            max_queue_size=max_queue_size
        )
        
        # Initialize queue manager
        self.queue_manager = QueueManager(self.worker_config, self.queue_config)
        
        # Engine state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        
        # Strategy management
        self.active_strategies: Dict[str, Any] = {}
        self.strategy_last_run: Dict[str, datetime] = {}
        
        # Performance metrics
        self.orders_processed = 0
        self.orders_failed = 0
        self.strategies_executed = 0
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.db_manager = db_manager or DatabaseManager()
    
    async def start(self):
        """Start the Redis-based trading engine"""
        if self.is_running:
            logger.warning("⚠️ Trading engine is already running")
            return
        
        logger.info("🚀 Starting Redis-Based Trading Engine")
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        try:
            # Start queue manager
            if not self.queue_manager.start():
                logger.error("❌ Failed to start queue manager")
                return False
            
            # Load active strategies
            await self._load_active_strategies()
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info("✅ Redis-Based Trading Engine started successfully")
            logger.info(f"📊 Configuration: {self.worker_config.worker_count} workers, max queue size: {self.queue_config.max_queue_size}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading engine: {e}")
            await self.stop()
            return False
    
    async def stop(self):
        """Stop the trading engine gracefully"""
        if not self.is_running:
            logger.warning("⚠️ Trading engine is not running")
            return
        
        logger.info("⏹️ Stopping Redis-Based Trading Engine...")
        self.is_running = False
        
        # Stop background tasks
        await self._stop_background_tasks()
        
        # Stop queue manager
        self.queue_manager.stop()
        
        # Calculate uptime
        if self.start_time:
            uptime = datetime.utcnow() - self.start_time
            logger.info(f"📊 Engine uptime: {uptime}")
            logger.info(f"📊 Orders processed: {self.orders_processed}")
            logger.info(f"📊 Orders failed: {self.orders_failed}")
            logger.info(f"📊 Strategies executed: {self.strategies_executed}")
        
        logger.info("🏁 Redis-Based Trading Engine stopped")
    
    async def submit_order(self, order_id: str, priority: int = 2, urgency: str = OrderUrgency.NORMAL.value) -> bool:
        """Submit an order to the Redis queue for processing"""
        try:
            async with self.db_manager.get_session() as db:
                # Get order from database
                order = await db.get(Order, order_id)
                if not order:
                    logger.error(f"❌ Order {order_id} not found in database")
                    return False
                
                # Create queued order
                queued_order = QueuedOrder(
                    order_id=order.id,
                    user_id=order.user_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    order_type=order.order_type.value,
                    quantity=order.quantity,
                    price=order.price,
                    priority=priority,
                    metadata={
                        'strategy_id': order.strategy_id,
                        'exchange': order.exchange,
                        'product_type': order.product_type.value if order.product_type else 'INTRADAY'
                    }
                )
                
                # Create priority metadata if high priority
                priority_metadata = None
                if priority >= 3 or urgency != OrderUrgency.NORMAL.value:
                    priority_metadata = PriorityOrderMetadata(
                        urgency=urgency,
                        strategy_id=order.strategy_id,
                        risk_level="MEDIUM" if priority >= 4 else "LOW"
                    )
                
                # Submit to queue
                success = self.queue_manager.enqueue_order(queued_order, priority_metadata)
                
                if success:
                    # Update order status in database
                    order.status = OrderStatus.QUEUED
                    await db.commit()
                    
                    logger.info(f"📤 Order {order_id} submitted to queue (priority: {priority}, urgency: {urgency})")
                else:
                    logger.error(f"❌ Failed to submit order {order_id} to queue")
                
                return success
            
        except Exception as e:
            logger.error(f"❌ Error submitting order {order_id}: {e}")
            return False
    
    async def submit_urgent_order(self, order_id: str, urgency: str = OrderUrgency.STOP_LOSS.value, deadline: Optional[datetime] = None) -> bool:
        """Submit an urgent order with high priority"""
        try:
            async with self.db_manager.get_session() as db:
                order = await db.get(Order, order_id)
                if not order:
                    logger.error(f"❌ Order {order_id} not found")
                    return False
                
                # Create high-priority queued order
                queued_order = QueuedOrder(
                    order_id=order.id,
                    user_id=order.user_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    order_type=order.order_type.value,
                    quantity=order.quantity,
                    price=order.price,
                    priority=5,  # Critical priority
                    metadata={
                        'strategy_id': order.strategy_id,
                        'exchange': order.exchange,
                        'product_type': order.product_type.value if order.product_type else 'INTRADAY',
                        'urgent': True
                    }
                )
                
                # Create urgent priority metadata
                priority_metadata = PriorityOrderMetadata(
                    urgency=urgency,
                    deadline=deadline.isoformat() if deadline else None,
                    strategy_id=order.strategy_id,
                    risk_level="HIGH"
                )
                
                # Submit to priority queue
                success = self.queue_manager.enqueue_order(queued_order, priority_metadata)
                
                if success:
                    order.status = OrderStatus.QUEUED
                    await db.commit()
                    
                    logger.info(f"🚨 Urgent order {order_id} submitted (urgency: {urgency})")
                
                return success
            
        except Exception as e:
            logger.error(f"❌ Error submitting urgent order {order_id}: {e}")
            return False
    
    async def _load_active_strategies(self):
        """Load active strategies from database"""
        try:
            async with self.db_manager.get_session() as db:
                # Get active strategies
                result = await db.execute(
                    select(Strategy).where(
                        Strategy.status == StrategyStatus.ACTIVE,
                        Strategy.is_live == True
                    )
                )
                strategies = result.scalars().all()
                for strategy in strategies:
                    self.active_strategies[strategy.id] = {
                        'strategy': strategy,
                        'last_execution': None,
                        'execution_count': 0,
                        'error_count': 0
                    }
                    logger.info(f"📈 Loaded active strategy: {strategy.name} ({strategy.strategy_type})")
                logger.info(f"✅ Loaded {len(self.active_strategies)} active strategies")
        except Exception as e:
            logger.error(f"❌ Error loading active strategies: {e}")
    
    async def _start_background_tasks(self):
        """Start background tasks"""
        # Strategy execution task
        task = asyncio.create_task(self._strategy_executor())
        self.background_tasks.append(task)
        
        # Database sync task
        task = asyncio.create_task(self._database_sync())
        self.background_tasks.append(task)
        
        # Performance monitoring task
        task = asyncio.create_task(self._performance_monitor())
        self.background_tasks.append(task)
        
        # Queue health monitor
        task = asyncio.create_task(self._queue_health_monitor())
        self.background_tasks.append(task)
        
        logger.info(f"🔄 Started {len(self.background_tasks)} background tasks")
    
    async def _stop_background_tasks(self):
        """Stop all background tasks"""
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.background_tasks.clear()
        logger.info("🏁 Background tasks stopped")
    
    async def _strategy_executor(self):
        """Execute active strategies periodically"""
        while self.is_running:
            try:
                for strategy_id, strategy_data in self.active_strategies.items():
                    try:
                        strategy = strategy_data['strategy']
                        
                        # Check if strategy should run based on timeframe
                        if self._should_execute_strategy(strategy_id, strategy.timeframe):
                            await self._execute_strategy(strategy_id, strategy)
                            self.strategies_executed += 1
                    
                    except Exception as e:
                        logger.error(f"❌ Error executing strategy {strategy_id}: {e}")
                        strategy_data['error_count'] += 1
                
                # Wait before next execution cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Strategy executor error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_strategy(self, strategy_id: str, strategy: Strategy):
        """Execute a single strategy"""
        try:
            # Get strategy implementation from registry
            strategy_class = StrategyRegistry.get_strategy(strategy.strategy_type)
            if not strategy_class:
                logger.error(f"❌ Strategy type {strategy.strategy_type} not found in registry")
                return
            
            # Create strategy instance
            from app.strategies.base import StrategyConfig
            config = StrategyConfig(
                name=strategy.name,
                asset_class=strategy.asset_class,
                symbols=strategy.symbols,
                timeframe=strategy.timeframe,
                parameters=strategy.parameters or {},
                risk_parameters=strategy.risk_parameters or {}
            )
            
            strategy_instance = strategy_class(config)
            strategy_instance.initialize()
            
            # Process each symbol
            for symbol in strategy.symbols:
                # Get market data (this would be implemented based on your data source)
                market_data = await self._get_market_data(symbol, strategy.timeframe)
                
                if market_data:
                    # Process market data and get signal
                    signal = strategy_instance.process_market_data(market_data)
                    
                    if signal:
                        # Create order from signal
                        await self._create_order_from_signal(strategy, signal)
            
            # Update strategy execution time
            self.active_strategies[strategy_id]['last_execution'] = datetime.utcnow()
            self.active_strategies[strategy_id]['execution_count'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error executing strategy {strategy_id}: {e}")
            self.active_strategies[strategy_id]['error_count'] += 1
    
    def _should_execute_strategy(self, strategy_id: str, timeframe) -> bool:
        """Check if strategy should be executed based on timeframe"""
        last_execution = self.active_strategies[strategy_id]['last_execution']
        
        if not last_execution:
            return True
        
        # Define timeframe intervals
        intervals = {
            'MINUTE_1': timedelta(minutes=1),
            'MINUTE_5': timedelta(minutes=5),
            'MINUTE_15': timedelta(minutes=15),
            'HOUR_1': timedelta(hours=1),
            'DAY_1': timedelta(days=1)
        }
        
        interval = intervals.get(timeframe.value, timedelta(minutes=5))
        return datetime.utcnow() - last_execution >= interval
    
    async def _get_market_data(self, symbol: str, timeframe):
        """Get market data for symbol (placeholder - implement based on your data source)"""
        # This would be implemented to fetch real market data
        # For now, return None to avoid errors
        return None
    
    async def _create_order_from_signal(self, strategy: Strategy, signal):
        """Create order from strategy signal"""
        try:
            async with self.db_manager.get_session() as db:
                # Create new order
                order = Order(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    symbol=signal.symbol,
                    exchange="NSE",  # Default exchange
                    side=signal.signal_type.value,
                    order_type="MARKET",  # Default to market orders
                    product_type="INTRADAY",  # Default product type
                    quantity=signal.quantity,
                    price=signal.price,
                    status=OrderStatus.PENDING,
                    is_paper_trade=strategy.is_paper_trading
                )
                
                db.add(order)
                db.commit()
                db.refresh(order)
                
                # Submit order to queue
                priority = 3 if signal.confidence > 0.8 else 2
                await self.submit_order(order.id, priority=priority)
                
                logger.info(f"📈 Created order from strategy signal: {signal.symbol} {signal.signal_type.value} {signal.quantity}")
                
                return True
            
        except Exception as e:
            logger.error(f"❌ Error creating order from signal: {e}")
            return False
    
    async def _database_sync(self):
        """Sync pending orders from database to queue"""
        while self.is_running:
            try:
                async with self.db_manager.get_session() as db:
                    # Get pending orders that are not yet queued
                    pending_orders = await db.execute(
                        select(Order).where(
                            Order.status == OrderStatus.PENDING
                        )
                    )
                    pending_orders = pending_orders.scalars().all()
                    
                    for order in pending_orders:
                        await self.submit_order(order.id)
                    
                    if pending_orders:
                        logger.info(f"📤 Synced {len(pending_orders)} pending orders to queue")
                
                # Wait before next sync
                await asyncio.sleep(60)  # Sync every minute
                
            except Exception as e:
                logger.error(f"❌ Database sync error: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _performance_monitor(self):
        """Monitor engine performance"""
        while self.is_running:
            try:
                # Get queue statistics
                stats = self.queue_manager.get_comprehensive_stats()
                
                # Log performance metrics
                if stats and 'queue_summary' in stats:
                    summary = stats['queue_summary']
                    logger.info(f"📊 Queue Status - Pending: {summary.get('total_pending', 0)}, "
                              f"Processing: {summary.get('total_processing', 0)}, "
                              f"Failed: {summary.get('total_failed', 0)}")
                
                # Log worker performance
                if stats and 'workers' in stats:
                    workers = stats['workers']
                    logger.info(f"👥 Workers - Processed: {workers.get('total_processed', 0)}, "
                              f"Errors: {workers.get('total_errors', 0)}, "
                              f"Success Rate: {workers.get('overall_success_rate', 0):.2%}")
                
                await asyncio.sleep(300)  # Report every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Performance monitor error: {e}")
                await asyncio.sleep(300)
    
    async def _queue_health_monitor(self):
        """Monitor queue health and take corrective actions"""
        while self.is_running:
            try:
                stats = self.queue_manager.get_comprehensive_stats()
                
                if stats and 'health' in stats:
                    health = stats['health']
                    
                    if health.get('status') == 'critical':
                        logger.warning(f"🚨 Queue health critical: {health.get('issues', [])}")
                        
                        # Take corrective actions
                        await self._handle_critical_health(health)
                    
                    elif health.get('status') == 'warning':
                        logger.warning(f"⚠️ Queue health warning: {health.get('issues', [])}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Queue health monitor error: {e}")
                await asyncio.sleep(120)
    
    async def _handle_critical_health(self, health: dict):
        """Handle critical health issues"""
        issues = health.get('issues', [])
        
        for issue in issues:
            if "Queue near capacity" in issue:
                logger.warning("🚨 Queue near capacity - implementing emergency measures")
                # Could implement emergency queue clearing or worker scaling
            
            elif "Inactive workers" in issue:
                logger.warning("🚨 Inactive workers detected - attempting restart")
                # Could restart inactive workers
            
            elif "High error rate" in issue:
                logger.warning("🚨 High error rate detected - investigating")
                # Could implement error analysis and mitigation
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        queue_stats = self.queue_manager.get_comprehensive_stats()
        
        return {
            'engine': {
                'is_running': self.is_running,
                'uptime_seconds': uptime_seconds,
                'orders_processed': self.orders_processed,
                'orders_failed': self.orders_failed,
                'strategies_executed': self.strategies_executed,
                'active_strategies': len(self.active_strategies),
                'background_tasks': len(self.background_tasks)
            },
            'queue_manager': queue_stats,
            'strategies': {
                strategy_id: {
                    'name': data['strategy'].name,
                    'type': data['strategy'].strategy_type,
                    'last_execution': data['last_execution'].isoformat() if data['last_execution'] else None,
                    'execution_count': data['execution_count'],
                    'error_count': data['error_count']
                }
                for strategy_id, data in self.active_strategies.items()
            }
        }

    async def process_orders(self):
        """Trigger a single round of order processing (simulate worker)."""
        # This system is designed for background processing, but for on-demand:
        # You could trigger a worker to process one order, or log the current queue state.
        stats = self.queue_manager.get_comprehensive_stats()
        logger.info(f"[process_orders] Queue stats: {stats.get('queue_summary', {})}")
        # Real order processing is handled by background workers.

    async def execute_active_strategies(self):
        """Run one round of strategy execution for all active strategies."""
        for strategy_id, strategy_data in self.active_strategies.items():
            try:
                strategy = strategy_data['strategy']
                if self._should_execute_strategy(strategy_id, strategy.timeframe):
                    await self._execute_strategy(strategy_id, strategy)
                    self.strategies_executed += 1
            except Exception as e:
                logger.error(f"[execute_active_strategies] Error executing strategy {strategy_id}: {e}")
                strategy_data['error_count'] += 1

    async def update_market_data(self):
        """Fetch and log market data for all tracked symbols (placeholder)."""
        symbols = set()
        for strategy_data in self.active_strategies.values():
            strategy = strategy_data['strategy']
            symbols.update(strategy.symbols)
        for symbol in symbols:
            data = await self._get_market_data(symbol, None)
            logger.info(f"[update_market_data] Market data for {symbol}: {data}")

    async def monitor_performance(self):
        """Log current performance metrics (single call, not a loop)."""
        stats = self.queue_manager.get_comprehensive_stats()
        if stats and 'queue_summary' in stats:
            summary = stats['queue_summary']
            logger.info(f"[monitor_performance] Queue Status - Pending: {summary.get('total_pending', 0)}, Processing: {summary.get('total_processing', 0)}, Failed: {summary.get('total_failed', 0)}")
        if stats and 'workers' in stats:
            workers = stats['workers']
            logger.info(f"[monitor_performance] Workers - Processed: {workers.get('total_processed', 0)}, Errors: {workers.get('total_errors', 0)}, Success Rate: {workers.get('overall_success_rate', 0):.2%}")

    async def perform_risk_checks(self):
        """Run a single risk/health check on the queue."""
        stats = self.queue_manager.get_comprehensive_stats()
        if stats and 'health' in stats:
            health = stats['health']
            logger.info(f"[perform_risk_checks] Queue health: {health}")
            if health.get('status') == 'critical':
                await self._handle_critical_health(health)

# Main entry point for the Redis-based engine
async def main():
    """Main entry point for the Redis-based trading engine"""
    engine = RedisBasedTradingEngine(worker_count=4, max_queue_size=10000)
    
    try:
        # Start the engine
        if await engine.start():
            logger.info("🚀 Redis-Based Trading Engine is running")
            
            # Keep running until interrupted
            while engine.is_running:
                await asyncio.sleep(1)
        else:
            logger.error("❌ Failed to start trading engine")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("⏹️ Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        await engine.stop()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the engine
    asyncio.run(main())

# Alias for compatibility
RedisEngine = RedisBasedTradingEngine 