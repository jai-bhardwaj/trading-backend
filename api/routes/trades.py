"""
Trades API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict

router = APIRouter(prefix="/api/trades", tags=["trades"])

@router.get("/{user_id}", response_model=List[Dict])
async def get_user_trades(user_id: str):
    """Get trades for a user"""
    from ..main import trading_service
    try:
        trades = trading_service.get_user_trades(user_id)
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user trades: {str(e)}")

@router.get("/{user_id}/symbol/{symbol}", response_model=List[Dict])
async def get_user_trades_by_symbol(user_id: str, symbol: str):
    """Get trades for a user and specific symbol"""
    from ..main import trading_service
    try:
        trades = trading_service.get_user_trades_by_symbol(user_id, symbol)
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user trades by symbol: {str(e)}") 