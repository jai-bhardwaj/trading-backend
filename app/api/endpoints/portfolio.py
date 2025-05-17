# app/api/endpoints/portfolio.py
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (  # Import dependencies
    get_broker_details_from_query,
    get_resolved_broker,
)
from app.api.models.portfolio import (  # Import portfolio API models
    BalanceModel,
    BalanceResponse,
    PositionModel,
    PositionsResponse,
    TradeHistoryResponse,
    TradeModel,
)
from app.core.interfaces import BrokerInterface

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/positions",
    response_model=PositionsResponse,
    summary="Get current trading positions",
)
async def get_user_positions(
    broker_details: Dict = Depends(get_broker_details_from_query),
    broker: BrokerInterface = Depends(get_resolved_broker),
):
    """
    Retrieves the current open trading positions for the specified user from the broker.
    Requires user_id and broker_id as query parameters.
    """
    user_id = broker_details["user_id"]
    broker_id = broker_details["broker_id"]  # Get broker_id for the response model
    logger.info(
        f"Received get positions request for user {user_id} via {broker.__class__.__name__}"
    )

    try:
        positions_list = await broker.get_positions(user_id=user_id)

        # Map the list of position dicts from the broker to PositionModel
        mapped_positions = [PositionModel(**pos_data) for pos_data in positions_list]

        return PositionsResponse(
            user_id=user_id,
            broker_id=broker_id,  # Include broker_id in response
            positions=mapped_positions,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error getting positions for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}",
        )


@router.get(
    "/balance",
    response_model=BalanceResponse,
    summary="Get account balance and margin details",
)
async def get_user_balance(
    broker_details: Dict = Depends(get_broker_details_from_query),
    broker: BrokerInterface = Depends(get_resolved_broker),
):
    """
    Retrieves the current account balance and margin details for the specified user from the broker.
    Requires user_id and broker_id as query parameters.
    """
    user_id = broker_details["user_id"]
    broker_id = broker_details["broker_id"]
    logger.info(
        f"Received get balance request for user {user_id} via {broker.__class__.__name__}"
    )

    try:
        balance_dict = await broker.get_balance(user_id=user_id)

        # Map the balance dict from the broker to BalanceModel
        mapped_balance = BalanceModel(**balance_dict)

        return BalanceResponse(
            user_id=user_id, broker_id=broker_id, balance=mapped_balance
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error getting balance for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}",
        )


@router.get(
    "/trades",
    response_model=TradeHistoryResponse,
    summary="Get trade history (trade book)",
)
async def get_user_trade_history(
    broker_details: Dict = Depends(get_broker_details_from_query),
    broker: BrokerInterface = Depends(get_resolved_broker),
):
    """
    Retrieves the list of executed trades (trade book) for the specified user from the broker.
    Requires user_id and broker_id as query parameters.
    """
    user_id = broker_details["user_id"]
    broker_id = broker_details["broker_id"]
    logger.info(
        f"Received get trade history request for user {user_id} via {broker.__class__.__name__}"
    )

    try:
        trades_list = await broker.get_trade_history(user_id=user_id)

        # Map the list of trade dicts from the broker to TradeModel
        # Ensure timestamps are converted to strings if needed
        mapped_trades = []
        for trade_data in trades_list:
            trade_data["trade_timestamp"] = str(
                trade_data.get("trade_timestamp")
            )  # Convert timestamp
            mapped_trades.append(TradeModel(**trade_data))

        return TradeHistoryResponse(
            user_id=user_id, broker_id=broker_id, trades=mapped_trades
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error getting trade history for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}",
        )
