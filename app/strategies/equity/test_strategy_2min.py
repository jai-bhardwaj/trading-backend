"""
Test Strategy 2 Min - Places orders every 2 minutes for testing

This is a test strategy designed to place orders every 2 minutes to test
the trading system's order execution, monitoring, and database operations.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, time, timedelta
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("test_strategy_2min", AssetClass.EQUITY)
class TestStrategy2Min(BaseStrategy):
    """
    Test Strategy - Places orders every 2 minutes
    
    This strategy is designed for testing purposes only. It will:
    - Place a BUY order every 2 minutes
    - Alternate between different test symbols
    - Use small position sizes for safety
    - Close positions after 4 minutes (2 cycles)
    
    Parameters:
    - order_interval_minutes: Minutes between orders (default: 2)
    - test_symbols: List of symbols to cycle through
    - max_position_size: Maximum position size as % of balance (default: 0.01)
    - auto_close_minutes: Minutes after which to close positions (default: 4)
    """
    
    def initialize(self) -> None:
        """Initialize test strategy parameters"""
        # Strategy parameters
        self.order_interval_minutes = self.parameters.get('order_interval_minutes', 2)
        self.max_position_size = self.parameters.get('max_position_size', 0.01)  # Very small for testing
        self.auto_close_minutes = self.parameters.get('auto_close_minutes', 4)
        
        # Test symbols to cycle through
        self.test_symbols = self.parameters.get('test_symbols', ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK'])
        self.current_symbol_index = 0
        
        # Risk management parameters (conservative for testing)
        self.max_drawdown = self.risk_parameters.get('max_drawdown', 0.02)
        self.stop_loss_pct = self.risk_parameters.get('stop_loss_pct', 0.01)
        self.take_profit_pct = self.risk_parameters.get('take_profit_pct', 0.02)
        
        # Strategy state
        self.last_order_time: Optional[datetime] = None
        self.entry_times: Dict[str, datetime] = {}
        self.order_counter = 0
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # Test mode flag
        self.is_test_mode = True
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate test signals every 2 minutes"""
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        current_time = market_data.timestamp
        
        # Check trading hours
        if not (self.market_start <= current_time.time() <= self.market_end):
            return None
        
        # Check for auto-close signals first
        auto_close_signal = self._check_auto_close(market_data.symbol, market_data.close, current_time)
        if auto_close_signal:
            return auto_close_signal
        
        # Check if it's time to place a new order
        if self._should_place_order(current_time):
            # Get the next test symbol
            test_symbol = self._get_next_test_symbol()
            
            # Only place order if this is the current test symbol
            if market_data.symbol == test_symbol:
                return self._create_test_buy_signal(market_data, current_time)
        
        return None
    
    def _should_place_order(self, current_time: datetime) -> bool:
        """Check if it's time to place a new order based on interval"""
        if self.last_order_time is None:
            return True
        
        time_since_last_order = current_time - self.last_order_time
        return time_since_last_order >= timedelta(minutes=self.order_interval_minutes)
    
    def _get_next_test_symbol(self) -> str:
        """Get the next symbol to test with (cycling through test symbols)"""
        symbol = self.test_symbols[self.current_symbol_index]
        self.current_symbol_index = (self.current_symbol_index + 1) % len(self.test_symbols)
        return symbol
    
    def _create_test_buy_signal(self, market_data: MarketData, current_time: datetime) -> StrategySignal:
        """Create a test BUY signal"""
        current_price = market_data.close
        
        # Calculate stop loss and take profit
        stop_loss = current_price * (1 - self.stop_loss_pct)
        take_profit = current_price * (1 + self.take_profit_pct)
        
        # Update last order time and counter
        self.last_order_time = current_time
        self.order_counter += 1
        
        return StrategySignal(
            signal_type=SignalType.BUY,
            symbol=market_data.symbol,
            confidence=0.5,  # Medium confidence for test
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'test_order': True,
                'order_number': self.order_counter,
                'test_symbol': market_data.symbol,
                'order_time': current_time.isoformat(),
                'strategy_type': 'TEST_2MIN',
                'entry_reason': f'Test order #{self.order_counter} - 2min interval'
            }
        )
    
    def _check_auto_close(self, symbol: str, current_price: float, current_time: datetime) -> Optional[StrategySignal]:
        """Check if position should be auto-closed after specified time"""
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            return None
        
        if symbol not in self.entry_times:
            return None
        
        entry_time = self.entry_times[symbol]
        time_held = current_time - entry_time
        
        if time_held >= timedelta(minutes=self.auto_close_minutes):
            return StrategySignal(
                signal_type=SignalType.CLOSE_LONG,
                symbol=symbol,
                confidence=1.0,
                price=current_price,
                metadata={
                    'exit_reason': f'Auto-close after {self.auto_close_minutes} minutes',
                    'time_held_minutes': time_held.total_seconds() / 60,
                    'entry_time': entry_time.isoformat(),
                    'strategy_type': 'TEST_2MIN',
                    'test_order': True
                }
            )
        
        return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate small position size for testing"""
        
        # Very small position value for testing
        max_position_value = current_balance * self.max_position_size
        
        # Calculate base position size
        if signal.price and signal.price > 0:
            base_quantity = int(max_position_value / signal.price)
        else:
            return 0
        
        # Ensure minimum quantity of 1 for testing
        test_quantity = max(1, base_quantity)
        
        # Cap at reasonable test size (max 10 shares)
        test_quantity = min(test_quantity, 10)
        
        return test_quantity
    
    def _validate_asset_class_specific(self, signal: StrategySignal) -> bool:
        """Test-specific validation"""
        
        # Check if it's market hours
        current_time = datetime.now().time()
        if not (self.market_start <= current_time <= self.market_end):
            return False
        
        # Ensure reasonable price
        if signal.price and (signal.price <= 0 or signal.price > 100000):
            return False
        
        # For test strategy, allow multiple positions for testing
        return True
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update position and track entry times"""
        super().update_position(symbol, quantity, price, side)
        
        # Track entry time for auto-close logic
        if side in ['BUY'] and symbol not in self.entry_times:
            self.entry_times[symbol] = datetime.now()
        
        # Clear entry data if position is closed
        if symbol in self.positions and self.positions[symbol]['quantity'] == 0:
            self.entry_times.pop(symbol, None)
    
    def check_stop_loss(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Check stop loss conditions for test positions"""
        if symbol not in self.positions or self.positions[symbol]['quantity'] == 0:
            return None
        
        position = self.positions[symbol]
        entry_price = position['average_price']
        
        if position['quantity'] > 0:  # Long position
            stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            if current_price <= stop_loss_price:
                return StrategySignal(
                    signal_type=SignalType.CLOSE_LONG,
                    symbol=symbol,
                    confidence=1.0,
                    price=current_price,
                    metadata={
                        'exit_reason': 'Stop Loss Triggered (TEST)',
                        'entry_price': entry_price,
                        'stop_loss_price': stop_loss_price,
                        'strategy_type': 'TEST_2MIN',
                        'test_order': True
                    }
                )
        
        return None
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current test strategy status"""
        status = super().get_strategy_status()
        status.update({
            'strategy_type': 'TEST_2MIN',
            'is_test_mode': self.is_test_mode,
            'order_interval_minutes': self.order_interval_minutes,
            'auto_close_minutes': self.auto_close_minutes,
            'order_counter': self.order_counter,
            'last_order_time': self.last_order_time.isoformat() if self.last_order_time else None,
            'current_test_symbol': self.test_symbols[self.current_symbol_index],
            'test_symbols': self.test_symbols,
            'active_test_positions': len([p for p in self.positions.values() if p['quantity'] != 0])
        })
        return status 