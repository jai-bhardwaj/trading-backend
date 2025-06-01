"""
Grid Trading Strategy for Cryptocurrency

This strategy places buy and sell orders at regular intervals above and below
the current price, profiting from market volatility and range-bound movements.
"""

import numpy as np
from typing import Optional, Dict, Any, List
from ..base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass
from ..registry import StrategyRegistry

@StrategyRegistry.register("grid_trading_crypto", AssetClass.CRYPTO)
class GridTradingStrategy(BaseStrategy):
    """
    Grid Trading Strategy for Cryptocurrency
    
    Parameters:
    - grid_spacing: Percentage spacing between grid levels (default: 0.02 = 2%)
    - num_grids: Number of grid levels above and below current price (default: 5)
    - base_order_size: Base order size in quote currency (default: 100)
    - max_total_investment: Maximum total investment (default: 1000)
    - rebalance_threshold: Price change % to trigger rebalancing (default: 0.1 = 10%)
    """
    
    def initialize(self) -> None:
        """Initialize strategy parameters"""
        self.grid_spacing = self.parameters.get('grid_spacing', 0.02)  # 2%
        self.num_grids = self.parameters.get('num_grids', 5)
        self.base_order_size = self.parameters.get('base_order_size', 100)
        self.max_total_investment = self.parameters.get('max_total_investment', 1000)
        self.rebalance_threshold = self.parameters.get('rebalance_threshold', 0.1)
        
        # Risk management parameters
        self.max_drawdown = self.risk_parameters.get('max_drawdown', 0.2)
        self.stop_loss_enabled = self.risk_parameters.get('stop_loss_enabled', False)
        
        # Strategy state
        self.grid_levels: Dict[str, List[Dict]] = {}  # {symbol: [grid_level_info]}
        self.last_rebalance_price: Dict[str, float] = {}
        self.total_invested: Dict[str, float] = {}
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """Process market data and generate grid trading signals"""
        
        # Add to historical data
        self.add_historical_data(market_data)
        
        symbol = market_data.symbol
        current_price = market_data.close
        
        # Initialize grid if not exists
        if symbol not in self.grid_levels:
            self._initialize_grid(symbol, current_price)
            return None
        
        # Check if rebalancing is needed
        if self._should_rebalance(symbol, current_price):
            return self._rebalance_grid(symbol, current_price)
        
        # Check for grid level triggers
        return self._check_grid_triggers(symbol, current_price, market_data)
    
    def _initialize_grid(self, symbol: str, current_price: float) -> None:
        """Initialize grid levels around current price"""
        grid_levels = []
        
        # Create buy levels (below current price)
        for i in range(1, self.num_grids + 1):
            buy_price = current_price * (1 - i * self.grid_spacing)
            grid_levels.append({
                'price': buy_price,
                'type': 'BUY',
                'level': -i,
                'filled': False,
                'order_size': self.base_order_size
            })
        
        # Create sell levels (above current price)
        for i in range(1, self.num_grids + 1):
            sell_price = current_price * (1 + i * self.grid_spacing)
            grid_levels.append({
                'price': sell_price,
                'type': 'SELL',
                'level': i,
                'filled': False,
                'order_size': self.base_order_size
            })
        
        self.grid_levels[symbol] = grid_levels
        self.last_rebalance_price[symbol] = current_price
        self.total_invested[symbol] = 0.0
    
    def _should_rebalance(self, symbol: str, current_price: float) -> bool:
        """Check if grid should be rebalanced"""
        if symbol not in self.last_rebalance_price:
            return False
        
        last_price = self.last_rebalance_price[symbol]
        price_change_pct = abs(current_price - last_price) / last_price
        
        return price_change_pct > self.rebalance_threshold
    
    def _rebalance_grid(self, symbol: str, current_price: float) -> Optional[StrategySignal]:
        """Rebalance grid around new price level"""
        
        # Cancel existing unfilled orders (in practice, you'd track order IDs)
        # For now, just reinitialize the grid
        self._initialize_grid(symbol, current_price)
        
        return StrategySignal(
            signal_type=SignalType.HOLD,
            symbol=symbol,
            confidence=0.5,
            price=current_price,
            metadata={
                'strategy_type': 'grid_trading',
                'action': 'rebalance',
                'new_center_price': current_price
            }
        )
    
    def _check_grid_triggers(self, symbol: str, current_price: float, market_data: MarketData) -> Optional[StrategySignal]:
        """Check if current price triggers any grid levels"""
        
        grid_levels = self.grid_levels[symbol]
        
        for level in grid_levels:
            if level['filled']:
                continue
            
            level_price = level['price']
            level_type = level['type']
            
            # Check if price has crossed this level
            if level_type == 'BUY' and current_price <= level_price:
                # Price dropped to buy level
                if self.total_invested[symbol] < self.max_total_investment:
                    return self._generate_grid_signal(symbol, level, market_data)
            
            elif level_type == 'SELL' and current_price >= level_price:
                # Price rose to sell level
                # Check if we have position to sell
                current_position = self.positions.get(symbol, {}).get('quantity', 0)
                if current_position > 0:
                    return self._generate_grid_signal(symbol, level, market_data)
        
        return None
    
    def _generate_grid_signal(self, symbol: str, level: Dict, market_data: MarketData) -> StrategySignal:
        """Generate trading signal for grid level"""
        
        signal_type = SignalType.BUY if level['type'] == 'BUY' else SignalType.SELL
        
        signal = StrategySignal(
            signal_type=signal_type,
            symbol=symbol,
            confidence=0.8,
            price=level['price'],
            metadata={
                'strategy_type': 'grid_trading',
                'grid_level': level['level'],
                'grid_price': level['price'],
                'order_size': level['order_size']
            }
        )
        
        # Mark level as filled
        level['filled'] = True
        
        return signal
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """Calculate position size for grid trading"""
        
        # Get order size from signal metadata
        order_size_value = signal.metadata.get('order_size', self.base_order_size)
        
        if signal.price and signal.price > 0:
            # For crypto, calculate quantity based on order value
            quantity = order_size_value / signal.price
            
            # Round to appropriate decimal places for crypto
            # Most cryptos support 8 decimal places
            quantity = round(quantity, 8)
            
            # Convert to integer representation if needed (depends on exchange)
            # For this example, we'll return the quantity as is
            return int(quantity * 100000000)  # Convert to satoshis for BTC-like precision
        
        return 0
    
    def _validate_asset_class_specific(self, signal: StrategySignal) -> bool:
        """Crypto-specific validation"""
        
        # Check if it's a valid crypto trading pair
        symbol = signal.symbol
        if not ('USDT' in symbol or 'BTC' in symbol or 'ETH' in symbol):
            # Basic validation for common crypto pairs
            pass
        
        # Check minimum order size
        order_size = signal.metadata.get('order_size', 0)
        if order_size < 10:  # Minimum $10 order
            return False
        
        # Check if we haven't exceeded maximum investment
        total_invested = self.total_invested.get(symbol, 0)
        if signal.signal_type == SignalType.BUY and total_invested >= self.max_total_investment:
            return False
        
        return True
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update position and track grid trading state"""
        super().update_position(symbol, quantity, price, side)
        
        # Update total invested tracking
        if symbol not in self.total_invested:
            self.total_invested[symbol] = 0.0
        
        if side == 'BUY':
            # Convert quantity back from integer representation
            actual_quantity = quantity / 100000000
            investment = actual_quantity * price
            self.total_invested[symbol] += investment
            
        elif side == 'SELL':
            # Reduce total invested (take profit)
            actual_quantity = quantity / 100000000
            divestment = actual_quantity * price
            self.total_invested[symbol] = max(0, self.total_invested[symbol] - divestment)
        
        # Reset filled status for grid levels that are now available again
        self._reset_available_grid_levels(symbol, price)
    
    def _reset_available_grid_levels(self, symbol: str, current_price: float) -> None:
        """Reset grid levels that are now available for trading again"""
        
        if symbol not in self.grid_levels:
            return
        
        grid_levels = self.grid_levels[symbol]
        
        for level in grid_levels:
            if not level['filled']:
                continue
            
            level_price = level['price']
            level_type = level['type']
            
            # Reset buy levels that are now below current price
            if level_type == 'BUY' and current_price > level_price * 1.01:  # 1% buffer
                level['filled'] = False
            
            # Reset sell levels that are now above current price
            elif level_type == 'SELL' and current_price < level_price * 0.99:  # 1% buffer
                level['filled'] = False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information including grid state"""
        info = super().get_strategy_info()
        
        info.update({
            'grid_levels': self.grid_levels,
            'total_invested': self.total_invested,
            'last_rebalance_prices': self.last_rebalance_price
        })
        
        return info 