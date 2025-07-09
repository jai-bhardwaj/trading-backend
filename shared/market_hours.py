"""
Market Hours Utility - Check if Indian markets are open
"""
from datetime import datetime, time
import pytz
import logging
import os

logger = logging.getLogger(__name__)

class MarketHours:
    """Utility to check Indian market hours"""
    
    def __init__(self):
        self.ist_tz = pytz.timezone('Asia/Kolkata')
        self.market_start = time(9, 15)  # 9:15 AM
        self.market_end = time(15, 30)   # 3:30 PM
        
    def is_market_open(self) -> bool:
        """Check if Indian markets are currently open"""
        # TEST OVERRIDE: Always open if env var is set
        if os.getenv("MARKET_HOURS_ALWAYS_OPEN", "false").lower() == "true":
            logger.info("[TEST] MARKET_HOURS_ALWAYS_OPEN is set: Forcing market open for testing.")
            return True
        
        # TEST MODE: Allow testing during market hours without override
        if os.getenv("MARKET_HOURS_TEST_MODE", "false").lower() == "true":
            logger.info("[TEST] MARKET_HOURS_TEST_MODE is set: Allowing testing during market hours.")
            return True
            
        try:
            # Get current time in IST
            now = datetime.now(self.ist_tz)
            current_time = now.time()
            current_day = now.weekday()  # Monday = 0, Sunday = 6
            
            # Check if it's a weekday (Monday = 0 to Friday = 4)
            if current_day >= 5:  # Saturday or Sunday
                logger.debug(f"Market closed - Weekend (day {current_day})")
                return False
            
            # Check if current time is within market hours
            if self.market_start <= current_time <= self.market_end:
                logger.debug(f"Market open - {current_time.strftime('%H:%M:%S')} IST")
                return True
            else:
                logger.debug(f"Market closed - {current_time.strftime('%H:%M:%S')} IST (hours: {self.market_start.strftime('%H:%M')} - {self.market_end.strftime('%H:%M')})")
                return False
                
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            # Default to closed if there's an error
            return False
    
    def get_market_status(self) -> dict:
        """Get detailed market status"""
        # TEST OVERRIDE: Always open if env var is set
        if os.getenv("MARKET_HOURS_ALWAYS_OPEN", "false").lower() == "true":
            logger.info("[TEST] MARKET_HOURS_ALWAYS_OPEN is set: Forcing market open for testing.")
            return {
                "is_open": True,
                "current_time": datetime.now(self.ist_tz).strftime('%H:%M:%S'),
                "current_day": datetime.now(self.ist_tz).strftime('%A'),
                "market_hours": f"{self.market_start.strftime('%H:%M')} - {self.market_end.strftime('%H:%M')} IST",
                "next_event": "Market closes in",
                "next_event_time": None
            }
        try:
            now = datetime.now(self.ist_tz)
            current_time = now.time()
            current_day = now.weekday()
            
            is_open = self.is_market_open()
            
            # Calculate time until market opens/closes
            if is_open:
                # Create timezone-aware datetime for market end
                market_end_dt = datetime.combine(now.date(), self.market_end, tzinfo=self.ist_tz)
                time_until_close = market_end_dt - now
                next_event = "Market closes in"
                next_event_time = time_until_close
            else:
                if current_day >= 5:  # Weekend
                    next_event = "Market opens Monday"
                    next_event_time = None
                elif current_time < self.market_start:  # Before market opens
                    # Create timezone-aware datetime for market start
                    market_start_dt = datetime.combine(now.date(), self.market_start, tzinfo=self.ist_tz)
                    time_until_open = market_start_dt - now
                    next_event = "Market opens in"
                    next_event_time = time_until_open
                else:  # After market closes
                    next_event = "Market opens tomorrow"
                    next_event_time = None
            
            return {
                "is_open": is_open,
                "current_time": current_time.strftime('%H:%M:%S'),
                "current_day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][current_day],
                "market_hours": f"{self.market_start.strftime('%H:%M')} - {self.market_end.strftime('%H:%M')} IST",
                "next_event": next_event,
                "next_event_time": str(next_event_time) if next_event_time else None
            }
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {"is_open": False, "error": str(e)}

# Global instance
market_hours = MarketHours() 