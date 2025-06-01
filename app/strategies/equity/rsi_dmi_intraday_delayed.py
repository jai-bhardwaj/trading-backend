"""
RSI DMI Intraday Delayed Entry Strategy for Equity Trading

Converted from the old Django-based architecture to the new BaseStrategy framework.
This strategy uses RSI and DMI indicators with delayed entry confirmation and supports both long and short positions.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, time
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("rsi_dmi_intraday_delayed", AssetClass.EQUITY)
class RSIDMIIntradayDelayedStrategy(BaseStrategy):
    """
    RSI DMI Intraday Delayed Entry Strategy for Equity
    
    Entry Conditions (Long):
    - Current candle: RSI >= rsi_UL AND +DI >= di_UL
    - Previous candle: RSI >= rsi_UL AND +DI >= di_UL
    - Both conditions must be satisfied for 2 consecutive candles
    
    Entry Conditions (Short):
    - Current candle: RSI <= rsi_LL AND -DI >= di_UL
    - Previous candle: RSI <= rsi_LL AND -DI >= di_UL
    - Both conditions must be satisfied for 2 consecutive candles
    
    Exit Conditions:
    - Intraday: Auto square-off at market close
    - Stop loss triggered
    
    Parameters:
    - rsi_UL: RSI upper limit for long entry (default: 70)
    - rsi_LL: RSI lower limit for short entry (default: 30)
    - di_UL: DI threshold for entry (default: 25)
    - max_position_size: Maximum position size as % of balance (default: 0.1)
    - order_side: 'B' for long only, 'S' for short only, 'BOTH' for both (default: 'BOTH')
    """
    
    def initialize(self) -> None:
        """Initialize strategy parameters"""
        # RSI and DMI parameters
        self.rsi_UL = self.parameters.get('rsi_UL', 70.0)
        self.rsi_LL = self.parameters.get('rsi_LL', 30.0)
        self.di_UL = self.parameters.get('di_UL', 25.0)
        self.max_position_size = self.parameters.get('max_position_size', 0.1)
        self.order_side = self.parameters.get('order_side', 'BOTH')  # 'B', 'S', or 'BOTH'
        
        # Risk management parameters
        self.max_drawdown = self.risk_parameters.get('max_drawdown', 0.05)
        self.stop_loss_pct = self.risk_parameters.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.risk_parameters.get('take_profit_pct', 0.04)
        
        # Strategy state
        self.entry_prices: Dict[str, float] = {}
        self.entry_times: Dict[str, datetime] = {}
        self.pending_orders: Dict[str, Dict] = {}  # For limit orders
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        self.square_off_time = time(15, 15)  # Square off 15 minutes before market close
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate RSI DMI delayed entry signals"""
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        # Check if we have enough data (need at least 2 candles for delayed entry)
        historical = self.historical_data.get(market_data.symbol, [])
        if len(historical) < 2:
            return None
        
        # Check trading hours
        current_time = market_data.timestamp.time()
        if not (self.market_start <= current_time <= self.market_end):
            return None
        
        # Check for intraday square-off
        if current_time >= self.square_off_time:
            return self._check_intraday_exit(market_data.symbol, market_data.close)
        
        # Get current and previous candle data
        current_candle = market_data
        previous_candle = historical[-1]  # Last historical candle
        
        # Ensure previous candle is from the same day
        if previous_candle.timestamp.date() != current_candle.timestamp.date():
            return None
        
        # Extract indicators from market data additional_data
        current_rsi = current_candle.additional_data.get('rsi_entry', 0)
        current_plus_di = current_candle.additional_data.get('+DI', 0)
        current_minus_di = current_candle.additional_data.get('-DI', 0)
        
        previous_rsi = previous_candle.additional_data.get('rsi_entry', 0)
        previous_plus_di = previous_candle.additional_data.get('+DI', 0)
        previous_minus_di = previous_candle.additional_data.get('-DI', 0)
        
        # Check for entry signals
        signal = None
        
        # Long entry conditions
        if self.order_side in ['B', 'BOTH']:
            if (float(current_rsi) >= self.rsi_UL and float(current_plus_di) >= self.di_UL and
                float(previous_rsi) >= self.rsi_UL and float(previous_plus_di) >= self.di_UL):
                
                # Check if we don't already have a long position
                if (market_data.symbol not in self.positions or 
                    self.positions[market_data.symbol]['quantity'] <= 0):
                    
                    signal = self._create_entry_signal(
                        market_data, SignalType.BUY, current_rsi, current_plus_di, 
                        previous_rsi, previous_plus_di, 'Long'
                    )
        
        # Short entry conditions
        if self.order_side in ['S', 'BOTH'] and not signal:
            if (float(current_rsi) <= self.rsi_LL and float(current_minus_di) >= self.di_UL and
                float(previous_rsi) <= self.rsi_LL and float(previous_minus_di) >= self.di_UL):
                
                # Check if we don't already have a short position
                if (market_data.symbol not in self.positions or 
                    self.positions[market_data.symbol]['quantity'] >= 0):
                    
                    signal = self._create_entry_signal(
                        market_data, SignalType.SELL, current_rsi, current_minus_di,
                        previous_rsi, previous_minus_di, 'Short'
                    )
        
        return signal
    
    def _create_entry_signal(self, market_data: MarketData, signal_type: SignalType, 
                           current_rsi: float, current_di: float, 
                           previous_rsi: float, previous_di: float, 
                           direction: str) -> StrategySignal:
        """Create entry signal with limit order"""
        
        # Use close price as limit price for delayed entry
        limit_price = market_data.close
        
        # Calculate stop loss and take profit
        if signal_type == SignalType.BUY:
            stop_loss = limit_price * (1 - self.stop_loss_pct)
            take_profit = limit_price * (1 + self.take_profit_pct)
        else:  # SELL
            stop_loss = limit_price * (1 + self.stop_loss_pct)
            take_profit = limit_price * (1 - self.take_profit_pct)
        
        return StrategySignal(
            signal_type=signal_type,
            symbol=market_data.symbol,
            confidence=0.85,
            price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'current_rsi': current_rsi,
                'current_di': current_di,
                'previous_rsi': previous_rsi,
                'previous_di': previous_di,
                'direction': direction,
                'entry_reason': f'{direction} delayed entry - 2 consecutive candles',
                'strategy_type': 'rsi_dmi_intraday_delayed',
                'limit_price': limit_price,
                'order_type': 'LIMIT'  # Move to metadata
            }
        )
    
    def _check_intraday_exit(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Check for intraday square-off"""
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            return None
        
        position = self.positions[symbol]
        
        if position['quantity'] > 0:
            signal_type = SignalType.CLOSE_LONG
        else:
            signal_type = SignalType.CLOSE_SHORT
        
        return StrategySignal(
            signal_type=signal_type,
            symbol=symbol,
            confidence=1.0,
            price=current_price,
            metadata={
                'exit_reason': 'Intraday Auto Square Off',
                'square_off_time': datetime.now().time(),
                'strategy_type': 'rsi_dmi_intraday_delayed'
            }
        )
    
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
        if not (self.market_start <= current_time <= self.square_off_time):
            return False
        
        # Ensure reasonable price
        if signal.price and (signal.price <= 0 or signal.price > 100000):
            return False
        
        # Check position limits based on order side configuration
        current_position = self.positions.get(signal.symbol, {}).get('quantity', 0)
        
        if signal.signal_type == SignalType.BUY:
            if self.order_side == 'S':  # Short only strategy
                return False
            if current_position > 0:  # Already long
                return False
        elif signal.signal_type == SignalType.SELL:
            if self.order_side == 'B':  # Long only strategy
                return False
            if current_position < 0:  # Already short
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
        """Check stop loss conditions for both long and short positions"""
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
                        'exit_reason': 'Stop Loss Triggered (Long)',
                        'entry_price': entry_price,
                        'stop_loss_price': stop_loss_price
                    }
                )
        elif position['quantity'] < 0:  # Short position
            stop_loss_price = entry_price * (1 + self.stop_loss_pct)
            if current_price >= stop_loss_price:
                return StrategySignal(
                    signal_type=SignalType.CLOSE_SHORT,
                    symbol=symbol,
                    confidence=1.0,
                    price=current_price,
                    metadata={
                        'exit_reason': 'Stop Loss Triggered (Short)',
                        'entry_price': entry_price,
                        'stop_loss_price': stop_loss_price
                    }
                )
        
        return None
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        status = super().get_strategy_status()
        status.update({
            'order_side': self.order_side,
            'rsi_UL': self.rsi_UL,
            'rsi_LL': self.rsi_LL,
            'di_UL': self.di_UL,
            'active_positions': len([p for p in self.positions.values() if p['quantity'] != 0]),
            'pending_orders': len(self.pending_orders),
            'square_off_time': self.square_off_time.strftime('%H:%M:%S')
        })
        return status 