"""
RSI DMI Strategy for Equity Trading
Updated for the new cleaned schema and enhanced strategy execution system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time
from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class RSIDMIStrategy(BaseStrategy):
    """
    RSI DMI Strategy for Equity
    
    Entry Conditions:
    - RSI > upper_limit (default: 70)
    - +DI > di_upper_limit (default: 25)
    
    Exit Conditions:
    - RSI < lower_limit (default: 30)
    """
    
    async def on_initialize(self):
        """Initialize strategy parameters"""
        # RSI and DMI parameters
        self.upper_limit = self.config.get('upper_limit', 70.0)
        self.lower_limit = self.config.get('lower_limit', 30.0)
        self.di_upper_limit = self.config.get('di_upper_limit', 25.0)
        self.max_position_size = self.config.get('max_position_size', 0.1)
        
        # Risk management parameters
        self.max_drawdown = self.config.get('max_drawdown', 0.05)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.04)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        
        # RSI calculation data
        self.price_changes: Dict[str, List[float]] = {}
        self.prev_prices: Dict[str, float] = {}
        self.rsi_period = self.config.get('rsi_period', 14)
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # Subscribe to configured symbols
        symbols = self.config.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        await self.subscribe_to_instruments(symbols)
        
        logger.info(f"Initialized RSIDMIStrategy with {len(symbols)} symbols")
    
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
        """Process market data for RSI and DMI calculation"""
        try:
            close_price = data.get('ltp', data.get('close', 0))
            
            # Initialize data structures
            if symbol not in self.price_changes:
                self.price_changes[symbol] = []
                self.prev_prices[symbol] = close_price
                return
            
            # Calculate price change for RSI
            price_change = close_price - self.prev_prices[symbol]
            self.price_changes[symbol].append(price_change)
            self.prev_prices[symbol] = close_price
            
            # Keep only required history
            if len(self.price_changes[symbol]) > self.rsi_period + 10:
                self.price_changes[symbol] = self.price_changes[symbol][-self.rsi_period:]
                
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate RSI DMI trading signals"""
        signals = []
        current_time = datetime.now()
        
        # Check trading hours
        if not (self.market_start <= current_time.time() <= self.market_end):
            return signals
        
        try:
            for symbol in self.subscribed_symbols:
                # Calculate RSI
                rsi = self.calculate_rsi(symbol)
                if rsi is None:
                    continue
                
                current_price = self.prev_prices.get(symbol)
                if not current_price:
                    continue
                
                # For demo purposes, simulate +DI and -DI values
                # In real implementation, these would be calculated from market data
                plus_di = 30 if rsi > 50 else 20  # Simplified simulation
                minus_di = 20 if rsi > 50 else 30  # Simplified simulation
                
                position_key = f"{symbol}_NSE_INTRADAY"
                
                # Check for exit signals first (if we have positions)
                if position_key in self.positions and self.positions[position_key].quantity > 0:
                    if rsi < self.lower_limit:
                        signals.append({
                            'type': 'SELL',
                            'symbol': symbol,
                            'exchange': 'NSE',
                            'quantity': self.positions[position_key].quantity,
                            'order_type': 'MARKET',
                            'product_type': 'INTRADAY',
                            'reason': f'RSI below lower limit - RSI: {rsi:.2f}'
                        })
                
                # Check for entry signals
                elif (position_key not in self.positions or 
                      self.positions[position_key].quantity == 0):
                    
                    if rsi > self.upper_limit and plus_di > self.di_upper_limit:
                        signals.append({
                            'type': 'BUY',
                            'symbol': symbol,
                            'exchange': 'NSE',
                            'quantity': 20,  # Base quantity
                            'order_type': 'MARKET',
                            'product_type': 'INTRADAY',
                            'reason': f'RSI and +DI above thresholds - RSI: {rsi:.2f}, +DI: {plus_di:.2f}'
                        })
        
        except Exception as e:
            logger.error(f"Error generating RSI DMI signals: {e}")
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Calculate current RSI and DMI values for all symbols
        current_indicators = {}
        for symbol in self.subscribed_symbols:
            rsi = self.calculate_rsi(symbol)
            if rsi is not None:
                current_indicators[symbol] = {
                    'rsi': round(rsi, 2),
                    'above_upper_limit': rsi > self.upper_limit,
                    'below_lower_limit': rsi < self.lower_limit
                }
        
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.subscribed_symbols),
            'rsi_period': self.rsi_period,
            'upper_limit': self.upper_limit,
            'lower_limit': self.lower_limit,
            'di_upper_limit': self.di_upper_limit,
            'current_indicators': current_indicators,
            'active_entry_times': len(self.entry_times)
        })
    
    async def on_order_filled(self, order):
        """Called when an order is filled"""
        if order.side.value == 'BUY':
            # Track entry details
            self.entry_prices[order.symbol] = order.average_price
            self.entry_times[order.symbol] = datetime.now()
            
            logger.info(f"RSI DMI position opened: {order.symbol} @ ₹{order.average_price}")
        
        elif order.side.value == 'SELL':
            # Clear entry data when position is closed
            self.entry_prices.pop(order.symbol, None)
            self.entry_times.pop(order.symbol, None)
            
            logger.info(f"RSI DMI position closed: {order.symbol} @ ₹{order.average_price}")
    
    async def on_position_opened(self, position):
        """Called when a new position is opened"""
        logger.info(f"RSI DMI position opened: {position.symbol} {position.quantity} shares")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a position is closed"""
        logger.info(f"RSI DMI position closed: {position.symbol} with P&L: ₹{pnl}") 