"""
Orders API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..models import OrderRequest, OrderResponse
from ..dependencies import get_trading_service
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def place_order(request: OrderRequest, trading_service: TradingService = Depends(get_trading_service)):
    """Place an order"""
    try:
        # Convert Pydantic model to dict
        order_data = {
            "user_id": request.user_id,
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "side": request.side.value,
            "order_type": request.order_type.value,
            "quantity": request.quantity,
            "price": request.price,
            "confidence": request.confidence
        }
        
        result = await trading_service.place_order(order_data)
        
        return OrderResponse(
            order_id=result.get("order_id", ""),
            status=result.get("status", "error"),
            broker_order_id=result.get("broker_order_id"),
            message=result.get("message", ""),
            error=result.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")

@router.get("/{user_id}", response_model=Dict)
async def get_user_orders(
    user_id: str, 
    limit: int = Query(default=50, ge=1, le=1000, description="Number of orders to return"),
    offset: int = Query(default=0, ge=0, description="Number of orders to skip"),
    status: Optional[str] = Query(default=None, description="Filter by order status"),
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format)"),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
    trading_service: TradingService = Depends(get_trading_service)
):
    """Get orders for a user with advanced filtering and pagination"""
    try:
        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get orders with filters
        orders_result = trading_service.get_user_orders_with_filters(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            symbol=symbol
        )
        
        return {
            "data": orders_result["orders"],
            "total": orders_result["total"],
            "page": (offset // limit) + 1,
            "totalPages": (orders_result["total"] + limit - 1) // limit,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user orders: {str(e)}")

@router.get("/{user_id}/summary", response_model=Dict)
async def get_user_orders_summary(
    user_id: str,
    status: Optional[str] = Query(default=None, description="Filter by order status"),
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format)"),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
    trading_service: TradingService = Depends(get_trading_service)
):
    """Get summary statistics for user orders with filters"""
    try:
        # Parse date filters
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get summary stats
        summary = trading_service.get_user_orders_summary(
            user_id=user_id,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            symbol=symbol
        )
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders summary: {str(e)}") 