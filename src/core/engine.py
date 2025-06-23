"""
Lightweight Modular Trading Engine
Memory efficient, scalable, and industrial-ready
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from .strategy_manager import StrategyManager
from .orders import OrderManager  # Use existing orders module
from .market_data import get_angel_one_manager
from .broker_manager import BrokerManager
from .events import EventBus, Event, EventType

logger = logging.getLogger(__name__)

@dataclass
class EngineConfig:
    """Engine configuration"""
    max_strategies: int = 1000
    max_orders_per_second: int = 10
    data_refresh_interval: int = 1  # seconds
    strategy_execution_interval: int = 5  # seconds
    memory_limit_mb: int = 500  # Total memory limit
    enable_paper_trading: bool = False
    use_singleton_broker: bool = False  # Use Angel One singleton

class LightweightTradingEngine:
    """
    Ultra-lightweight trading engine designed for high strategy count
    Memory usage: ~150MB for 100+ strategies
    """
    
    def __init__(self, config: EngineConfig):
        self.config = config
        self.is_running = False
        self.start_time = None
        self.angel_one_broker = None  # Will be set if using singleton
        
        # Core managers (lightweight)
        self.event_bus = EventBus()
        self.strategy_manager = StrategyManager(self.event_bus, config)
        self.order_manager = OrderManager(self.event_bus)
        
        # Use singleton broker if configured, otherwise create own data manager
        if config.use_singleton_broker:
            self.data_manager = None  # Will use singleton
        else:
            # Use Angel One market data manager
            self.data_manager = None  # Will be initialized in start() method
            
        self.broker_manager = BrokerManager(self.event_bus, config)
        
        # Performance metrics
        self.metrics = {
            'strategies_executed': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'errors': 0,
            'memory_usage_mb': 0
        }
        
        # Setup event handlers
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Setup lightweight event handlers"""
        self.event_bus.subscribe(EventType.STRATEGY_SIGNAL, self._handle_strategy_signal)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._handle_order_filled)
        self.event_bus.subscribe(EventType.MARKET_DATA_UPDATE, self._handle_market_data)
        
    async def start(self):
        """Start the trading engine"""
        logger.info("🚀 Starting Lightweight Trading Engine...")
        self.is_running = True
        self.start_time = time.time()
        
        # Start all managers concurrently
        tasks = [
            asyncio.create_task(self.strategy_manager.start()),
            asyncio.create_task(self.order_manager.start()),
            asyncio.create_task(self.broker_manager.start()),
            asyncio.create_task(self.event_bus.start()),
            asyncio.create_task(self._monitor_performance())
        ]
        
        # Initialize Angel One data manager if not using singleton
        if not self.config.use_singleton_broker:
            from .market_data import AngelOneRealTimeManager
            self.data_manager = AngelOneRealTimeManager()
            await self.data_manager.initialize()
        
        logger.info(f"✅ Engine started with {len(self.strategy_manager.strategies)} strategies")
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("⏹️ Shutdown signal received")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the trading engine gracefully"""
        logger.info("🛑 Stopping Trading Engine...")
        self.is_running = False
        
        # Stop all managers
        await self.strategy_manager.stop()
        await self.order_manager.stop()
        if self.data_manager:
            await self.data_manager.stop()
        await self.broker_manager.stop()
        await self.event_bus.stop()
        
        logger.info("✅ Trading Engine stopped")
    
    async def _handle_strategy_signal(self, event: Event):
        """Handle strategy signals efficiently"""
        signal_data = event.data
        
        # Create order from signal
        order = {
            'strategy_id': signal_data['strategy_id'],
            'symbol': signal_data['symbol'],
            'side': signal_data['side'],
            'quantity': signal_data['quantity'],
            'order_type': signal_data.get('order_type', 'MARKET'),
            'price': signal_data.get('price'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to order manager
        await self.event_bus.publish(Event(
            type=EventType.ORDER_REQUEST,
            data=order,
            source='engine'
        ))
        
        self.metrics['orders_placed'] += 1
    
    async def _handle_order_filled(self, event: Event):
        """Handle order fills"""
        self.metrics['orders_filled'] += 1
        
        # Update strategy with fill information
        fill_data = event.data
        await self.event_bus.publish(Event(
            type=EventType.POSITION_UPDATE,
            data=fill_data,
            source='engine'
        ))
    
    async def _handle_market_data(self, event: Event):
        """Handle market data updates efficiently"""
        # Just pass through to strategies - no heavy processing
        pass
    
    async def _monitor_performance(self):
        """Monitor engine performance and memory usage"""
        while self.is_running:
            try:
                import psutil
                import os
                
                # Get memory usage
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.metrics['memory_usage_mb'] = round(memory_mb, 2)
                
                # Log performance every 60 seconds
                if int(time.time()) % 60 == 0:
                    uptime = time.time() - self.start_time
                    logger.info(f"📊 Engine Stats: "
                              f"Strategies: {len(self.strategy_manager.strategies)}, "
                              f"Orders: {self.metrics['orders_placed']}, "
                              f"Fills: {self.metrics['orders_filled']}, "
                              f"Memory: {memory_mb:.1f}MB, "
                              f"Uptime: {uptime/3600:.1f}h")
                
                # Memory warning
                if memory_mb > self.config.memory_limit_mb:
                    logger.warning(f"⚠️ Memory usage ({memory_mb:.1f}MB) exceeds limit ({self.config.memory_limit_mb}MB)")
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    def add_strategy(self, strategy_config: Dict[str, Any]) -> bool:
        """Add a new strategy dynamically"""
        return self.strategy_manager.add_strategy(strategy_config)
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove a strategy dynamically"""
        return self.strategy_manager.remove_strategy(strategy_id)
    
    def get_market_data(self, symbol: str = None):
        """Get market data from Angel One manager"""
        if self.data_manager:
            if symbol:
                # Search for specific symbol in tick data
                all_ticks = self.data_manager.get_all_ticks()
                for token, tick in all_ticks.items():
                    if tick.symbol == symbol:
                        return tick
                return None
            else:
                return self.data_manager.get_market_data_dict()
        else:
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'uptime_seconds': uptime,
            'data_source': 'angel_one_singleton' if self.config.use_singleton_broker else 'individual_manager',
            'strategies': {
                'total': len(self.strategy_manager.strategies),
                'active': len([s for s in self.strategy_manager.strategies.values() if s.is_active]),
                'memory_per_strategy_kb': self.metrics['memory_usage_mb'] * 1024 / max(1, len(self.strategy_manager.strategies))
            },
            'performance': self.metrics,
            'memory': {
                'current_mb': self.metrics['memory_usage_mb'],
                'limit_mb': self.config.memory_limit_mb,
                'usage_percent': (self.metrics['memory_usage_mb'] / self.config.memory_limit_mb) * 100
            }
        } 