"""
BTST Momentum Gain 4% Strategy for Equity Trading

Converted from the old Django-based architecture to the new BaseStrategy framework.
This strategy uses MACD and Stochastic signals with 4% momentum and 1 day holding period.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, time, timedelta
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("btst_momentum_gain_4", AssetClass.EQUITY)
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
    
    Parameters:
    - momentum_percentage: Minimum momentum % from day's open (default: 4.0)
    - max_position_size: Maximum position size as % of balance (default: 0.1)
    """
    
    def initialize(self) -> None:
        """Initialize strategy parameters"""
        # Strategy parameters
        self.momentum_percentage = self.parameters.get('momentum_percentage', 4.0)
        self.max_position_size = self.parameters.get('max_position_size', 0.1)
        
        # Risk management parameters
        self.max_drawdown = self.risk_parameters.get('max_drawdown', 0.05)
        self.stop_loss_pct = self.risk_parameters.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.risk_parameters.get('take_profit_pct', 0.06)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        self.day_open_prices: Dict[str, float] = {}
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # BTST - 1 day holding period
        self.exit_days = 1
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate BTST momentum signals"""
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        # Check if we have enough data
        if len(self.historical_data.get(market_data.symbol, [])) < 20:
            return None
        
        # Check trading hours
        current_time = market_data.timestamp.time()
        if not (self.market_start <= current_time <= self.market_end):
            return None
        
        # Get current price and indicators
        current_price = market_data.close
        
        # Extract signals from market data additional_data
        macd_signal = market_data.additional_data.get('macd_signal', 0)
        stoch_signal = market_data.additional_data.get('stoch_signal', 0)
        
        # Get day's open price (first candle of the day)
        self._update_day_open_price(market_data)
        
        # Check for exit signals first (time-based exit)
        exit_signal = self._check_time_based_exit(market_data.symbol, current_price)
        if exit_signal:
            return exit_signal
        
        # Check for entry signals
        if (int(macd_signal) == 1 and int(stoch_signal) == 1):
            
            # Check if we don't already have a position
            if (market_data.symbol not in self.positions or 
                self.positions[market_data.symbol]['quantity'] == 0):
                
                # Calculate momentum from day's open
                day_open = self.day_open_prices.get(market_data.symbol)
                if day_open and day_open > 0:
                    momentum_pct = ((current_price - day_open) / day_open) * 100
                    
                    if momentum_pct >= self.momentum_percentage:
                        # Calculate stop loss and take profit
                        stop_loss = current_price * (1 - self.stop_loss_pct)
                        take_profit = current_price * (1 + self.take_profit_pct)
                        
                        return StrategySignal(
                            signal_type=SignalType.BUY,
                            symbol=market_data.symbol,
                            confidence=0.8,
                            price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            metadata={
                                'macd_signal': macd_signal,
                                'stoch_signal': stoch_signal,
                                'momentum_pct': momentum_pct,
                                'day_open': day_open,
                                'strategy_type': 'BTST',
                                'entry_reason': f'MACD+Stoch signals with {momentum_pct:.2f}% momentum (BTST)'
                            }
                        )
        
        return None
    
    def _update_day_open_price(self, market_data: MarketData) -> None:
        """Update the day's opening price for momentum calculation"""
        symbol = market_data.symbol
        current_date = market_data.timestamp.date()
        
        # Check if this is the first candle of the day
        if symbol not in self.day_open_prices:
            self.day_open_prices[symbol] = market_data.open
        else:
            # Check if we have historical data to determine if this is a new day
            historical = self.historical_data.get(symbol, [])
            if historical:
                last_date = historical[-1].timestamp.date()
                if current_date > last_date:
                    # New day, update open price
                    self.day_open_prices[symbol] = market_data.open
    
    def _check_time_based_exit(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Check if position should be exited based on BTST time duration (1 day)"""
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            return None
        
        if symbol not in self.entry_times:
            return None
        
        entry_time = self.entry_times[symbol]
        current_time = datetime.now()
        
        # Calculate days since entry
        days_held = (current_time.date() - entry_time.date()).days
        
        if days_held >= self.exit_days:
            return StrategySignal(
                signal_type=SignalType.CLOSE_LONG,
                symbol=symbol,
                confidence=1.0,
                price=current_price,
                metadata={
                    'exit_reason': 'Time-based exit (BTST - 1 day)',
                    'days_held': days_held,
                    'entry_time': entry_time,
                    'strategy_type': 'BTST'
                }
            )
        
        return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate position size based on risk management"""
        
        # Maximum position value based on balance
        max_position_value = current_balance * self.max_position_size
        
        # Calculate base position size
        if signal.price and signal.price > 0:
            base_quantity = int(max_position_value / signal.price)
        else:
            return 0
        
        # Adjust based on confidence and momentum
        momentum_pct = signal.metadata.get('momentum_pct', 0)
        momentum_multiplier = min(1.2, 1.0 + (momentum_pct - self.momentum_percentage) / 100)
        
        adjusted_quantity = int(base_quantity * signal.confidence * momentum_multiplier)
        
        # Ensure minimum lot size
        min_lot_size = 1
        adjusted_quantity = max(adjusted_quantity, min_lot_size)
        
        return adjusted_quantity
    
    def _validate_asset_class_specific(self, signal: StrategySignal) -> bool:
        """Equity-specific validation"""
        
        # Check if it's market hours
        current_time = datetime.now().time()
        if not (self.market_start <= current_time <= self.market_end):
            return False
        
        # Ensure reasonable price
        if signal.price and (signal.price <= 0 or signal.price > 100000):
            return False
        
        # Check position limits
        current_position = self.positions.get(signal.symbol, {}).get('quantity', 0)
        
        if signal.signal_type == SignalType.BUY and current_position > 0:
            # Already long, don't add more
            return False
        
        return True
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update position and track entry prices"""
        super().update_position(symbol, quantity, price, side)
        
        # Track entry price and time for exit logic
        if side in ['BUY'] and symbol not in self.entry_prices:
            self.entry_prices[symbol] = price
            self.entry_times[symbol] = datetime.now()
        
        # Clear entry data if position is closed
        if symbol in self.positions and self.positions[symbol]['quantity'] == 0:
            self.entry_prices.pop(symbol, None)
            self.entry_times.pop(symbol, None)
    
    def check_stop_loss(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Check stop loss conditions"""
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            return None
        
        position = self.positions[symbol]
        entry_price = self.entry_prices.get(symbol, position['average_price'])
        
        if position['quantity'] > 0:  # Long position
            stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            if current_price <= stop_loss_price:
                return StrategySignal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=symbol,
                    confidence=1.0,
                    price=current_price,
                    metadata={
                        'exit_reason': 'Stop Loss Triggered (BTST)',
                        'entry_price': entry_price,
                        'stop_loss_price': stop_loss_price,
                        'strategy_type': 'BTST'
                    }
                )
        
        return None
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        status = super().get_strategy_status()
        status.update({
            'strategy_type': 'BTST',
            'momentum_percentage': self.momentum_percentage,
            'exit_days': self.exit_days,
            'active_positions': len([p for p in self.positions.values() if p['quantity'] != 0]),
            'day_open_prices': self.day_open_prices
        })
        return status 