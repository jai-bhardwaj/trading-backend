from typing import Dict, Optional
from fastapi import Depends, HTTPException, status
from app.api.dependencies.auth import get_current_user
from app.models.user import User as UserModel
import os
import logging


# --- Mock Broker Implementation ---
class MockBroker:
    """A simple mock broker for testing purposes."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def place_order(self, order):
        return {
            "broker_order_id": f"MOCK-{order.symbol}-{order.quantity}",
            "status": "PENDING",
            "message": "Order placed in mock broker.",
            "internal_order_id": getattr(order, "internal_order_id", None),
        }

    async def cancel_order(self, user_id, broker_order_id, variety=None):
        return {
            "status": "CANCELLED",
            "message": f"Order {broker_order_id} cancelled in mock broker.",
        }

    async def get_order_status(self, user_id, broker_order_id):
        return {
            "broker_order_id": broker_order_id,
            "status": "COMPLETED",
            "status_message": "Order completed in mock broker.",
            "symbol": "SBIN-EQ",
            "side": "BUY",
            "quantity": 10,
            "filled_quantity": 10,
            "pending_quantity": 0,
            "average_price": 350.50,
            "order_type": "LIMIT",
            "product_type": "INTRADAY",
            "trigger_price": 348.00,
            "price": 350.50,
            "order_timestamp": None,
        }

    async def get_order_history(self, user_id):
        return [
            {
                "broker_order_id": f"MOCK-ORDER-1",
                "internal_order_id": "MOCK-INT-1",
                "status": "COMPLETED",
                "status_message": "Order completed in mock broker.",
                "symbol": "SBIN-EQ",
                "side": "BUY",
                "quantity": 10,
                "filled_quantity": 10,
                "pending_quantity": 0,
                "average_price": 350.50,
                "order_type": "LIMIT",
                "product_type": "INTRADAY",
                "trigger_price": 348.00,
                "price": 350.50,
                "order_timestamp": None,
            }
        ]


# --- Broker Resolver Dependency ---
async def get_resolved_broker(
    broker_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Resolves and returns the appropriate broker instance for the user.
    Supports mock broker for testing and can be extended for real brokers.
    """
    logger = logging.getLogger("broker_resolver")
    if not broker_id:
        broker_id = "mock_broker"

    # Example: Add real broker resolution here
    if broker_id == "mock_broker":
        logger.info(f"Using MockBroker for user {current_user.username}")
        return MockBroker(user_id=current_user.id)

    # Extend here for real brokers, e.g.:
    # if broker_id == "angelone":
    #     return AngelOneBroker(user_id=current_user.id, ...)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Broker '{broker_id}' is not supported.",
    )


# --- Existing dependencies ---
async def get_broker_details_from_body(
    broker_id: Optional[str] = None, current_user: UserModel = Depends(get_current_user)
) -> Dict:
    """
    Get broker details from the request body or use default broker.
    This is a dependency that can be used in FastAPI endpoints.
    """
    if not broker_id:
        # Use default broker if none specified
        broker_id = "mock_broker"

    return {"broker_id": broker_id, "user_id": current_user.id}


async def get_broker_details_from_query(
    broker_id: Optional[str] = None, current_user: UserModel = Depends(get_current_user)
) -> Dict:
    """
    Get broker details from the query parameters or use default broker.
    This is a dependency that can be used in FastAPI endpoints.
    """
    if not broker_id:
        broker_id = "mock_broker"
    return {"broker_id": broker_id, "user_id": current_user.id}
