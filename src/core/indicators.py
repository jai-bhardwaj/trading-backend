"""
Safe Financial Indicators

This module provides safe implementations of technical indicators that prevent
division by zero errors and handle edge cases gracefully.
"""

import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SafeIndicators:
    """Safe technical indicator calculations"""
    
    @staticmethod
    def safe_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI safely, preventing division by zero
        
        Args:
            prices: List of price values
            period: RSI period (default 14)
            
        Returns:
            RSI value or None if cannot be calculated
        """
        try:
            if not prices or len(prices) < period + 1:
                logger.warning(f"Insufficient data for RSI calculation. Need {period + 1} prices, got {len(prices)}")
                return None
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                price_changes.append(change)
            
            if len(price_changes) < period:
                logger.warning(f"Insufficient price changes for RSI. Need {period}, got {len(price_changes)}")
                return None
            
            # Separate gains and losses
            gains = [max(change, 0) for change in price_changes]
            losses = [abs(min(change, 0)) for change in price_changes]
            
            # Calculate initial averages
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            # Handle edge case where avg_loss is zero
            if avg_loss == 0:
                if avg_gain == 0:
                    logger.warning("Both average gain and loss are zero, RSI undefined")
                    return None
                else:
                    # When there are no losses, RSI = 100
                    return 100.0
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Validate result
            if not (0 <= rsi <= 100):
                logger.error(f"RSI calculation resulted in invalid value: {rsi}")
                return None
            
            return round(rsi, 2)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    @staticmethod
    def safe_moving_average(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate simple moving average safely
        
        Args:
            prices: List of price values
            period: Moving average period
            
        Returns:
            Moving average or None if cannot be calculated
        """
        try:
            if not prices or len(prices) < period:
                return None
            
            if period <= 0:
                logger.error(f"Invalid period for moving average: {period}")
                return None
            
            recent_prices = prices[-period:]
            
            # Check for valid prices
            valid_prices = [p for p in recent_prices if p is not None and p > 0]
            if len(valid_prices) < period:
                logger.warning(f"Insufficient valid prices for MA. Need {period}, got {len(valid_prices)}")
                return None
            
            return sum(valid_prices) / len(valid_prices)
            
        except Exception as e:
            logger.error(f"Error calculating moving average: {e}")
            return None
    
    @staticmethod
    def safe_bollinger_bands(prices: List[float], period: int = 20, 
                           std_dev: float = 2.0) -> Optional[Tuple[float, float, float]]:
        """
        Calculate Bollinger Bands safely
        
        Args:
            prices: List of price values
            period: Period for calculation
            std_dev: Standard deviation multiplier
            
        Returns:
            (upper_band, middle_band, lower_band) or None if cannot be calculated
        """
        try:
            if not prices or len(prices) < period:
                return None
            
            # Calculate moving average
            ma = SafeIndicators.safe_moving_average(prices, period)
            if ma is None:
                return None
            
            # Calculate standard deviation
            recent_prices = prices[-period:]
            variance = sum((p - ma) ** 2 for p in recent_prices) / period
            
            if variance < 0:
                logger.error(f"Negative variance in Bollinger Bands calculation: {variance}")
                return None
            
            std = variance ** 0.5
            
            upper_band = ma + (std_dev * std)
            lower_band = ma - (std_dev * std)
            
            return (upper_band, ma, lower_band)
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return None
    
    @staticmethod
    def safe_percentage_change(old_value: float, new_value: float) -> Optional[float]:
        """
        Calculate percentage change safely
        
        Args:
            old_value: Previous value
            new_value: Current value
            
        Returns:
            Percentage change or None if cannot be calculated
        """
        try:
            if old_value == 0:
                if new_value == 0:
                    return 0.0  # No change
                else:
                    logger.warning("Cannot calculate percentage change from zero base")
                    return None
            
            change = ((new_value - old_value) / abs(old_value)) * 100
            return round(change, 2)
            
        except Exception as e:
            logger.error(f"Error calculating percentage change: {e}")
            return None 