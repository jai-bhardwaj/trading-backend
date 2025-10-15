"""
Test Strategy - Migrated to new architecture
A simple test strategy for development and testing purposes
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List
import redis.asyncio as redis

# Add parent directories to path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/strategy-service')

from shared.models import MarketDataTick, TradingSignal, SignalType, StrategyConfig
from shared.timezone import get_ist_now, get_ist_timestamp
from base.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class TestStrategy(BaseStrategy):
    """Test Strategy using new architecture"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy parameters
        self.test_mode = self.parameters.get('test_mode', True)
        self.signal_interval = self.parameters.get('signal_interval', 10)  # Generate signal every N ticks
        self.tick_count = 0
        
        logger.info(f"Test Strategy initialized with parameters:")
        logger.info(f"  Test Mode: {self.test_mode}")
        logger.info(f"  Signal Interval: {self.signal_interval}")
    
    async def run(self, market_data: Dict[str, MarketDataTick]) -> List[TradingSignal]:
        """Run Test strategy"""
        signals = []
        
        # Log the market data received
        logger.info(f"[TestStrategy] Processing market data for {len(market_data)} symbols")
        
        # Simple test logic - generate a basic signal for each symbol periodically
        for symbol in self.symbols:
            if symbol not in market_data:
                logger.warning(f"⚠️ No market data for {symbol}")
                continue
            
            try:
                current_tick = market_data[symbol]
                self.tick_count += 1
                
                # Generate signal every N ticks for testing
                if self.tick_count % self.signal_interval == 0:
                    signal = TradingSignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        confidence=0.5,  # Medium confidence for testing
                        price=current_tick.ltp,
                        quantity=self.calculate_quantity(current_tick.ltp),
                        timestamp=get_ist_now(),
                        metadata={
                            'strategy': 'test_strategy',
                            'test_mode': self.test_mode,
                            'reason': 'Test signal generation',
                            'tick_count': self.tick_count,
                            'signal_interval': self.signal_interval
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📊 Test Strategy generated signal for {symbol}: BUY @ {current_tick.ltp}")
                
            except Exception as e:
                logger.error(f"❌ Error in Test strategy for {symbol}: {e}")
        
        if signals:
            logger.info(f"[TestStrategy] Generated {len(signals)} test signals")
        
        return signals

async def main():
    """Main entry point for the strategy service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment variables
    strategy_id = os.getenv('STRATEGY_ID', 'test_strategy')
    symbols_str = os.getenv('SYMBOLS', 'RELIANCE,TCS,INFY')
    symbols = [s.strip() for s in symbols_str.split(',')]
    
    # Strategy parameters
    parameters = {
        'test_mode': os.getenv('TEST_MODE', 'true').lower() == 'true',
        'signal_interval': int(os.getenv('SIGNAL_INTERVAL', '10')),
        'capital': float(os.getenv('CAPITAL', '100000')),
        'max_quantity': int(os.getenv('MAX_QUANTITY', '1000')),
        'min_quantity': int(os.getenv('MIN_QUANTITY', '1'))
    }
    
    # Redis configuration
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    
    # Create strategy configuration
    config = StrategyConfig(
        strategy_id=strategy_id,
        symbols=symbols,
        parameters=parameters,
        enabled=True,
        redis_url=redis_url
    )
    
    # Create and start strategy
    strategy = TestStrategy(config)
    
    try:
        logger.info(f"🚀 Starting Test Strategy Service...")
        success = await strategy.start()
        
        if success:
            logger.info(f"✅ Test Strategy Service started successfully")
            
            # Keep running
            while True:
                await asyncio.sleep(60)  # Health check every minute
                
                # Log stats every 5 minutes
                stats = strategy.get_stats()
                if stats['ticks_processed'] % 300 == 0:  # Every 5 minutes (300 ticks)
                    logger.info(f"📊 Strategy Stats: {stats}")
        else:
            logger.error(f"❌ Failed to start Test Strategy Service")
            
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
    finally:
        await strategy.stop()
        logger.info("✅ Test Strategy Service stopped")

if __name__ == "__main__":
    asyncio.run(main())
