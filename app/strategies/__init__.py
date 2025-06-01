"""
Algorithmic Trading Strategies Package

This package contains the base strategy framework and implementations
for different asset classes and trading approaches.
"""

from .base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, AssetClass, TimeFrame, SignalType
from .registry import StrategyRegistry

# Initialize the registry first
_registry_initialized = False

def initialize_strategies():
    """Initialize and register all available strategies"""
    global _registry_initialized
    
    if _registry_initialized:
        return
    
    try:
        # Import equity strategy modules to auto-register them
        from .equity import btst_momentum_strategy, rsi_dmi_strategy, swing_momentum_strategy, rsi_dmi_intraday_delayed, test_strategy_2min
        print("✓ Equity strategies loaded")
    except ImportError as e:
        print(f"⚠ Could not load equity strategies: {e}")
    
    try:
        # Import derivatives strategy modules to auto-register them
        from . import derivatives
        print("✓ Derivatives strategies loaded")
    except ImportError as e:
        print(f"⚠ Could not load derivatives strategies: {e}")
    
    try:
        # Import crypto strategy modules to auto-register them  
        from . import crypto
        print("✓ Crypto strategies loaded")
    except ImportError as e:
        print(f"⚠ Could not load crypto strategies: {e}")
    
    _registry_initialized = True
    print(f"📊 Strategy Registry initialized with {len(StrategyRegistry.list_strategies())} strategies")

# Auto-initialize when module is imported
initialize_strategies()

__all__ = [
    'BaseStrategy',
    'StrategySignal', 
    'StrategyConfig',
    'MarketData',
    'AssetClass',
    'TimeFrame',
    'SignalType',
    'StrategyRegistry',
    'initialize_strategies'
] 