"""
Strategy Manager
Manages trading strategies with lightweight memory usage
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .events import EventBus, Event, EventType

logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    strategy_id: str
    name: str
    symbols: List[str]
    parameters: Dict[str, Any]
    is_active: bool = True
    
class BaseStrategy:
    """Base strategy class"""
    
    def __init__(self, config: StrategyConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.is_active = config.is_active
        self.last_execution = None
        
    async def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute strategy logic - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement execute method")

class StrategyManager:
    """
    Lightweight strategy manager
    Memory usage: ~5MB per 100 strategies
    """
    
    def __init__(self, event_bus: EventBus, config):
        self.event_bus = event_bus
        self.config = config
        self.strategies: Dict[str, BaseStrategy] = {}
        self.is_running = False
        
        # Performance tracking
        self.executions_count = 0
        self.signals_generated = 0
        
    async def start(self):
        """Start strategy manager"""
        self.is_running = True
        logger.info(f"🧠 Strategy Manager started with {len(self.strategies)} strategies")
        
        # Start execution loop
        while self.is_running:
            try:
                await self._run_strategies()
                await asyncio.sleep(1)  # Execute every second
            except Exception as e:
                logger.error(f"❌ Strategy execution error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop strategy manager"""
        self.is_running = False
        logger.info(f"🧠 Strategy Manager stopped. Executions: {self.executions_count}")
    
    async def _run_strategies(self):
        """Run all active strategies"""
        # This would get market data and execute strategies
        # For now, it's a placeholder
        pass
    
    def add_strategy(self, strategy_config: StrategyConfig) -> bool:
        """Add a new strategy"""
        try:
            # Create strategy instance based on config
            strategy = self._create_strategy_instance(strategy_config)
            self.strategies[strategy_config.strategy_id] = strategy
            logger.info(f"➕ Added strategy: {strategy_config.name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add strategy {strategy_config.name}: {e}")
            return False
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove a strategy"""
        if strategy_id in self.strategies:
            strategy = self.strategies.pop(strategy_id)
            logger.info(f"➖ Removed strategy: {strategy.config.name}")
            return True
        return False
    
    def _create_strategy_instance(self, config: StrategyConfig) -> BaseStrategy:
        """Create strategy instance - placeholder implementation"""
        return BaseStrategy(config, self.event_bus)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy manager statistics"""
        return {
            'total_strategies': len(self.strategies),
            'active_strategies': len([s for s in self.strategies.values() if s.is_active]),
            'executions_count': self.executions_count,
            'signals_generated': self.signals_generated
        } 