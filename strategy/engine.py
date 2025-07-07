"""
Strategy Engine - Signal generation and publishing (dynamic configuration)
"""

import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict
from strategy.market_data import MarketDataProvider
from strategy.registry import register_strategies_to_registry, get_strategy_class
from shared.config import ConfigLoader

logger = logging.getLogger(__name__)

class StrategyEngine:
    """Strategy engine with live market data and signal publishing (uses registry)"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.redis_client = None
        self.market_data_provider = MarketDataProvider()
        self.strategies = {}  # strategy_id -> strategy instance
        self.running = False
        self.config_loader = ConfigLoader()
    
    async def initialize(self):
        try:
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connected")
            
            # Initialize market data provider
            await self.market_data_provider.initialize()
            logger.info("✅ Market data provider initialized")
            
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
            else:
                logger.warning(f"⚠️ Strategy class not found for {strategy_id}")
    
    async def publish_signal(self, signal: Dict):
        try:
            await self.redis_client.publish(
                'strategy_signals', 
                json.dumps(signal, default=str)
            )
            logger.info(f"✅ Published signal: {signal['symbol']} {signal['signal_type']}")
        except Exception as e:
            logger.error(f"❌ Error publishing signal: {e}")
    
    async def run_strategy(self, strategy_id: str) -> List[Dict]:
        try:
            if strategy_id not in self.strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            strategy = self.strategies[strategy_id]
            if not strategy.enabled:
                return []
            signals = await strategy.run()
            for signal in signals:
                await self.publish_signal(signal)
            return signals
        except Exception as e:
            logger.error(f"❌ Strategy execution error: {e}")
            return []
    
    async def run_all_strategies(self) -> List[Dict]:
        all_signals = []
        for strategy_id, strategy in self.strategies.items():
            signals = await self.run_strategy(strategy_id)
            all_signals.extend(signals)
        return all_signals
    
    async def start_continuous_execution(self, interval_seconds: int = 60):
        self.running = True
        logger.info(f"🚀 Starting continuous strategy execution (interval: {interval_seconds}s)")
        while self.running:
            try:
                await self.run_all_strategies()
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