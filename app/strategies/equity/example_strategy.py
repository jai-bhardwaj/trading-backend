"""
Example Strategy Implementation for the New Trading Engine
Updated to work with the new cleaned schema and enhanced strategy execution system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class SimpleMovingAverageStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy
    
    Buy when short MA crosses above long MA
    Sell when short MA crosses below long MA
    """
    
    async def on_initialize(self):
        """Initialize strategy components"""
        self.short_period = self.config.get('short_period', 10)
        self.long_period = self.config.get('long_period', 20)
        self.min_confidence = self.config.get('min_confidence', 0.6)
        
        # Price history for MA calculation
        self.price_history: Dict[str, list] = {}
        
        # Subscribe to configured symbols
        symbols = self.config.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        await self.subscribe_to_instruments(symbols)
        
        logger.info(f"Initialized SimpleMovingAverageStrategy with periods: {self.short_period}/{self.long_period}")
    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data updates"""
        try:
            close_price = data.get('ltp', data.get('close', 0))
            
            # Initialize price history for new symbol
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            # Add current price
            self.price_history[symbol].append(close_price)
            
            # Keep only required history
            max_period = max(self.short_period, self.long_period)
            if len(self.price_history[symbol]) > max_period + 10:
                self.price_history[symbol] = self.price_history[symbol][-max_period:]
                
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals based on MA crossover"""
        signals = []
        
        try:
            for symbol, prices in self.price_history.items():
                if len(prices) < self.long_period + 1:
                    continue
                
                # Calculate moving averages
                short_ma = sum(prices[-self.short_period:]) / self.short_period
                long_ma = sum(prices[-self.long_period:]) / self.long_period
                
                # Previous MAs for crossover detection
                prev_short_ma = sum(prices[-self.short_period-1:-1]) / self.short_period
                prev_long_ma = sum(prices[-self.long_period-1:-1]) / self.long_period
                
                current_price = prices[-1]
                signal_type = None
                confidence = 0.0
                
                # Bullish crossover (short MA crosses above long MA)
                if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                    signal_type = 'BUY'
                    # Confidence based on MA separation
                    confidence = min(abs(short_ma - long_ma) / long_ma * 10, 1.0)
                
                # Bearish crossover (short MA crosses below long MA) 
                elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
                    # Check if we have a position to close
                    position_key = f"{symbol}_NSE_INTRADAY"
                    if position_key in self.positions and self.positions[position_key].quantity > 0:
                        signal_type = 'SELL'
                        confidence = min(abs(short_ma - long_ma) / long_ma * 10, 1.0)
                
                # Generate signal if confidence is sufficient
                if signal_type and confidence >= self.min_confidence:
                    quantity = 10 if signal_type == 'BUY' else self.positions[f"{symbol}_NSE_INTRADAY"].quantity
                    
                    signals.append({
                        'type': signal_type,
                        'symbol': symbol,
                        'exchange': 'NSE',
                        'quantity': quantity,
                        'order_type': 'MARKET',
                        'product_type': 'INTRADAY',
                        'reason': f'MA crossover - Short: {short_ma:.2f}, Long: {long_ma:.2f}'
                    })
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.price_history),
            'total_price_points': sum(len(prices) for prices in self.price_history.values()),
            'short_period': self.short_period,
            'long_period': self.long_period
        })

class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    
    Buy when RSI < oversold_threshold
    Sell when RSI > overbought_threshold
    """
    
    async def on_initialize(self):
        """Initialize strategy components"""
        self.rsi_period = self.config.get('rsi_period', 14)
        self.oversold_threshold = self.config.get('oversold_threshold', 30)
        self.overbought_threshold = self.config.get('overbought_threshold', 70)
        self.min_confidence = self.config.get('min_confidence', 0.7)
        
        # Price change history for RSI calculation
        self.price_changes: Dict[str, list] = {}
        self.prev_prices: Dict[str, float] = {}
        
        # Subscribe to configured symbols
        symbols = self.config.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        await self.subscribe_to_instruments(symbols)
        
        logger.info(f"Initialized RSIMeanReversionStrategy with RSI period: {self.rsi_period}")
    
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
    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data for RSI calculation"""
        try:
            close_price = data.get('ltp', data.get('close', 0))
            
            # Initialize data structures
            if symbol not in self.price_changes:
                self.price_changes[symbol] = []
                self.prev_prices[symbol] = close_price
                return
            
            # Calculate price change
            price_change = close_price - self.prev_prices[symbol]
            self.price_changes[symbol].append(price_change)
            self.prev_prices[symbol] = close_price
            
            # Keep only required history
            if len(self.price_changes[symbol]) > self.rsi_period + 10:
                self.price_changes[symbol] = self.price_changes[symbol][-self.rsi_period:]
                
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate RSI-based signals"""
        signals = []
        
        try:
            for symbol in self.prev_prices.keys():
                rsi = self.calculate_rsi(symbol)
                if rsi is None:
                    continue
                
                current_price = self.prev_prices[symbol]
                signal_type = None
                confidence = 0.0
                
                if rsi <= self.oversold_threshold:
                    # Check if we don't already have a position
                    position_key = f"{symbol}_NSE_INTRADAY"
                    if position_key not in self.positions or self.positions[position_key].quantity == 0:
                        signal_type = 'BUY'
                        # Higher confidence for more extreme oversold conditions
                        confidence = min((self.oversold_threshold - rsi) / self.oversold_threshold + 0.5, 1.0)
                
                elif rsi >= self.overbought_threshold:
                    # Check if we have a position to close
                    position_key = f"{symbol}_NSE_INTRADAY"
                    if position_key in self.positions and self.positions[position_key].quantity > 0:
                        signal_type = 'SELL'
                        # Higher confidence for more extreme overbought conditions
                        confidence = min((rsi - self.overbought_threshold) / (100 - self.overbought_threshold) + 0.5, 1.0)
                
                # Generate signal if confidence is sufficient
                if signal_type and confidence >= self.min_confidence:
                    quantity = 10 if signal_type == 'BUY' else self.positions[f"{symbol}_NSE_INTRADAY"].quantity
                    
                    signals.append({
                        'type': signal_type,
                        'symbol': symbol,
                        'exchange': 'NSE',
                        'quantity': quantity,
                        'order_type': 'MARKET',
                        'product_type': 'INTRADAY',
                        'reason': f'RSI {signal_type.lower()} signal - RSI: {rsi:.2f}'
                    })
            
        except Exception as e:
            logger.error(f"Error generating RSI signals: {e}")
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Calculate current RSI values for all symbols
        current_rsi = {}
        for symbol in self.prev_prices.keys():
            rsi = self.calculate_rsi(symbol)
            if rsi is not None:
                current_rsi[symbol] = round(rsi, 2)
        
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.price_changes),
            'rsi_period': self.rsi_period,
            'oversold_threshold': self.oversold_threshold,
            'overbought_threshold': self.overbought_threshold,
            'current_rsi': current_rsi
        }) 