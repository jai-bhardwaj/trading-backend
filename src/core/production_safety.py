"""
Production Safety System
Prevents fallback to demo trading when live broker connection fails
"""

import logging
import time
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Trading mode enum"""
    LIVE = "LIVE"
    PAPER = "PAPER"
    DISABLED = "DISABLED"

class ProductionSafetyValidator:
    """Ensures production trading never falls back to demo mode"""
    
    def __init__(self):
        self.intended_mode = TradingMode.LIVE
        self.current_mode = TradingMode.DISABLED
        self.broker_connection_attempts = 0
        self.last_connection_attempt = None
        self.max_connection_attempts = 3
        self.connection_retry_delay = 300  # 5 minutes
        
    def set_intended_mode(self, mode: TradingMode):
        """Set the intended trading mode"""
        self.intended_mode = mode
        logger.info(f"🎯 Intended trading mode set to: {mode.value}")
    
    def validate_trading_mode_safety(self, attempted_mode: TradingMode, 
                                   broker_connected: bool) -> bool:
        """
        Validate that we never fall back to unsafe modes
        CRITICAL: Prevents accidental demo trading in production
        """
        
        # If intended mode is LIVE but broker not connected
        if self.intended_mode == TradingMode.LIVE:
            if not broker_connected:
                logger.critical("🚨 BROKER CONNECTION FAILED - STOPPING ALL TRADING")
                logger.critical("🚨 Will NOT fall back to paper trading in production")
                return False  # STOP - don't allow any trading
            
            if attempted_mode != TradingMode.LIVE:
                logger.critical(f"🚨 PRODUCTION SAFETY VIOLATION: Attempted {attempted_mode.value} when LIVE intended")
                return False
        
        return True
    
    def should_allow_trading(self, broker_connected: bool) -> bool:
        """Determine if trading should be allowed"""
        if not self.validate_trading_mode_safety(TradingMode.LIVE, broker_connected):
            return False
        
        # Additional safety checks
        if self.intended_mode == TradingMode.LIVE and not broker_connected:
            return False
        
        return True

# Global instance
_production_safety = None

def get_production_safety_validator() -> ProductionSafetyValidator:
    global _production_safety
    if _production_safety is None:
        _production_safety = ProductionSafetyValidator()
    return _production_safety
