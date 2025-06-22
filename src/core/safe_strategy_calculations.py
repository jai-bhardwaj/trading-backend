"""
Safe Strategy Calculations Module
Integrates safe financial calculations into all trading strategies
"""

import logging
from typing import List, Optional, Dict, Any
from .safe_rsi_calculator import get_safe_rsi_calculator
from .financial_calculations import SafeFinancialCalculator, CalculationConfig

logger = logging.getLogger(__name__)

class SafeStrategyCalculator:
    """
    Safe calculation provider for all trading strategies
    Prevents division by zero and calculation errors
    """
    
    def __init__(self):
        self.rsi_calculator = get_safe_rsi_calculator()
        self.financial_calculator = SafeFinancialCalculator()
        self.calculation_errors_prevented = 0
        
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Safe RSI calculation with error handling"""
        try:
            result = self.rsi_calculator.calculate_rsi(prices, period)
            if result is None:
                self.calculation_errors_prevented += 1
                logger.warning(f"RSI calculation returned None - error prevented")
            return result
        except Exception as e:
            self.calculation_errors_prevented += 1
            logger.error(f"RSI calculation error prevented: {e}")
            return None
    
    def calculate_moving_average(self, prices: List[float], period: int) -> Optional[float]:
        """Safe moving average calculation"""
        try:
            result = self.financial_calculator.calculate_moving_average(prices, period)
            if result is None:
                self.calculation_errors_prevented += 1
            return result
        except Exception as e:
            self.calculation_errors_prevented += 1
            logger.error(f"MA calculation error prevented: {e}")
            return None
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, 
                                std_dev: float = 2.0) -> tuple:
        """Safe Bollinger Bands calculation"""
        try:
            result = self.financial_calculator.calculate_bollinger_bands(prices, period, std_dev)
            if result == (None, None, None):
                self.calculation_errors_prevented += 1
            return result
        except Exception as e:
            self.calculation_errors_prevented += 1
            logger.error(f"Bollinger Bands calculation error prevented: {e}")
            return (None, None, None)
    
    def calculate_percentage_change(self, current: float, previous: float) -> Optional[float]:
        """Safe percentage change calculation"""
        try:
            result = self.financial_calculator.calculate_percentage_change(current, previous)
            if result is None:
                self.calculation_errors_prevented += 1
            return result
        except Exception as e:
            self.calculation_errors_prevented += 1
            logger.error(f"Percentage change calculation error prevented: {e}")
            return None
    
    def get_rsi_signal(self, prices: List[float], period: int = 14,
                      oversold: float = 30.0, overbought: float = 70.0) -> Dict[str, Any]:
        """Get safe RSI trading signal"""
        try:
            from .financial_calculations import FinancialIndicators
            indicators = FinancialIndicators()
            return indicators.get_rsi_signal(prices, period, oversold, overbought)
        except Exception as e:
            self.calculation_errors_prevented += 1
            logger.error(f"RSI signal calculation error prevented: {e}")
            return {
                'rsi': None,
                'signal': 'NEUTRAL',
                'strength': 'UNKNOWN',
                'reason': 'Calculation error prevented'
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get calculation error prevention statistics"""
        return {
            'calculation_errors_prevented': self.calculation_errors_prevented,
            'rsi_calculator_stats': 'Available',
            'financial_calculator_stats': 'Available'
        }

# Global instance
_safe_strategy_calculator = None

def get_safe_strategy_calculator() -> SafeStrategyCalculator:
    """Get global safe strategy calculator"""
    global _safe_strategy_calculator
    if _safe_strategy_calculator is None:
        _safe_strategy_calculator = SafeStrategyCalculator()
    return _safe_strategy_calculator
