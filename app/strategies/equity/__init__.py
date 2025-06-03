"""
Equity Trading Strategies

This module contains strategy implementations specifically designed for equity markets.
All strategies have been migrated to work with the new cleaned schema and enhanced
strategy execution system using the updated BaseStrategy class.
"""

from .test_strategy_2min import TestStrategy2Min
from .example_strategy import SimpleMovingAverageStrategy, RSIMeanReversionStrategy
from .swing_momentum_strategy import SwingMomentumGain4Strategy
from .rsi_dmi_strategy import RSIDMIStrategy
from .rsi_dmi_intraday_delayed import RSIDMIIntradayDelayedStrategy
from .btst_momentum_strategy import BTSTMomentumGain4Strategy

__all__ = [
    # Test strategies
    'TestStrategy2Min',
    
    # Example strategies
    'SimpleMovingAverageStrategy',
    'RSIMeanReversionStrategy',
    
    # Production strategies
    'SwingMomentumGain4Strategy',
    'RSIDMIStrategy', 
    'RSIDMIIntradayDelayedStrategy',
    'BTSTMomentumGain4Strategy'
]

# Strategy registry for easy access
EQUITY_STRATEGIES = {
    # Test and example strategies
    'test_strategy_2min': TestStrategy2Min,
    'simple_moving_average': SimpleMovingAverageStrategy,
    'rsi_mean_reversion': RSIMeanReversionStrategy,
    
    # Production strategies
    'swing_momentum_gain_4': SwingMomentumGain4Strategy,
    'rsi_dmi_equity': RSIDMIStrategy,
    'rsi_dmi_intraday_delayed': RSIDMIIntradayDelayedStrategy,
    'btst_momentum_gain_4': BTSTMomentumGain4Strategy,
}

def get_strategy_class(strategy_name: str):
    """Get strategy class by name."""
    return EQUITY_STRATEGIES.get(strategy_name)

def list_available_strategies():
    """List all available equity strategy names."""
    return list(EQUITY_STRATEGIES.keys())

def get_strategy_info():
    """Get information about all available strategies."""
    return {
        'test_strategy_2min': {
            'name': 'Test Strategy 2 Min',
            'description': 'Test strategy that places orders every 2 minutes for system testing',
            'type': 'TEST',
            'timeframe': '2M',
            'risk_level': 'LOW'
        },
        'simple_moving_average': {
            'name': 'Simple Moving Average Crossover',
            'description': 'Buy when short MA crosses above long MA, sell when it crosses below',
            'type': 'TREND_FOLLOWING',
            'timeframe': 'INTRADAY',
            'risk_level': 'MEDIUM'
        },
        'rsi_mean_reversion': {
            'name': 'RSI Mean Reversion',
            'description': 'Buy when RSI is oversold, sell when overbought',
            'type': 'MEAN_REVERSION',
            'timeframe': 'INTRADAY',
            'risk_level': 'MEDIUM'
        },
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