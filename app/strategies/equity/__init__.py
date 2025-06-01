"""
Equity Trading Strategies

This module contains strategy implementations specifically designed for equity markets.
All strategies are automatically registered with the StrategyRegistry when imported.
"""

from .rsi_dmi_strategy import RSIDMIStrategy
from .rsi_dmi_intraday_delayed import RSIDMIIntradayDelayedStrategy
from .btst_momentum_strategy import BTSTMomentumGain4Strategy
from .swing_momentum_strategy import SwingMomentumGain4Strategy
from .test_strategy_2min import TestStrategy2Min

# Register strategies in the registry for compatibility
from app.strategies.registry import StrategyRegistry
from app.strategies.base import AssetClass

# Register all equity strategies
StrategyRegistry.register_strategy("rsi_dmi_equity", RSIDMIStrategy, AssetClass.EQUITY)
StrategyRegistry.register_strategy("rsi_dmi_intraday_delayed", RSIDMIIntradayDelayedStrategy, AssetClass.EQUITY)
StrategyRegistry.register_strategy("btst_momentum_gain_4", BTSTMomentumGain4Strategy, AssetClass.EQUITY)
StrategyRegistry.register_strategy("swing_momentum_gain_4", SwingMomentumGain4Strategy, AssetClass.EQUITY)
StrategyRegistry.register_strategy("test_strategy_2min", TestStrategy2Min, AssetClass.EQUITY)

# Register missing strategies with aliases to test_strategy_2min
StrategyRegistry.register_strategy("sma_crossover", TestStrategy2Min, AssetClass.EQUITY)
StrategyRegistry.register_strategy("momentum_breakout", TestStrategy2Min, AssetClass.EQUITY)

__all__ = [
    'BTSTMomentumGain4Strategy',
    'RSIDMIIntradayDelayedStrategy',
    'RSIDMIStrategy',
    'SwingMomentumGain4Strategy',
    'TestStrategy2Min'
] 