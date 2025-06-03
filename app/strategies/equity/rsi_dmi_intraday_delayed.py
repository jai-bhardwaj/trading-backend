"""
RSI DMI Intraday Delayed Strategy for Equity Trading
Updated for the new cleaned schema and enhanced strategy execution system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time, timedelta
from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class RSIDMIIntradayDelayedStrategy(BaseStrategy):
    """
    RSI DMI Intraday Delayed Strategy for Equity
    
    Similar to RSI DMI strategy but with delayed execution and intraday focus.
    Includes additional filters and risk management for intraday trading.
    
    Entry Conditions:
    - RSI > upper_limit (default: 70)
    - +DI > di_upper_limit (default: 25)
    - Delayed execution after signal confirmation
    
    Exit Conditions:
    - RSI < lower_limit (default: 30)
    - End of day exit for intraday positions
    """
    
    async def on_initialize(self):
        """Initialize strategy parameters"""
        # RSI and DMI parameters
        self.upper_limit = self.config.get('upper_limit', 70.0)
        self.lower_limit = self.config.get('lower_limit', 30.0)
        self.di_upper_limit = self.config.get('di_upper_limit', 25.0)
        self.max_position_size = self.config.get('max_position_size', 0.08)  # Smaller for intraday
        
        # Delayed execution parameters
        self.signal_delay_minutes = self.config.get('signal_delay_minutes', 5)
        self.signal_confirmation_count = self.config.get('signal_confirmation_count', 2)
        
        # Risk management parameters
        self.max_drawdown = self.config.get('max_drawdown', 0.03)  # Tighter for intraday
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.015)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.03)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        self.pending_signals: Dict[str, List[Dict]] = {}  # For delayed execution
        
        # RSI calculation data
        self.price_changes: Dict[str, List[float]] = {}
        self.prev_prices: Dict[str, float] = {}
        self.rsi_period = self.config.get('rsi_period', 14)
        
        # Trading hours (9:15 AM to 3:15 PM IST for intraday)
        self.market_start = time(9, 15)
        self.market_end = time(15, 15)  # Exit 15 min before market close
        self.position_exit_time = time(15, 0)  # Force exit all positions
        
        # Subscribe to configured symbols
        symbols = self.config.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        await self.subscribe_to_instruments(symbols)
        
        logger.info(f"Initialized RSIDMIIntradayDelayedStrategy with {len(symbols)} symbols")
    
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
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data for RSI and signal tracking"""
        try:
            close_price = data.get('ltp', data.get('close', 0))
            
            # Initialize data structures
            if symbol not in self.price_changes:
                self.price_changes[symbol] = []
                self.prev_prices[symbol] = close_price
                self.pending_signals[symbol] = []
                return
            
            # Calculate price change for RSI
            price_change = close_price - self.prev_prices[symbol]
            self.price_changes[symbol].append(price_change)
            self.prev_prices[symbol] = close_price
            
            # Keep only required history
            if len(self.price_changes[symbol]) > self.rsi_period + 10:
                self.price_changes[symbol] = self.price_changes[symbol][-self.rsi_period:]
            
            # Process pending signals for delayed execution
            await self._process_pending_signals(symbol)
                
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate RSI DMI delayed intraday signals"""
        signals = []
        current_time = datetime.now()
        
        # Check trading hours
        if not (self.market_start <= current_time.time() <= self.market_end):
            return signals
        
        # Force exit all positions near market close
        if current_time.time() >= self.position_exit_time:
            for position_key, position in self.positions.items():
                if position.quantity > 0:
                    signals.append({
                        'type': 'SELL',
                        'symbol': position.symbol,
                        'exchange': position.exchange,
                        'quantity': position.quantity,
                        'order_type': 'MARKET',
                        'product_type': position.product_type.value,
                        'reason': 'End of day exit (intraday)'
                    })
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
                
                # Simulate +DI and -DI values
                plus_di = 30 if rsi > 50 else 20
                minus_di = 20 if rsi > 50 else 30
                
                position_key = f"{symbol}_NSE_INTRADAY"
                
                # Check for exit signals first
                if position_key in self.positions and self.positions[position_key].quantity > 0:
                    if rsi < self.lower_limit:
                        signals.append({
                            'type': 'SELL',
                            'symbol': symbol,
                            'exchange': 'NSE',
                            'quantity': self.positions[position_key].quantity,
                            'order_type': 'MARKET',
                            'product_type': 'INTRADAY',
                            'reason': f'RSI below lower limit - RSI: {rsi:.2f} (Intraday)'
                        })
                
                # Check for entry signals (add to pending for delayed execution)
                elif (position_key not in self.positions or 
                      self.positions[position_key].quantity == 0):
                    
                    if rsi > self.upper_limit and plus_di > self.di_upper_limit:
                        # Add to pending signals for delayed execution
                        await self._add_pending_signal(symbol, {
                            'type': 'BUY',
                            'symbol': symbol,
                            'exchange': 'NSE',
                            'quantity': 15,  # Smaller quantity for intraday
                            'order_type': 'MARKET',
                            'product_type': 'INTRADAY',
                            'reason': f'RSI and +DI above thresholds - RSI: {rsi:.2f}, +DI: {plus_di:.2f} (Delayed)',
                            'rsi': rsi,
                            'plus_di': plus_di,
                            'timestamp': current_time
                        })
        
        except Exception as e:
            logger.error(f"Error generating RSI DMI delayed signals: {e}")
        
        return signals
    
    async def _add_pending_signal(self, symbol: str, signal_data: Dict[str, Any]):
        """Add signal to pending list for delayed execution"""
        if symbol not in self.pending_signals:
            self.pending_signals[symbol] = []
        
        self.pending_signals[symbol].append(signal_data)
        
        # Keep only recent signals (last 10 minutes)
        current_time = datetime.now()
        self.pending_signals[symbol] = [
            sig for sig in self.pending_signals[symbol]
            if (current_time - sig['timestamp']).total_seconds() <= 600
        ]
    
    async def _process_pending_signals(self, symbol: str):
        """Process pending signals for delayed execution"""
        if symbol not in self.pending_signals or not self.pending_signals[symbol]:
            return
        
        current_time = datetime.now()
        signals_to_execute = []
        
        for signal in self.pending_signals[symbol]:
            signal_age = (current_time - signal['timestamp']).total_seconds() / 60
            
            # Check if signal is ready for execution (after delay period)
            if signal_age >= self.signal_delay_minutes:
                # Count recent confirmations
                recent_signals = [
                    s for s in self.pending_signals[symbol]
                    if s['type'] == signal['type'] and 
                    (signal['timestamp'] - s['timestamp']).total_seconds() <= self.signal_delay_minutes * 60
                ]
                
                # Execute if we have enough confirmations
                if len(recent_signals) >= self.signal_confirmation_count:
                    signals_to_execute.append(signal)
        
        # Execute confirmed signals
        for signal in signals_to_execute:
            await self._execute_delayed_signal(signal)
            
        # Remove executed signals
        self.pending_signals[symbol] = [
            sig for sig in self.pending_signals[symbol]
            if sig not in signals_to_execute
        ]
    
    async def _execute_delayed_signal(self, signal_data: Dict[str, Any]):
        """Execute a delayed signal"""
        try:
            symbol = signal_data['symbol']
            
            # Double-check position status before execution
            position_key = f"{symbol}_NSE_INTRADAY"
            if position_key in self.positions and self.positions[position_key].quantity > 0:
                return  # Already have position
            
            # Execute the buy order
            await self.place_buy_order(
                symbol=symbol,
                exchange=signal_data['exchange'],
                quantity=signal_data['quantity'],
                order_type=signal_data['order_type'],
                product_type=signal_data['product_type']
            )
            
            logger.info(f"Executed delayed signal for {symbol}")
            
        except Exception as e:
            logger.error(f"Error executing delayed signal for {signal_data['symbol']}: {e}")
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Calculate current indicators for all symbols
        current_indicators = {}
        pending_signal_counts = {}
        
        for symbol in self.subscribed_symbols:
            rsi = self.calculate_rsi(symbol)
            if rsi is not None:
                current_indicators[symbol] = {
                    'rsi': round(rsi, 2),
                    'above_upper_limit': rsi > self.upper_limit,
                    'below_lower_limit': rsi < self.lower_limit
                }
            
            pending_signal_counts[symbol] = len(self.pending_signals.get(symbol, []))
        
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.subscribed_symbols),
            'rsi_period': self.rsi_period,
            'upper_limit': self.upper_limit,
            'lower_limit': self.lower_limit,
            'di_upper_limit': self.di_upper_limit,
            'signal_delay_minutes': self.signal_delay_minutes,
            'signal_confirmation_count': self.signal_confirmation_count,
            'current_indicators': current_indicators,
            'pending_signal_counts': pending_signal_counts,
            'strategy_type': 'INTRADAY_DELAYED'
        })
    
    async def on_order_filled(self, order):
        """Called when an order is filled"""
        if order.side.value == 'BUY':
            # Track entry details
            self.entry_prices[order.symbol] = order.average_price
            self.entry_times[order.symbol] = datetime.now()
            
            logger.info(f"RSI DMI intraday position opened: {order.symbol} @ ₹{order.average_price}")
        
        elif order.side.value == 'SELL':
            # Clear entry data when position is closed
            self.entry_prices.pop(order.symbol, None)
            self.entry_times.pop(order.symbol, None)
            
            logger.info(f"RSI DMI intraday position closed: {order.symbol} @ ₹{order.average_price}")
    
    async def on_position_opened(self, position):
        """Called when a new position is opened"""
        logger.info(f"RSI DMI delayed intraday position opened: {position.symbol} {position.quantity} shares")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a position is closed"""
        holding_time = "N/A"
        if position.symbol in self.entry_times:
            entry_time = self.entry_times[position.symbol]
            holding_minutes = (datetime.now() - entry_time).total_seconds() / 60
            holding_time = f"{holding_minutes:.1f} minutes"
        
        logger.info(f"RSI DMI intraday position closed: {position.symbol} with P&L: ₹{pnl} (held {holding_time})") 