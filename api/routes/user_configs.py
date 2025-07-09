"""
User Strategy Configs API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
from ..models import UserStrategyConfig, UpdateUserStrategyConfigRequest

router = APIRouter(prefix="/api/user-strategy-configs", tags=["user-configs"])

@router.get("/{user_id}", response_model=List[UserStrategyConfig])
async def get_user_strategy_configs(user_id: str):
    """Get strategy configs for a user"""
    from ..main import trading_service
    try:
        configs = trading_service.get_user_strategy_configs(user_id)
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user strategy configs: {str(e)}")

@router.get("/{user_id}/{strategy_id}", response_model=UserStrategyConfig)
async def get_user_strategy_config(user_id: str, strategy_id: str):
    """Get specific strategy config for a user"""
    from ..main import trading_service
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
    request: UpdateUserStrategyConfigRequest
):
    """Update user strategy config"""
    from ..main import trading_service
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