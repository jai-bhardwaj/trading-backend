"""
Load Test Strategy for Testing System Capacity
A lightweight strategy to test how many strategies the system can handle.
"""

import asyncio
import logging
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, time
from ..base_strategy import BaseStrategy
from ..registry import AutomaticStrategyRegistry
from app.core.timezone_utils import now_ist
from app.models.base import AssetClass

logger = logging.getLogger(__name__)

@AutomaticStrategyRegistry.register("load_test_strategy", AssetClass.EQUITY)
class LoadTestStrategy(BaseStrategy):
    """
    Lightweight Load Test Strategy
    
    Simulates realistic strategy behavior for load testing:
    - Processes market data
    - Generates signals based on simple conditions
    - Updates metrics
    - Minimal memory footprint
    """
    
    async def on_initialize(self):
        """Initialize load test strategy parameters"""
        self.strategy_number = self.parameters.get('strategy_number', 1)
        self.signal_frequency = self.parameters.get('signal_frequency', 0.1)  # 10% chance per check
        self.symbols = self.parameters.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        self.max_signals = self.parameters.get('max_signals', 100)
        
        # State
        self.signals_generated = 0
        self.last_signal_time = None
        self.price_history = {}
        
        logger.info(f"🧪 Load Test Strategy #{self.strategy_number} initialized")
    
    async def process_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process market data with lightweight calculations"""
        try:
            symbol = market_data.get('symbol', 'UNKNOWN')
            price = market_data.get('close', 100.0)
            
            # Store price history (keep only last 5 prices for memory efficiency)
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(price)
            if len(self.price_history[symbol]) > 5:
                self.price_history[symbol].pop(0)
            
            # Simple signal generation logic
            if self.signals_generated < self.max_signals:
                if random.random() < self.signal_frequency:
                    signal = {
                        'type': random.choice(['BUY', 'SELL']),
                        'symbol': symbol,
                        'exchange': 'NSE',
                        'quantity': random.randint(1, 10),
                        'order_type': 'MARKET',
                        'product_type': 'INTRADAY',
                        'reason': f'Load test signal #{self.signals_generated + 1}',
                        'strategy_number': self.strategy_number
                    }
                    
                    self.signals_generated += 1
                    self.last_signal_time = now_ist()
                    
                    if self.signals_generated % 10 == 0:  # Log every 10th signal
                        logger.info(f"📊 Strategy #{self.strategy_number}: Generated signal #{self.signals_generated}")
                    
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Load test strategy #{self.strategy_number} error: {e}")
            return None
    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Handle market data updates"""
        # Minimal processing to simulate real strategy
        pass
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate signals for subscribed symbols"""
        signals = []
        
        # Simulate processing each symbol
        for symbol in self.symbols:
            # Create mock market data
            mock_data = {
                'symbol': symbol,
                'close': random.uniform(100, 3000),
                'volume': random.randint(1000, 100000)
            }
            
            signal = await self.process_market_data(mock_data)
            if signal:
                signals.append(signal)
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Update metrics
        self.metrics['custom_metrics'].update({
            'strategy_number': self.strategy_number,
            'signals_generated': self.signals_generated,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'memory_usage_mb': self._estimate_memory_usage()
        })
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        import sys
        
        # Rough estimation based on object sizes
        base_size = sys.getsizeof(self)
        price_history_size = sum(sys.getsizeof(prices) for prices in self.price_history.values())
        
        return (base_size + price_history_size) / (1024 * 1024)  # Convert to MB
    
    def get_load_test_stats(self) -> Dict[str, Any]:
        """Get load test specific statistics"""
        return {
            'strategy_number': self.strategy_number,
            'signals_generated': self.signals_generated,
            'last_signal_time': self.last_signal_time,
            'symbols_tracked': len(self.price_history),
            'estimated_memory_mb': self._estimate_memory_usage()
        } 