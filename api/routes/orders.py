"""
Orders API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
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

@router.get("/{user_id}", response_model=List[Dict])
async def get_user_orders(user_id: str, trading_service: TradingService = Depends(get_trading_service)):
    """Get orders for a user"""
    try:
        orders = trading_service.get_user_orders(user_id)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user orders: {str(e)}") 