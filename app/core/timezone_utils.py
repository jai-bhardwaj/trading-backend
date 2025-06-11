"""
Timezone utilities for the trading system.
All times should use IST (Indian Standard Time) consistently.
"""

from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from typing import Optional, Union

# Indian Standard Time
IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """Get current datetime in IST timezone."""
    return datetime.now(IST)


def utc_to_ist(dt: datetime) -> datetime:
    """Convert UTC datetime to IST."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(IST)


def ist_to_utc(dt: datetime) -> datetime:
    """Convert IST datetime to UTC."""
    if dt.tzinfo is None:
        # Assume IST if no timezone info
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(ZoneInfo("UTC"))


def parse_datetime_ist(dt_string: str) -> datetime:
    """Parse datetime string and ensure it's in IST."""
    dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    return dt


def format_datetime_ist(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format datetime in IST timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    return dt.strftime(fmt)


def today_ist() -> date:
    """Get today's date in IST."""
    return now_ist().date()


def market_time_ist(hour: int = 9, minute: int = 15) -> datetime:
    """Get market time for today in IST (default: 9:15 AM)."""
    today = today_ist()
    return datetime.combine(today, time(hour, minute), tzinfo=IST)


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """Check if the given time (or current time) is during market hours in IST."""
    if dt is None:
        dt = now_ist()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_start = time(9, 15)
    market_end = time(15, 30)
    
    current_time = dt.time()
    weekday = dt.weekday()
    
    # Monday = 0, Sunday = 6
    # Market is open Monday to Friday
    return (0 <= weekday <= 4) and (market_start <= current_time <= market_end)


def trading_day_start_ist(dt: Optional[datetime] = None) -> datetime:
    """Get the start of the trading day (9:15 AM IST) for the given date."""
    if dt is None:
        dt = now_ist()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    
    return datetime.combine(dt.date(), time(9, 15), tzinfo=IST)


def trading_day_end_ist(dt: Optional[datetime] = None) -> datetime:
    """Get the end of the trading day (3:30 PM IST) for the given date."""
    if dt is None:
        dt = now_ist()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    
    return datetime.combine(dt.date(), time(15, 30), tzinfo=IST)


def log_timestamp_ist() -> str:
    """Get formatted timestamp for logging in IST."""
    return format_datetime_ist(now_ist(), "%Y-%m-%d %H:%M:%S IST") 