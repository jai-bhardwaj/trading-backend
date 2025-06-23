"""
Financial Calculations Module with Division by Zero Protection
Safe implementation of financial indicators for trading strategies
"""

import math
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CalculationError(Exception):
    """Custom exception for financial calculation errors"""
    pass

class EdgeCaseHandling(Enum):
    """How to handle edge cases in calculations"""
    RETURN_NULL = "return_null"           # Return None for invalid cases
    USE_DEFAULT = "use_default"           # Use sensible defaults
    RAISE_ERROR = "raise_error"           # Raise exception
    LOG_WARNING = "log_warning"           # Log warning and continue

@dataclass
class CalculationConfig:
    """Configuration for financial calculations"""
    edge_case_handling: EdgeCaseHandling = EdgeCaseHandling.USE_DEFAULT
    min_periods: int = 2                   # Minimum data points required
    precision: int = 6                     # Decimal precision
    infinity_threshold: float = 1e6        # Values above this treated as infinity
    zero_threshold: float = 1e-8           # Values below this treated as zero
    
    # RSI specific config
    rsi_min_value: float = 0.0
    rsi_max_value: float = 100.0
    rsi_default_oversold: float = 30.0
    rsi_default_overbought: float = 70.0
    
    # Moving Average config
    ma_min_periods: int = 2
    
    # Bollinger Bands config
    bb_default_std: float = 2.0
    bb_min_periods: int = 20

class SafeFinancialCalculations:
    """Thread-safe financial calculations with comprehensive error handling"""
    
    def __init__(self, config: CalculationConfig = None):
        self.config = config or CalculationConfig()
        
        # Performance optimization: pre-compile common calculations
        self._calculation_cache = {}
        self._max_cache_size = 1000
        
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI with comprehensive division by zero protection
        
        Args:
            prices: List of price values
            period: RSI calculation period (default 14)
            
        Returns:
            RSI value between 0-100, or None if calculation not possible
        """
        try:
            # Input validation
            if not self._validate_price_data(prices, min_periods=period + 1):
                return self._handle_edge_case("RSI: Insufficient price data", None)
            
            # Calculate price changes
            price_changes = self._calculate_price_changes(prices)
            
            if len(price_changes) < period:
                return self._handle_edge_case("RSI: Insufficient price changes", None)
            
            # Get recent changes for RSI calculation
            recent_changes = price_changes[-period:]
            
            # Separate gains and losses
            gains = [change for change in recent_changes if change > self.config.zero_threshold]
            losses = [-change for change in recent_changes if change < -self.config.zero_threshold]
            
            # Calculate average gain and loss with division by zero protection
            avg_gain = self._safe_mean(gains)
            avg_loss = self._safe_mean(losses)
            
            # Handle edge cases
            if avg_loss < self.config.zero_threshold:
                # No losses - RSI approaches 100
                if avg_gain > self.config.zero_threshold:
                    return self._clamp_rsi(100.0)
                else:
                    # No gains or losses - neutral RSI
                    return self._handle_edge_case("RSI: No significant price movement", 50.0)
            
            if avg_gain < self.config.zero_threshold:
                # No gains - RSI approaches 0
                return self._clamp_rsi(0.0)
            
            # Calculate Relative Strength (RS) with division protection
            rs = self._safe_divide(avg_gain, avg_loss, "RSI RS calculation")
            
            if rs is None:
                return self._handle_edge_case("RSI: RS calculation failed", 50.0)
            
            # Calculate RSI with division protection
            if rs > self.config.infinity_threshold:
                return self._clamp_rsi(100.0)
            
            rsi = 100.0 - (100.0 / (1.0 + rs))
            
            return self._clamp_rsi(rsi)
            
        except Exception as e:
            logger.error(f"❌ RSI calculation error: {e}")
            return self._handle_edge_case(f"RSI calculation exception: {e}", None)
    
    def calculate_moving_average(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate moving average with validation
        
        Args:
            prices: List of price values
            period: MA calculation period
            
        Returns:
            Moving average value, or None if calculation not possible
        """
        try:
            if not self._validate_price_data(prices, min_periods=period):
                return self._handle_edge_case("MA: Insufficient price data", None)
            
            # Get recent prices
            recent_prices = prices[-period:]
            
            # Calculate MA with validation
            ma = self._safe_mean(recent_prices)
            
            if ma is None:
                return self._handle_edge_case("MA: Mean calculation failed", None)
            
            return self._round_financial_value(ma)
            
        except Exception as e:
            logger.error(f"❌ Moving Average calculation error: {e}")
            return self._handle_edge_case(f"MA calculation exception: {e}", None)
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, 
                                 std_dev: float = 2.0) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate Bollinger Bands with comprehensive validation
        
        Args:
            prices: List of price values
            period: Period for calculation
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band) or (None, None, None)
        """
        try:
            if not self._validate_price_data(prices, min_periods=period):
                return self._handle_edge_case("BB: Insufficient price data", (None, None, None))
            
            # Get recent prices
            recent_prices = prices[-period:]
            
            # Calculate middle band (SMA)
            middle_band = self._safe_mean(recent_prices)
            if middle_band is None:
                return self._handle_edge_case("BB: Middle band calculation failed", (None, None, None))
            
            # Calculate standard deviation with division protection
            std = self._safe_std(recent_prices)
            if std is None:
                return self._handle_edge_case("BB: Standard deviation calculation failed", (None, None, None))
            
            # Calculate bands
            band_width = std * std_dev
            upper_band = middle_band + band_width
            lower_band = middle_band - band_width
            
            # Ensure lower band is not negative for prices
            lower_band = max(0.0, lower_band)
            
            return (
                self._round_financial_value(upper_band),
                self._round_financial_value(middle_band),
                self._round_financial_value(lower_band)
            )
            
        except Exception as e:
            logger.error(f"❌ Bollinger Bands calculation error: {e}")
            return self._handle_edge_case(f"BB calculation exception: {e}", (None, None, None))
    
    def calculate_percentage_change(self, current_value: float, previous_value: float) -> Optional[float]:
        """
        Calculate percentage change with division by zero protection
        
        Args:
            current_value: Current value
            previous_value: Previous value
            
        Returns:
            Percentage change, or None if calculation not possible
        """
        try:
            if abs(previous_value) < self.config.zero_threshold:
                if abs(current_value) < self.config.zero_threshold:
                    return 0.0  # Both values are zero - no change
                else:
                    # Previous value is zero, current is not - infinite change
                    return self._handle_edge_case("Percentage change: Division by zero", None)
            
            pct_change = ((current_value - previous_value) / abs(previous_value)) * 100.0
            
            # Clamp extreme values
            if abs(pct_change) > self.config.infinity_threshold:
                sign = 1 if pct_change > 0 else -1
                return self._handle_edge_case("Percentage change: Extreme value", sign * 999.99)
            
            return self._round_financial_value(pct_change)
            
        except Exception as e:
            logger.error(f"❌ Percentage change calculation error: {e}")
            return self._handle_edge_case(f"Percentage change exception: {e}", None)
    
    def calculate_volatility(self, prices: List[float], period: int = 20) -> Optional[float]:
        """
        Calculate price volatility (standard deviation of returns)
        
        Args:
            prices: List of price values
            period: Period for calculation
            
        Returns:
            Volatility value, or None if calculation not possible
        """
        try:
            if not self._validate_price_data(prices, min_periods=period + 1):
                return self._handle_edge_case("Volatility: Insufficient price data", None)
            
            # Calculate returns
            returns = []
            for i in range(len(prices) - period, len(prices)):
                if i > 0 and abs(prices[i-1]) > self.config.zero_threshold:
                    ret = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(ret)
            
            if len(returns) < 2:
                return self._handle_edge_case("Volatility: Insufficient returns", None)
            
            # Calculate standard deviation of returns
            volatility = self._safe_std(returns)
            
            if volatility is None:
                return self._handle_edge_case("Volatility: Standard deviation calculation failed", None)
            
            # Annualize volatility (assuming 252 trading days)
            annualized_volatility = volatility * math.sqrt(252) * 100  # Convert to percentage
            
            return self._round_financial_value(annualized_volatility)
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation error: {e}")
            return self._handle_edge_case(f"Volatility calculation exception: {e}", None)
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.03) -> Optional[float]:
        """
        Calculate Sharpe ratio with proper risk handling
        
        Args:
            returns: List of return values
            risk_free_rate: Risk-free rate (default 3%)
            
        Returns:
            Sharpe ratio, or None if calculation not possible
        """
        try:
            if not returns or len(returns) < 2:
                return self._handle_edge_case("Sharpe: Insufficient returns data", None)
            
            # Calculate mean return
            mean_return = self._safe_mean(returns)
            if mean_return is None:
                return self._handle_edge_case("Sharpe: Mean return calculation failed", None)
            
            # Calculate standard deviation of returns
            std_return = self._safe_std(returns)
            if std_return is None or std_return < self.config.zero_threshold:
                return self._handle_edge_case("Sharpe: Standard deviation calculation failed or zero", None)
            
            # Calculate excess return
            excess_return = mean_return - risk_free_rate
            
            # Calculate Sharpe ratio with division protection
            sharpe = self._safe_divide(excess_return, std_return, "Sharpe ratio calculation")
            
            if sharpe is None:
                return self._handle_edge_case("Sharpe: Division failed", None)
            
            # Clamp extreme values
            if abs(sharpe) > self.config.infinity_threshold:
                sign = 1 if sharpe > 0 else -1
                return self._handle_edge_case("Sharpe: Extreme value", sign * 100.0)
            
            return self._round_financial_value(sharpe)
            
        except Exception as e:
            logger.error(f"❌ Sharpe ratio calculation error: {e}")
            return self._handle_edge_case(f"Sharpe calculation exception: {e}", None)
    
    def _validate_price_data(self, prices: List[float], min_periods: int = 2) -> bool:
        """Validate price data for calculations"""
        if not prices or len(prices) < min_periods:
            return False
        
        # Check for valid price values
        valid_prices = [p for p in prices if isinstance(p, (int, float)) and not math.isnan(p) and not math.isinf(p) and p >= 0]
        
        return len(valid_prices) >= min_periods and len(valid_prices) == len(prices)
    
    def _calculate_price_changes(self, prices: List[float]) -> List[float]:
        """Calculate price changes safely"""
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if not math.isnan(change) and not math.isinf(change):
                changes.append(change)
        return changes
    
    def _safe_mean(self, values: List[float]) -> Optional[float]:
        """Calculate mean with safety checks"""
        if not values:
            return None
        
        try:
            # Filter out invalid values
            valid_values = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)]
            
            if not valid_values:
                return None
            
            mean_val = sum(valid_values) / len(valid_values)
            
            if math.isnan(mean_val) or math.isinf(mean_val):
                return None
            
            return mean_val
            
        except (ZeroDivisionError, OverflowError):
            return None
    
    def _safe_std(self, values: List[float]) -> Optional[float]:
        """Calculate standard deviation with safety checks"""
        if not values or len(values) < 2:
            return None
        
        try:
            # Filter out invalid values
            valid_values = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)]
            
            if len(valid_values) < 2:
                return None
            
            mean_val = sum(valid_values) / len(valid_values)
            
            if math.isnan(mean_val) or math.isinf(mean_val):
                return None
            
            # Calculate variance
            variance = sum((v - mean_val) ** 2 for v in valid_values) / (len(valid_values) - 1)
            
            if variance < 0 or math.isnan(variance) or math.isinf(variance):
                return None
            
            std_val = math.sqrt(variance)
            
            if math.isnan(std_val) or math.isinf(std_val):
                return None
            
            return std_val
            
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
    
    def _safe_divide(self, numerator: float, denominator: float, operation: str) -> Optional[float]:
        """Perform safe division with comprehensive error handling"""
        try:
            # Check for zero denominator
            if abs(denominator) < self.config.zero_threshold:
                logger.warning(f"Division by zero avoided in {operation}: {numerator} / {denominator}")
                return None
            
            # Check for valid inputs
            if math.isnan(numerator) or math.isinf(numerator) or math.isnan(denominator) or math.isinf(denominator):
                logger.warning(f"Invalid inputs in {operation}: {numerator} / {denominator}")
                return None
            
            result = numerator / denominator
            
            # Check for invalid result
            if math.isnan(result) or math.isinf(result):
                logger.warning(f"Invalid result in {operation}: {numerator} / {denominator} = {result}")
                return None
            
            return result
            
        except (ZeroDivisionError, OverflowError):
            logger.warning(f"Exception in {operation}: {numerator} / {denominator}")
            return None
    
    def _clamp_rsi(self, rsi_value: float) -> float:
        """Clamp RSI value to valid range [0, 100]"""
        return max(self.config.rsi_min_value, min(self.config.rsi_max_value, rsi_value))
    
    def _round_financial_value(self, value: float) -> float:
        """Round financial values to appropriate precision"""
        try:
            # Use Decimal for precise rounding
            decimal_value = Decimal(str(value))
            rounded_value = decimal_value.quantize(
                Decimal('0.' + '0' * self.config.precision),
                rounding=ROUND_HALF_UP
            )
            return float(rounded_value)
        except (InvalidOperation, ValueError):
            return round(value, self.config.precision)
    
    def _handle_edge_case(self, message: str, default_value: Any) -> Any:
        """Handle edge cases based on configuration"""
        if self.config.edge_case_handling == EdgeCaseHandling.RAISE_ERROR:
            raise CalculationError(message)
        elif self.config.edge_case_handling == EdgeCaseHandling.LOG_WARNING:
            logger.warning(f"Financial calculation edge case: {message}")
            return default_value
        elif self.config.edge_case_handling == EdgeCaseHandling.USE_DEFAULT:
            return default_value
        else:  # RETURN_NULL
            return None

class FinancialIndicators:
    """High-level financial indicators using safe calculations"""
    
    def __init__(self, config: CalculationConfig = None):
        self.calculator = SafeFinancialCalculations(config)
    
    def get_rsi_signal(self, prices: List[float], period: int = 14, 
                      oversold: float = 30.0, overbought: float = 70.0) -> Dict[str, Any]:
        """
        Get RSI-based trading signal
        
        Returns:
            Dictionary with RSI value and signal information
        """
        rsi = self.calculator.calculate_rsi(prices, period)
        
        if rsi is None:
            return {
                'rsi': None,
                'signal': 'NEUTRAL',
                'strength': 'UNKNOWN',
                'reason': 'RSI calculation failed'
            }
        
        # Determine signal
        if rsi <= oversold:
            signal = 'BUY'
            strength = 'STRONG' if rsi <= oversold * 0.8 else 'MODERATE'
            reason = f'RSI oversold at {rsi:.1f}'
        elif rsi >= overbought:
            signal = 'SELL'
            strength = 'STRONG' if rsi >= overbought * 1.2 else 'MODERATE'
            reason = f'RSI overbought at {rsi:.1f}'
        else:
            signal = 'NEUTRAL'
            strength = 'WEAK'
            reason = f'RSI neutral at {rsi:.1f}'
        
        return {
            'rsi': rsi,
            'signal': signal,
            'strength': strength,
            'reason': reason,
            'oversold_level': oversold,
            'overbought_level': overbought
        }
    
    def get_bollinger_signal(self, prices: List[float], period: int = 20, 
                           std_dev: float = 2.0) -> Dict[str, Any]:
        """
        Get Bollinger Bands-based trading signal
        
        Returns:
            Dictionary with Bollinger Bands values and signal information
        """
        upper, middle, lower = self.calculator.calculate_bollinger_bands(prices, period, std_dev)
        
        if upper is None or middle is None or lower is None:
            return {
                'upper_band': None,
                'middle_band': None,
                'lower_band': None,
                'signal': 'NEUTRAL',
                'strength': 'UNKNOWN',
                'reason': 'Bollinger Bands calculation failed'
            }
        
        current_price = prices[-1] if prices else 0
        
        # Determine signal
        if current_price <= lower:
            signal = 'BUY'
            strength = 'STRONG'
            reason = f'Price at lower band: {current_price:.2f} <= {lower:.2f}'
        elif current_price >= upper:
            signal = 'SELL'
            strength = 'STRONG'
            reason = f'Price at upper band: {current_price:.2f} >= {upper:.2f}'
        else:
            signal = 'NEUTRAL'
            strength = 'WEAK'
            reason = f'Price within bands: {lower:.2f} < {current_price:.2f} < {upper:.2f}'
        
        return {
            'upper_band': upper,
            'middle_band': middle,
            'lower_band': lower,
            'current_price': current_price,
            'signal': signal,
            'strength': strength,
            'reason': reason
        }

# Global calculator instance
_global_calculator = None

def get_financial_calculator(config: CalculationConfig = None) -> SafeFinancialCalculations:
    """Get global financial calculator instance"""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = SafeFinancialCalculations(config)
    return _global_calculator

def get_financial_indicators(config: CalculationConfig = None) -> FinancialIndicators:
    """Get financial indicators instance"""
    return FinancialIndicators(config) 