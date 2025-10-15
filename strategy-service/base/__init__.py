"""
Base Strategy Framework Package

This package contains the base classes and utilities for all trading strategies:
- BaseStrategy: Abstract base class for all strategies
- MarketDataConsumer: Redis Stream consumer for market data
- SignalPublisher: Redis publisher for trading signals
- TechnicalIndicators: Collection of technical analysis indicators
"""

from .base_strategy import BaseStrategy
from .market_data_consumer import MarketDataConsumer
from .signal_publisher import SignalPublisher
from .indicators import TechnicalIndicators

__all__ = [
    'BaseStrategy',
    'MarketDataConsumer', 
    'SignalPublisher',
    'TechnicalIndicators'
]
