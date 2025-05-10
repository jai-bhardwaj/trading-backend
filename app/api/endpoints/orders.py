# app/api/endpoints/orders.py
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path, Body
from typing import List, Optional, Dict
import logging

from app.api.models.order import OrderCreate, OrderResponse
from app.core.interfaces import BrokerInterface, Order as InternalOrder # Import internal Order model
from app.api.dependencies import get_resolved_broker, get_broker_details_from_body, get_broker_details_from_query # Import dependencies

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Place a new order"
)
async def place_new_order(
    order_in: OrderCreate, # Order details are in the request body
    # Use a dependency that extracts details *from the body* (order_in)
    broker: BrokerInterface = Depends(
        lambda details=Depends(lambda p: get_broker_details_from_body(p.__dict__)): get_resolved_broker(details)
    )
    # ^^ This complex Depends ensures get_resolved_broker gets details derived from the order_in body model
):
    """
    Places a new order based on the details provided in the request body.
    Selects the broker based on `broker_id` and `is_paper_trade` flag.
    """
    logger.info(f"Received place order request for user {order_in.user_id} via broker {broker.__class__.__name__}")

    try:
        # 1. Convert API model (OrderCreate) to internal domain model (InternalOrder)
        #    This allows adding more internal fields later without changing API model
        internal_order = InternalOrder(
            user_id=order_in.user_id,
            symbol=order_in.symbol,
            exchange=order_in.exchange,
            product_type=order_in.product_type,
            order_type=order_in.order_type,
            side=order_in.side,
            quantity=order_in.quantity,
            broker_id=order_in.broker_id, # Store intended broker
            price=order_in.price,
            trigger_price=order_in.trigger_price,
            variety=order_in.variety,
            tag=order_in.tag,
            is_paper_trade=order_in.is_paper_trade,
            # Internal fields like status will be set by broker/system
        )

        # 2. Call the broker's place_order method
        result = await broker.place_order(internal_order)

        # 3. Format the response
        # The result dict from broker should contain broker_order_id, status, message
        return OrderResponse(
            broker_order_id=result.get("broker_order_id"),
            status=result.get("status", "UNKNOWN"),
            message=result.get("message"),
            internal_order_id=internal_order.internal_order_id, # Include internal ID if available (e.g., from mock)
            broker=broker.__class__.__name__
        )

    except (ValueError, ConnectionError, ConnectionAbortedError) as e:
         # Catch specific errors from broker interaction or validation
         logger.error(f"Error placing order for user {order_in.user_id}: {e}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST, # Or appropriate status code
             detail=f"Failed to place order: {e}"
         )
    except HTTPException as e:
         # Re-raise HTTP exceptions from dependencies
         raise e
    except Exception as e:
        # Catch unexpected errors
        logger.exception(f"Unexpected error placing order for user {order_in.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}"
        )


@router.delete(
    "/{broker_order_id}",
    response_model=OrderResponse,
    summary="Cancel an existing order"
)
async def cancel_existing_order(
    broker_order_id: str = Path(..., description="The order ID provided by the broker"),
    # Get user/broker details from query parameters for DELETE usually
    broker_details: Dict = Depends(get_broker_details_from_query),
    # Resolve the broker instance based on query params
    broker: BrokerInterface = Depends(get_resolved_broker),
    variety: Optional[str] = Query("NORMAL", description="Order variety (e.g., NORMAL, AMO) - Important for some brokers like Angel One")
):
    """
    Cancels an existing order identified by the broker's order ID.
    Requires user_id and broker_id (and potentially is_paper_trade) as query parameters
    to identify the correct broker session/instance.
    """
    user_id = broker_details["user_id"] # Extract user_id from resolved details
    logger.info(f"Received cancel order request for user {user_id}, broker order ID {broker_order_id} via {broker.__class__.__name__}")

    try:
        result = await broker.cancel_order(
            user_id=user_id,
            broker_order_id=broker_order_id,
            variety=variety
            )

        return OrderResponse(
            broker_order_id=broker_order_id,
            status=result.get("status", "UNKNOWN"),
            message=result.get("message"),
            broker=broker.__class__.__name__
        )

    except (ValueError, ConnectionError, ConnectionAbortedError) as e:
         logger.error(f"Error cancelling order {broker_order_id} for user {user_id}: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to cancel order: {e}")
    except HTTPException as e:
         raise e
    except Exception as e:
        logger.exception(f"Unexpected error cancelling order {broker_order_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {e}")


@router.get(
    "/{broker_order_id}",
    response_model=OrderResponse, # Use OrderResponse, it includes status fields
    summary="Get the status of a specific order"
)
async def get_order_details(
    broker_order_id: str = Path(..., description="The order ID provided by the broker"),
    broker_details: Dict = Depends(get_broker_details_from_query),
    broker: BrokerInterface = Depends(get_resolved_broker)
):
    """
    Retrieves the current status and details of a specific order from the broker.
    Requires user_id and broker_id as query parameters.
    """
    user_id = broker_details["user_id"]
    logger.info(f"Received get order status request for user {user_id}, broker order ID {broker_order_id} via {broker.__class__.__name__}")

    try:
        # Get the raw status dict from the broker
        order_status_dict = await broker.get_order_status(user_id=user_id, broker_order_id=broker_order_id)

        # Map the result dict to the OrderResponse model
        # Handle cases where the order is not found or errors occur
        if order_status_dict.get("status") == "NOT_FOUND":
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=order_status_dict.get("message", "Order not found"))
        if order_status_dict.get("status") == "ERROR" or order_status_dict.get("status") == "MAPPING_ERROR":
             raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=order_status_dict.get("message", "Failed to retrieve order status from broker"))

        # Convert the successful status dict into the response model
        # Ensure timestamps are strings if needed by model
        order_timestamp_str = str(order_status_dict.get("order_timestamp")) if order_status_dict.get("order_timestamp") else None

        return OrderResponse(
            broker_order_id=order_status_dict.get("broker_order_id"),
            internal_order_id=order_status_dict.get("internal_order_id"), # If available (e.g., from mock)
            status=order_status_dict.get("status", "UNKNOWN"),
            message=order_status_dict.get("status_message"),
            broker=broker.__class__.__name__,
            symbol=order_status_dict.get("symbol"),
            side=order_status_dict.get("side"),
            quantity=order_status_dict.get("quantity"),
            filled_quantity=order_status_dict.get("filled_quantity"),
            pending_quantity=order_status_dict.get("pending_quantity"),
            average_price=order_status_dict.get("average_price"),
            order_type=order_status_dict.get("order_type"),
            product_type=order_status_dict.get("product_type"),
            trigger_price=order_status_dict.get("trigger_price"),
            price=order_status_dict.get("price"),
            order_timestamp=order_timestamp_str,
        )

    except HTTPException as e:
         raise e # Re-raise validation or not found errors
    except Exception as e:
        logger.exception(f"Unexpected error getting order status {broker_order_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {e}")


@router.get(
    "/",
    response_model=List[OrderResponse], # Returns a list of orders
    summary="Get order history for the user"
)
async def get_user_order_history(
    broker_details: Dict = Depends(get_broker_details_from_query),
    broker: BrokerInterface = Depends(get_resolved_broker)
):
    """
    Retrieves the list of orders (order book) for the specified user from the broker.
    Requires user_id and broker_id as query parameters.
    """
    user_id = broker_details["user_id"]
    logger.info(f"Received get order history request for user {user_id} via {broker.__class__.__name__}")

    try:
        order_history_list = await broker.get_order_history(user_id=user_id)

        # Map each order dict in the list to the OrderResponse model
        response_list = []
        for order_data in order_history_list:
             order_timestamp_str = str(order_data.get("order_timestamp")) if order_data.get("order_timestamp") else None
             response_list.append(
                 OrderResponse(
                     broker_order_id=order_data.get("broker_order_id"),
                     internal_order_id=order_data.get("internal_order_id"),
                     status=order_data.get("status", "UNKNOWN"),
                     message=order_data.get("status_message"),
                     broker=broker.__class__.__name__, # Add broker name for clarity
                     symbol=order_data.get("symbol"),
                     side=order_data.get("side"),
                     quantity=order_data.get("quantity"),
                     filled_quantity=order_data.get("filled_quantity"),
                     pending_quantity=order_data.get("pending_quantity"),
                     average_price=order_data.get("average_price"),
                     order_type=order_data.get("order_type"),
                     product_type=order_data.get("product_type"),
                     trigger_price=order_data.get("trigger_price"),
                     price=order_data.get("price"),
                     order_timestamp=order_timestamp_str,
                 )
             )
        return response_list

    except HTTPException as e:
         raise e
    except Exception as e:
        logger.exception(f"Unexpected error getting order history for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {e}")