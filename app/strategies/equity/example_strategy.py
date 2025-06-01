"""
Example Strategy Implementation using Strategy Registry

This demonstrates how to create a strategy that automatically registers
itself with the StrategyRegistry using decorators.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

logger = logging.getLogger(__name__)

@StrategyRegistry.register("simple_moving_average", AssetClass.EQUITY)
class SimpleMovingAverageStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy
    
    Buy when short MA crosses above long MA
    Sell when short MA crosses below long MA
    """
    
    def initialize(self) -> None:
        """Initialize strategy components"""
        self.short_period = self.parameters.get('short_period', 10)
        self.long_period = self.parameters.get('long_period', 20)
        self.min_confidence = self.parameters.get('min_confidence', 0.6)
        
        # Price history for MA calculation
        self.price_history: Dict[str, list] = {}
        
        logger.info(f"Initialized {self.name} with periods: {self.short_period}/{self.long_period}")
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate signals"""
        try:
            symbol = market_data.symbol
            close_price = market_data.close
            
            # Initialize price history for new symbol
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            # Add current price
            self.price_history[symbol].append(close_price)
            
            # Keep only required history
            max_period = max(self.short_period, self.long_period)
            if len(self.price_history[symbol]) > max_period + 10:
                self.price_history[symbol] = self.price_history[symbol][-max_period:]
            
            # Need enough data for calculation
            if len(self.price_history[symbol]) < self.long_period:
                return None
            
            # Calculate moving averages
            prices = self.price_history[symbol]
            short_ma = sum(prices[-self.short_period:]) / self.short_period
            long_ma = sum(prices[-self.long_period:]) / self.long_period
            
            # Previous MAs for crossover detection
            if len(prices) >= self.long_period + 1:
                prev_short_ma = sum(prices[-self.short_period-1:-1]) / self.short_period
                prev_long_ma = sum(prices[-self.long_period-1:-1]) / self.long_period
                
                # Detect crossovers
                signal_type = None
                confidence = 0.0
                
                # Bullish crossover (short MA crosses above long MA)
                if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                    signal_type = SignalType.BUY
                    # Confidence based on MA separation
                    confidence = min(abs(short_ma - long_ma) / long_ma * 10, 1.0)
                
                # Bearish crossover (short MA crosses below long MA) 
                elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                    signal_type = SignalType.SELL
                    confidence = min(abs(short_ma - long_ma) / long_ma * 10, 1.0)
                
                # Generate signal if confidence is sufficient
                if signal_type and confidence >= self.min_confidence:
                    return StrategySignal(
                        signal_type=signal_type,
                        symbol=symbol,
                        confidence=confidence,
                        price=close_price,
                        metadata={
                            'short_ma': round(short_ma, 2),
                            'long_ma': round(long_ma, 2),
                            'ma_diff': round(short_ma - long_ma, 2),
                            'strategy': self.name
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing market data in {self.name}: {e}")
            return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate position size based on risk management"""
        try:
            # Risk per trade (default 2% of balance)
            risk_per_trade = self.risk_parameters.get('risk_per_trade', 0.02)
            max_position_size = self.risk_parameters.get('max_position_size', 0.1)  # 10% of balance
            
            # Calculate position value based on confidence
            position_value = current_balance * risk_per_trade * signal.confidence
            
            # Limit position size
            max_value = current_balance * max_position_size
            position_value = min(position_value, max_value)
            
            # Convert to quantity
            if signal.price and signal.price > 0:
                quantity = int(position_value / signal.price)
                return max(1, quantity)  # At least 1 share
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0


@StrategyRegistry.register("rsi_mean_reversion", AssetClass.EQUITY)
class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    
    Buy when RSI < oversold_threshold
    Sell when RSI > overbought_threshold
    """
    
    def initialize(self) -> None:
        """Initialize strategy components"""
        self.rsi_period = self.parameters.get('rsi_period', 14)
        self.oversold_threshold = self.parameters.get('oversold_threshold', 30)
        self.overbought_threshold = self.parameters.get('overbought_threshold', 70)
        self.min_confidence = self.parameters.get('min_confidence', 0.7)
        
        # Price change history for RSI calculation
        self.price_changes: Dict[str, list] = {}
        self.prev_prices: Dict[str, float] = {}
        
        logger.info(f"Initialized {self.name} with RSI period: {self.rsi_period}")
    
    def calculate_rsi(self, symbol: str) -> Optional[float]:
        """Calculate RSI for given symbol"""
        if symbol not in self.price_changes or len(self.price_changes[symbol]) < self.rsi_period:
            return None
        
        changes = self.price_changes[symbol][-self.rsi_period:]
        
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        if avg_loss == 0:
            return 100  # No losses, RSI = 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate RSI signals"""
        try:
            symbol = market_data.symbol
            close_price = market_data.close
            
            # Initialize data structures
            if symbol not in self.price_changes:
                self.price_changes[symbol] = []
                self.prev_prices[symbol] = close_price
                return None
            
            # Calculate price change
            price_change = close_price - self.prev_prices[symbol]
            self.price_changes[symbol].append(price_change)
            self.prev_prices[symbol] = close_price
            
            # Keep only required history
            if len(self.price_changes[symbol]) > self.rsi_period + 10:
                self.price_changes[symbol] = self.price_changes[symbol][-self.rsi_period:]
            
            # Calculate RSI
            rsi = self.calculate_rsi(symbol)
            if rsi is None:
                return None
            
            # Generate signals based on RSI levels
            signal_type = None
            confidence = 0.0
            
            if rsi <= self.oversold_threshold:
                signal_type = SignalType.BUY
                # Higher confidence for more extreme oversold conditions
                confidence = min((self.oversold_threshold - rsi) / self.oversold_threshold + 0.5, 1.0)
            
            elif rsi >= self.overbought_threshold:
                signal_type = SignalType.SELL
                # Higher confidence for more extreme overbought conditions
                confidence = min((rsi - self.overbought_threshold) / (100 - self.overbought_threshold) + 0.5, 1.0)
            
            # Generate signal if confidence is sufficient
            if signal_type and confidence >= self.min_confidence:
                return StrategySignal(
                    signal_type=signal_type,
                    symbol=symbol,
                    confidence=confidence,
                    price=close_price,
                    metadata={
                        'rsi': round(rsi, 2),
                        'oversold_threshold': self.oversold_threshold,
                        'overbought_threshold': self.overbought_threshold,
                        'strategy': self.name
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing market data in {self.name}: {e}")
            return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate position size based on RSI strategy risk management"""
        try:
            # Conservative position sizing for mean reversion
            risk_per_trade = self.risk_parameters.get('risk_per_trade', 0.015)  # 1.5%
            max_position_size = self.risk_parameters.get('max_position_size', 0.08)  # 8%
            
            # Position value based on confidence and RSI extremity
            position_value = current_balance * risk_per_trade * signal.confidence
            max_value = current_balance * max_position_size
            position_value = min(position_value, max_value)
            
            if signal.price and signal.price > 0:
                quantity = int(position_value / signal.price)
                return max(1, quantity)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0 