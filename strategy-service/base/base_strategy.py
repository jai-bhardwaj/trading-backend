"""
Base Strategy Class for Strategy Service
"""
import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from shared.models import MarketDataTick, TradingSignal, SignalType, StrategyConfig, StrategyStats
from base.market_data_consumer import MarketDataConsumer
from base.signal_publisher import SignalPublisher
from base.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy_id = config.strategy_id
        self.symbols = config.symbols
        self.parameters = config.parameters
        self.enabled = config.enabled
        
        # Initialize components
        self.market_data_consumer = MarketDataConsumer(
            redis_url=config.redis_url,
            consumer_group=config.consumer_group
        )
        self.signal_publisher = SignalPublisher(
            redis_url=config.redis_url,
            signal_channel=config.signal_channel
        )
        self.indicators = TechnicalIndicators()
        
        # Statistics
        self.stats = StrategyStats(strategy_id=self.strategy_id)
        self.running = False
        
        # Market data buffer for strategies
        self.market_data_buffer: Dict[str, List[MarketDataTick]] = {}
        
        logger.info(f"✅ Initialized strategy: {self.strategy_id}")
    
    async def start(self):
        """Start the strategy"""
        try:
            logger.info(f"🚀 Starting strategy: {self.strategy_id}")
            
            # Connect to Redis
            consumer_connected = await self.market_data_consumer.connect()
            publisher_connected = await self.signal_publisher.connect()
            
            if not consumer_connected or not publisher_connected:
                logger.error(f"❌ Failed to connect to Redis for strategy: {self.strategy_id}")
                return False
            
            # Set tick handler
            self.market_data_consumer.set_tick_handler(self._handle_tick)
            
            # Start consuming market data
            self.running = True
            await self.market_data_consumer.start_consuming(self.symbols)
            
            logger.info(f"✅ Strategy {self.strategy_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start strategy {self.strategy_id}: {e}")
            self.stats.errors_count += 1
            self.stats.last_error = str(e)
            self.stats.is_healthy = False
            return False
    
    async def stop(self):
        """Stop the strategy"""
        try:
            logger.info(f"🛑 Stopping strategy: {self.strategy_id}")
            
            self.running = False
            
            # Stop consuming
            await self.market_data_consumer.stop()
            
            # Disconnect from Redis
            await self.market_data_consumer.disconnect()
            await self.signal_publisher.disconnect()
            
            logger.info(f"✅ Strategy {self.strategy_id} stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping strategy {self.strategy_id}: {e}")
    
    def _handle_tick(self, tick: MarketDataTick):
        """Handle incoming market data tick"""
        try:
            # Update statistics
            self.stats.ticks_processed += 1
            
            # Add to buffer
            symbol = tick.symbol
            if symbol not in self.market_data_buffer:
                self.market_data_buffer[symbol] = []
            
            self.market_data_buffer[symbol].append(tick)
            
            # Keep buffer size manageable (last 1000 ticks per symbol)
            if len(self.market_data_buffer[symbol]) > 1000:
                self.market_data_buffer[symbol] = self.market_data_buffer[symbol][-1000:]
            
            # Run strategy logic
            asyncio.create_task(self._run_strategy_logic(tick))
            
        except Exception as e:
            logger.error(f"❌ Error handling tick for {self.strategy_id}: {e}")
            self.stats.errors_count += 1
            self.stats.last_error = str(e)
    
    async def _run_strategy_logic(self, tick: MarketDataTick):
        """Run strategy logic for a tick"""
        try:
            # Get market data for all symbols
            market_data = {}
            for symbol in self.symbols:
                latest_tick = self.market_data_consumer.get_latest_tick(symbol)
                if latest_tick:
                    market_data[symbol] = latest_tick
            
            # Run strategy implementation
            signals = await self.run(market_data)
            
            # Publish signals
            for signal in signals:
                await self.publish_signal(signal)
                
        except Exception as e:
            logger.error(f"❌ Error in strategy logic for {self.strategy_id}: {e}")
            self.stats.errors_count += 1
            self.stats.last_error = str(e)
    
    @abstractmethod
    async def run(self, market_data: Dict[str, MarketDataTick]) -> List[TradingSignal]:
        """
        Run the strategy logic and return trading signals
        
        Args:
            market_data: Dictionary mapping symbol to latest MarketDataTick
            
        Returns:
            List of TradingSignal objects
        """
        pass
    
    async def publish_signal(self, signal: TradingSignal):
        """Publish a trading signal"""
        try:
            success = await self.signal_publisher.publish_signal(signal)
            if success:
                self.stats.signals_generated += 1
                self.stats.last_signal_time = datetime.now()
                logger.info(f"📊 Strategy {self.strategy_id} generated signal: {signal.symbol} {signal.signal_type.value}")
            else:
                logger.error(f"❌ Failed to publish signal for {self.strategy_id}")
                
        except Exception as e:
            logger.error(f"❌ Error publishing signal for {self.strategy_id}: {e}")
            self.stats.errors_count += 1
            self.stats.last_error = str(e)
    
    def get_historical_buffer(self, symbol: str, periods: int = 100) -> List[MarketDataTick]:
        """Get historical market data from buffer"""
        if symbol not in self.market_data_buffer:
            return []
        
        buffer = self.market_data_buffer[symbol]
        return buffer[-periods:] if periods > 0 else buffer
    
    def get_latest_tick(self, symbol: str) -> Optional[MarketDataTick]:
        """Get the latest tick for a symbol"""
        buffer = self.get_historical_buffer(symbol, 1)
        return buffer[0] if buffer else None
    
    def calculate_quantity(self, price: float) -> int:
        """Calculate order quantity based on capital and price"""
        try:
            capital = self.parameters.get('capital', 100000)
            max_quantity = self.parameters.get('max_quantity', 1000)
            min_quantity = self.parameters.get('min_quantity', 1)
            
            if price <= 0:
                return min_quantity
            
            quantity = int(capital / price)
            quantity = max(min_quantity, min(quantity, max_quantity))
            
            return quantity
            
        except Exception as e:
            logger.error(f"❌ Error calculating quantity: {e}")
            return 1
    
    def health_check(self) -> Dict[str, Any]:
        """Get strategy health status"""
        return {
            "strategy_id": self.strategy_id,
            "enabled": self.enabled,
            "running": self.running,
            "is_healthy": self.stats.is_healthy,
            "symbols": self.symbols,
            "uptime": (datetime.now() - self.stats.uptime_start).total_seconds(),
            "last_error": self.stats.last_error
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            "strategy_id": self.strategy_id,
            "signals_generated": self.stats.signals_generated,
            "last_signal_time": self.stats.last_signal_time.isoformat() if self.stats.last_signal_time else None,
            "ticks_processed": self.stats.ticks_processed,
            "errors_count": self.stats.errors_count,
            "uptime_start": self.stats.uptime_start.isoformat(),
            "is_healthy": self.stats.is_healthy,
            "last_error": self.stats.last_error,
            "consumer_stats": self.market_data_consumer.get_stats() if hasattr(self.market_data_consumer, 'get_stats') else {},
            "publisher_stats": self.signal_publisher.get_stats()
        }
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.strategy_id} enabled={self.enabled} running={self.running}>"
