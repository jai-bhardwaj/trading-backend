"""
Algorithmic Trading Strategies Package

This package contains the base strategy framework and implementations
for different asset classes and trading approaches.

The strategies are automatically discovered and registered using the
AutomaticStrategyRegistry system.
"""

import logging
from .base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, AssetClass, TimeFrame, SignalType
from .registry import AutomaticStrategyRegistry, StrategyRegistry, StrategyMetadata

logger = logging.getLogger(__name__)

# Initialize the automatic strategy registry
_registry_initialized = False

def initialize_strategies(force_reload: bool = False):
    """
    Initialize and automatically discover all available strategies
    
    Args:
        force_reload: Force reload of all strategy files
    """
    global _registry_initialized
    
    if _registry_initialized and not force_reload:
        logger.info("Strategy registry already initialized")
        return
    
    try:
        logger.info("🚀 Initializing Automatic Strategy Registry...")
        
        # Initialize the automatic registry
        AutomaticStrategyRegistry.initialize(auto_discover=True)
        
        # Log discovered strategies
        strategies = AutomaticStrategyRegistry.list_strategies()
        logger.info(f"✅ Strategy Registry initialized with {len(strategies)} strategies:")
        
        # Group strategies by asset class for better reporting
        for asset_class in AssetClass:
            asset_strategies = AutomaticStrategyRegistry.list_strategies_by_asset_class(asset_class)
            if asset_strategies:
                logger.info(f"   📈 {asset_class.value}: {asset_strategies}")
        
        # Log any strategies without asset class
        unclassified = []
        for strategy_name in strategies:
            metadata = AutomaticStrategyRegistry.get_strategy_metadata(strategy_name)
            if not metadata or not metadata.asset_class:
                unclassified.append(strategy_name)
        
        if unclassified:
            logger.warning(f"   ⚠️  Unclassified: {unclassified}")
        
        _registry_initialized = True
        logger.info("🎯 Strategy Registry initialization complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize strategy registry: {e}")
        raise

def reload_strategies():
    """
    Hot reload all strategy files (useful for development)
    """
    try:
        logger.info("🔄 Hot reloading strategies...")
        count = AutomaticStrategyRegistry.hot_reload()
        logger.info(f"✅ Hot reload complete: {count} strategies available")
        return count
    except Exception as e:
        logger.error(f"❌ Failed to hot reload strategies: {e}")
        return 0

def get_strategy_info():
    """
    Get comprehensive information about all registered strategies
    
    Returns:
        Dict with strategy information and metadata
    """
    try:
        strategies = AutomaticStrategyRegistry.list_strategies()
        metadata_dict = AutomaticStrategyRegistry.get_all_metadata()
        
        info = {
            'total_strategies': len(strategies),
            'asset_classes': {},
            'strategies': {}
        }
        
        # Group by asset class
        for asset_class in AssetClass:
            asset_strategies = AutomaticStrategyRegistry.list_strategies_by_asset_class(asset_class)
            if asset_strategies:
                info['asset_classes'][asset_class.value] = asset_strategies
        
        # Add detailed strategy information
        for strategy_name in strategies:
            metadata = metadata_dict.get(strategy_name)
            if metadata:
                info['strategies'][strategy_name] = {
                    'class_name': metadata.class_name,
                    'asset_class': metadata.asset_class.value if metadata.asset_class else None,
                    'description': metadata.description,
                    'version': metadata.version,
                    'author': metadata.author,
                    'file_path': metadata.file_path,
                    'module_path': metadata.module_path,
                    'last_modified': metadata.last_modified.isoformat(),
                    'parameters': metadata.parameters,
                    'is_active': metadata.is_active
                }
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting strategy info: {e}")
        return {'error': str(e)}

# Auto-initialize when module is imported
try:
    initialize_strategies()
except Exception as e:
    logger.error(f"Failed to auto-initialize strategies: {e}")

# Export the main components
__all__ = [
    # Base framework
    'BaseStrategy',
    'StrategySignal', 
    'StrategyConfig',
    'MarketData',
    'AssetClass',
    'TimeFrame',
    'SignalType',
    
    # Registry system
    'AutomaticStrategyRegistry',
    'StrategyRegistry',  # Backward compatibility alias
    'StrategyMetadata',
    
    # Utility functions
    'initialize_strategies',
    'reload_strategies',
    'get_strategy_info'
] 