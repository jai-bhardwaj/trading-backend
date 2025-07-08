"""
Swing Momentum Strategy - Swing trading with momentum
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from strategy.base import BaseStrategy
from strategy.market_data import MarketDataProvider, MarketData

logger = logging.getLogger(__name__)

class SwingMomentumStrategy(BaseStrategy):
    """Swing Momentum Strategy - Swing trading with momentum gain"""
    
    def __init__(self, config: Dict[str, Any], market_data_provider: MarketDataProvider):
        super().__init__(config, market_data_provider)
        self.momentum_percentage = self.parameters.get('momentum_percentage', 4.0)
        self.holding_days = self.parameters.get('holding_days', 2)
        
    async def run(self, market_data: Dict[str, MarketData]) -> List[Dict]:
        """Run Swing Momentum strategy"""
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                logger.warning(f"⚠️ No market data for {symbol}")
                continue
                
            try:
                # Get historical data for momentum calculation
                hist_data = await self._get_historical_data(symbol)
                if not hist_data or len(hist_data) < 2:
                    logger.warning(f"⚠️ Insufficient historical data for {symbol}")
                    continue
                
                # Check if we have MACD and Stochastic signals
                if not await self._check_macd_stoch_signals(symbol):
                    continue
                
                # Calculate momentum
                momentum = self._calculate_momentum(hist_data)
                if momentum is None:
                    continue
                
                # Check momentum condition
                if momentum >= self.momentum_percentage:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'confidence': 0.8,
                        'price': market_data[symbol].ltp,
                        'quantity': self._calculate_quantity(market_data[symbol].ltp),
                        'timestamp': datetime.now(),
                        'metadata': {
                            'strategy': 'Swing Momentum',
                            'momentum_percentage': momentum,
                            'required_momentum': self.momentum_percentage,
                            'holding_days': self.holding_days
                        }
                    }
                    signals.append(signal)
                    logger.info(f"📈 Swing Momentum BUY signal for {symbol}: Momentum={momentum:.2f}%")
                    
            except Exception as e:
                logger.error(f"❌ Error in Swing Momentum strategy for {symbol}: {e}")
                
        return signals
    
    async def _get_historical_data(self, symbol: str) -> List[Dict]:
        """Get historical data for momentum calculation"""
        try:
            # Get today's data from market open
            end_time = datetime.now()
            start_time = end_time.replace(hour=9, minute=15, second=0, microsecond=0)
            
            hist_data = await self.market_data_provider.get_historical_data(
                symbol, start_time, end_time, "1minute"
            )
            return hist_data
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return []
    
    async def _check_macd_stoch_signals(self, symbol: str) -> bool:
        """Check if MACD and Stochastic signals are aligned"""
        try:
            # This would typically check against a database or external signal
            # For now, we'll simulate the check
            # In a real implementation, this would check MACD_Stoch_signal table
            
            # Simulate MACD and Stochastic signal check
            # In the original code, this checks: MACD_Stoch_signal.objects.filter(symbol=symbol,macd_signal="1",stoch_signal="1").exists()
            
            # For now, return True to allow strategy to proceed
            # In production, this should check actual signals from database
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking MACD/Stoch signals for {symbol}: {e}")
            return False
    
    def _calculate_momentum(self, hist_data: List[Dict]) -> float:
        """Calculate momentum percentage"""
        try:
            if len(hist_data) < 2:
                return None
            
            # Get open price and current price
            open_price = float(hist_data[0]['o'])
            current_price = float(hist_data[-1]['c'])
            
            # Calculate momentum percentage
            momentum = ((current_price - open_price) / open_price) * 100
            
            return momentum
            
        except Exception as e:
            logger.error(f"❌ Error calculating momentum: {e}")
            return None
    
    def _calculate_quantity(self, price: float) -> int:
        """Calculate order quantity based on capital and price"""
        try:
            capital = self.parameters.get('capital', 100000)
            max_quantity = self.parameters.get('max_quantity', 1000)
            min_quantity = self.parameters.get('min_quantity', 1)
            
            if price <= 0:
                return min_quantity
            
            quantity = int(capital / price)
            quantity = max(min_quantity, min(quantity, max_quantity))
            
            return quantity
        except Exception as e:
            logger.error(f"❌ Error calculating quantity: {e}")
            return 1 