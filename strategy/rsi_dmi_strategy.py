"""
RSI DMI Strategy - Based on RSI and DMI indicators
"""
import logging
from typing import Dict, List, Any
from datetime import datetime
from strategy.base import BaseStrategy
from strategy.market_data import MarketDataProvider, MarketData

logger = logging.getLogger(__name__)

class RSIDMIStrategy(BaseStrategy):
    """RSI DMI Strategy - Entry based on RSI and DMI indicators"""
    
    def __init__(self, config: Dict[str, Any], market_data_provider: MarketDataProvider):
        super().__init__(config, market_data_provider)
        self.upper_limit = self.parameters.get('upper_limit', 70)
        self.lower_limit = self.parameters.get('lower_limit', 30)
        self.di_upper_limit = self.parameters.get('di_upper_limit', 25)
        
    async def run(self, market_data: Dict[str, MarketData]) -> List[Dict]:
        """Run RSI DMI strategy"""
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                logger.warning(f"⚠️ No market data for {symbol}")
                continue
                
            try:
                # Get historical data for RSI and DMI calculation
                hist_data = await self._get_historical_data(symbol)
                if not hist_data or len(hist_data) < 14:
                    logger.warning(f"⚠️ Insufficient historical data for {symbol}")
                    continue
                
                # Calculate RSI and DMI
                rsi_data = self._calculate_rsi(hist_data)
                dmi_data = self._calculate_dmi(hist_data)
                
                if not rsi_data or not dmi_data:
                    continue
                
                # Get latest values
                current_rsi = rsi_data[-1]
                current_di_plus = dmi_data['+DI'][-1]
                current_di_minus = dmi_data['-DI'][-1]
                
                # Check entry conditions
                if (current_rsi > self.upper_limit and 
                    current_di_plus > self.di_upper_limit):
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'BUY',
                        'confidence': 0.8,
                        'price': market_data[symbol].ltp,
                        'quantity': self._calculate_quantity(market_data[symbol].ltp),
                        'timestamp': datetime.now(),
                        'metadata': {
                            'strategy': 'RSI DMI',
                            'rsi_value': current_rsi,
                            'di_plus': current_di_plus,
                            'di_minus': current_di_minus,
                            'upper_limit': self.upper_limit,
                            'di_upper_limit': self.di_upper_limit
                        }
                    }
                    signals.append(signal)
                    logger.info(f"📈 RSI DMI BUY signal for {symbol}: RSI={current_rsi:.2f}, +DI={current_di_plus:.2f}")
                
                # Check exit conditions
                elif current_rsi < self.lower_limit:
                    signal = {
                        'symbol': symbol,
                        'signal_type': 'SELL',
                        'confidence': 0.7,
                        'price': market_data[symbol].ltp,
                        'quantity': self._calculate_quantity(market_data[symbol].ltp),
                        'timestamp': datetime.now(),
                        'metadata': {
                            'strategy': 'RSI DMI',
                            'rsi_value': current_rsi,
                            'exit_reason': 'RSI Below Lower Limit'
                        }
                    }
                    signals.append(signal)
                    logger.info(f"📉 RSI DMI SELL signal for {symbol}: RSI={current_rsi:.2f}")
                    
            except Exception as e:
                logger.error(f"❌ Error in RSI DMI strategy for {symbol}: {e}")
                
        return signals
    
    async def _get_historical_data(self, symbol: str) -> List[Dict]:
        """Get historical data for calculations"""
        try:
            # Get last 50 candles for calculations
            end_time = datetime.now()
            start_time = end_time.replace(hour=9, minute=15, second=0, microsecond=0)
            
            hist_data = await self.market_data_provider.get_historical_data(
                symbol, "1minute", 1  # symbol, interval, days
            )
            return hist_data
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return []
    
    def _calculate_rsi(self, hist_data: List[Dict]) -> List[float]:
        """Calculate RSI values"""
        try:
            if len(hist_data) < 14:
                return []
            
            closes = [float(candle['c']) for candle in hist_data]
            gains = []
            losses = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(max(change, 0))
                losses.append(max(-change, 0))
            
            # Calculate average gains and losses
            avg_gain = sum(gains[:14]) / 14
            avg_loss = sum(losses[:14]) / 14
            
            rsi_values = []
            for i in range(14, len(closes)):
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
                
                # Update averages
                if i < len(gains):
                    avg_gain = (avg_gain * 13 + gains[i-1]) / 14
                    avg_loss = (avg_loss * 13 + losses[i-1]) / 14
            
            return rsi_values
        except Exception as e:
            logger.error(f"❌ Error calculating RSI: {e}")
            return []
    
    def _calculate_dmi(self, hist_data: List[Dict]) -> Dict[str, List[float]]:
        """Calculate DMI (Directional Movement Index) values"""
        try:
            if len(hist_data) < 14:
                return {}
            
            highs = [float(candle['h']) for candle in hist_data]
            lows = [float(candle['l']) for candle in hist_data]
            
            plus_dm = []
            minus_dm = []
            true_ranges = []
            
            for i in range(1, len(hist_data)):
                high_diff = highs[i] - highs[i-1]
                low_diff = lows[i-1] - lows[i]
                
                if high_diff > low_diff and high_diff > 0:
                    plus_dm.append(high_diff)
                else:
                    plus_dm.append(0)
                
                if low_diff > high_diff and low_diff > 0:
                    minus_dm.append(low_diff)
                else:
                    minus_dm.append(0)
                
                # True Range
                tr1 = highs[i] - lows[i]
                tr2 = abs(highs[i] - highs[i-1])
                tr3 = abs(lows[i] - lows[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            # Calculate smoothed averages
            period = 14
            avg_plus_dm = sum(plus_dm[:period]) / period
            avg_minus_dm = sum(minus_dm[:period]) / period
            avg_tr = sum(true_ranges[:period]) / period
            
            di_plus_values = []
            di_minus_values = []
            
            for i in range(period, len(hist_data)):
                if avg_tr == 0:
                    di_plus = 0
                    di_minus = 0
                else:
                    di_plus = (avg_plus_dm / avg_tr) * 100
                    di_minus = (avg_minus_dm / avg_tr) * 100
                
                di_plus_values.append(di_plus)
                di_minus_values.append(di_minus)
                
                # Update averages
                if i < len(plus_dm):
                    avg_plus_dm = (avg_plus_dm * 13 + plus_dm[i-1]) / 14
                    avg_minus_dm = (avg_minus_dm * 13 + minus_dm[i-1]) / 14
                    avg_tr = (avg_tr * 13 + true_ranges[i-1]) / 14
            
            return {
                '+DI': di_plus_values,
                '-DI': di_minus_values
            }
        except Exception as e:
            logger.error(f"❌ Error calculating DMI: {e}")
            return {}
    
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