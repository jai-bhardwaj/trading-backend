"""
Strategy Engine - Signal generation and publishing (dynamic configuration)
"""

import asyncio
import json
import logging
import redis.asyncio as redis
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict
from strategy.registry import register_strategies_to_registry, get_strategy_class
from shared.config import ConfigLoader
from shared.market_hours import market_hours
import threading

logger = logging.getLogger(__name__)

class StrategyEngine:
    """Strategy engine with live market data and signal publishing (uses registry)"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.redis_client = None
        self.strategies = {}  # strategy_id -> strategy instance
        self.running = False
        self.config_loader = ConfigLoader()
        self.live_market_data = {}  # symbol -> MarketDataTick
        self._market_data_lock = asyncio.Lock()
        self.strategy_stats = {}  # Track strategy performance
        self.market_data_provider = None  # Initialize market data provider
    
    async def initialize(self):
        try:
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connected")
            
            
            # Load configurations
            self.config_loader.load_symbols()
            self.config_loader.load_strategies()
            logger.info("✅ Configurations loaded")
            
            # Register strategies
            register_strategies_to_registry()
            logger.info("✅ Strategies registered in registry")
            
            # Load strategies dynamically
            await self._load_strategies_from_config()
            logger.info("✅ Strategy engine initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy engine: {e}")
            raise
    
    async def _load_strategies_from_config(self):
        """Load strategies dynamically from configuration"""
        loaded_count = 0
        for strategy_id, strategy_config in self.config_loader.strategies.items():
            if not strategy_config.enabled:
                logger.info(f"⏭️ Skipping disabled strategy: {strategy_id}")
                continue
                
            strategy_cls = get_strategy_class(strategy_id)
            if strategy_cls:
                # Convert StrategyConfig to dict format expected by strategies
                config_dict = {
                    "strategy_id": strategy_config.strategy_id,
                    "symbols": strategy_config.symbols,
                    "parameters": strategy_config.parameters,
                    "enabled": strategy_config.enabled
                }
                self.strategies[strategy_id] = strategy_cls(config_dict, self.market_data_provider)
                logger.info(f"✅ Added strategy: {strategy_id} with {len(strategy_config.symbols)} symbols")
                loaded_count += 1
            else:
                logger.warning(f"⚠️ Strategy class not found for {strategy_id} - make sure it's registered in the registry")
        
        if loaded_count == 0:
            logger.warning("⚠️ No strategies loaded from configuration. Please ensure:")
            logger.warning("   1. Strategies exist in the database with valid configurations")
            logger.warning("   2. All strategies are registered in the strategy registry")
            logger.warning("   3. Strategy classes exist and are properly imported")
        else:
            logger.info(f"✅ Loaded {loaded_count} strategies from configuration")
    
    async def publish_signal(self, signal: Dict):
        try:
            await self.redis_client.publish(
                'strategy_signals', 
                json.dumps(signal, default=str)
            )
            logger.info(f"✅ Published signal: {signal['symbol']} {signal['signal_type']}")
        except Exception as e:
            logger.error(f"❌ Error publishing signal: {e}")
    
    def _collect_all_symbols(self):
        """Collect all unique symbols needed by all strategies"""
        symbols = set()
        for strategy in self.strategies.values():
            for symbol in strategy.symbols:
                symbols.add(symbol)
        return list(symbols)
    
    async def _handle_market_tick(self, tick: Any):
        """Handle incoming market tick from Redis"""
        try:
            async with self._market_data_lock:
                self.live_market_data[tick.symbol] = tick
                
            # Log every 100th tick
            total_ticks = len(self.live_market_data)
            if total_ticks % 100 == 0:
                logger.info(f"📊 Received tick for {tick.symbol} @ {tick.ltp} (Total symbols: {total_ticks})")
        except Exception as e:
            logger.error(f"Error handling market tick: {e}")


    async def _get_market_data_for_symbols(self, symbols):
        """Return a dict: symbol -> latest market data from Redis"""
        symbol_data = {}
        
        # Get data from Redis live market data
        async with self._market_data_lock:
            for symbol in symbols:
                if symbol in self.live_market_data:
                    tick = self.live_market_data[symbol]
                    # Convert MarketDataTick to compatible format
                    symbol_data[symbol] = tick
        
        if not symbol_data:
            logger.debug(f"📊 No live data available for symbols: {symbols}")
        
        return symbol_data

    async def run_strategy(self, strategy_id: str) -> List[Dict]:
        try:
            if strategy_id not in self.strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            strategy = self.strategies[strategy_id]
            if not strategy.enabled:
                return []
            # Pass live market data for this strategy's symbols
            market_data = await self._get_market_data_for_symbols(strategy.symbols)
            signals = await strategy.run(market_data)
            for signal in signals:
                # Add strategy_id to the signal before publishing
                signal['strategy_id'] = strategy_id
                await self.publish_signal(signal)
            return signals
        except Exception as e:
            logger.error(f"❌ Strategy execution error: {e}")
            return []
    
    async def run_all_strategies(self) -> List[Dict]:
        all_signals = []
        execution_time = datetime.now()
        
        for strategy_id, strategy in self.strategies.items():
            signals = await self.run_strategy(strategy_id)
            if signals:
                # Track strategy performance
                if strategy_id not in self.strategy_stats:
                    self.strategy_stats[strategy_id] = {"signals_generated": 0, "last_signal": None}
                self.strategy_stats[strategy_id]["signals_generated"] += len(signals)
                self.strategy_stats[strategy_id]["last_signal"] = execution_time
                
                logger.info(f"📊 Strategy {strategy_id} generated {len(signals)} signals")
                for signal in signals:
                    logger.info(f"📊 Strategy {strategy_id}: {signal['symbol']} {signal['signal_type']} (confidence: {signal['confidence']:.2f})")
            
            all_signals.extend(signals)
        
        if all_signals:
            logger.info(f"📊 Strategy execution at {execution_time.strftime('%H:%M:%S')}: {len(all_signals)} signals generated")
        else:
            logger.debug(f"📊 Strategy execution at {execution_time.strftime('%H:%M:%S')}: No signals")
        
        return all_signals
    
    async def start_continuous_execution(self, interval_seconds: int = 60):
        self.running = True
        logger.info(f"🚀 Starting continuous strategy execution (interval: {interval_seconds}s)")
        
        # For real-time execution, use more frequent logging
        log_interval = 10 if interval_seconds <= 5 else 60
        
        execution_count = 0
        market_closed_count = 0
        last_market_status_log = None
        
        while self.running:
            try:
                # Check market hours first
                market_status = market_hours.get_market_status()
                current_time = market_status["current_time"]
                
                if not market_status["is_open"]:
                    market_closed_count += 1
                    
                    # Log market closed status only once or every 10 minutes
                    should_log = (
                        market_closed_count == 1 or 
                        market_closed_count % 60 == 0 or  # Log every 60 executions (10 minutes with 10s interval)
                        (last_market_status_log and 
                         (datetime.now() - last_market_status_log).seconds > 600)  # 10 minutes
                    )
                    
                    if should_log:
                        logger.info(f"📊 Market closed - {current_time} IST ({market_status['current_day']})")
                        logger.info(f"📊 Market hours: {market_status['market_hours']}")
                        if market_status['next_event_time']:
                            logger.info(f"📊 {market_status['next_event']}: {market_status['next_event_time']}")
                        logger.info(f"📊 Pausing strategy execution until market opens...")
                        last_market_status_log = datetime.now()
                    
                    # Sleep longer when market is closed to reduce API calls
                    # Use 5 minutes when market is closed instead of the normal interval
                    sleep_time = 300 if interval_seconds <= 60 else interval_seconds * 2
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    # Reset counter when market opens
                    if market_closed_count > 0:
                        logger.info(f"📊 Market opened - {current_time} IST")
                        logger.info(f"📊 Resuming strategy execution...")
                        market_closed_count = 0
                        last_market_status_log = None
                
                # Only execute strategies when market is open
                await self.run_all_strategies()
                execution_count += 1
                
                # Log execution count every 10 executions for real-time mode
                if interval_seconds <= 5 and execution_count % log_interval == 0:
                    logger.info(f"🔄 Executed strategies {execution_count} times")
                
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"❌ Error in continuous execution: {e}")
                await asyncio.sleep(5)
    
    async def stop_continuous_execution(self):
        self.running = False
        logger.info("🛑 Stopped continuous strategy execution")
    
    async def close(self):
        if self.market_data_provider:
            await self.market_data_provider.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("✅ Strategy engine closed")

    def get_strategy_stats(self) -> Dict:
        """Get strategy performance statistics"""
        return self.strategy_stats 