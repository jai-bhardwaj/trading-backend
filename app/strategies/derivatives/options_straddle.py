"""
Options Straddle Strategy for Derivatives Trading

This strategy implements a long straddle approach, buying both call and put options
at the same strike price, profiting from high volatility movements in either direction.
"""

import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("options_straddle", AssetClass.DERIVATIVES)
class OptionsStraddleStrategy(BaseStrategy):
    """
    Options Straddle Strategy for Derivatives
    
    Parameters:
    - volatility_threshold: Minimum implied volatility to enter (default: 0.15)
    - days_to_expiry_min: Minimum days to expiry (default: 7)
    - days_to_expiry_max: Maximum days to expiry (default: 45)
    - profit_target: Profit target as multiple of premium paid (default: 2.0)
    - stop_loss: Stop loss as percentage of premium paid (default: 0.5)
    - max_positions: Maximum number of straddle positions (default: 3)
    """
    
    def initialize(self) -> None:
        """Initialize strategy parameters"""
        self.volatility_threshold = self.parameters.get('volatility_threshold', 0.15)
        self.days_to_expiry_min = self.parameters.get('days_to_expiry_min', 7)
        self.days_to_expiry_max = self.parameters.get('days_to_expiry_max', 45)
        self.profit_target = self.parameters.get('profit_target', 2.0)
        self.stop_loss = self.parameters.get('stop_loss', 0.5)
        self.max_positions = self.parameters.get('max_positions', 3)
        
        # Risk management parameters
        self.max_position_size = self.risk_parameters.get('max_position_size', 0.05)
        self.max_daily_loss = self.risk_parameters.get('max_daily_loss', 0.02)
        
        # Strategy state
        self.straddle_positions: Dict[str, Dict] = {}
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate options straddle signals"""
        
        # Reset daily P&L if new day
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
        
        # Check daily loss limit
        if self.daily_pnl < -self.max_daily_loss:
            return None  # Stop trading for the day
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        # For options, we need additional data like strike, expiry, option type
        option_data = market_data.additional_data
        
        if not self._is_valid_option_data(option_data):
            return None
        
        # Check if this is an ATM option pair opportunity
        if self._is_atm_straddle_opportunity(market_data, option_data):
            return self._generate_straddle_entry_signal(market_data, option_data)
        
        # Check for exit signals on existing positions
        return self._check_exit_signals(market_data, option_data)
    
    def _is_valid_option_data(self, option_data: Dict[str, Any]) -> bool:
        """Validate that we have required options data"""
        required_fields = ['strike_price', 'expiry_date', 'option_type', 'implied_volatility']
        return all(field in option_data for field in required_fields)
    
    def _is_atm_straddle_opportunity(self, market_data: MarketData, option_data: Dict[str, Any]) -> bool:
        """Check if this is a good ATM straddle opportunity"""
        
        # Check if we already have max positions
        if len(self.straddle_positions) >= self.max_positions:
            return False
        
        # Check implied volatility threshold
        iv = option_data.get('implied_volatility', 0)
        if iv < self.volatility_threshold:
            return False
        
        # Check days to expiry
        expiry_date = option_data.get('expiry_date')
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        
        days_to_expiry = (expiry_date - datetime.now().date()).days
        if not (self.days_to_expiry_min <= days_to_expiry <= self.days_to_expiry_max):
            return False
        
        # Check if strike is close to current price (ATM)
        strike_price = option_data.get('strike_price', 0)
        current_price = market_data.close
        
        # Consider ATM if within 2% of current price
        price_diff_pct = abs(strike_price - current_price) / current_price
        if price_diff_pct > 0.02:
            return False
        
        return True
    
    def _generate_straddle_entry_signal(self, market_data: MarketData, option_data: Dict[str, Any]) -> StrategySignal:
        """Generate signal to enter straddle position"""
        
        strike_price = option_data.get('strike_price')
        expiry_date = option_data.get('expiry_date')
        
        # Create unique identifier for this straddle
        straddle_id = f"{market_data.symbol}_{strike_price}_{expiry_date}"
        
        signal = StrategySignal(
            signal_type=SignalType.BUY,  # Buy straddle (both call and put)
            symbol=market_data.symbol,
            confidence=0.8,
            price=market_data.close,
            metadata={
                'strategy_type': 'options_straddle',
                'straddle_id': straddle_id,
                'strike_price': strike_price,
                'expiry_date': expiry_date,
                'implied_volatility': option_data.get('implied_volatility'),
                'option_type': 'STRADDLE',  # Both call and put
                'entry_reason': 'high_volatility_atm'
            }
        )
        
        return signal
    
    def _check_exit_signals(self, market_data: MarketData, option_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Check for exit signals on existing straddle positions"""
        
        strike_price = option_data.get('strike_price')
        expiry_date = option_data.get('expiry_date')
        straddle_id = f"{market_data.symbol}_{strike_price}_{expiry_date}"
        
        if straddle_id not in self.straddle_positions:
            return None
        
        position = self.straddle_positions[straddle_id]
        entry_premium = position.get('entry_premium', 0)
        current_premium = market_data.close  # Assuming this is the current option premium
        
        # Calculate P&L
        pnl_multiple = current_premium / entry_premium if entry_premium > 0 else 0
        
        # Check profit target
        if pnl_multiple >= self.profit_target:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=market_data.symbol,
                confidence=0.9,
                price=current_premium,
                metadata={
                    'strategy_type': 'options_straddle',
                    'straddle_id': straddle_id,
                    'exit_reason': 'profit_target',
                    'pnl_multiple': pnl_multiple,
                    'entry_premium': entry_premium
                }
            )
        
        # Check stop loss
        if pnl_multiple <= self.stop_loss:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=market_data.symbol,
                confidence=0.9,
                price=current_premium,
                metadata={
                    'strategy_type': 'options_straddle',
                    'straddle_id': straddle_id,
                    'exit_reason': 'stop_loss',
                    'pnl_multiple': pnl_multiple,
                    'entry_premium': entry_premium
                }
            )
        
        # Check time decay (close position 1 day before expiry)
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        
        days_to_expiry = (expiry_date - datetime.now().date()).days
        if days_to_expiry <= 1:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=market_data.symbol,
                confidence=0.8,
                price=current_premium,
                metadata={
                    'strategy_type': 'options_straddle',
                    'straddle_id': straddle_id,
                    'exit_reason': 'time_decay',
                    'days_to_expiry': days_to_expiry
                }
            )
        
        return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate position size for options straddle"""
        
        # For options, position size is typically in lots
        max_position_value = current_balance * self.max_position_size
        
        # Estimate total premium for straddle (call + put)
        # This is simplified - in practice, you'd get both call and put premiums
        estimated_straddle_premium = signal.price * 2  # Rough estimate
        
        if estimated_straddle_premium > 0:
            lots = int(max_position_value / estimated_straddle_premium)
        else:
            lots = 0
        
        # Minimum 1 lot for options
        return max(lots, 1)
    
    def _validate_asset_class_specific(self, signal: StrategySignal) -> bool:
        """Derivatives-specific validation"""
        
        # Check if it's within trading hours for derivatives
        # This can be enhanced with actual market hours
        
        # Validate options-specific data
        metadata = signal.metadata
        if 'strike_price' not in metadata or 'expiry_date' not in metadata:
            return False
        
        # Check if expiry is in the future
        expiry_date = metadata.get('expiry_date')
        if isinstance(expiry_date, str):
            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        
        if expiry_date <= datetime.now().date():
            return False
        
        return True
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update position and track straddle positions"""
        super().update_position(symbol, quantity, price, side)
        
        # Track straddle positions separately
        # This is simplified - in practice, you'd track call and put separately
        if side == 'BUY':
            # Entering straddle position
            straddle_id = f"{symbol}_{price}"  # Simplified ID
            self.straddle_positions[straddle_id] = {
                'entry_premium': price,
                'quantity': quantity,
                'entry_time': datetime.now()
            }
        elif side == 'SELL':
            # Exiting straddle position
            # Find and remove the position
            for straddle_id, position in list(self.straddle_positions.items()):
                if symbol in straddle_id:
                    # Calculate P&L
                    entry_premium = position['entry_premium']
                    pnl = (price - entry_premium) * quantity
                    self.daily_pnl += pnl
                    
                    # Remove position
                    del self.straddle_positions[straddle_id]
                    break 