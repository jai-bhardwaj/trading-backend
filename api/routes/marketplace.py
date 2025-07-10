"""
Marketplace API Routes - For frontend compatibility
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

@router.get("/", response_model=List[Dict])
async def get_marketplace(trading_service: TradingService = Depends(get_trading_service)):
    """Get all available strategies from marketplace (same as strategies for now)"""
    try:
        strategies = trading_service.get_strategies()
        # Convert to marketplace format expected by frontend
        marketplace_strategies = []
        for strategy in strategies:
            marketplace_strategies.append({
                "strategy_id": strategy["id"],
                "name": strategy["name"],
                "description": strategy.get("description", ""),
                "category": strategy["strategy_type"],
                "risk_level": "medium",  # Default value
                "min_capital": 10000,  # Default value
                "expected_return_annual": 15.0,  # Default value
                "max_drawdown": 10.0,  # Default value
                "symbols": strategy["symbols"],
                "parameters": strategy["parameters"],
                "is_active": strategy["enabled"]
            })
        return marketplace_strategies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get marketplace: {str(e)}") 