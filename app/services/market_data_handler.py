"""
Market Data Handler - Integration with Trading Engine

This handler provides:
1. Integration with the trading engine
2. Real-time market data processing
3. Strategy notifications for price updates
4. Performance optimized data handling
5. Multi-symbol monitoring
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time

from app.services.market_data_service import AngelOneMarketDataService, get_market_data_service
from app.brokers.base import MarketData
from app.models.base import TimeFrame
from app.database import get_database

logger = logging.getLogger(__name__)

class MarketDataHandler:
    """
    High-performance market data handler for trading strategies
    
    Features:
    - Real-time data distribution to multiple strategies
    - Efficient data caching and buffering
    - Performance metrics and monitoring
    - Configurable data filters and conditions
    - Strategy-specific data subscriptions
    """
    
    def __init__(self, broker_config_id: str):
        self.broker_config_id = broker_config_id
        self.market_data_service: Optional[AngelOneMarketDataService] = None
        
        # Strategy subscriptions
        self.strategy_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # strategy_id -> symbols
        self.symbol_subscribers: Dict[str, Set[str]] = defaultdict(set)      # symbol -> strategy_ids
        
        # Data callbacks
        self.data_callbacks: Dict[str, List[Callable]] = defaultdict(list)  # symbol -> callbacks
        
        # Performance tracking
        self.data_counters: Dict[str, int] = defaultdict(int)
        self.last_update_times: Dict[str, datetime] = {}
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Data buffers for strategies
        self.price_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.volume_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Configuration
        self.max_update_frequency = 1.0  # seconds between updates per symbol
        self.performance_log_interval = 60  # seconds
        
        # Task management
        self.running_tasks: List[asyncio.Task] = []
        self.is_running = False
        
    async def initialize(self):
        """Initialize the market data handler"""
        try:
            # Get market data service
            self.market_data_service = await get_market_data_service(self.broker_config_id)
            
            # Register for live data callbacks
            self.market_data_service.add_data_callback(self._on_market_data_update)
            
            # Start performance monitoring
            self._start_performance_monitor()
            
            self.is_running = True
            logger.info("Market data handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize market data handler: {e}")
            raise
    
    async def subscribe_strategy(self, strategy_id: str, symbols: List[str]) -> bool:
        """Subscribe a strategy to market data for specific symbols"""
        try:
            if not self.market_data_service:
                raise Exception("Market data service not initialized")
            
            # Add strategy subscriptions
            for symbol in symbols:
                self.strategy_subscriptions[strategy_id].add(symbol)
                self.symbol_subscribers[symbol].add(strategy_id)
            
            # Subscribe to market data service
            await self.market_data_service.subscribe_to_symbols(symbols)
            
            logger.info(f"Strategy {strategy_id} subscribed to {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe strategy {strategy_id}: {e}")
            return False
    
    async def unsubscribe_strategy(self, strategy_id: str, symbols: Optional[List[str]] = None):
        """Unsubscribe a strategy from market data"""
        try:
            if symbols is None:
                # Unsubscribe from all symbols for this strategy
                symbols = list(self.strategy_subscriptions.get(strategy_id, set()))
            
            for symbol in symbols:
                if strategy_id in self.strategy_subscriptions:
                    self.strategy_subscriptions[strategy_id].discard(symbol)
                
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(strategy_id)
                    
                    # Remove symbol if no more subscribers
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
                        # You might want to notify market data service to unsubscribe
            
            # Clean up empty strategy subscriptions
            if strategy_id in self.strategy_subscriptions and not self.strategy_subscriptions[strategy_id]:
                del self.strategy_subscriptions[strategy_id]
            
            logger.info(f"Strategy {strategy_id} unsubscribed from {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe strategy {strategy_id}: {e}")
    
    def add_data_callback(self, symbol: str, callback: Callable[[MarketData], None]):
        """Add a callback for specific symbol data updates"""
        self.data_callbacks[symbol].append(callback)
    
    async def _on_market_data_update(self, market_data: MarketData):
        """Handle market data updates from the service"""
        start_time = time.time()
        
        try:
            symbol = market_data.symbol
            
            # Check rate limiting
            if not self._should_process_update(symbol, market_data.timestamp):
                return
            
            # Update data buffers
            self._update_buffers(symbol, market_data)
            
            # Update counters
            self.data_counters[symbol] += 1
            self.last_update_times[symbol] = market_data.timestamp
            
            # Notify strategy subscribers
            await self._notify_subscribers(symbol, market_data)
            
            # Call registered callbacks
            for callback in self.data_callbacks.get(symbol, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(market_data)
                    else:
                        callback(market_data)
                except Exception as e:
                    logger.error(f"Error in data callback for {symbol}: {e}")
            
            # Track processing time
            processing_time = time.time() - start_time
            self.processing_times[symbol].append(processing_time)
            
        except Exception as e:
            logger.error(f"Error processing market data update: {e}")
    
    def _should_process_update(self, symbol: str, timestamp: datetime) -> bool:
        """Check if we should process this update based on rate limiting"""
        if symbol not in self.last_update_times:
            return True
        
        time_diff = (timestamp - self.last_update_times[symbol]).total_seconds()
        return time_diff >= self.max_update_frequency
    
    def _update_buffers(self, symbol: str, market_data: MarketData):
        """Update data buffers for the symbol"""
        # Price buffer
        self.price_buffers[symbol].append({
            'timestamp': market_data.timestamp,
            'ltp': market_data.ltp,
            'open': market_data.open,
            'high': market_data.high,
            'low': market_data.low,
            'close': market_data.close,
            'change': market_data.change,
            'change_pct': market_data.change_pct
        })
        
        # Volume buffer
        self.volume_buffers[symbol].append({
            'timestamp': market_data.timestamp,
            'volume': market_data.volume
        })
    
    async def _notify_subscribers(self, symbol: str, market_data: MarketData):
        """Notify all strategies subscribed to this symbol"""
        try:
            strategy_ids = self.symbol_subscribers.get(symbol, set())
            
            if not strategy_ids:
                return
            
            # Prepare notification data
            notification_data = {
                'type': 'market_data_update',
                'symbol': symbol,
                'data': market_data.to_dict(),
                'timestamp': market_data.timestamp.isoformat()
            }
            
            # Send to trading engine for strategy processing
            # This would typically go through a message queue
            for strategy_id in strategy_ids:
                await self._send_to_strategy(strategy_id, notification_data)
            
        except Exception as e:
            logger.error(f"Error notifying subscribers for {symbol}: {e}")
    
    async def _send_to_strategy(self, strategy_id: str, data: Dict):
        """Send data to a specific strategy"""
        try:
            # This would typically interface with your trading engine
            # For now, we'll just log the event
            logger.debug(f"Sending market data to strategy {strategy_id}: {data['symbol']}")
            
            # In a real implementation, you might:
            # 1. Send to Redis queue for strategy processing
            # 2. Call strategy callback directly
            # 3. Send via WebSocket to strategy process
            
        except Exception as e:
            logger.error(f"Error sending data to strategy {strategy_id}: {e}")
    
    def _start_performance_monitor(self):
        """Start performance monitoring task"""
        async def monitor_performance():
            while self.is_running:
                try:
                    await asyncio.sleep(self.performance_log_interval)
                    self._log_performance_metrics()
                except Exception as e:
                    logger.error(f"Error in performance monitor: {e}")
        
        task = asyncio.create_task(monitor_performance())
        self.running_tasks.append(task)
    
    def _log_performance_metrics(self):
        """Log performance metrics"""
        try:
            total_updates = sum(self.data_counters.values())
            active_symbols = len(self.symbol_subscribers)
            active_strategies = len(self.strategy_subscriptions)
            
            avg_processing_times = {}
            for symbol, times in self.processing_times.items():
                if times:
                    avg_processing_times[symbol] = sum(times) / len(times)
            
            logger.info(f"Market Data Performance - "
                       f"Active Symbols: {active_symbols}, "
                       f"Active Strategies: {active_strategies}, "
                       f"Total Updates: {total_updates}, "
                       f"Avg Processing Time: {sum(avg_processing_times.values()) / len(avg_processing_times) if avg_processing_times else 0:.4f}s")
            
        except Exception as e:
            logger.error(f"Error logging performance metrics: {e}")
    
    async def get_current_price(self, symbol: str, exchange: str = "NSE") -> Optional[MarketData]:
        """Get current price for a symbol"""
        if not self.market_data_service:
            return None
        
        return await self.market_data_service.get_live_price(symbol, exchange)
    
    async def get_price_history(self, symbol: str, timeframe: TimeFrame, 
                               duration_minutes: int = 60) -> List[Dict]:
        """Get recent price history for a symbol"""
        try:
            if not self.market_data_service:
                return []
            
            to_date = datetime.now()
            from_date = to_date - timedelta(minutes=duration_minutes)
            
            return await self.market_data_service.get_historical_data(
                symbol, "NSE", timeframe, from_date, to_date
            )
            
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return []
    
    def get_price_buffer(self, symbol: str, count: int = 100) -> List[Dict]:
        """Get recent price data from buffer"""
        if symbol not in self.price_buffers:
            return []
        
        buffer = self.price_buffers[symbol]
        return list(buffer)[-count:]
    
    def get_volume_buffer(self, symbol: str, count: int = 100) -> List[Dict]:
        """Get recent volume data from buffer"""
        if symbol not in self.volume_buffers:
            return []
        
        buffer = self.volume_buffers[symbol]
        return list(buffer)[-count:]
    
    def get_statistics(self, symbol: str) -> Dict[str, Any]:
        """Get statistics for a symbol"""
        return {
            'update_count': self.data_counters.get(symbol, 0),
            'last_update': self.last_update_times.get(symbol),
            'subscriber_count': len(self.symbol_subscribers.get(symbol, set())),
            'avg_processing_time': sum(self.processing_times.get(symbol, [])) / len(self.processing_times.get(symbol, [])) if self.processing_times.get(symbol) else 0,
            'buffer_size': len(self.price_buffers.get(symbol, []))
        }
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        return {
            'active_symbols': len(self.symbol_subscribers),
            'active_strategies': len(self.strategy_subscriptions),
            'total_updates': sum(self.data_counters.values()),
            'symbols': {symbol: self.get_statistics(symbol) for symbol in self.symbol_subscribers.keys()}
        }
    
    async def shutdown(self):
        """Shutdown the market data handler"""
        try:
            self.is_running = False
            
            # Cancel all running tasks
            for task in self.running_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.running_tasks:
                await asyncio.gather(*self.running_tasks, return_exceptions=True)
            
            logger.info("Market data handler shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global instance manager
_market_data_handlers: Dict[str, MarketDataHandler] = {}

async def get_market_data_handler(broker_config_id: str) -> MarketDataHandler:
    """Get or create market data handler instance"""
    if broker_config_id not in _market_data_handlers:
        handler = MarketDataHandler(broker_config_id)
        await handler.initialize()
        _market_data_handlers[broker_config_id] = handler
    
    return _market_data_handlers[broker_config_id]

async def shutdown_all_handlers():
    """Shutdown all market data handlers"""
    for handler in _market_data_handlers.values():
        await handler.shutdown()
    
    _market_data_handlers.clear() 