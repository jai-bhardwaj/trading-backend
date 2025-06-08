"""
Simple models for the pure Redis service
"""

from enum import Enum

class BrokerName(Enum):
    ANGEL_ONE = "ANGEL_ONE"
    
class TimeFrame(Enum):
    SECOND_1 = "1s"
    MINUTE_1 = "1m" 