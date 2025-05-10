# app/api/dependencies.py
from fastapi import Depends, HTTPException, status, Body, Query, Path
from typing import Dict, Optional, Annotated, Any
import asyncio
import logging

from app.core.interfaces import BrokerInterface
from app.brokers.mock_broker import MockBroker
from app.brokers.angelone import AngelOneBroker # Import AngelOneBroker
from config import settings, logger # Import logger from config

# --- Broker Instance Management (In-Memory per Worker) ---
# Stores initialized broker instances for each user_id + broker_id combination.
# Warning: State is per worker process in multi-worker setups (e.g., gunicorn).
# Use Redis or similar shared cache for robust multi-worker state.
_broker_instances: Dict[str, BrokerInterface] = {} # Key: f"{user_id}_{broker_id}"
_broker_init_locks: Dict[str, asyncio.Lock] = {}   # Key: f"{user_id}_{broker_id}"

async def get_broker_instance(
    user_id: str,           # Get user_id from path, query, or body depending on endpoint
    broker_id: str,         # Get broker_id from path, query, or body
    is_paper_trade: bool    # Get paper trade flag from query or body
) -> BrokerInterface:
    """
    Dependency function to get an initialized broker instance for a specific user.
    Handles selection between live brokers and the mock broker based on flags.
    Manages initialization locks and basic caching.
    """
    actual_broker_id = "mock_broker" if is_paper_trade else broker_id
    instance_key = f"{user_id}_{actual_broker_id}" # Cache key includes user

    logger.debug(f"Requesting broker instance. User: {user_id}, Requested Broker: {broker_id}, Paper: {is_paper_trade}. Using: {actual_broker_id} (Key: {instance_key})")

    # Check if config exists for the target broker
    if actual_broker_id not in settings.BROKER_CONFIG:
        logger.error(f"Configuration for broker '{actual_broker_id}' not found.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration for broker '{actual_broker_id}' not found."
        )

    broker_config = settings.BROKER_CONFIG[actual_broker_id]

    # Get or create lock for this specific user+broker combination
    lock = _broker_init_locks.setdefault(instance_key, asyncio.Lock())

    async with lock:
        # Double-check if instance was created while waiting for the lock
        if instance_key in _broker_instances:
            logger.debug(f"Returning cached broker instance for key: {instance_key}")
            return _broker_instances[instance_key]

        # --- Instance Creation and Initialization ---
        logger.info(f"No cached instance found for key {instance_key}. Creating and initializing...")
        instance: Optional[BrokerInterface] = None

        try:
            if actual_broker_id == "mock_broker":
                instance = MockBroker()
            elif actual_broker_id == "angelone":
                # Check if essential Angel One config is loaded
                if not all(broker_config.values()): # Basic check if any value is None/empty
                     logger.error(f"Cannot initialize Angel One for user {user_id}: Missing credentials in configuration.")
                     raise ValueError("Angel One credentials missing in server configuration.")
                instance = AngelOneBroker()
            # Add elif for other real brokers:
            # elif actual_broker_id == "other_broker":
            #     instance = OtherBroker()
            else:
                 # Should not happen due to config check, but defensive coding
                 logger.error(f"Unknown broker type requested: {actual_broker_id}")
                 raise HTTPException(status_code=501, detail=f"Broker type '{actual_broker_id}' is not implemented.")

            # Initialize the created instance (this might involve API login)
            await instance.initialize(user_id=user_id, config=broker_config)

            # Store the successfully initialized instance
            _broker_instances[instance_key] = instance
            logger.info(f"Successfully initialized and cached broker instance for key: {instance_key}")
            return instance

        except (ValueError, ConnectionError, ConnectionAbortedError) as e:
            # Initialization failed (e.g., bad credentials, API down)
            logger.error(f"Failed to initialize broker for key {instance_key}: {e}", exc_info=True)
            # Do not cache failed instances. Remove lock if it was just created for this attempt?
            # Consider specific error codes for more informative HTTP exceptions
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to initialize or connect to broker '{actual_broker_id}' for user {user_id}. Reason: {e}"
            )
        except Exception as e:
             # Catch unexpected errors during init
             logger.exception(f"Unexpected error initializing broker for key {instance_key}: {e}")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Unexpected server error during broker initialization for user {user_id}."
             )
    # Lock is released here


# --- Helper Dependency to Extract Broker Info from Request ---
# This makes it easier to use get_broker_instance in endpoints

async def get_broker_details_from_body(
    payload: Dict = Body(...) # Generic way to access body, specific models better
) -> Dict[str, Any]:
    """Extracts broker details typically found in a request body."""
    user_id = payload.get("user_id")
    broker_id = payload.get("broker_id")
    is_paper_trade = payload.get("is_paper_trade", False) # Default to False

    if not user_id or not broker_id:
         raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing 'user_id' or 'broker_id' in request body.")

    return {"user_id": user_id, "broker_id": broker_id, "is_paper_trade": is_paper_trade}

async def get_broker_details_from_query(
    user_id: str = Query(...),
    broker_id: str = Query(...),
    is_paper_trade: bool = Query(False)
) -> Dict[str, Any]:
    """Extracts broker details typically found in query parameters."""
    return {"user_id": user_id, "broker_id": broker_id, "is_paper_trade": is_paper_trade}


# --- The Main Dependency Used by Endpoints ---
# This combines getting the details and getting the instance

async def get_resolved_broker(
    broker_details: Dict[str, Any] = Depends(get_broker_details_from_query) # Default to query, override in endpoint if needed
) -> BrokerInterface:
    """
    Resolves and returns the correct, initialized BrokerInterface instance
    based on details extracted from the request (query params by default).
    """
    try:
        return await get_broker_instance(
            user_id=broker_details["user_id"],
            broker_id=broker_details["broker_id"],
            is_paper_trade=broker_details["is_paper_trade"]
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise e
    except Exception as e:
        # Catch other unexpected errors during resolution
        logger.exception(f"Error resolving broker instance for details {broker_details}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error resolving broker.")

# Example of how to use Depends with body extraction in an endpoint:
# broker_details: Dict[str, Any] = Depends(get_broker_details_from_body)
# broker: BrokerInterface = await get_resolved_broker(broker_details)