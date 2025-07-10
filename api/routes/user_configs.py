"""
User Strategy Configs API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models import UserStrategyConfig, UpdateUserStrategyConfigRequest
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/user-configs", tags=["user-configs"])

@router.get("/{user_id}", response_model=List[UserStrategyConfig])
async def get_user_strategy_configs(user_id: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get strategy configs for a user"""
    try:
        configs = trading_service.get_user_strategy_configs(user_id)
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user strategy configs: {str(e)}")

@router.get("/{user_id}/{strategy_id}", response_model=UserStrategyConfig)
async def get_user_strategy_config(user_id: str, strategy_id: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get specific strategy config for a user"""
    try:
        config = trading_service.get_user_strategy_config(user_id, strategy_id)
        if not config:
            raise HTTPException(status_code=404, detail="Strategy config not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user strategy config: {str(e)}")

@router.put("/{user_id}/{strategy_id}", response_model=UserStrategyConfig)
async def update_user_strategy_config(
    user_id: str,
    strategy_id: str,
    request: UpdateUserStrategyConfigRequest,
    trading_service: TradingService = Depends(get_trading_service)
):
    """Update user strategy config"""
    try:
        updates = {}
        if request.enabled is not None:
            updates["enabled"] = request.enabled
        if request.risk_limits is not None:
            updates["risk_limits"] = request.risk_limits
        if request.order_preferences is not None:
            updates["order_preferences"] = request.order_preferences
        
        config = trading_service.update_user_strategy_config(user_id, strategy_id, updates)
        if not config:
            raise HTTPException(status_code=500, detail="Failed to update strategy config")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user strategy config: {str(e)}") 