"""
Multi-User Broker API Endpoints

FastAPI endpoints for managing multiple broker accounts across multiple users.
Provides secure access to broker operations with proper authentication and authorization.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import HTTPBearer
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.core.multi_user_broker_manager import (
    multi_user_broker_manager, BrokerOperationResult,
    add_user_broker, remove_user_broker, place_order_for_user,
    get_positions_for_user, get_balance_for_user, get_all_user_positions
)
from app.brokers.base import BrokerOrder
from app.models.base import OrderSide, OrderType, ProductType, BrokerName
from app.api.auth import get_current_user, get_current_admin
from app.models.base import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brokers", tags=["Multi-User Brokers"])
security = HTTPBearer()

# Pydantic Models
class BrokerSessionInfo(BaseModel):
    """Broker session information"""
    user_id: str
    config_id: str
    broker_name: str
    session_id: str
    authenticated_at: datetime
    last_activity: datetime
    health_status: str
    error_count: int

class OrderRequest(BaseModel):
    """Order placement request"""
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(default="NSE", description="Exchange")
    side: OrderSide = Field(..., description="Buy or Sell")
    order_type: OrderType = Field(..., description="Order type")
    product_type: ProductType = Field(..., description="Product type")
    quantity: int = Field(..., gt=0, description="Quantity")
    price: Optional[float] = Field(None, description="Price for limit orders")
    trigger_price: Optional[float] = Field(None, description="Trigger price for SL orders")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "TCS",
                "exchange": "NSE",
                "side": "BUY",
                "order_type": "MARKET",
                "product_type": "DELIVERY",
                "quantity": 1
            }
        }

class OperationResult(BaseModel):
    """Standard operation result"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    execution_time: Optional[float] = None

class SystemStatus(BaseModel):
    """System status information"""
    total_users: int
    total_sessions: int
    healthy_sessions: int
    error_sessions: int
    expired_sessions: int
    by_broker: Dict[str, Dict[str, int]]
    uptime: str
    background_tasks: int

# Endpoints

@router.post("/add", response_model=OperationResult)
async def add_broker_account(
    broker_config_id: str = Body(..., description="Broker configuration ID"),
    current_user: User = Depends(get_current_user)
):
    """Add a broker account for the current user"""
    try:
        result = await add_user_broker(current_user.id, broker_config_id)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error adding broker account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add broker account: {str(e)}"
        )

@router.delete("/remove/{broker_config_id}", response_model=OperationResult)
async def remove_broker_account(
    broker_config_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a broker account for the current user"""
    try:
        result = await remove_user_broker(current_user.id, broker_config_id)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error removing broker account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove broker account: {str(e)}"
        )

@router.get("/sessions", response_model=List[BrokerSessionInfo])
async def get_user_broker_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get all active broker sessions for the current user"""
    try:
        sessions = await multi_user_broker_manager.get_user_brokers(current_user.id)
        
        return [
            BrokerSessionInfo(
                user_id=session.user_id,
                config_id=session.config_id,
                broker_name=session.broker_name.value,
                session_id=session.session_id,
                authenticated_at=session.authenticated_at,
                last_activity=session.last_activity,
                health_status=session.health_status,
                error_count=session.error_count
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}"
        )

@router.post("/orders/place", response_model=OperationResult)
async def place_order(
    broker_config_id: str = Body(..., description="Broker configuration ID"),
    order: OrderRequest = Body(..., description="Order details"),
    current_user: User = Depends(get_current_user)
):
    """Place an order using a specific broker account"""
    try:
        # Convert to BrokerOrder
        broker_order = BrokerOrder(
            symbol=order.symbol,
            exchange=order.exchange,
            side=order.side,
            order_type=order.order_type,
            product_type=order.product_type,
            quantity=order.quantity,
            price=order.price,
            trigger_price=order.trigger_price
        )
        
        result = await place_order_for_user(current_user.id, broker_config_id, broker_order)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place order: {str(e)}"
        )

@router.get("/positions/{broker_config_id}", response_model=OperationResult)
async def get_positions(
    broker_config_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get positions from a specific broker account"""
    try:
        result = await get_positions_for_user(current_user.id, broker_config_id)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )

@router.get("/positions", response_model=Dict[str, OperationResult])
async def get_all_positions(
    current_user: User = Depends(get_current_user)
):
    """Get positions from all broker accounts for the current user"""
    try:
        results = await get_all_user_positions(current_user.id)
        
        # Convert to response format
        response = {}
        for config_id, result in results.items():
            response[config_id] = OperationResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                execution_time=result.execution_time
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting all positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all positions: {str(e)}"
        )

@router.get("/balance/{broker_config_id}", response_model=OperationResult)
async def get_balance(
    broker_config_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get balance from a specific broker account"""
    try:
        result = await get_balance_for_user(current_user.id, broker_config_id)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balance: {str(e)}"
        )

@router.get("/balances", response_model=Dict[str, OperationResult])
async def get_all_balances(
    current_user: User = Depends(get_current_user)
):
    """Get balances from all broker accounts for the current user"""
    try:
        results = await multi_user_broker_manager.get_all_user_balances(current_user.id)
        
        # Convert to response format
        response = {}
        for config_id, result in results.items():
            response[config_id] = OperationResult(
                success=result.success,
                message=result.message,
                data=result.data,
                error_code=result.error_code,
                execution_time=result.execution_time
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting all balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all balances: {str(e)}"
        )

@router.get("/market-data/{broker_config_id}/{symbol}", response_model=OperationResult)
async def get_market_data(
    broker_config_id: str,
    symbol: str,
    exchange: str = Query(default="NSE", description="Exchange"),
    current_user: User = Depends(get_current_user)
):
    """Get market data from a specific broker account"""
    try:
        result = await multi_user_broker_manager.get_market_data_for_user(
            current_user.id, broker_config_id, symbol, exchange
        )
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market data: {str(e)}"
        )

# Admin endpoints

@router.get("/admin/status", response_model=SystemStatus)
async def get_system_status(
    current_admin: User = Depends(get_current_admin)
):
    """Get overall system status (Admin only)"""
    try:
        status = await multi_user_broker_manager.get_system_status()
        
        return SystemStatus(**status)
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/admin/users/{user_id}/sessions", response_model=List[BrokerSessionInfo])
async def get_user_sessions_admin(
    user_id: str,
    current_admin: User = Depends(get_current_admin)
):
    """Get broker sessions for any user (Admin only)"""
    try:
        sessions = await multi_user_broker_manager.get_user_brokers(user_id)
        
        return [
            BrokerSessionInfo(
                user_id=session.user_id,
                config_id=session.config_id,
                broker_name=session.broker_name.value,
                session_id=session.session_id,
                authenticated_at=session.authenticated_at,
                last_activity=session.last_activity,
                health_status=session.health_status,
                error_count=session.error_count
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}"
        )

@router.delete("/admin/users/{user_id}/sessions/{config_id}", response_model=OperationResult)
async def remove_user_session_admin(
    user_id: str,
    config_id: str,
    current_admin: User = Depends(get_current_admin)
):
    """Remove a broker session for any user (Admin only)"""
    try:
        result = await remove_user_broker(user_id, config_id)
        
        return OperationResult(
            success=result.success,
            message=result.message,
            data=result.data,
            error_code=result.error_code,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error(f"Error removing user session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user session: {str(e)}"
        )

@router.post("/admin/initialize", response_model=OperationResult)
async def initialize_broker_manager(
    current_admin: User = Depends(get_current_admin)
):
    """Initialize the multi-user broker manager (Admin only)"""
    try:
        success = await multi_user_broker_manager.initialize()
        
        return OperationResult(
            success=success,
            message="Broker manager initialized successfully" if success else "Failed to initialize broker manager"
        )
        
    except Exception as e:
        logger.error(f"Error initializing broker manager: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize broker manager: {str(e)}"
        )

@router.post("/admin/shutdown", response_model=OperationResult)
async def shutdown_broker_manager(
    current_admin: User = Depends(get_current_admin)
):
    """Shutdown the multi-user broker manager (Admin only)"""
    try:
        await multi_user_broker_manager.shutdown()
        
        return OperationResult(
            success=True,
            message="Broker manager shutdown successfully"
        )
        
    except Exception as e:
        logger.error(f"Error shutting down broker manager: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to shutdown broker manager: {str(e)}"
        )

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        status = await multi_user_broker_manager.get_system_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": status["total_sessions"],
            "healthy_sessions": status["healthy_sessions"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        } 