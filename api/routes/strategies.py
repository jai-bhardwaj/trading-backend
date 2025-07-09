"""
Strategies API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
from ..models import Strategy

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("/", response_model=List[Strategy])
async def get_strategies():
    """Get all available strategies"""
    from ..main import trading_service
    try:
        strategies = trading_service.get_strategies()
        return strategies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategies: {str(e)}") 