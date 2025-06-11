"""
Test Strategy for Trading System
Places orders at configurable intervals for system testing purposes.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time, timedelta
from ..base_strategy import BaseStrategy
from ..registry import AutomaticStrategyRegistry
from app.core.timezone_utils import now_ist, is_market_hours
from app.models.base import AssetClass

logger = logging.getLogger(__name__)

@AutomaticStrategyRegistry.register("test_strategy", AssetClass.EQUITY)
class TestStrategy(BaseStrategy):
    """
    Test Strategy for System Testing
    
    This strategy places orders at configurable intervals for testing purposes.
    Perfect for validating the trading system, order execution, and monitoring.
    
    Configuration:
    - order_interval_minutes: How often to place orders (default: 5 minutes)
    - test_symbols: List of symbols to test with (default: ['RELIANCE'])
    - test_quantity: Quantity per order (default: 1)
    - max_test_orders: Maximum number of orders to place (default: 10)
    - alternate_sides: Whether to alternate BUY/SELL (default: True)
    """
    
    async def on_initialize(self):
        """Initialize test strategy parameters"""
        # Test configuration
        self.order_interval_minutes = self.parameters.get('order_interval_minutes', 10)  # Generate orders every 10 minutes
        self.test_symbols = self.parameters.get('test_symbols', ['RELIANCE-EQ'])
        self.test_quantity = self.parameters.get('test_quantity', 1)
        self.max_test_orders = self.parameters.get('max_test_orders', 50)  # Increased for more testing
        self.alternate_sides = self.parameters.get('alternate_sides', True)
        
        # Test state
        self.last_order_time = None
        self.order_count = 0
        self.current_side = 'BUY'  # Start with BUY orders
        self.test_start_time = now_ist()
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        logger.info(f"🧪 Test Strategy initialized:")
        logger.info(f"   📅 Order interval: {self.order_interval_minutes} minutes")
        logger.info(f"   📊 Test symbols: {self.test_symbols}")
        logger.info(f"   📦 Test quantity: {self.test_quantity}")
        logger.info(f"   🔢 Max orders: {self.max_test_orders}")
        logger.info(f"   🔄 Alternate sides: {self.alternate_sides}")
    
    async def process_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process market data and generate test signals"""
        current_time = now_ist()
        
        # Check if we've reached max orders
        if self.order_count >= self.max_test_orders:
            return None
        
        # Trading hours check disabled for testing - generate orders 24/7 for system testing
        # if not is_market_hours(current_time):
        #     return None
        
        # Check if it's time for next order
        if self._should_place_order(current_time):
            try:
                # Determine order side
                order_side = self._get_next_order_side()
                
                # Create test signal
                signal = {
                    'type': order_side,
                    'symbol': market_data.get('symbol', self.test_symbols[0]),
                    'exchange': 'NSE',
                    'quantity': self.test_quantity,
                    'order_type': 'MARKET',
                    'product_type': 'INTRADAY',
                    'confidence': 0.8,
                    'metadata': {
                        'test_order_number': self.order_count + 1,
                        'order_interval_minutes': self.order_interval_minutes,
                        'reason': f'Test order #{self.order_count + 1} - {self.order_interval_minutes}min interval'
                    }
                }
                
                # Update state
                self.last_order_time = current_time
                self.order_count += 1
                
                logger.info(f"🧪 Test signal generated: {order_side} {signal['symbol']} x{self.test_quantity} (Order #{self.order_count})")
                
                return signal
                
            except Exception as e:
                logger.error(f"❌ Error generating test signal: {e}")
                return None
        
        return None
    

    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data (minimal processing for test strategy)"""
        # Just log occasionally for testing
        if self.order_count == 0:
            logger.debug(f"📈 Test strategy received market data for {symbol}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate test signals at configured intervals"""
        signals = []
        current_time = now_ist()
        
        # Check if we've reached max orders
        if self.order_count >= self.max_test_orders:
            logger.info(f"🏁 Test strategy completed: {self.order_count} orders placed")
            return signals
        
        # Trading hours check disabled for testing - generate orders 24/7 for system testing
        # if not is_market_hours(current_time):
        #     return signals
        
        # Check if it's time for next order
        if self._should_place_order(current_time):
            try:
                # Determine order side
                order_side = self._get_next_order_side()
                
                # Create test signal for the first test symbol
                test_symbol = self.test_symbols[0]
                
                signal = {
                    'type': order_side,
                    'symbol': test_symbol,
                    'exchange': 'NSE',
                    'quantity': self.test_quantity,
                    'order_type': 'MARKET',
                    'product_type': 'INTRADAY',
                    'reason': f'Test order #{self.order_count + 1} - {self.order_interval_minutes}min interval'
                }
                
                signals.append(signal)
                
                # Update state
                self.last_order_time = current_time
                self.order_count += 1
                
                logger.info(f"🧪 Test signal generated: {order_side} {test_symbol} x{self.test_quantity} (Order #{self.order_count})")
                
            except Exception as e:
                logger.error(f"❌ Error generating test signal: {e}")
        
        return signals
    
    def _should_place_order(self, current_time: datetime) -> bool:
        """Check if it's time to place the next order"""
        if self.last_order_time is None:
            return True  # Place first order immediately
        
        time_elapsed = current_time - self.last_order_time
        interval_seconds = self.order_interval_minutes * 60
        
        return time_elapsed.total_seconds() >= interval_seconds
    
    def _get_next_order_side(self) -> str:
        """Get the next order side (BUY/SELL)"""
        if not self.alternate_sides:
            return 'BUY'  # Always BUY if not alternating
        
        # Alternate between BUY and SELL
        if self.current_side == 'BUY':
            self.current_side = 'SELL'
            return 'BUY'
        else:
            self.current_side = 'BUY'
            return 'SELL'
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        current_time = now_ist()
        runtime_minutes = (current_time - self.test_start_time).total_seconds() / 60
        
        # Calculate next order time
        next_order_time = "Now"
        if self.last_order_time:
            next_order_in = self.order_interval_minutes - ((current_time - self.last_order_time).total_seconds() / 60)
            if next_order_in > 0:
                next_order_time = f"{next_order_in:.1f} minutes"
        
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'test_symbols': self.test_symbols,
            'order_interval_minutes': self.order_interval_minutes,
            'orders_placed': self.order_count,
            'max_orders': self.max_test_orders,
            'progress_percentage': round((self.order_count / self.max_test_orders) * 100, 1),
            'runtime_minutes': round(runtime_minutes, 1),
            'next_order_in': next_order_time,
            'current_side': self.current_side,
            'alternate_sides': self.alternate_sides,
            'test_status': 'COMPLETED' if self.order_count >= self.max_test_orders else 'RUNNING'
        })
    
    async def on_order_filled(self, order):
        """Called when a test order is filled"""
        logger.info(f"✅ Test order filled: {order.side.value} {order.symbol} x{order.quantity} @ ₹{order.average_price}")
        
        # Log progress
        remaining_orders = self.max_test_orders - self.order_count
        if remaining_orders > 0:
            logger.info(f"📊 Test progress: {self.order_count}/{self.max_test_orders} orders completed ({remaining_orders} remaining)")
        else:
            logger.info(f"🎉 Test completed! All {self.max_test_orders} orders placed successfully")
    
    async def on_position_opened(self, position):
        """Called when a test position is opened"""
        logger.info(f"📈 Test position opened: {position.symbol} {position.quantity} shares")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a test position is closed"""
        logger.info(f"📉 Test position closed: {position.symbol} with P&L: ₹{pnl}")
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of test execution"""
        current_time = now_ist()
        runtime_minutes = (current_time - self.test_start_time).total_seconds() / 60
        
        return {
            'test_start_time': self.test_start_time.isoformat(),
            'runtime_minutes': round(runtime_minutes, 1),
            'orders_placed': self.order_count,
            'max_orders': self.max_test_orders,
            'progress_percentage': round((self.order_count / self.max_test_orders) * 100, 1),
            'order_interval_minutes': self.order_interval_minutes,
            'test_symbols': self.test_symbols,
            'test_quantity': self.test_quantity,
            'alternate_sides': self.alternate_sides,
            'status': 'COMPLETED' if self.order_count >= self.max_test_orders else 'RUNNING'
        } 