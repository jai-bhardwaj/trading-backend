"""
Timezone Utilities for Indian Standard Time (IST)
Provides IST-aware datetime functions to replace UTC usage throughout the system.
"""

import pytz
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

# Indian Standard Time timezone
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

class ISTDateTime:
    """IST-aware datetime utilities for the trading system"""
    
    @staticmethod
    def now() -> datetime:
        """Get current datetime in IST"""
        return datetime.now(IST)
    
    @staticmethod
    def utcnow() -> datetime:
        """
        Replacement for datetime.utcnow() - returns IST time instead.
        This maintains compatibility with existing code while using IST.
        """
        return datetime.now(IST)
    
    @staticmethod
    def today() -> datetime:
        """Get today's date at midnight in IST"""
        return datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def from_timestamp(timestamp: float) -> datetime:
        """Convert timestamp to IST datetime"""
        return datetime.fromtimestamp(timestamp, IST)
    
    @staticmethod
    def to_utc(ist_datetime: datetime) -> datetime:
        """Convert IST datetime to UTC (for external APIs if needed)"""
        if ist_datetime.tzinfo is None:
            # Assume it's IST if no timezone info
            ist_datetime = IST.localize(ist_datetime)
        return ist_datetime.astimezone(UTC)
    
    @staticmethod
    def from_utc(utc_datetime: datetime) -> datetime:
        """Convert UTC datetime to IST"""
        if utc_datetime.tzinfo is None:
            utc_datetime = UTC.localize(utc_datetime)
        return utc_datetime.astimezone(IST)
    
    @staticmethod
    def market_open_time(date: Optional[datetime] = None) -> datetime:
        """Get market opening time (9:15 AM IST) for given date"""
        if date is None:
            date = ISTDateTime.today()
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return date.replace(hour=9, minute=15)
    
    @staticmethod
    def market_close_time(date: Optional[datetime] = None) -> datetime:
        """Get market closing time (3:30 PM IST) for given date"""
        if date is None:
            date = ISTDateTime.today()
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return date.replace(hour=15, minute=30)
    
    @staticmethod
    def is_market_hours(dt: Optional[datetime] = None) -> bool:
        """Check if given datetime (or current time) is during market hours"""
        if dt is None:
            dt = ISTDateTime.now()
        
        # Convert to IST if needed
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        elif dt.tzinfo != IST:
            dt = dt.astimezone(IST)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if dt.weekday() >= 5:  # Saturday or Sunday
            return False
        
        market_open = ISTDateTime.market_open_time(dt)
        market_close = ISTDateTime.market_close_time(dt)
        
        return market_open <= dt <= market_close
    
    @staticmethod
    def format_ist(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S IST") -> str:
        """Format datetime in IST with IST suffix"""
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        elif dt.tzinfo != IST:
            dt = dt.astimezone(IST)
        return dt.strftime(format_str)

# Compatibility aliases for easy migration
ist_now = ISTDateTime.now
ist_utcnow = ISTDateTime.utcnow  # This is the key replacement for datetime.utcnow()
ist_today = ISTDateTime.today

# For database timezone setting
IST_TIMEZONE_STR = "Asia/Kolkata"

def get_ist_timezone():
    """Get IST timezone object"""
    return IST

def get_current_ist_time():
    """Get current time in IST - alias for ISTDateTime.now()"""
    return ISTDateTime.now()

# Create timezone-aware datetime for database defaults
def default_ist_timestamp():
    """Default timestamp function for database fields"""
    return ISTDateTime.now()

# Market-specific utilities
class MarketTime:
    """Market timing utilities in IST"""
    
    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 15
    MARKET_CLOSE_HOUR = 15
    MARKET_CLOSE_MINUTE = 30
    
    @staticmethod
    def next_market_open(from_time: Optional[datetime] = None) -> datetime:
        """Get next market opening time"""
        if from_time is None:
            from_time = ISTDateTime.now()
        
        # Convert to IST
        if from_time.tzinfo is None:
            from_time = IST.localize(from_time)
        elif from_time.tzinfo != IST:
            from_time = from_time.astimezone(IST)
        
        # If it's already past market close or weekend, go to next weekday
        market_close = ISTDateTime.market_close_time(from_time)
        
        if from_time > market_close or from_time.weekday() >= 5:
            # Move to next weekday
            days_ahead = 1
            while (from_time + timedelta(days=days_ahead)).weekday() >= 5:
                days_ahead += 1
            next_day = from_time + timedelta(days=days_ahead)
            return ISTDateTime.market_open_time(next_day)
        
        # If before market open today, return today's market open
        market_open = ISTDateTime.market_open_time(from_time)
        if from_time < market_open:
            return market_open
        
        # Otherwise, return next day's market open
        next_day = from_time + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return ISTDateTime.market_open_time(next_day)
    
    @staticmethod
    def time_to_market_open(from_time: Optional[datetime] = None) -> timedelta:
        """Get time remaining until next market open"""
        if from_time is None:
            from_time = ISTDateTime.now()
        
        next_open = MarketTime.next_market_open(from_time)
        return next_open - from_time

# Trading session utilities
def is_trading_session(dt: Optional[datetime] = None) -> bool:
    """Check if it's currently a trading session"""
    return ISTDateTime.is_market_hours(dt)

def get_trading_day(dt: Optional[datetime] = None) -> datetime:
    """Get the trading day for a given datetime"""
    if dt is None:
        dt = ISTDateTime.now()
    
    # Convert to IST
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    elif dt.tzinfo != IST:
        dt = dt.astimezone(IST)
    
    # If before 9:15 AM, consider it part of previous trading day
    if dt.hour < 9 or (dt.hour == 9 and dt.minute < 15):
        dt = dt - timedelta(days=1)
    
    # Find the most recent weekday
    while dt.weekday() >= 5:
        dt = dt - timedelta(days=1)
    
    return dt.replace(hour=0, minute=0, second=0, microsecond=0) 