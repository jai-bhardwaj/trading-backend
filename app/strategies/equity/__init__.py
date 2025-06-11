"""
Equity Trading Strategies

This module contains strategy implementations specifically designed for equity markets.
All strategies work with the AutomaticStrategyRegistry for automatic discovery.
"""

from .swing_momentum_strategy import SwingMomentumGain4Strategy
from .rsi_dmi_strategy import RSIDMIStrategy
from .rsi_dmi_intraday_delayed import RSIDMIIntradayDelayedStrategy
from .btst_momentum_strategy import BTSTMomentumGain4Strategy

# Import test strategy with error handling
try:
    from .test_strategy import TestStrategy
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import TestStrategy: {e}")
    TestStrategy = None

__all__ = [
    # Production strategies
    'SwingMomentumGain4Strategy',
    'RSIDMIStrategy', 
    'RSIDMIIntradayDelayedStrategy',
    'BTSTMomentumGain4Strategy'
]

# Add test strategy to exports if available
if TestStrategy is not None:
    __all__.append('TestStrategy')

# Strategy registry for easy access
EQUITY_STRATEGIES = {
    # Production strategies
    'swing_momentum_gain_4': SwingMomentumGain4Strategy,
    'rsi_dmi_equity': RSIDMIStrategy,
    'rsi_dmi_intraday_delayed': RSIDMIIntradayDelayedStrategy,
    'btst_momentum_gain_4': BTSTMomentumGain4Strategy,
}

# Add test strategy if available
if TestStrategy is not None:
    EQUITY_STRATEGIES['test_strategy'] = TestStrategy

def get_strategy_class(strategy_name: str):
    """Get strategy class by name."""
    return EQUITY_STRATEGIES.get(strategy_name)

def list_available_strategies():
    """List all available equity strategy names."""
    return list(EQUITY_STRATEGIES.keys())

def get_strategy_info():
    """Get information about all available strategies."""
    info = {
        'swing_momentum_gain_4': {
            'name': 'Swing Momentum Gain 4%',
            'description': 'MACD + Stochastic signals with 4% momentum, 2-day holding',
            'type': 'SWING_TRADING',
            'timeframe': '2D',
            'risk_level': 'MEDIUM'
        },
        'rsi_dmi_equity': {
            'name': 'RSI DMI Strategy',
            'description': 'RSI and DMI indicators for entry/exit signals',
            'type': 'TECHNICAL',
            'timeframe': 'INTRADAY',
            'risk_level': 'MEDIUM'
        },
        'rsi_dmi_intraday_delayed': {
            'name': 'RSI DMI Intraday Delayed',
            'description': 'RSI DMI with delayed execution and signal confirmation',
            'type': 'TECHNICAL_DELAYED',
            'timeframe': 'INTRADAY',
            'risk_level': 'LOW'
        },
        'btst_momentum_gain_4': {
            'name': 'BTST Momentum Gain 4%',
            'description': 'Buy Today Sell Tomorrow with 4% momentum signals',
            'type': 'BTST',
            'timeframe': '1D',
            'risk_level': 'MEDIUM'
        }
    }
    
    # Add test strategy info if available
    if TestStrategy is not None:
        info['test_strategy'] = {
            'name': 'Test Strategy',
            'description': 'Places orders at configurable intervals for system testing',
            'type': 'TESTING',
            'timeframe': 'CONFIGURABLE',
            'risk_level': 'LOW'
        }
    
    return info 