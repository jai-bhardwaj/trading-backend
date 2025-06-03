"""
Test Strategy 2 Min - Places orders every 2 minutes for testing
Updated for the new cleaned schema and enhanced strategy execution system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time, timedelta
from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class TestStrategy2Min(BaseStrategy):
    """
    Test Strategy - Places orders every 2 minutes for the new system
    
    This strategy is designed for testing purposes only. It will:
    - Place a BUY order every 2 minutes
    - Alternate between different test symbols
    - Use small position sizes for safety
    - Close positions after 4 minutes (2 cycles)
    """
    
    async def on_initialize(self):
        """Initialize test strategy parameters"""
        # Strategy parameters
        self.order_interval_minutes = self.config.get('order_interval_minutes', 2)
        self.max_position_size = self.config.get('max_position_size', 0.01)  # Very small for testing
        self.auto_close_minutes = self.config.get('auto_close_minutes', 4)
        
        # Test symbols to cycle through
        self.test_symbols = self.config.get('test_symbols', ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK'])
        self.current_symbol_index = 0
        
        # Risk management parameters (conservative for testing)
        self.max_drawdown = self.config.get('max_drawdown', 0.02)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.01)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.02)
        
        # Strategy state
        self.last_order_time: Optional[datetime] = None
        self.entry_times: Dict[str, datetime] = {}
        self.order_counter = 0
        
        # Trading hours (9:15 AM to 3:30 PM IST)
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        
        # Subscribe to test symbols
        await self.subscribe_to_instruments(self.test_symbols)
        
        logger.info(f"Test Strategy 2Min initialized with {len(self.test_symbols)} symbols")
    
    async def on_market_data(self, symbol: str, data: Dict[str, Any]):
        """Process market data updates for test strategy"""
        try:
            current_price = data.get('ltp', data.get('close', 100.0))
            current_time = datetime.now()
            
            # Check trading hours
            if not (self.market_start <= current_time.time() <= self.market_end):
                return
            
            # Check for auto-close signals first
            if await self._should_auto_close(symbol, current_time):
                await self.exit_position(symbol, "NSE")
                return
            
            # Check if it's time to place a new order
            if self._should_place_order(current_time):
                # Get the next test symbol
                test_symbol = self._get_next_test_symbol()
                
                # Only place order if this is the current test symbol
                if symbol == test_symbol:
                    await self._place_test_order(symbol, current_price)
                    
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals every 2 minutes"""
        signals = []
        current_time = datetime.now()
        
        # Check trading hours
        if not (self.market_start <= current_time.time() <= self.market_end):
            return signals
        
        # Check for auto-close signals
        for position_key, position in self.positions.items():
            if position.quantity > 0:
                symbol = position.symbol
                if await self._should_auto_close(symbol, current_time):
                    signals.append({
                        'type': 'SELL',
                        'symbol': symbol,
                        'exchange': position.exchange,
                        'quantity': position.quantity,
                        'order_type': 'MARKET',
                        'product_type': position.product_type.value,
                        'reason': f'Auto-close after {self.auto_close_minutes} minutes'
                    })
        
        # Check if it's time to place a new order
        if self._should_place_order(current_time):
            test_symbol = self._get_next_test_symbol()
            
            # Only create signal if we don't have a position in this symbol
            position_key = f"{test_symbol}_NSE_INTRADAY"
            if position_key not in self.positions or self.positions[position_key].quantity == 0:
                signals.append({
                    'type': 'BUY',
                    'symbol': test_symbol,
                    'exchange': 'NSE',
                    'quantity': 1,  # Small test quantity
                    'order_type': 'MARKET',
                    'product_type': 'INTRADAY',
                    'reason': f'Test order #{self.order_counter + 1} - 2min interval'
                })
                
                self.order_counter += 1
                self.last_order_time = current_time
        
        return signals
    
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
    
    async def _should_auto_close(self, symbol: str, current_time: datetime) -> bool:
        """Check if position should be auto-closed after specified time"""
        if symbol not in self.entry_times:
            return False
        
        entry_time = self.entry_times[symbol]
        time_held = current_time - entry_time
        
        return time_held >= timedelta(minutes=self.auto_close_minutes)
    
    async def _place_test_order(self, symbol: str, current_price: float):
        """Place a test buy order"""
        try:
            await self.place_buy_order(
                symbol=symbol,
                exchange="NSE",
                quantity=1,  # Small test quantity
                order_type='MARKET',
                product_type='INTRADAY'
            )
            
            # Track entry time for auto-close
            self.entry_times[symbol] = datetime.now()
            self.order_counter += 1
            self.last_order_time = datetime.now()
            
            logger.info(f"Placed test order #{self.order_counter} for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to place test order for {symbol}: {e}")
    
    async def on_strategy_iteration(self):
        """Called after each strategy iteration"""
        # Update custom metrics
        self.metrics['custom_metrics'].update({
            'order_counter': self.order_counter,
            'current_test_symbol': self.test_symbols[self.current_symbol_index],
            'active_test_positions': len([p for p in self.positions.values() if p.quantity > 0]),
            'last_order_time': self.last_order_time.isoformat() if self.last_order_time else None
        })
    
    async def on_order_filled(self, order):
        """Called when an order is filled"""
        logger.info(f"Test order filled: {order.symbol} {order.side.value} {order.quantity} @ {order.average_price}")
    
    async def on_position_opened(self, position):
        """Called when a new position is opened"""
        logger.info(f"Test position opened: {position.symbol} {position.quantity} shares")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a position is closed"""
        logger.info(f"Test position closed: {position.symbol} with P&L: ₹{pnl}") 