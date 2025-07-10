"""
FastAPI Dependencies
"""

from fastapi import HTTPException
from .services.trading_service import TradingService

# Global app state - will be set by main.py
_app_state = None

def set_app_state(app_state):
    """Set the global app state (called from main.py)"""
    global _app_state
    _app_state = app_state

async def get_trading_service() -> TradingService:
    """Dependency function to get trading service"""
    if _app_state is None or _app_state.trading_service is None:
        raise HTTPException(
            status_code=503, 
            detail="Trading service not initialized. Please wait for service startup."
        )
    return _app_state.trading_service 