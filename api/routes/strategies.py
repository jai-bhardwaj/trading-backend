"""
Strategies API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models import Strategy
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("/", response_model=List[Strategy])
async def get_strategies(trading_service: TradingService = Depends(get_trading_service)):
    """Get all available strategies"""
    try:
        strategies = trading_service.get_strategies()
        return strategies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategies: {str(e)}")

@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get a specific strategy by ID"""
    try:
        strategies = trading_service.get_strategies()
        for strategy in strategies:
            if strategy["id"] == strategy_id:
                return strategy
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategy: {str(e)}") 