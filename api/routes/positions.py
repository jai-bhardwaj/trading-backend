"""
Positions API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/positions", tags=["positions"])

@router.get("/{user_id}", response_model=List[Dict])
async def get_user_positions(user_id: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get positions for a user"""
    try:
        positions = trading_service.get_user_positions(user_id)
        return positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user positions: {str(e)}")

@router.get("/{user_id}/{symbol}", response_model=Dict)
async def get_user_position(user_id: str, symbol: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get specific position for a user and symbol"""
    try:
        position = trading_service.get_user_position(user_id, symbol)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        return position
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user position: {str(e)}") 