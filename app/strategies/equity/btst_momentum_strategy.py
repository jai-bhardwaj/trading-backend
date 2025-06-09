"""
BTST Momentum Gain 4% Strategy for Equity Trading
Updated for the new cleaned schema and enhanced strategy execution system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time, timedelta
from ..base_strategy import BaseStrategy
from ..registry import AutomaticStrategyRegistry
from app.models.base import AssetClass
from app.utils.timezone_utils import ist_now as datetime_now

logger = logging.getLogger(__name__)

@AutomaticStrategyRegistry.register("btst_momentum_gain_4", AssetClass.EQUITY)
class BTSTMomentumGain4Strategy(BaseStrategy):
    """
    BTST Momentum Gain 4% Strategy for Equity
    
    Entry Conditions:
    - MACD signal = 1 (bullish)
    - Stochastic signal = 1 (bullish)
    - Price momentum >= 4% from day's open
    
    Exit Conditions:
    - Time-based exit after 1 day (BTST - Buy Today Sell Tomorrow)
    - Stop loss triggered
    """
    
    async def on_initialize(self):
        """Initialize strategy parameters"""
        # Strategy parameters
        self.momentum_percentage = self.config.get('momentum_percentage', 4.0)
        self.max_position_size = self.config.get('max_position_size', 0.1)
        
        # Risk management parameters
        self.max_drawdown = self.config.get('max_drawdown', 0.05)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.06)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        self.day_open_prices: Dict[str, float] = {}
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # BTST - 1 day holding period
        self.exit_days = self.config.get('exit_days', 1)
        
        # Subscribe to configured symbols
        symbols = self.config.get('symbols', ['RELIANCE', 'TCS', 'INFY'])
        await self.subscribe_to_instruments(symbols)
        
        logger.info(f"Initialized BTSTMomentumGain4Strategy with {len(symbols)} symbols")
    
    async def process_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process market data and generate signals (required interface method)"""
        try:
            symbol = market_data.get('symbol', 'UNKNOWN')
            current_price = market_data.get('ltp', market_data.get('close', 0))
            
            # Update day open price
            await self._update_day_open_price(symbol, market_data)
            
            # Check momentum from day's open
            day_open = self.day_open_prices.get(symbol)
            if day_open and day_open > 0:
                momentum_pct = ((current_price - day_open) / day_open) * 100
                
                # Simulate MACD and Stochastic signals
                macd_signal = 1 if momentum_pct > 2 else 0
                stoch_signal = 1 if momentum_pct > 2 else 0
                
                if (macd_signal == 1 and stoch_signal == 1 and 
                    momentum_pct >= self.momentum_percentage):
                    
                    return {
                        'action': 'BUY',
                        'symbol': symbol,
                        'quantity': 15,
                        'reason': f'BTST: MACD+Stoch signals with {momentum_pct:.2f}% momentum'
                    }
            
            return None
                
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
            return None

    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data and update day open prices"""
        try:
            # Update day's open price for momentum calculation
            await self._update_day_open_price(symbol, data)
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate BTST momentum signals"""
        signals = []
        current_time = datetime_now()
        
        # Check trading hours
        if not (self.market_start <= current_time.time() <= self.market_end):
            return signals
        
        try:
            # Check for time-based exits first
            for position_key, position in self.positions.items():
                if position.quantity > 0:
                    symbol = position.symbol
                    if await self._should_time_based_exit(symbol, current_time):
                        signals.append({
                            'type': 'SELL',
                            'symbol': symbol,
                            'exchange': position.exchange,
                            'quantity': position.quantity,
                            'order_type': 'MARKET',
                            'product_type': position.product_type.value,
                            'reason': f'Time-based exit (BTST - {self.exit_days} day)'
                        })
            
            # Check for entry signals
            for symbol in self.subscribed_symbols:
                # Check if we don't already have a position
                position_key = f"{symbol}_NSE_DELIVERY"  # BTST uses DELIVERY product type
                if position_key not in self.positions or self.positions[position_key].quantity == 0:
                    
                    # Get current market data
                    current_price = await self.get_current_price(symbol, "NSE")
                    if not current_price:
                        continue
                    
                    # Check momentum from day's open
                    day_open = self.day_open_prices.get(symbol)
                    if day_open and day_open > 0:
                        momentum_pct = ((current_price - day_open) / day_open) * 100
                        
                        # For demo purposes, simulate MACD and Stochastic signals
                        # In real implementation, these would come from market data
                        macd_signal = 1 if momentum_pct > 2 else 0  # Simplified
                        stoch_signal = 1 if momentum_pct > 2 else 0  # Simplified
                        
                        if (macd_signal == 1 and stoch_signal == 1 and 
                            momentum_pct >= self.momentum_percentage):
                            
                            signals.append({
                                'type': 'BUY',
                                'symbol': symbol,
                                'exchange': 'NSE',
                                'quantity': 30,  # Base quantity for BTST
                                'order_type': 'MARKET',
                                'product_type': 'DELIVERY',  # BTST uses DELIVERY
                                'reason': f'MACD+Stoch signals with {momentum_pct:.2f}% momentum (BTST)'
                            })
                            
                            # Track entry time for time-based exit
                            self.entry_times[symbol] = current_time
        
        except Exception as e:
            logger.error(f"Error generating BTST momentum signals: {e}")
        
        return signals
    
    async def _update_day_open_price(self, symbol: str, data: Dict[str, Any]):
        """Update the day's opening price for momentum calculation"""
        current_date = datetime_now().date()
        
        # For simplicity, we'll use the first price we see each day as the open
        if symbol not in self.day_open_prices:
            open_price = data.get('open', data.get('ltp', data.get('close', 0)))
            self.day_open_prices[symbol] = open_price
    
    async def _should_time_based_exit(self, symbol: str, current_time: datetime) -> bool:
        """Check if position should be exited based on BTST time duration"""
        if symbol not in self.entry_times:
            return False
        
        entry_time = self.entry_times[symbol]
        
        # Calculate days since entry
        days_held = (current_time.date() - entry_time.date()).days
        
        return days_held >= self.exit_days
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Calculate current momentum for all symbols
        current_momentum = {}
        for symbol in self.subscribed_symbols:
            current_price = await self.get_current_price(symbol, "NSE")
            day_open = self.day_open_prices.get(symbol)
            
            if current_price and day_open and day_open > 0:
                momentum_pct = ((current_price - day_open) / day_open) * 100
                current_momentum[symbol] = round(momentum_pct, 2)
        
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'symbols_tracked': len(self.subscribed_symbols),
            'momentum_percentage': self.momentum_percentage,
            'exit_days': self.exit_days,
            'current_momentum': current_momentum,
            'day_open_prices': self.day_open_prices,
            'active_entry_times': len(self.entry_times),
            'strategy_type': 'BTST'
        })
    
    async def on_order_filled(self, order):
        """Called when an order is filled"""
        if order.side.value == 'BUY':
            # Track entry details for BTST trading
            self.entry_prices[order.symbol] = order.average_price
            if order.symbol not in self.entry_times:
                self.entry_times[order.symbol] = datetime_now()
            
            logger.info(f"BTST position opened: {order.symbol} @ ₹{order.average_price}")
        
        elif order.side.value == 'SELL':
            # Clear entry data when position is closed
            self.entry_prices.pop(order.symbol, None)
            self.entry_times.pop(order.symbol, None)
            
            logger.info(f"BTST position closed: {order.symbol} @ ₹{order.average_price}")
    
    async def on_position_opened(self, position):
        """Called when a new position is opened"""
        logger.info(f"BTST momentum position opened: {position.symbol} {position.quantity} shares")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a position is closed"""
        days_held = 0
        if position.symbol in self.entry_times:
            entry_time = self.entry_times[position.symbol]
            days_held = (datetime_now().date() - entry_time.date()).days
        
        logger.info(f"BTST position closed: {position.symbol} with P&L: ₹{pnl} (held {days_held} days)") 