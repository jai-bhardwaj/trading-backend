"""
Real-time Test Strategy for Testing and Development

This strategy is designed for testing the automatic strategy registry
and real-time execution capabilities of the trading engine.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time
from app.strategies.base import BaseStrategy, StrategySignal, StrategyConfig, MarketData, SignalType, AssetClass

logger = logging.getLogger(__name__)

class RealtimeTestStrategy(BaseStrategy):
    """
    Simple test strategy for real-time testing and development
    
    This strategy generates simple buy/sell signals based on basic conditions
    and is primarily used for testing the strategy execution framework.
    """
    
    # Strategy metadata for automatic registry
    STRATEGY_NAME = "RealtimeTestStrategy"
    ASSET_CLASS = AssetClass.EQUITY
    VERSION = "1.0.0"
    AUTHOR = "Trading Team"
    DEPENDENCIES = []
    DEFAULT_PARAMETERS = {
        'signal_interval': 60,  # Generate signal every 60 seconds
        'test_symbol': 'RELIANCE',
        'min_price_change': 0.01  # Minimum price change to trigger signal
    }
    
    def initialize(self) -> None:
        """Initialize strategy-specific components"""
        # Get parameters from config
        self.signal_interval = self.parameters.get('signal_interval', 60)
        self.test_symbol = self.parameters.get('test_symbol', 'RELIANCE')
        self.min_price_change = self.parameters.get('min_price_change', 0.01)
        
        # Strategy state
        self.last_signal_time = None
        self.last_price = None
        self.signal_count = 0
        
        # Add test symbol if not in symbols list
        if self.test_symbol not in self.symbols:
            self.symbols.append(self.test_symbol)
        
        logger.info(f"RealtimeTestStrategy initialized with symbol: {self.test_symbol}")
    
    def process_market_data(self, market_data: MarketData) -> Optional[StrategySignal]:
        """
        Process market data and generate test signals
        
        Args:
            market_data: Current market data
            
        Returns:
            StrategySignal if conditions are met, None otherwise
        """
        try:
            logger.info(f"🔍 RealtimeTestStrategy processing market data for {market_data.symbol}")
            
            # Only process data for our test symbol
            if market_data.symbol != self.test_symbol:
                logger.debug(f"Skipping {market_data.symbol}, looking for {self.test_symbol}")
                return None
            
            current_time = datetime.now()
            current_price = market_data.close
            
            logger.info(f"💰 Processing {self.test_symbol}: current_price={current_price}, last_price={self.last_price}")
            
            # Check if enough time has passed since last signal
            if (self.last_signal_time and 
                (current_time - self.last_signal_time).total_seconds() < self.signal_interval):
                time_since_last = (current_time - self.last_signal_time).total_seconds()
                logger.info(f"⏰ Time check failed: {time_since_last}s < {self.signal_interval}s required")
                return None
            
            # Check if price has changed enough
            if self.last_price is None:
                logger.info(f"📊 First price data for {self.test_symbol}, setting last_price={current_price}")
                self.last_price = current_price
                return None
            
            price_change = abs(current_price - self.last_price)
            logger.info(f"📈 Price change: {price_change} (min required: {self.min_price_change})")
            
            if price_change < self.min_price_change:
                logger.info(f"❌ Price change too small: {price_change} < {self.min_price_change}")
                return None
            
            # Generate alternating buy/sell signals for testing
            signal_type = SignalType.BUY if self.signal_count % 2 == 0 else SignalType.SELL
            
            logger.info(f"🎯 Generating signal #{self.signal_count + 1}: {signal_type.value}")
            
            # Create test signal
            signal = StrategySignal(
                signal_type=signal_type,
                symbol=market_data.symbol,
                confidence=0.75,  # Test confidence level
                quantity=10,  # Small test quantity
                price=current_price,
                metadata={
                    'strategy': 'RealtimeTestStrategy',
                    'signal_number': self.signal_count + 1,
                    'price_change': price_change,
                    'test_mode': True
                }
            )
            
            # Update state
            self.last_signal_time = current_time
            self.last_price = current_price
            self.signal_count += 1
            
            logger.info(f"✅ RealtimeTestStrategy generated signal #{self.signal_count}: "
                       f"{signal_type.value} {market_data.symbol} @ {current_price} (change: {price_change})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in RealtimeTestStrategy.process_market_data: {e}")
            return None
    
    def calculate_position_size(self, signal: StrategySignal, current_balance: float) -> int:
        """
        Calculate position size for test strategy
        
        Args:
            signal: Trading signal
            current_balance: Current account balance
            
        Returns:
            Position size (always small for testing)
        """
        # For testing, always return a small fixed position size
        return 10
    
    def _validate_asset_class_specific(self, signal: StrategySignal) -> bool:
        """Validate signal for equity asset class"""
        # Basic validation for equity signals
        if signal.quantity and signal.quantity <= 0:
            return False
        
        if signal.price and signal.price <= 0:
            return False
        
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        base_info = super().get_strategy_info()
        
        # Add test strategy specific info
        base_info.update({
            'signal_count': self.signal_count,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'test_symbol': self.test_symbol,
            'last_price': self.last_price,
            'signal_interval': self.signal_interval
        })
        
        return base_info 