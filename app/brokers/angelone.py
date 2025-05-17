# app/brokers/angelone.py
import asyncio
import logging
import time  # For potential rate limiting waits
from typing import Any, Dict, List, Optional

import pyotp
import SmartApi  # Ensure this is the correct import for your SDK
from SmartApi import SmartConnect

from app.brokers.mapping_utils import (  # Import mapping functions
    map_angelone_balance,
    map_angelone_order_status,
    map_angelone_positions,
    map_angelone_trade_history,
    map_order_to_angelone,
)
from app.core.interfaces import Balance, BrokerInterface, Order, Position

# from smartapi import SmartWebSocketV2 # Import if implementing websockets


logger = logging.getLogger(__name__)

# --- Session Management (Simple In-Memory per User) ---
# Warning: In a multi-worker setup (like gunicorn), this state is per worker.
# A robust solution needs a shared cache (Redis) or DB for session data.
_user_sessions: Dict[str, Dict[str, Any]] = (
    {}
)  # { user_id: {"smartApi": SmartConnect, "session_data": {}, "lock": asyncio.Lock} }


class AngelOneBroker(BrokerInterface):
    """Implementation of BrokerInterface for Angel One SmartAPI."""

    def __init__(self):
        # Instance holds no user-specific state until initialize is called
        logger.info("AngelOneBroker instance created (awaits initialization per user)")

    async def _get_smartapi_instance(
        self, user_id: str, config: Dict[str, Any]
    ) -> SmartConnect:
        """
        Gets or initializes the SmartConnect instance for a user.
        Handles login and session management (basic in-memory).
        """
        if user_id not in _user_sessions:
            # Create entry for the user with a lock
            _user_sessions[user_id] = {
                "smartApi": None,
                "session_data": None,
                "lock": asyncio.Lock(),
                "config": config,  # Store config for potential re-login
            }

        user_session = _user_sessions[user_id]

        async with user_session["lock"]:  # Acquire lock before checking/initializing
            if user_session["smartApi"] and user_session["session_data"]:
                # TODO: Add session expiry check here
                # If expired, attempt refresh token logic or re-login
                logger.debug(f"Using existing Angel One session for user {user_id}")
                return user_session["smartApi"]

            # Initialize if not present or expired (add expiry check logic here)
            logger.info(f"No valid session found for user {user_id}. Attempting login.")
            api_key = config.get("api_key")
            client_id = config.get("client_id")
            password = config.get("password")
            totp_secret = config.get("totp_secret")

            if not all([api_key, client_id, password, totp_secret]):
                raise ValueError(
                    f"Missing required Angel One credentials in config for user {user_id}"
                )

            smartApi = SmartConnect(api_key=api_key)
            logger.info(f"Attempting Angel One login for client ID: {client_id}")

            try:
                # --- Run synchronous login in a thread pool ---
                session_data = await asyncio.to_thread(
                    self._perform_login, smartApi, client_id, password, totp_secret
                )
                # ----------------------------------------------

                if not session_data or "jwtToken" not in session_data:
                    raise ConnectionError(
                        "Failed to retrieve valid session data from Angel One."
                    )

                # Store the initialized instance and session data
                user_session["smartApi"] = smartApi
                user_session["session_data"] = session_data

                # Optional: Set access token if needed by library (check docs)
                # await asyncio.to_thread(smartApi.setSessionExpiryHook, self._session_expiry_hook) # Example hook
                # smartApi.set_access_token(session_data['jwtToken'])

                logger.info(
                    f"Angel One session established successfully for user {user_id}."
                )
                return smartApi

            except Exception as e:
                logger.error(
                    f"Failed to initialize Angel One session for user {user_id}: {e}",
                    exc_info=True,
                )
                # Clear potentially bad state
                user_session["smartApi"] = None
                user_session["session_data"] = None
                raise ConnectionError(
                    f"Angel One initialization/login failed for user {user_id}: {e}"
                )
        # Lock released automatically

    def _perform_login(
        self, smartApi: SmartConnect, client_id: str, password: str, totp_secret: str
    ) -> Dict[str, Any]:
        """Synchronous helper method to perform the login. Called within to_thread."""
        try:
            # Generate TOTP within the synchronous function
            totp = pyotp.TOTP(totp_secret).now()
            # Avoid logging TOTP in production environments if possible
            logger.info(
                f"Generated TOTP for Angel One login (client {client_id})."
            )  # Careful with logging TOTP
            data = smartApi.generateSession(client_id, password, totp)

            if data.get("status") and data.get("data"):
                logger.info(
                    f"Angel One session generated successfully for {client_id}."
                )
                return data["data"]
            else:
                error_message = data.get("message", "Unknown login error")
                error_code = data.get("errorcode", "N/A")
                logger.error(
                    f"Angel One login failed for {client_id}: {error_message} (Code: {error_code})"
                )
                # Map specific error codes if needed (e.g., AB1010 invalid TOTP)
                raise ConnectionError(
                    f"Angel One login failed ({error_code}): {error_message}"
                )

        except Exception as e:
            logger.error(
                f"Exception during Angel One login execution for {client_id}: {e}",
                exc_info=True,
            )
            raise  # Re-raise the exception

    # --- Interface Methods ---

    async def initialize(self, user_id: str, config: Dict[str, Any]):
        """Initialize by ensuring a valid session exists for the user."""
        # The main logic is now handled within _get_smartapi_instance
        logger.info(f"Initializing AngelOneBroker connection for user {user_id}...")
        await self._get_smartapi_instance(
            user_id, config
        )  # This will trigger login if needed
        logger.info(
            f"AngelOneBroker connection check/initialization complete for user {user_id}."
        )

    async def _run_sync_api_call(
        self, user_id: str, func_name: str, *args, **kwargs
    ) -> Any:
        """Helper to run synchronous SDK methods safely in a thread pool."""
        smartApi = await self._get_smartapi_instance(
            user_id, _user_sessions[user_id]["config"]
        )  # Get potentially refreshed instance

        if not hasattr(smartApi, func_name):
            raise AttributeError(f"SmartConnect object has no attribute '{func_name}'")

        api_method = getattr(smartApi, func_name)

        try:
            # Execute the synchronous API method in a thread
            result = await asyncio.to_thread(api_method, *args, **kwargs)
            # --- Basic Response Handling ---
            if isinstance(result, dict):
                if (
                    result.get("status") == True
                    or str(result.get("status")).lower() == "success"
                ):
                    logger.debug(
                        f"Angel One API call {func_name} successful for user {user_id}."
                    )
                    return result.get("data")  # Return the actual data payload
                else:
                    error_message = result.get("message", "Unknown API error")
                    error_code = result.get("errorcode", "N/A")
                    logger.error(
                        f"Angel One API call {func_name} failed for user {user_id}: {error_message} (Code: {error_code})"
                    )
                    # TODO: Handle specific error codes (e.g., session expiry, rate limits)
                    # If session expired (e.g., AG8002), clear session and force re-login on next call?
                    # if error_code == 'AG8002':
                    #     logger.warning(f"Angel One session possibly expired for user {user_id}. Clearing session.")
                    #     _user_sessions[user_id]['smartApi'] = None
                    #     _user_sessions[user_id]['session_data'] = None
                    raise ConnectionAbortedError(
                        f"Angel One API Error ({error_code}): {error_message}"
                    )
            elif result is None:
                # Some API calls might return None on failure or success? Check docs.
                logger.warning(
                    f"Angel One API call {func_name} returned None for user {user_id}. Args: {args}, Kwargs: {kwargs}"
                )
                return None  # Or raise error depending on expected behavior
            else:
                # Handle cases where the response might not be the expected dict
                logger.warning(
                    f"Unexpected response format from {func_name} for user {user_id}: {type(result)} - {result}"
                )
                return result  # Or raise an error

        except Exception as e:
            # Catch errors during asyncio.to_thread or within the API call execution
            logger.error(
                f"Error during Angel One API call {func_name} execution for user {user_id}: {e}",
                exc_info=True,
            )
            # Check for specific SDK exceptions if available
            raise ConnectionError(
                f"Failed to execute Angel One API call {func_name} for user {user_id}: {e}"
            )

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Places an order using the Angel One API."""
        if order.is_paper_trade:
            raise ValueError("Cannot send paper trade order to live Angel One broker.")

        try:
            # Mapping MUST handle fetching symboltoken - this is critical
            order_params = map_order_to_angelone(order)
            logger.info(
                f"Placing Angel One order for user {order.user_id}: Params={order_params}"
            )

            # Ensure symboltoken is present (mapping should handle this, add check)
            if not order_params.get("symboltoken"):
                logger.error(
                    f"Missing 'symboltoken' for order: {order.symbol}. Implement token fetching in mapping_utils."
                )
                raise ValueError(
                    f"Cannot place order for {order.symbol} without a valid 'symboltoken'."
                )

            result_data = await self._run_sync_api_call(
                order.user_id, "placeOrder", order_params
            )

            broker_order_id = (
                result_data.get("orderid") if isinstance(result_data, dict) else None
            )

            if broker_order_id:
                logger.info(
                    f"Angel One order placed successfully for user {order.user_id}. Broker Order ID: {broker_order_id}"
                )
                return {
                    "broker_order_id": broker_order_id,
                    "status": "PLACED",
                    "message": "Order placed successfully.",
                }  # Status might be different initially
            else:
                logger.error(
                    f"Angel One place order call succeeded but did not return an order ID. User: {order.user_id}, Response data: {result_data}"
                )
                return {
                    "broker_order_id": None,
                    "status": "UNKNOWN",
                    "message": "Order placement response did not contain order ID.",
                }

        except (ValueError, ConnectionAbortedError, ConnectionError) as e:
            # Catch mapping errors or API errors from _run_sync_api_call
            logger.error(
                f"Failed to place Angel One order for user {order.user_id}: {e}",
                exc_info=True,
            )
            return {
                "broker_order_id": None,
                "status": "ERROR",
                "message": f"Failed to place order: {e}",
            }
        except Exception as e:
            # Catch unexpected errors
            logger.exception(
                f"Unexpected error placing Angel One order for user {order.user_id}: {e}"
            )
            return {
                "broker_order_id": None,
                "status": "ERROR",
                "message": f"Unexpected error: {e}",
            }

    async def cancel_order(
        self, user_id: str, broker_order_id: str, variety: Optional[str] = "NORMAL"
    ) -> Dict[str, Any]:
        """Cancels an order using the Angel One API."""
        # Angel One cancelOrder needs variety and order id. Variety is often 'NORMAL'.
        # If cancelling AMO/ROBO/etc orders, the correct variety must be supplied.
        if not variety:
            logger.warning(
                "Variety not provided for cancel order, defaulting to 'NORMAL'. This might fail for AMO/Special orders."
            )
            variety = "NORMAL"  # Default, but might be wrong!

        logger.info(
            f"Attempting to cancel Angel One order {broker_order_id} (Variety: {variety}) for user {user_id}"
        )
        try:
            # Params expected: variety, orderid
            result_data = await self._run_sync_api_call(
                user_id, "cancelOrder", variety, broker_order_id
            )

            cancelled_order_id = (
                result_data.get("orderid") if isinstance(result_data, dict) else None
            )

            if cancelled_order_id == broker_order_id:
                logger.info(
                    f"Angel One cancel order request successful for order {broker_order_id}, user {user_id}."
                )
                # The actual status change needs confirmation via order book/update
                return {
                    "broker_order_id": broker_order_id,
                    "status": "CANCEL_REQUESTED",
                    "message": "Cancel request sent.",
                }
            else:
                # This might occur if the API call succeeds but confirms differently, or structure changes
                logger.warning(
                    f"Angel One cancel order response for {broker_order_id} had unexpected data: {result_data}. Assuming success if no exception."
                )
                # Check if the error message indicates it was already cancelled/completed
                return {
                    "broker_order_id": broker_order_id,
                    "status": "CANCEL_REQUESTED",
                    "message": "Cancel request sent (response structure unexpected).",
                }

        except (ValueError, ConnectionAbortedError, ConnectionError) as e:
            logger.error(
                f"Failed to cancel Angel One order {broker_order_id} for user {user_id}: {e}",
                exc_info=True,
            )
            # Check error message for common reasons like "order already completed/cancelled"
            message = f"Failed to cancel order: {e}"
            status = "ERROR"
            if "already" in str(e).lower() and (
                "completed" in str(e).lower()
                or "cancelled" in str(e).lower()
                or "rejected" in str(e).lower()
            ):
                status = "ALREADY_CLOSED"  # Or fetch status to be sure
                message = f"Order likely already closed: {e}"
                logger.warning(
                    f"Cancel failed for {broker_order_id}, likely already closed."
                )

            return {
                "broker_order_id": broker_order_id,
                "status": status,
                "message": message,
            }
        except Exception as e:
            logger.exception(
                f"Unexpected error cancelling Angel One order {broker_order_id} for user {user_id}: {e}"
            )
            return {
                "broker_order_id": broker_order_id,
                "status": "ERROR",
                "message": f"Unexpected error: {e}",
            }

    async def get_order_status(
        self, user_id: str, broker_order_id: str
    ) -> Dict[str, Any]:
        """Gets the status of a specific order by checking the order book."""
        logger.info(
            f"Fetching Angel One order status for order {broker_order_id}, user {user_id}"
        )
        try:
            # Angel One typically doesn't have a get_order_by_id. Fetch order book.
            order_book_data = await self._run_sync_api_call(user_id, "orderBook")

            if isinstance(order_book_data, list):
                for order_detail in order_book_data:
                    if (
                        isinstance(order_detail, dict)
                        and order_detail.get("orderid") == broker_order_id
                    ):
                        logger.info(
                            f"Found order {broker_order_id} in order book for user {user_id}."
                        )
                        return map_angelone_order_status(
                            order_detail
                        )  # Map the found order
                # Order not found in the list
                logger.warning(
                    f"Order {broker_order_id} not found in Angel One order book for user {user_id}."
                )
                return {
                    "broker_order_id": broker_order_id,
                    "status": "NOT_FOUND",
                    "message": "Order not found in today's order book.",
                }
            else:
                logger.error(
                    f"Unexpected data type received from Angel One orderBook for user {user_id}: {type(order_book_data)}"
                )
                raise ValueError("Unexpected data format from orderBook API.")

        except (ValueError, ConnectionAbortedError, ConnectionError) as e:
            logger.error(
                f"Failed to get Angel One order status for {broker_order_id}, user {user_id}: {e}",
                exc_info=True,
            )
            return {
                "broker_order_id": broker_order_id,
                "status": "ERROR",
                "message": f"Failed to get order status: {e}",
            }
        except Exception as e:
            logger.exception(
                f"Unexpected error getting Angel One order status for {broker_order_id}, user {user_id}: {e}"
            )
            return {
                "broker_order_id": broker_order_id,
                "status": "ERROR",
                "message": f"Unexpected error: {e}",
            }

    async def get_order_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets the order history (order book) for the user."""
        logger.info(f"Fetching Angel One order history for user {user_id}")
        try:
            order_book_data = await self._run_sync_api_call(user_id, "orderBook")
            if isinstance(order_book_data, list):
                return [
                    map_angelone_order_status(od)
                    for od in order_book_data
                    if isinstance(od, dict)
                ]
            else:
                logger.error(
                    f"Unexpected data type received from Angel One orderBook for user {user_id}: {type(order_book_data)}"
                )
                return []  # Return empty list on unexpected format
        except Exception as e:
            logger.error(
                f"Failed to get Angel One order history for user {user_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error

    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets current trading positions from Angel One."""
        logger.info(f"Fetching Angel One positions for user {user_id}")
        try:
            position_data = await self._run_sync_api_call(user_id, "position")
            # position() response structure needs checking - is it list directly or nested?
            if isinstance(position_data, list):
                return [pos.__dict__ for pos in map_angelone_positions(position_data)]
            elif (
                isinstance(position_data, dict)
                and "data" in position_data
                and isinstance(position_data["data"], list)
            ):
                # Handle if data is nested under a 'data' key
                return [
                    pos.__dict__
                    for pos in map_angelone_positions(position_data["data"])
                ]
            else:
                logger.error(
                    f"Unexpected data type received from Angel One position API for user {user_id}: {type(position_data)}"
                )
                return []
        except Exception as e:
            logger.error(
                f"Failed to get Angel One positions for user {user_id}: {e}",
                exc_info=True,
            )
            return []

    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Gets account balance and margin details from Angel One."""
        logger.info(f"Fetching Angel One balance/profile for user {user_id}")
        try:
            # Profile endpoint often contains RMS/balance details
            profile_data = await self._run_sync_api_call(
                user_id, "getProfile", None
            )  # Pass profile request object if needed by SDK

            if isinstance(profile_data, dict):
                # Pass the entire profile data to the mapping function
                balance_obj = map_angelone_balance(profile_data)
                return balance_obj.__dict__
            else:
                logger.error(
                    f"Unexpected data type received from Angel One getProfile API for user {user_id}: {type(profile_data)}"
                )
                # Return a default/error structure
                return Balance(
                    available_cash=0, margin_used=0, total_balance=0
                ).__dict__
        except Exception as e:
            logger.error(
                f"Failed to get Angel One balance for user {user_id}: {e}",
                exc_info=True,
            )
            return Balance(
                available_cash=0, margin_used=0, total_balance=0
            ).__dict__  # Return default on error

    async def get_trade_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets the trade history (trade book) for the user."""
        logger.info(f"Fetching Angel One trade history for user {user_id}")
        try:
            trade_book_data = await self._run_sync_api_call(user_id, "tradeBook")
            if isinstance(trade_book_data, list):
                return map_angelone_trade_history(trade_book_data)
            else:
                logger.error(
                    f"Unexpected data type received from Angel One tradeBook for user {user_id}: {type(trade_book_data)}"
                )
                return []
        except Exception as e:
            logger.error(
                f"Failed to get Angel One trade history for user {user_id}: {e}",
                exc_info=True,
            )
            return []

    # --- Session Expiry Hook Example (Optional) ---
    # def _session_expiry_hook(self):
    #      logger.warning("Angel One session expiry hook called!")
    #      # Implement logic here to attempt re-login using refresh token or credentials
    #      # This hook might be called synchronously by the library, be careful with async calls inside it
    #      # Might need to signal the main application loop to handle re-login asynchronously
    #      # For simplicity, we rely on checks within _get_smartapi_instance for now.
