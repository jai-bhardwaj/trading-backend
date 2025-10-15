"""
Technical Indicators for Strategy Service
"""
import logging
from typing import List, Dict, Tuple
from shared.models import MarketDataTick

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Collection of technical indicators for trading strategies"""
    
    @staticmethod
    def calculate_rsi(ticks: List[MarketDataTick], period: int = 14) -> List[float]:
        """Calculate RSI (Relative Strength Index)"""
        try:
            if len(ticks) < period + 1:
                return []
            
            closes = [tick.ltp for tick in ticks]
            gains = []
            losses = []
            
            # Calculate price changes
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(max(change, 0))
                losses.append(max(-change, 0))
            
            if len(gains) < period:
                return []
            
            # Calculate initial average gains and losses
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            rsi_values = []
            
            # Calculate RSI for remaining periods
            for i in range(period, len(gains)):
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
                
                # Update averages using Wilder's smoothing
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            return rsi_values
            
        except Exception as e:
            logger.error(f"❌ Error calculating RSI: {e}")
            return []
    
    @staticmethod
    def calculate_dmi(ticks: List[MarketDataTick], period: int = 14) -> Dict[str, List[float]]:
        """Calculate DMI (Directional Movement Index)"""
        try:
            if len(ticks) < period + 1:
                return {"+DI": [], "-DI": []}
            
            highs = [tick.high for tick in ticks]
            lows = [tick.low for tick in ticks]
            
            plus_dm = []
            minus_dm = []
            true_ranges = []
            
            # Calculate directional movement and true range
            for i in range(1, len(ticks)):
                high_diff = highs[i] - highs[i-1]
                low_diff = lows[i-1] - lows[i]
                
                # Plus DM
                if high_diff > low_diff and high_diff > 0:
                    plus_dm.append(high_diff)
                else:
                    plus_dm.append(0)
                
                # Minus DM
                if low_diff > high_diff and low_diff > 0:
                    minus_dm.append(low_diff)
                else:
                    minus_dm.append(0)
                
                # True Range
                tr1 = highs[i] - lows[i]
                tr2 = abs(highs[i] - highs[i-1])
                tr3 = abs(lows[i] - lows[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            if len(plus_dm) < period:
                return {"+DI": [], "-DI": []}
            
            # Calculate smoothed averages
            avg_plus_dm = sum(plus_dm[:period]) / period
            avg_minus_dm = sum(minus_dm[:period]) / period
            avg_tr = sum(true_ranges[:period]) / period
            
            di_plus_values = []
            di_minus_values = []
            
            # Calculate DI values
            for i in range(period, len(plus_dm)):
                if avg_tr == 0:
                    di_plus = 0
                    di_minus = 0
                else:
                    di_plus = (avg_plus_dm / avg_tr) * 100
                    di_minus = (avg_minus_dm / avg_tr) * 100
                
                di_plus_values.append(di_plus)
                di_minus_values.append(di_minus)
                
                # Update averages using Wilder's smoothing
                avg_plus_dm = (avg_plus_dm * (period - 1) + plus_dm[i]) / period
                avg_minus_dm = (avg_minus_dm * (period - 1) + minus_dm[i]) / period
                avg_tr = (avg_tr * (period - 1) + true_ranges[i]) / period
            
            return {
                "+DI": di_plus_values,
                "-DI": di_minus_values
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating DMI: {e}")
            return {"+DI": [], "-DI": []}
    
    @staticmethod
    def calculate_sma(ticks: List[MarketDataTick], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        try:
            if len(ticks) < period:
                return []
            
            closes = [tick.ltp for tick in ticks]
            sma_values = []
            
            for i in range(period - 1, len(closes)):
                sma = sum(closes[i - period + 1:i + 1]) / period
                sma_values.append(sma)
            
            return sma_values
            
        except Exception as e:
            logger.error(f"❌ Error calculating SMA: {e}")
            return []
    
    @staticmethod
    def calculate_ema(ticks: List[MarketDataTick], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        try:
            if len(ticks) < period:
                return []
            
            closes = [tick.ltp for tick in ticks]
            ema_values = []
            
            # Calculate smoothing factor
            multiplier = 2 / (period + 1)
            
            # First EMA is SMA
            first_sma = sum(closes[:period]) / period
            ema_values.append(first_sma)
            
            # Calculate subsequent EMAs
            for i in range(period, len(closes)):
                ema = (closes[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
                ema_values.append(ema)
            
            return ema_values
            
        except Exception as e:
            logger.error(f"❌ Error calculating EMA: {e}")
            return []
    
    @staticmethod
    def calculate_bollinger_bands(ticks: List[MarketDataTick], period: int = 20, std_dev: float = 2.0) -> Dict[str, List[float]]:
        """Calculate Bollinger Bands"""
        try:
            if len(ticks) < period:
                return {"upper": [], "middle": [], "lower": []}
            
            closes = [tick.ltp for tick in ticks]
            sma_values = TechnicalIndicators.calculate_sma(ticks, period)
            
            upper_band = []
            lower_band = []
            
            for i in range(period - 1, len(closes)):
                # Calculate standard deviation for this period
                period_closes = closes[i - period + 1:i + 1]
                mean = sum(period_closes) / len(period_closes)
                variance = sum((x - mean) ** 2 for x in period_closes) / len(period_closes)
                std = variance ** 0.5
                
                sma = sma_values[i - period + 1]
                upper_band.append(sma + (std_dev * std))
                lower_band.append(sma - (std_dev * std))
            
            return {
                "upper": upper_band,
                "middle": sma_values,
                "lower": lower_band
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating Bollinger Bands: {e}")
            return {"upper": [], "middle": [], "lower": []}
    
    @staticmethod
    def calculate_macd(ticks: List[MarketDataTick], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(ticks) < slow_period:
                return {"macd": [], "signal": [], "histogram": []}
            
            closes = [tick.ltp for tick in ticks]
            
            # Calculate EMAs
            fast_ema = TechnicalIndicators.calculate_ema(ticks, fast_period)
            slow_ema = TechnicalIndicators.calculate_ema(ticks, slow_period)
            
            # Calculate MACD line
            macd_line = []
            min_length = min(len(fast_ema), len(slow_ema))
            
            for i in range(min_length):
                macd_line.append(fast_ema[i] - slow_ema[i])
            
            # Calculate signal line (EMA of MACD)
            if len(macd_line) < signal_period:
                return {"macd": macd_line, "signal": [], "histogram": []}
            
            # Create temporary ticks for signal line calculation
            macd_ticks = []
            for i, macd_value in enumerate(macd_line):
                # Create a dummy tick with MACD value as price
                tick = MarketDataTick(
                    symbol="MACD",
                    token="",
                    ltp=macd_value,
                    change=0,
                    change_percent=0,
                    high=macd_value,
                    low=macd_value,
                    volume=0,
                    bid=macd_value,
                    ask=macd_value,
                    open=macd_value,
                    close=macd_value,
                    timestamp=ticks[i].timestamp,
                    exchange_timestamp=ticks[i].exchange_timestamp
                )
                macd_ticks.append(tick)
            
            signal_line = TechnicalIndicators.calculate_ema(macd_ticks, signal_period)
            
            # Calculate histogram
            histogram = []
            min_signal_length = min(len(macd_line), len(signal_line))
            
            for i in range(min_signal_length):
                histogram.append(macd_line[i] - signal_line[i])
            
            return {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating MACD: {e}")
            return {"macd": [], "signal": [], "histogram": []}
    
    @staticmethod
    def calculate_stochastic(ticks: List[MarketDataTick], k_period: int = 14, d_period: int = 3) -> Dict[str, List[float]]:
        """Calculate Stochastic Oscillator"""
        try:
            if len(ticks) < k_period:
                return {"%K": [], "%D": []}
            
            k_values = []
            
            for i in range(k_period - 1, len(ticks)):
                # Get high and low for the period
                period_highs = [ticks[j].high for j in range(i - k_period + 1, i + 1)]
                period_lows = [ticks[j].low for j in range(i - k_period + 1, i + 1)]
                
                highest_high = max(period_highs)
                lowest_low = min(period_lows)
                current_close = ticks[i].ltp
                
                if highest_high == lowest_low:
                    k_value = 50  # Neutral when no range
                else:
                    k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
                
                k_values.append(k_value)
            
            # Calculate %D (SMA of %K)
            d_values = []
            if len(k_values) >= d_period:
                for i in range(d_period - 1, len(k_values)):
                    d_value = sum(k_values[i - d_period + 1:i + 1]) / d_period
                    d_values.append(d_value)
            
            return {
                "%K": k_values,
                "%D": d_values
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating Stochastic: {e}")
            return {"%K": [], "%D": []}
