"""
Centralized Timezone Configuration for Trading Backend
All services use IST (Indian Standard Time)
"""
import os
from datetime import datetime
import pytz

# IST Timezone
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

def get_ist_timestamp():
    """Get current timestamp in IST as ISO format"""
    return get_ist_now().isoformat()

def convert_to_ist(dt):
    """Convert datetime to IST"""
    if dt.tzinfo is None:
        # If naive datetime, assume UTC
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(IST)

def format_ist_time(dt=None):
    """Format datetime in IST for logging"""
    if dt is None:
        dt = get_ist_now()
    elif dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
        dt = dt.astimezone(IST)
    return dt.strftime('%Y-%m-%d %H:%M:%S IST')

# Set default timezone for the application
os.environ['TZ'] = 'Asia/Kolkata'

# Export commonly used functions
__all__ = [
    'IST',
    'get_ist_now',
    'get_ist_timestamp', 
    'convert_to_ist',
    'format_ist_time'
]
