"""
Positions API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict

router = APIRouter(prefix="/api/positions", tags=["positions"])

@router.get("/{user_id}", response_model=List[Dict])
async def get_user_positions(user_id: str):
    """Get positions for a user"""
    from ..main import trading_service
    try:
        positions = trading_service.get_user_positions(user_id)
        return positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user positions: {str(e)}")

@router.get("/{user_id}/{symbol}", response_model=Dict)
async def get_user_position(user_id: str, symbol: str):
    """Get specific position for a user and symbol"""
    from ..main import trading_service
    try:
        position = trading_service.get_user_position(user_id, symbol)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        return position
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user position: {str(e)}") 