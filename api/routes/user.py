"""
User API Routes - For user dashboard and management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/dashboard", response_model=Dict)
async def get_user_dashboard(trading_service: TradingService = Depends(get_trading_service)):
    """Get user dashboard data"""
    try:
        # Get all strategies configured for the admin user
        user_configs = trading_service.get_user_strategy_configs("admin_user_id")
        
        # Get all available strategies from marketplace for reference
        all_strategies = trading_service.get_strategies()
        strategy_map = {strategy["id"]: strategy for strategy in all_strategies}
        
        # Convert user configs to active strategies format
        active_strategies = []
        for config in user_configs:
            if config["enabled"]:
                strategy_info = strategy_map.get(config["strategy_id"], {})
                active_strategies.append({
                    "user_id": "admin",
                    "strategy_id": config["strategy_id"],
                    "status": "active",
                    "activated_at": "2025-07-08T03:11:58.703988",
                    "allocation_amount": 50000,
                    "custom_parameters": config.get("order_preferences", {}),
                    "total_orders": 0,
                    "successful_orders": 0,
                    "total_pnl": 0.0
                })
        
        dashboard_data = {
            "user_info": {
                "user_id": "admin",
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "status": "active"
            },
            "active_strategies": active_strategies,
            "recent_orders": [],
            "portfolio_summary": {
                "total_value": 100000,
                "day_change": 0.0,
                "day_change_pct": 0.0,
                "total_pnl": 0.0,
                "available_balance": 100000
            },
            "system_status": {
                "engine_running": True,
                "total_users": 1,
                "active_strategies": len(active_strategies),
                "total_orders": 0,
                "memory_usage_mb": 128,
                "uptime_seconds": 3600
            }
        }
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user dashboard: {str(e)}")

@router.post("/activate/{strategy_id}", response_model=Dict)
async def activate_strategy(
    strategy_id: str, 
    allocation_amount: int = 0,
    trading_service: TradingService = Depends(get_trading_service)
):
    """Activate a strategy for the user"""
    try:
        # For now, return success response
        # In a real app, this would actually activate the strategy
        result = {
            "user_id": "admin",
            "strategy_id": strategy_id,
            "status": "active",
            "activated_at": "2025-07-10T19:45:00.000000",
            "allocation_amount": allocation_amount,
            "custom_parameters": {},
            "total_orders": 0,
            "successful_orders": 0,
            "total_pnl": 0.0
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate strategy: {str(e)}")

@router.post("/deactivate/{strategy_id}", response_model=Dict)
async def deactivate_strategy(
    strategy_id: str,
    trading_service: TradingService = Depends(get_trading_service)
):
    """Deactivate a strategy for the user"""
    try:
        # For now, return success response
        # In a real app, this would actually deactivate the strategy
        result = {
            "user_id": "admin",
            "strategy_id": strategy_id,
            "status": "available",
            "activated_at": None,
            "allocation_amount": 0,
            "custom_parameters": {},
            "total_orders": 0,
            "successful_orders": 0,
            "total_pnl": 0.0
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate strategy: {str(e)}") 