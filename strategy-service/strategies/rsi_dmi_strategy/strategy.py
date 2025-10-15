"""
RSI DMI Strategy - Migrated to new architecture
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
from base.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class RSIDMIStrategy(BaseStrategy):
    """RSI DMI Strategy using new architecture"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy parameters
        self.entry_rsi_ul = self.parameters.get('entry_rsi_UL', 70)
        self.di_ul = self.parameters.get('di_UL', 25)
        self.rsi_ll = self.parameters.get('rsi_LL', 30)
        
        logger.info(f"RSI DMI Strategy initialized with parameters:")
        logger.info(f"  Entry RSI Upper Limit: {self.entry_rsi_ul}")
        logger.info(f"  DI Upper Limit: {self.di_ul}")
        logger.info(f"  RSI Lower Limit: {self.rsi_ll}")
    
    async def run(self, market_data: Dict[str, MarketDataTick]) -> List[TradingSignal]:
        """Run RSI DMI strategy"""
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                logger.warning(f"⚠️ No market data for {symbol}")
                continue
            
            try:
                # Get historical data for RSI and DMI calculation
                hist_data = self.get_historical_buffer(symbol, 50)  # Get last 50 ticks
                if len(hist_data) < 15:  # Need at least 15 ticks for RSI/DMI calculation
                    logger.warning(f"⚠️ Insufficient historical data for {symbol}: {len(hist_data)} ticks")
                    continue
                
                # Calculate RSI and DMI
                rsi_values = self.indicators.calculate_rsi(hist_data, 14)
                dmi_data = self.indicators.calculate_dmi(hist_data, 14)
                
                if not rsi_values or not dmi_data or len(rsi_values) < 2 or len(dmi_data['+DI']) < 2:
                    logger.warning(f"⚠️ Insufficient indicator data for {symbol}")
                    continue
                
                # Get latest values
                latest_rsi = rsi_values[-1]
                latest_di_plus = dmi_data['+DI'][-1]
                latest_di_minus = dmi_data['-DI'][-1]
                
                # Get previous values for confirmation
                prev_rsi = rsi_values[-2] if len(rsi_values) > 1 else latest_rsi
                prev_di_plus = dmi_data['+DI'][-2] if len(dmi_data['+DI']) > 1 else latest_di_plus
                prev_di_minus = dmi_data['-DI'][-2] if len(dmi_data['-DI']) > 1 else latest_di_minus
                
                current_tick = market_data[symbol]
                
                # Check buy conditions (both current and previous must satisfy)
                if (latest_rsi >= self.entry_rsi_ul and 
                    latest_di_plus >= self.di_ul and
                    prev_rsi >= self.entry_rsi_ul and 
                    prev_di_plus >= self.di_ul):
                    
                    signal = TradingSignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        confidence=0.8,
                        price=current_tick.ltp,
                        quantity=self.calculate_quantity(current_tick.ltp),
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'RSI DMI',
                            'latest_rsi': latest_rsi,
                            'latest_di_plus': latest_di_plus,
                            'prev_rsi': prev_rsi,
                            'prev_di_plus': prev_di_plus,
                            'entry_rsi_ul': self.entry_rsi_ul,
                            'di_ul': self.di_ul
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📈 RSI DMI BUY signal for {symbol}: RSI={latest_rsi:.2f}, +DI={latest_di_plus:.2f}")
                
                # Check sell conditions (both current and previous must satisfy)
                elif (latest_rsi <= self.rsi_ll and 
                      latest_di_minus >= self.di_ul and
                      prev_rsi <= self.rsi_ll and 
                      prev_di_minus >= self.di_ul):
                    
                    signal = TradingSignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        confidence=0.8,
                        price=current_tick.ltp,
                        quantity=self.calculate_quantity(current_tick.ltp),
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'RSI DMI',
                            'latest_rsi': latest_rsi,
                            'latest_di_minus': latest_di_minus,
                            'prev_rsi': prev_rsi,
                            'prev_di_minus': prev_di_minus,
                            'rsi_ll': self.rsi_ll,
                            'di_ul': self.di_ul
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📉 RSI DMI SELL signal for {symbol}: RSI={latest_rsi:.2f}, -DI={latest_di_minus:.2f}")
                    
            except Exception as e:
                logger.error(f"❌ Error in RSI DMI strategy for {symbol}: {e}")
                
        return signals

async def main():
    """Main entry point for the strategy service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment variables
    strategy_id = os.getenv('STRATEGY_ID', 'rsi_dmi_strategy')
    symbols_str = os.getenv('SYMBOLS', 'RELIANCE,TCS,INFY')
    symbols = [s.strip() for s in symbols_str.split(',')]
    
    # Strategy parameters
    parameters = {
        'entry_rsi_UL': float(os.getenv('ENTRY_RSI_UL', '70')),
        'di_UL': float(os.getenv('DI_UL', '25')),
        'rsi_LL': float(os.getenv('RSI_LL', '30')),
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
    strategy = RSIDMIStrategy(config)
    
    try:
        logger.info(f"🚀 Starting RSI DMI Strategy Service...")
        success = await strategy.start()
        
        if success:
            logger.info(f"✅ RSI DMI Strategy Service started successfully")
            
            # Keep running
            while True:
                await asyncio.sleep(60)  # Health check every minute
                
                # Log stats every 5 minutes
                stats = strategy.get_stats()
                if stats['ticks_processed'] % 300 == 0:  # Every 5 minutes (300 ticks)
                    logger.info(f"📊 Strategy Stats: {stats}")
        else:
            logger.error(f"❌ Failed to start RSI DMI Strategy Service")
            
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
    finally:
        await strategy.stop()
        logger.info("✅ RSI DMI Strategy Service stopped")

if __name__ == "__main__":
    asyncio.run(main())
