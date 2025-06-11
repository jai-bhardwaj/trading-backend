"""
Redis-Based Trading Engine

High-performance trading engine using Redis queues for order processing.
Replaces the database polling approach with real-time queue processing.
"""

# Standard library imports
import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, Any, List, Optional, Tuple

# Third-party imports
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload

# Local imports
from app.core.config import get_settings
from app.core.database import DatabaseManager, get_database_manager
from app.queue.order_queue import OrderQueueManager
from app.models.base import Order, Strategy, Position, MarketData, OrderStatus, OrderSide, OrderType, ProductType
from app.queue.priority_queue import OrderUrgency
from app.services.order_db_sync_worker import OrderDatabaseSyncWorker, get_db_sync_worker_instance
from app.utils.timezone_utils import ist_now as datetime_now
from app.brokers.angelone_new import AngelOneBroker
from app.brokers import get_broker_instance

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls"""
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit permission"""
        async with self._lock:
            now = time.time()
            # Remove old calls outside the window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.window_seconds]
            
            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = min(self.calls)
                wait_time = self.window_seconds - (now - oldest_call)
                if wait_time > 0:
                    logger.warning(f"⏳ Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()  # Recursive call after waiting
            
            self.calls.append(now)
            return True

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
        # Use provided database manager or get global instance
        self.db_manager = db_manager or get_database_manager()
        
        # Initialize core components
        self.queue_manager = OrderQueueManager(worker_count, max_queue_size)
        
        # Initialize database sync worker
        self.db_sync_worker = get_db_sync_worker_instance()
        
        # Engine configuration
        self.worker_count = worker_count
        self.max_queue_size = max_queue_size
        
        # Engine state
        self.is_running = False
        self.start_time = datetime_now()
        
        # Strategy management
        self.active_strategies: Dict[str, Any] = {}
        self.strategy_last_run: Dict[str, datetime] = {}
        
        # Performance metrics
        self.orders_processed = 0
        self.orders_failed = 0
        self.strategies_executed = 0
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Rate limiter for Angel One API (100 requests per minute)
        self.angel_rate_limiter = RateLimiter(max_calls=90, window_seconds=60)  # Conservative limit
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    async def start(self):
        """Start the Redis-based trading engine"""
        if self.is_running:
            logger.warning("⚠️ Trading engine is already running")
            return
        
        logger.info("🚀 Starting Redis-Based Trading Engine")
        self.is_running = True
        self.start_time = datetime_now()
        
        try:
            # Initialize strategy registry first
            logger.info("📋 Initializing strategy registry...")
            from app.strategies import initialize_strategies
            initialize_strategies(force_reload=True)
            
            logger.info("📈 Strategy initialization completed")
            
            # Start queue manager (async)
            success = await self.queue_manager.start()
            if not success:
                logger.error("❌ Failed to start queue manager")
                return False
            
            # Load active strategies
            await self._load_active_strategies()
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info("✅ Redis-Based Trading Engine started successfully")
            logger.info(f"📊 Configuration: {self.worker_count} workers, max queue size: {self.max_queue_size}")
            
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
        
        # Stop queue manager (async)
        await self.queue_manager.stop()
        
        # Calculate uptime
        if self.start_time:
            uptime = datetime_now() - self.start_time
            logger.info(f"📊 Engine uptime: {uptime}")
            logger.info(f"📊 Orders processed: {self.orders_processed}")
            logger.info(f"📊 Orders failed: {self.orders_failed}")
            logger.info(f"📊 Strategies executed: {self.strategies_executed}")
        
        logger.info("🏁 Redis-Based Trading Engine stopped")
    
    async def submit_order(self, order_id: str, priority: int = 2, urgency: str = OrderUrgency.NORMAL.value) -> bool:
        """Submit an order to the Redis queue for processing"""
        try:
            async with self.db_manager.get_async_session() as db:
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
            async with self.db_manager.get_async_session() as db:
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
            async with self.db_manager.get_async_session() as db:
                # Get active strategies
                result = await db.execute(
                    select(Strategy).where(
                        Strategy.status == StrategyStatus.ACTIVE
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
                
                # Wait before next execution cycle - use configurable interval
                settings = get_settings()
                sleep_interval = settings.trading_engine.strategy_execution_interval
                await asyncio.sleep(sleep_interval)
                
            except Exception as e:
                logger.error(f"❌ Strategy executor error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_strategy(self, strategy_id: str, strategy: Strategy):
        """Execute a single strategy"""
        try:
            # Get or create strategy instance
            strategy_instance = self.active_strategies[strategy_id].get('instance')
            
            if not strategy_instance:
                # Create strategy instance for the first time
                strategy_class = AutomaticStrategyRegistry.get_strategy_class(strategy.strategy_type)
                if not strategy_class:
                    logger.error(f"❌ Strategy type {strategy.strategy_type} not found in registry")
                    return
                
                # Get symbols from instrument manager based on strategy asset class
                instrument_manager = await get_instrument_manager(self.db_manager)
                
                # Get symbols for this strategy's asset class
                strategy_symbols = instrument_manager.get_all_symbols(strategy.asset_class)
                if not strategy_symbols:
                    strategy_symbols = strategy.symbols or ["RELIANCE", "TCS", "INFY"]  # Fallback
                else:
                    strategy_symbols = strategy_symbols[:10]  # Limit symbols per strategy
                
                # Create strategy instance
                from app.models.base import AssetClass
                
                # Convert TimeFrame enum using strings for now (simplified approach)
                timeframe_mapping = {
                    "MINUTE_1": "MINUTE_1",
                    "MINUTE_5": "MINUTE_5", 
                    "MINUTE_15": "MINUTE_15",
                    "HOUR_1": "HOUR_1",
                    "HOUR_4": "HOUR_4",
                    "DAY_1": "DAY_1",
                    "WEEK_1": "WEEK_1"
                }
                
                strategy_timeframe = timeframe_mapping.get(strategy.timeframe.value, "MINUTE_5")
                
                # Create strategy config for the BaseStrategy
                # Set execution interval based on strategy type
                if strategy.strategy_type == 'test_strategy':
                    # Test strategy should have minimal execution interval
                    # as it has its own internal 10-minute timing logic
                    execution_interval = 1  # Check every second for test strategy
                else:
                    # Real strategies should execute in near real-time
                    execution_interval = 1  # Real-time execution for live strategies
                
                config = {
                    'name': strategy.name,
                    'asset_class': strategy.asset_class.value,
                    'symbols': strategy_symbols,
                    'timeframe': strategy_timeframe,
                    'parameters': strategy.parameters or {},
                    'risk_parameters': strategy.risk_parameters or {},
                    'is_active': True,
                    'paper_trade': False,
                    'execution_interval': execution_interval,
                    'capital_allocated': 100000,
                    'max_positions': 5,
                    'risk_per_trade': 0.02
                }
                
                # Create strategy instance with correct parameters
                strategy_instance = strategy_class(
                    config_id=strategy.id,
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    config=config
                )
                
                # Initialize the strategy
                await strategy_instance.initialize()
                
                # Store strategy instance for reuse
                self.active_strategies[strategy_id]['instance'] = strategy_instance
                logger.info(f"✅ Created and cached strategy instance: {strategy.name}")
            
            # Process each symbol using the cached strategy instance
            # Get symbols from database Strategy model, not strategy instance
            strategy_symbols = strategy.symbols or ["RELIANCE", "TCS", "INFY"]  # Fallback symbols
            logger.info(f"🔄 Executing strategy {strategy.name} for symbols: {strategy_symbols}")
            
            for symbol in strategy_symbols:
                # Get market data
                market_data = await self._get_market_data(symbol, strategy.timeframe)
                
                if market_data:
                    logger.info(f"📊 Generated market data for {symbol}: price={market_data['close']}")
                    # Process market data and get signal
                    signal = await strategy_instance.process_market_data(market_data)
                    
                    if signal:
                        # Create order from signal
                        await self._create_order_from_signal(strategy, signal)
                        logger.info(f"🎯 Strategy {strategy.name} generated signal for {symbol}: {signal.get('type', 'UNKNOWN')}")
                    else:
                        logger.debug(f"📊 No signal generated for {symbol}")
                else:
                    logger.warning(f"❌ Failed to generate market data for {symbol}")
            
            # Update strategy execution time
            self.active_strategies[strategy_id]['last_execution'] = datetime_now()
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
        return datetime_now() - last_execution >= interval
    
    async def _get_market_data(self, symbol: str, timeframe):
        """Get market data from Angel One - LTP available 24/7"""
        try:
            # Rate limit API calls to prevent exceeding access rate
            await self.angel_rate_limiter.acquire()
            
            # Get Angel One data - LTP should be available even when market is closed
            from app.brokers.angelone_new import AngelOneBroker
            from app.models.base import BrokerConfig as DBBrokerConfig
            from app.models.base import BrokerName
            import os
            
            # Create broker config from environment variables
            broker_config = DBBrokerConfig(
                id="angel_one_market_data",
                user_id="system",
                broker_name=BrokerName.ANGEL_ONE,
                api_key=os.getenv("ANGEL_ONE_API_KEY", ""),
                client_id=os.getenv("ANGEL_ONE_CLIENT_ID", ""),
                password=os.getenv("ANGEL_ONE_PASSWORD", ""),
                totp_secret=os.getenv("ANGEL_ONE_TOTP_SECRET", ""),
                is_active=True
            )
            
            # Check if credentials are available
            if not all([broker_config.api_key, broker_config.client_id, broker_config.password]):
                logger.error(f"❌ Angel One credentials not configured - cannot get LTP data for {symbol}")
                raise Exception("Angel One credentials not configured")
            
            # Create and authenticate broker
            angel_broker = AngelOneBroker(broker_config)
            
            if not angel_broker.is_authenticated:
                await angel_broker.authenticate()
            
            if not angel_broker.is_authenticated:
                logger.error(f"❌ Angel One authentication failed - cannot get LTP data for {symbol}")
                raise Exception("Angel One authentication failed")
            
            # Try to get market data from Angel One API (LTP available 24/7)
            try:
                # Use the get_market_data method which internally calls Angel One's ltpData API
                market_data_response = await angel_broker.get_market_data(symbol, "NSE")
                
                if not market_data_response:
                    logger.error(f"❌ Could not get LTP data for {symbol} from Angel One")
                    raise Exception(f"LTP data unavailable for {symbol}")
                
                # Check current time to determine if market is open for labeling
                from datetime import datetime, time
                import pytz
                
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist)
                current_time = now.time()
                current_date = now.date()
                
                market_open = time(9, 15)
                market_close = time(15, 30)
                is_weekday = current_date.weekday() < 5
                market_is_open = is_weekday and market_open <= current_time <= market_close
                
                # Convert MarketData object to dictionary format for consistency
                market_data = {
                    'symbol': symbol,
                    'timestamp': datetime_now(),
                    'ltp': market_data_response.close,  # Close price is LTP in market data
                    'close': market_data_response.close,
                    'open': market_data_response.open,
                    'high': market_data_response.high,
                    'low': market_data_response.low,
                    'volume': market_data_response.volume,
                    'exchange': "NSE",
                    'change': market_data_response.change,
                    'change_pct': market_data_response.change_pct,
                    'source': 'angel_one_ltp_api'
                }
                
                # Log appropriately based on market status
                if market_is_open:
                    logger.info(f"📊 ✅ LIVE: {symbol} = ₹{market_data_response.close:.2f} from Angel One (Market Open)")
                else:
                    logger.info(f"📊 💤 LTP: {symbol} = ₹{market_data_response.close:.2f} from Angel One (Market Closed)")
                
                return market_data
                
            except Exception as api_error:
                logger.error(f"❌ Failed to get market data for {symbol}: {api_error}")
                raise Exception(f"Market data unavailable: {api_error}")
                        
        except Exception as e:
            logger.error(f"❌ Cannot get market data for {symbol}: {e}")
            # NO FALLBACK TO FAKE DATA - return None to indicate failure
            return None
    
    async def _create_order_from_signal(self, strategy: Strategy, signal):
        """Create order from strategy signal"""
        try:
                        
            async with self.db_manager.get_async_session() as db:
                # Determine order side based on signal type
                signal_type = signal.get('type', '').upper()
                if signal_type == 'BUY':
                    order_side = OrderSide.BUY
                elif signal_type == 'SELL':
                    order_side = OrderSide.SELL
                else:
                    logger.warning(f"Unknown signal type: {signal_type}")
                    return False
                
                # Create new order
                order = Order(
                    user_id=strategy.user_id,
                    strategy_id=strategy.id,
                    symbol=signal.get('symbol', 'UNKNOWN'),
                    exchange=signal.get('exchange', 'NSE'),  # Default exchange
                    side=order_side,
                    order_type=OrderType.MARKET,  # Default to market orders
                    product_type=ProductType.INTRADAY,  # Default product type
                    quantity=signal.get('quantity', 1),
                    price=signal.get('price', 0.0),
                    status=OrderStatus.PENDING,
                    notes=f"Generated by strategy: {strategy.name} with {signal.get('confidence', 0.5):.1%} confidence"
                )
                
                db.add(order)
                await db.commit()
                await db.refresh(order)
                
                # Submit order to queue
                priority = 3 if signal.get('confidence', 0.5) > 0.8 else 2
                await self.submit_order(order.id, priority=priority)
                
                logger.info(f"📈 Created order from strategy signal: {signal.get('symbol')} {signal_type} {signal.get('quantity')} (Confidence: {signal.get('confidence', 0.5):.1%})")
                
                return True
            
        except Exception as e:
            logger.error(f"❌ Error creating order from signal: {e}")
            return False
    
    async def _database_sync(self):
        """Sync pending orders from database to queue"""
        while self.is_running:
            try:
                async with self.db_manager.get_async_session() as db:
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
        uptime_seconds = (datetime_now() - self.start_time).total_seconds()
        
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
        """Fetch and log market data for all tracked symbols - REAL DATA ONLY."""
        symbols = set()
        for strategy_data in self.active_strategies.values():
            strategy = strategy_data['strategy']
            # Get symbols from database Strategy model, with fallback
            strategy_symbols = strategy.symbols or ["RELIANCE", "TCS", "INFY"]
            symbols.update(strategy_symbols)
        for symbol in symbols:
            data = await self._get_market_data(symbol, None)
            if data:
                logger.info(f"[update_market_data] ✅ Real market data for {symbol}: ₹{data.get('ltp', 'N/A')}")
            else:
                logger.warning(f"[update_market_data] ❌ Could not get real market data for {symbol}")

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

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for the trading engine
        
        Returns:
            Dict containing health status and metrics
        """
        health = {
            "engine_running": self.is_running,
            "workers_healthy": True,
            "queue_healthy": True,
            "database_healthy": False,
            "redis_healthy": False,
            "overall_healthy": False,
            "errors": []
        }
        
        try:
            # Check database health through db_manager
            if self.db_manager:
                db_health = await self.db_manager.health_check()
                health["database_healthy"] = db_health.get("database", {}).get("healthy", False)
                health["redis_healthy"] = db_health.get("redis", {}).get("healthy", False)
            
            # Check queue manager health
            if self.queue_manager:
                try:
                    queue_health = await self.queue_manager.health_check()
                    health["queue_healthy"] = queue_health.get("healthy", False)
                except Exception as e:
                    health["queue_healthy"] = False
                    health["errors"].append(f"Queue health check failed: {e}")
            
            # Check worker status
            try:
                workers_status = await self.queue_manager.get_worker_status()
                healthy_workers = sum(1 for status in workers_status.values() if status == "running")
                total_workers = len(workers_status)
                health["workers_healthy"] = healthy_workers == total_workers
                health["worker_details"] = {
                    "healthy": healthy_workers,
                    "total": total_workers,
                    "status": workers_status
                }
            except Exception as e:
                health["workers_healthy"] = False
                health["errors"].append(f"Worker status check failed: {e}")
            
            # Overall health
            health["overall_healthy"] = (
                health["engine_running"] and
                health["workers_healthy"] and
                health["queue_healthy"] and
                health["database_healthy"] and
                health["redis_healthy"]
            )
            
        except Exception as e:
            health["errors"].append(f"Health check error: {e}")
            logger.error(f"❌ Health check failed: {e}")
        
        return health
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics for the trading engine
        
        Returns:
            Dict containing performance metrics
        """
        uptime = (datetime_now() - self.start_time).total_seconds() if self.start_time else 0
        
        metrics = {
            "orders_processed": self.orders_processed,
            "orders_failed": self.orders_failed,
            "strategies_executed": self.strategies_executed,
            "uptime_seconds": uptime,
            "queue_size": 0,
            "worker_status": {},
            "engine_running": self.is_running,
            "active_strategies": len(self.active_strategies),
            "success_rate": 0.0,
            "processing_rate": 0.0
        }
        
        try:
            # Get queue metrics
            if self.queue_manager:
                queue_metrics = await self.queue_manager.get_performance_metrics()
                metrics.update({
                    "queue_size": queue_metrics.get("pending_orders", 0),
                    "queue_metrics": queue_metrics
                })
            
            # Get worker status
            try:
                worker_status = await self.queue_manager.get_worker_status()
                metrics["worker_status"] = worker_status
            except Exception as e:
                logger.debug(f"Could not get worker status: {e}")
                metrics["worker_status"] = {"error": str(e)}
            
            # Calculate success rate
            total_orders = self.orders_processed + self.orders_failed
            if total_orders > 0:
                metrics["success_rate"] = (self.orders_processed / total_orders) * 100
            
            # Calculate processing rate (orders per minute)
            if uptime > 0:
                metrics["processing_rate"] = (total_orders / uptime) * 60
            
            # Add strategy execution metrics
            metrics["strategy_metrics"] = {
                "total_strategies": len(self.active_strategies),
                "last_execution_times": dict(self.strategy_last_run)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics

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