"""
Strategy Registry for Dynamic Strategy Discovery and Management

This module provides a registry system for managing different strategy implementations
and making it easy to add new strategies without modifying core engine code.
"""

from typing import Dict, Type, List, Optional
import logging
from .base import BaseStrategy, AssetClass

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    Registry for managing strategy classes
    
    This allows for dynamic discovery and instantiation of strategies
    without hardcoding strategy types in the engine.
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _asset_class_strategies: Dict[AssetClass, List[str]] = {}
    
    @classmethod
    def register(cls, strategy_name: str, asset_class: AssetClass = None):
        """
        Decorator to register a strategy class
        
        Usage:
            @StrategyRegistry.register("mean_reversion", AssetClass.EQUITY)
            class MeanReversionStrategy(BaseStrategy):
                pass
        """
        def decorator(strategy_class: Type[BaseStrategy]):
            cls._strategies[strategy_name] = strategy_class
            
            # Group by asset class for easier discovery
            if asset_class:
                if asset_class not in cls._asset_class_strategies:
                    cls._asset_class_strategies[asset_class] = []
                cls._asset_class_strategies[asset_class].append(strategy_name)
            
            logger.info(f"Registered strategy: {strategy_name} for {asset_class}")
            return strategy_class
        
        return decorator
    
    @classmethod
    def register_strategy(cls, strategy_name: str, strategy_class: Type[BaseStrategy], 
                         asset_class: AssetClass = None):
        """
        Programmatically register a strategy class
        
        Args:
            strategy_name: Unique name for the strategy
            strategy_class: Strategy class that extends BaseStrategy
            asset_class: Asset class this strategy is designed for
        """
        cls._strategies[strategy_name] = strategy_class
        
        if asset_class:
            if asset_class not in cls._asset_class_strategies:
                cls._asset_class_strategies[asset_class] = []
            cls._asset_class_strategies[asset_class].append(strategy_name)
        
        logger.info(f"Registered strategy: {strategy_name} for {asset_class}")
    
    @classmethod
    def get_strategy_class(cls, strategy_name: str) -> Optional[Type[BaseStrategy]]:
        """
        Get strategy class by name
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Strategy class or None if not found
        """
        return cls._strategies.get(strategy_name)
    
    @classmethod
    def create_strategy(cls, strategy_name: str, config) -> Optional[BaseStrategy]:
        """
        Create strategy instance by name
        
        Args:
            strategy_name: Name of the strategy
            config: Strategy configuration
            
        Returns:
            Strategy instance or None if strategy not found
        """
        strategy_class = cls.get_strategy_class(strategy_name)
        if strategy_class:
            try:
                return strategy_class(config)
            except Exception as e:
                logger.error(f"Error creating strategy {strategy_name}: {e}")
                return None
        else:
            logger.error(f"Strategy {strategy_name} not found in registry")
            return None
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Get list of all registered strategy names"""
        return list(cls._strategies.keys())
    
    @classmethod
    def list_strategies_by_asset_class(cls, asset_class: AssetClass) -> List[str]:
        """Get list of strategies for specific asset class"""
        return cls._asset_class_strategies.get(asset_class, [])
    
    @classmethod
    def get_all_asset_classes(cls) -> List[AssetClass]:
        """Get list of all asset classes with registered strategies"""
        return list(cls._asset_class_strategies.keys())
    
    @classmethod
    def get_strategy_info(cls) -> Dict[str, Dict]:
        """Get information about all registered strategies"""
        info = {}
        for name, strategy_class in cls._strategies.items():
            info[name] = {
                'class_name': strategy_class.__name__,
                'module': strategy_class.__module__,
                'doc': strategy_class.__doc__ or "No description available"
            }
        return info
    
    @classmethod
    def clear_registry(cls):
        """Clear all registered strategies (mainly for testing)"""
        cls._strategies.clear()
        cls._asset_class_strategies.clear()
        logger.info("Strategy registry cleared") 