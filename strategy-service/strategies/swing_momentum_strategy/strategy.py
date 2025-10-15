"""
Swing Momentum Strategy - Migrated to new architecture
Swing trading with momentum
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

class SwingMomentumStrategy(BaseStrategy):
    """Swing Momentum Strategy using new architecture"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy parameters
        self.momentum_percentage = self.parameters.get('momentum_percentage', 4.0)
        self.holding_days = self.parameters.get('holding_days', 2)
        
        logger.info(f"Swing Momentum Strategy initialized with parameters:")
        logger.info(f"  Momentum Percentage: {self.momentum_percentage}")
        logger.info(f"  Holding Days: {self.holding_days}")
    
    async def run(self, market_data: Dict[str, MarketDataTick]) -> List[TradingSignal]:
        """Run Swing Momentum strategy"""
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                logger.warning(f"⚠️ No market data for {symbol}")
                continue
            
            try:
                # Get historical data for momentum calculation
                hist_data = self.get_historical_buffer(symbol, 50)  # Get last 50 ticks
                if len(hist_data) < 2:
                    logger.warning(f"⚠️ Insufficient historical data for {symbol}: {len(hist_data)} ticks")
                    continue
                
                # Check if we have MACD and Stochastic signals (simplified for new architecture)
                if not await self._check_macd_stoch_signals(symbol):
                    continue
                
                # Calculate momentum
                momentum = self._calculate_momentum(hist_data)
                if momentum is None:
                    continue
                
                # Check momentum condition
                if momentum >= self.momentum_percentage:
                    current_tick = market_data[symbol]
                    
                    signal = TradingSignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        confidence=0.8,
                        price=current_tick.ltp,
                        quantity=self.calculate_quantity(current_tick.ltp),
                        timestamp=get_ist_now(),
                        metadata={
                            'strategy': 'Swing Momentum',
                            'momentum_percentage': momentum,
                            'required_momentum': self.momentum_percentage,
                            'holding_days': self.holding_days
                        }
                    )
                    signals.append(signal)
                    logger.info(f"📈 Swing Momentum BUY signal for {symbol}: Momentum={momentum:.2f}%")
                    
            except Exception as e:
                logger.error(f"❌ Error in Swing Momentum strategy for {symbol}: {e}")
                
        return signals
    
    async def _check_macd_stoch_signals(self, symbol: str) -> bool:
        """Check if MACD and Stochastic signals are aligned"""
        try:
            # In the new architecture, we can calculate MACD and Stochastic directly
            hist_data = self.get_historical_buffer(symbol, 50)
            if len(hist_data) < 26:  # Need at least 26 ticks for MACD calculation
                return False
            
            # Calculate MACD
            macd_data = self.indicators.calculate_macd(hist_data, 12, 26, 9)
            if not macd_data or not macd_data['macd'] or len(macd_data['macd']) < 2:
                return False
            
            # Calculate Stochastic
            stoch_data = self.indicators.calculate_stochastic(hist_data, 14, 3)
            if not stoch_data or not stoch_data['%K'] or len(stoch_data['%K']) < 2:
                return False
            
            # Check if MACD line is above signal line (bullish)
            latest_macd = macd_data['macd'][-1]
            latest_signal = macd_data['signal'][-1]
            macd_bullish = latest_macd > latest_signal
            
            # Check if Stochastic %K is above %D (bullish)
            latest_k = stoch_data['%K'][-1]
            latest_d = stoch_data['%D'][-1] if stoch_data['%D'] else latest_k
            stoch_bullish = latest_k > latest_d
            
            # Both indicators should be bullish
            return macd_bullish and stoch_bullish
            
        except Exception as e:
            logger.error(f"❌ Error checking MACD/Stoch signals for {symbol}: {e}")
            return False
    
    def _calculate_momentum(self, hist_data: List[MarketDataTick]) -> float:
        """Calculate momentum percentage"""
        try:
            if len(hist_data) < 2:
                return None
            
            # Get open price and current price
            open_price = hist_data[0].ltp
            current_price = hist_data[-1].ltp
            
            # Calculate momentum percentage
            momentum = ((current_price - open_price) / open_price) * 100
            
            return momentum
            
        except Exception as e:
            logger.error(f"❌ Error calculating momentum: {e}")
            return None

async def main():
    """Main entry point for the strategy service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment variables
    strategy_id = os.getenv('STRATEGY_ID', 'swing_momentum_strategy')
    symbols_str = os.getenv('SYMBOLS', 'RELIANCE,TCS,INFY')
    symbols = [s.strip() for s in symbols_str.split(',')]
    
    # Strategy parameters
    parameters = {
        'momentum_percentage': float(os.getenv('MOMENTUM_PERCENTAGE', '4.0')),
        'holding_days': int(os.getenv('HOLDING_DAYS', '2')),
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
    strategy = SwingMomentumStrategy(config)
    
    try:
        logger.info(f"🚀 Starting Swing Momentum Strategy Service...")
        success = await strategy.start()
        
        if success:
            logger.info(f"✅ Swing Momentum Strategy Service started successfully")
            
            # Keep running
            while True:
                await asyncio.sleep(60)  # Health check every minute
                
                # Log stats every 5 minutes
                stats = strategy.get_stats()
                if stats['ticks_processed'] % 300 == 0:  # Every 5 minutes (300 ticks)
                    logger.info(f"📊 Strategy Stats: {stats}")
        else:
            logger.error(f"❌ Failed to start Swing Momentum Strategy Service")
            
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
    finally:
        await strategy.stop()
        logger.info("✅ Swing Momentum Strategy Service stopped")

if __name__ == "__main__":
    asyncio.run(main())
