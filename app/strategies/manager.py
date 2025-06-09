"""
Strategy Manager for Dynamic Strategy Execution

This module provides a comprehensive strategy management system that uses
the AutomaticStrategyRegistry to dynamically load and execute trading strategies.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from app.utils.timezone_utils import ist_now as datetime_now
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base_strategy import BaseStrategy
from app.models.base import AssetClass
from .registry import AutomaticStrategyRegistry

logger = logging.getLogger(__name__)

class StrategyManager:
    """
    Manages multiple trading strategies and their execution
    
    Features:
    - Dynamic strategy loading using AutomaticStrategyRegistry
    - Concurrent strategy execution
    - Signal aggregation and filtering
    - Performance tracking
    - Strategy lifecycle management
    """
    
    def __init__(self, max_workers: int = 4):
        self.active_strategies: Dict[str, BaseStrategy] = {}
        self.strategy_configs: Dict[str, StrategyConfig] = {}
        self.strategy_signals: Dict[str, List[Dict[str, Any]]] = {}
        self.strategy_performance: Dict[str, Dict[str, float]] = {}
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(f"StrategyManager initialized with {max_workers} workers")
    
    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get all available strategies from registry with detailed metadata"""
        try:
            strategies = AutomaticStrategyRegistry.list_strategies()
            metadata_dict = AutomaticStrategyRegistry.get_all_metadata()
            
            available_strategies = {}
            
            for strategy_name in strategies:
                metadata = metadata_dict.get(strategy_name)
                if metadata:
                    available_strategies[strategy_name] = {
                        'class_name': metadata.class_name,
                        'asset_class': metadata.asset_class.value if metadata.asset_class else None,
                        'description': metadata.description,
                        'version': metadata.version,
                        'author': metadata.author,
                        'module_path': metadata.module_path,
                        'parameters': metadata.parameters,
                        'is_active': metadata.is_active,
                        'last_modified': metadata.last_modified.isoformat()
                    }
                else:
                    # Fallback for strategies without metadata
                    strategy_class = AutomaticStrategyRegistry.get_strategy_class(strategy_name)
                    available_strategies[strategy_name] = {
                        'class_name': strategy_class.__name__ if strategy_class else 'Unknown',
                        'asset_class': None,
                        'description': 'No metadata available',
                        'version': '1.0.0',
                        'author': 'Unknown',
                        'module_path': strategy_class.__module__ if strategy_class else 'Unknown',
                        'parameters': {},
                        'is_active': True,
                        'last_modified': datetime_now().isoformat()
                    }
            
            return available_strategies
            
        except Exception as e:
            logger.error(f"Error getting available strategies: {e}")
            return {}
    
    def get_strategies_by_asset_class(self, asset_class: AssetClass) -> List[str]:
        """Get strategies available for specific asset class"""
        return AutomaticStrategyRegistry.list_strategies_by_asset_class(asset_class)
    
    def create_strategy(self, strategy_name: str, config: StrategyConfig) -> bool:
        """
        Create and register a strategy instance
        
        Args:
            strategy_name: Name of strategy from registry
            config: Strategy configuration
            
        Returns:
            True if strategy created successfully, False otherwise
        """
        try:
            # Check if strategy already exists
            strategy_id = f"{strategy_name}_{config.name}"
            if strategy_id in self.active_strategies:
                logger.warning(f"Strategy {strategy_id} already exists")
                return False
            
            # Create strategy instance using registry
            strategy = AutomaticStrategyRegistry.create_strategy(strategy_name, config)
            if not strategy:
                logger.error(f"Failed to create strategy {strategy_name}")
                return False
            
            # Register strategy
            self.active_strategies[strategy_id] = strategy
            self.strategy_configs[strategy_id] = config
            self.strategy_signals[strategy_id] = []
            self.strategy_performance[strategy_id] = {
                'total_signals': 0,
                'successful_signals': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'last_signal_time': None
            }
            
            logger.info(f"✓ Strategy {strategy_id} created and registered")
            return True
            
        except Exception as e:
            logger.error(f"Error creating strategy {strategy_name}: {e}")
            return False
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove a strategy instance"""
        try:
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]
                del self.strategy_configs[strategy_id]
                del self.strategy_signals[strategy_id]
                del self.strategy_performance[strategy_id]
                logger.info(f"Strategy {strategy_id} removed")
                return True
            else:
                logger.warning(f"Strategy {strategy_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error removing strategy {strategy_id}: {e}")
            return False
    
    def get_active_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active strategies"""
        info = {}
        for strategy_id, strategy in self.active_strategies.items():
            config = self.strategy_configs[strategy_id]
            performance = self.strategy_performance[strategy_id]
            
            info[strategy_id] = {
                'strategy_class': strategy.__class__.__name__,
                'asset_class': config.asset_class.value,
                'symbols': config.symbols,
                'timeframe': config.timeframe.value,
                'is_active': config.is_active,
                'paper_trade': config.paper_trade,
                'performance': performance,
                'signal_count': len(self.strategy_signals[strategy_id])
            }
        
        return info
    
    def process_market_data_single(self, strategy_id: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process market data for a single strategy"""
        try:
            if strategy_id not in self.active_strategies:
                return None
            
            strategy = self.active_strategies[strategy_id]
            config = self.strategy_configs[strategy_id]
            
            # Check if strategy should process this data
            if not config.is_active:
                return None
            
            if market_data.symbol not in config.symbols:
                return None
            
            if market_data.asset_class != config.asset_class:
                return None
            
            # Process market data
            signal = strategy.process_market_data(market_data)
            
            if signal:
                # Validate signal
                if strategy.validate_signal(signal):
                    # Store signal
                    self.strategy_signals[strategy_id].append(signal)
                    
                    # Update performance metrics
                    perf = self.strategy_performance[strategy_id]
                    perf['total_signals'] += 1
                    perf['last_signal_time'] = datetime.utcnow().isoformat()
                    
                    logger.info(f"Signal generated by {strategy_id}: {signal.signal_type.value} {signal.symbol} @ {signal.confidence:.2f}")
                    return signal
                else:
                    logger.warning(f"Invalid signal from {strategy_id}: {signal}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing market data for {strategy_id}: {e}")
            return None
    
    def process_market_data(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process market data across all active strategies
        
        Args:
            market_data: Market data to process
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            # Get relevant strategies for this market data
            relevant_strategies = []
            for strategy_id, config in self.strategy_configs.items():
                if (config.is_active and 
                    market_data.symbol in config.symbols and 
                    market_data.asset_class == config.asset_class):
                    relevant_strategies.append(strategy_id)
            
            if not relevant_strategies:
                return signals
            
            # Process concurrently for better performance
            if len(relevant_strategies) > 1:
                futures = []
                for strategy_id in relevant_strategies:
                    future = self.executor.submit(self.process_market_data_single, strategy_id, market_data)
                    futures.append(future)
                
                # Collect results
                for future in futures:
                    try:
                        signal = future.result(timeout=5.0)  # 5 second timeout
                        if signal:
                            signals.append(signal)
                    except Exception as e:
                        logger.error(f"Error in concurrent strategy execution: {e}")
            else:
                # Single strategy - process directly
                signal = self.process_market_data_single(relevant_strategies[0], market_data)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            return signals
    
    def get_recent_signals(self, strategy_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent signals from strategies"""
        try:
            if strategy_id:
                if strategy_id in self.strategy_signals:
                    return self.strategy_signals[strategy_id][-limit:]
                return []
            else:
                # Get signals from all strategies
                all_signals = []
                for signals in self.strategy_signals.values():
                    all_signals.extend(signals)
                
                # Sort by timestamp and return recent ones
                all_signals.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                return all_signals[:limit]
                
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []
    
    def filter_signals(self, signals: List[Dict[str, Any]], 
                      min_confidence: float = 0.7,
                      allowed_symbols: Optional[Set[str]] = None,
                      signal_types: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """Filter signals based on criteria"""
        filtered = []
        
        for signal in signals:
            # Confidence filter
            if signal.get('confidence', 0) < min_confidence:
                continue
            
            # Symbol filter
            if allowed_symbols and signal.get('symbol') not in allowed_symbols:
                continue
            
            # Signal type filter
            if signal_types and signal.get('type') not in signal_types:
                continue
            
            filtered.append(signal)
        
        return filtered
    
    def update_strategy_performance(self, strategy_id: str, pnl: float, success: bool):
        """Update strategy performance metrics"""
        try:
            if strategy_id not in self.strategy_performance:
                return
            
            perf = self.strategy_performance[strategy_id]
            perf['total_pnl'] += pnl
            
            if success:
                perf['successful_signals'] += 1
            
            # Calculate win rate
            if perf['total_signals'] > 0:
                perf['win_rate'] = perf['successful_signals'] / perf['total_signals']
            
            logger.info(f"Updated performance for {strategy_id}: PnL={pnl}, Success={success}")
            
        except Exception as e:
            logger.error(f"Error updating strategy performance: {e}")
    
    def get_strategy_performance(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for strategies"""
        if strategy_id:
            return self.strategy_performance.get(strategy_id, {})
        else:
            return self.strategy_performance.copy()
    
    def shutdown(self):
        """Cleanup and shutdown strategy manager"""
        try:
            logger.info("Shutting down StrategyManager...")
            self.executor.shutdown(wait=True)
            self.active_strategies.clear()
            self.strategy_configs.clear()
            self.strategy_signals.clear()
            self.strategy_performance.clear()
            logger.info("StrategyManager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.shutdown()


# Example usage and testing functions
def create_example_strategies() -> List[Dict[str, Any]]:
    """Create example strategy configurations"""

    
    strategies = [
        {
            'name': 'simple_moving_average',
            'config': StrategyConfig(
                name='SMA_10_20_NIFTY',
                asset_class=AssetClass.EQUITY,
                symbols=['NIFTY', 'BANKNIFTY'],
                timeframe=TimeFrame.MINUTE_5,
                parameters={
                    'short_period': 10,
                    'long_period': 20,
                    'min_confidence': 0.6
                },
                risk_parameters={
                    'risk_per_trade': 0.02,
                    'max_position_size': 0.1
                },
                is_active=True,
                paper_trade=True
            )
        },
        {
            'name': 'rsi_mean_reversion',
            'config': StrategyConfig(
                name='RSI_14_EQUITY',
                asset_class=AssetClass.EQUITY,
                symbols=['RELIANCE', 'TCS', 'INFY'],
                timeframe=TimeFrame.MINUTE_15,
                parameters={
                    'rsi_period': 14,
                    'oversold_threshold': 30,
                    'overbought_threshold': 70,
                    'min_confidence': 0.7
                },
                risk_parameters={
                    'risk_per_trade': 0.015,
                    'max_position_size': 0.08
                },
                is_active=True,
                paper_trade=True
            )
        }
    ]
    
    return strategies


async def test_strategy_manager():
    """Test the strategy manager with example strategies"""
    print("🧪 Testing Strategy Manager...")
    
    # Initialize manager
    manager = StrategyManager(max_workers=2)
    
    # Show available strategies
    available = manager.get_available_strategies()
    print(f"📋 Available strategies: {list(available.keys())}")
    
    # Create example strategies
    example_configs = create_example_strategies()
    
    for strategy_def in example_configs:
        success = manager.create_strategy(strategy_def['name'], strategy_def['config'])
        print(f"{'✓' if success else '✗'} Created strategy: {strategy_def['name']}")
    
    # Show active strategies
    active = manager.get_active_strategies()
    print(f"🎯 Active strategies: {len(active)}")
    for strategy_id, info in active.items():
        print(f"  - {strategy_id}: {info['strategy_class']} on {info['symbols']}")
    
    # Simulate market data processing
    test_data = MarketData(
        symbol='NIFTY',
        timestamp=datetime.utcnow(),
        open=18000.0,
        high=18100.0,
        low=17950.0,
        close=18050.0,
        volume=1000000,
        asset_class=AssetClass.EQUITY,
        exchange='NSE'
    )
    
    print(f"📊 Processing test market data for {test_data.symbol}...")
    signals = manager.process_market_data(test_data)
    print(f"📈 Generated {len(signals)} signals")
    
    for signal in signals:
        print(f"  🎯 {signal.signal_type.value} {signal.symbol} @ confidence {signal.confidence:.2f}")
    
    # Get recent signals
    recent = manager.get_recent_signals(limit=5)
    print(f"📋 Recent signals: {len(recent)}")
    
    # Cleanup
    manager.shutdown()
    print("✅ Strategy Manager test completed")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_strategy_manager()) 