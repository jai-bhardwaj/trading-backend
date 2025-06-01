"""
RSI DMI Strategy for Equity Trading

Converted from the old Django-based architecture to the new BaseStrategy framework.
This strategy uses RSI and DMI indicators for entry and exit signals.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, time
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("rsi_dmi_equity", AssetClass.EQUITY)
class RSIDMIStrategy(BaseStrategy):
    """
    RSI DMI Strategy for Equity
    
    Entry Conditions:
    - RSI > upper_limit (default: 70)
    - +DI > di_upper_limit (default: 25)
    
    Exit Conditions:
    - RSI < lower_limit (default: 30)
    
    Parameters:
    - upper_limit: RSI upper threshold for entry (default: 70)
    - lower_limit: RSI lower threshold for exit (default: 30)
    - di_upper_limit: +DI threshold for entry (default: 25)
    - max_position_size: Maximum position size as % of balance (default: 0.1)
    """
    
    def initialize(self) -> None:
        """Initialize strategy parameters"""
        # RSI and DMI parameters
        self.upper_limit = self.parameters.get('upper_limit', 70.0)
        self.lower_limit = self.parameters.get('lower_limit', 30.0)
        self.di_upper_limit = self.parameters.get('di_upper_limit', 25.0)
        self.max_position_size = self.parameters.get('max_position_size', 0.1)
        
        # Risk management parameters
        self.max_drawdown = self.risk_parameters.get('max_drawdown', 0.05)
        self.stop_loss_pct = self.risk_parameters.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.risk_parameters.get('take_profit_pct', 0.04)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate RSI DMI signals"""
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        # Check if we have enough data
        if len(self.historical_data.get(market_data.symbol, [])) < 20:
            return None
        
        # Check trading hours
        current_time = market_data.timestamp.time()
        if not (self.market_start <= current_time <= self.market_end):
            return None
        
        # Get current candle data (assuming market_data has RSI and DMI indicators)
        current_price = market_data.close
        
        # Extract indicators from market data additional_data
        rsi_entry = market_data.additional_data.get('rsi_entry', 0)
        rsi_exit = market_data.additional_data.get('rsi_exit', 0)
        plus_di = market_data.additional_data.get('+DI', 0)
        minus_di = market_data.additional_data.get('-DI', 0)
        
        # Check for exit signals first (if we have positions)
        if market_data.symbol in self.positions and self.positions[market_data.symbol]['quantity'] > 0:
            if float(rsi_exit) < float(self.lower_limit):
                return StrategySignal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=market_data.symbol,
                    confidence=0.9,
                    price=current_price,
                    metadata={
                        'rsi_exit': rsi_exit,
                        'exit_reason': 'RSI Below Lower Limit',
                        'strategy_type': 'rsi_dmi'
                    }
                )
        
        # Check for entry signals
        elif (float(rsi_entry) > float(self.upper_limit) and 
              float(plus_di) > float(self.di_upper_limit)):
            
            # Check if we don't already have a position
            if (market_data.symbol not in self.positions or 
                self.positions[market_data.symbol]['quantity'] == 0):
                
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
                        'rsi_entry': rsi_entry,
                        'plus_di': plus_di,
                        'entry_reason': 'RSI and +DI above thresholds',
                        'strategy_type': 'rsi_dmi'
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
        
        # Adjust based on confidence
        adjusted_quantity = int(base_quantity * signal.confidence)
        
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
        elif signal.signal_type == SignalType.SELL and current_position < 0:
            # Already short, don't add more
            return False
        
        return True
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update position and track entry prices"""
        super().update_position(symbol, quantity, price, side)
        
        # Track entry price and time for exit logic
        if side in ['BUY', 'SELL'] and symbol not in self.entry_prices:
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
                        'exit_reason': 'Stop Loss Triggered',
                        'entry_price': entry_price,
                        'stop_loss_price': stop_loss_price
                    }
                )
        
        return None
    
    def should_exit_at_market_close(self, symbol: str) -> bool:
        """Check if position should be exited at market close"""
        # For intraday strategy, exit all positions at market close
        current_time = datetime.now().time()
        market_close_buffer = time(15, 15)  # Exit 15 minutes before market close
        
        return current_time >= market_close_buffer 