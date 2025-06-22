"""
Safe RSI Calculator with Division by Zero Protection
Fixes critical financial calculation vulnerabilities
"""

import math
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class SafeRSICalculator:
    """Thread-safe RSI calculator with comprehensive division by zero protection"""
    
    def __init__(self):
        self.zero_threshold = 1e-8
        self.max_rsi = 100.0
        self.min_rsi = 0.0
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI with comprehensive division by zero protection
        
        Args:
            prices: List of price values
            period: RSI calculation period
            
        Returns:
            RSI value between 0-100, or None if calculation not possible
        """
        try:
            # Validation
            if not prices or len(prices) < period + 1:
                logger.warning(f"Insufficient price data for RSI: {len(prices) if prices else 0} < {period + 1}")
                return None
            
            # Calculate price changes
            changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if not math.isnan(change) and not math.isinf(change):
                    changes.append(change)
            
            if len(changes) < period:
                logger.warning(f"Insufficient price changes for RSI: {len(changes)} < {period}")
                return None
            
            # Get recent changes
            recent_changes = changes[-period:]
            
            # Separate gains and losses
            gains = [change for change in recent_changes if change > self.zero_threshold]
            losses = [-change for change in recent_changes if change < -self.zero_threshold]
            
            # Calculate averages with division protection
            avg_gain = self._safe_mean(gains)
            avg_loss = self._safe_mean(losses)
            
            # Handle edge cases
            if avg_loss < self.zero_threshold:
                if avg_gain > self.zero_threshold:
                    # Only gains, no losses
                    logger.info("RSI: Only gains detected, returning 100")
                    return self.max_rsi
                else:
                    # No significant movement
                    logger.info("RSI: No significant price movement, returning 50")
                    return 50.0
            
            if avg_gain < self.zero_threshold:
                # Only losses, no gains
                logger.info("RSI: Only losses detected, returning 0")
                return self.min_rsi
            
            # Calculate RS with division protection
            rs = avg_gain / avg_loss
            
            # Protect against extreme values
            if rs > 1e6:
                logger.warning("RSI: Extremely high RS value, capping RSI at 100")
                return self.max_rsi
            
            # Calculate RSI
            rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Clamp to valid range
            rsi = max(self.min_rsi, min(self.max_rsi, rsi))
            
            return round(rsi, 2)
            
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return None
    
    def _safe_mean(self, values: List[float]) -> float:
        """Calculate mean with safety checks"""
        if not values:
            return 0.0
        
        try:
            valid_values = [v for v in values if not math.isnan(v) and not math.isinf(v)]
            if not valid_values:
                return 0.0
            
            return sum(valid_values) / len(valid_values)
        except:
            return 0.0

# Global instance
_global_rsi_calculator = None

def get_safe_rsi_calculator() -> SafeRSICalculator:
    """Get global safe RSI calculator instance"""
    global _global_rsi_calculator
    if _global_rsi_calculator is None:
        _global_rsi_calculator = SafeRSICalculator()
    return _global_rsi_calculator 