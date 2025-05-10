# app/brokers/base.py
# Re-exporting the interface for potentially cleaner imports elsewhere
# Or this file could contain shared broker utility functions in a larger app.
from app.core.interfaces import BrokerInterface, Order, Position, Balance

# No code needed here unless you add shared utilities