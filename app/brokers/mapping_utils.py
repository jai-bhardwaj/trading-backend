# app/brokers/mapping_utils.py
"""
Utility functions to map data between the internal system representation
(e.g., Order, Position objects) and the specific formats required by
broker APIs (e.g., Angel One SmartAPI parameters).

This is CRUCIAL for broker integration. The mappings here are ILLUSTRATIVE
and need to be carefully verified against official broker documentation.
"""
import asyncio
import logging
from typing import Dict, Optional

from app.core.interfaces import Balance, Order, Position

logger = logging.getLogger(__name__)

# Cache for symbol tokens to avoid repeated API calls
_symbol_token_cache: Dict[str, str] = {}

# --- Angel One Mapping ---

async def fetch_symbol_token(smartapi_instance, symbol: str, exchange: str) -> Optional[tuple[str, str]]:
    """
    Fetch symbol token for a given symbol and exchange using Angel One's searchScrip API.
    
    Args:
        smartapi_instance: The SmartConnect instance
        symbol: Trading symbol (e.g., "RELIANCE")
        exchange: Exchange name (e.g., "NSE")
    
    Returns:
        Tuple of (symbol_token, correct_trading_symbol) if found, None otherwise
    """
    # Create cache key
    cache_key = f"{symbol}_{exchange}"
    
    # Check cache first
    if cache_key in _symbol_token_cache:
        logger.debug(f"Found cached symbol token for {symbol} on {exchange}")
        cached_value = _symbol_token_cache[cache_key]
        # Handle both old format (just token) and new format (token, symbol)
        if isinstance(cached_value, tuple):
            return cached_value
        else:
            # Old cache format, return with original symbol
            return (cached_value, symbol)
    
    try:
        # Use searchScrip API to find the symbol token
        logger.info(f"Searching for symbol token: {symbol} on {exchange}")
        
        # Run the synchronous searchScrip call in a thread
        search_result = await asyncio.to_thread(
            smartapi_instance.searchScrip, exchange, symbol
        )
        
        if search_result and isinstance(search_result, dict):
            if search_result.get("status") and search_result.get("data"):
                data = search_result["data"]
                
                # searchScrip returns a list of matching instruments
                if isinstance(data, list) and len(data) > 0:
                    # Look for exact match first
                    for instrument in data:
                        if (instrument.get("tradingsymbol") == symbol and 
                            instrument.get("exchange") == exchange):
                            token = instrument.get("symboltoken")
                            if token:
                                # Cache the result
                                result = (token, symbol)
                                _symbol_token_cache[cache_key] = result
                                logger.info(f"Found exact symbol token for {symbol}: {token}")
                                return result
                    
                    # If no exact match and exchange is NSE, look for equity symbol (symbol-EQ)
                    if exchange.upper() == "NSE":
                        equity_symbol = f"{symbol}-EQ"
                        for instrument in data:
                            if (instrument.get("tradingsymbol") == equity_symbol and 
                                instrument.get("exchange") == exchange):
                                token = instrument.get("symboltoken")
                                if token:
                                    # Cache the result with the correct trading symbol
                                    result = (token, equity_symbol)
                                    _symbol_token_cache[cache_key] = result
                                    logger.info(f"Found equity symbol token for {symbol}: {equity_symbol} -> {token}")
                                    return result
                    
                    # If still no match, try the first result (might be close match)
                    first_result = data[0]
                    token = first_result.get("symboltoken")
                    trading_symbol = first_result.get("tradingsymbol")
                    if token and trading_symbol:
                        result = (token, trading_symbol)
                        logger.warning(f"Using first search result for {symbol}: {trading_symbol} -> {token}")
                        _symbol_token_cache[cache_key] = result
                        return result
                        
                logger.warning(f"No matching instruments found for {symbol} on {exchange}")
            else:
                error_msg = search_result.get("message", "Unknown error")
                logger.error(f"searchScrip API error for {symbol}: {error_msg}")
        else:
            logger.error(f"Invalid response from searchScrip API for {symbol}: {search_result}")
            
    except Exception as e:
        logger.error(f"Exception while fetching symbol token for {symbol} on {exchange}: {e}", exc_info=True)
    
    return None

def map_order_to_angelone(order: Order, smartapi_instance=None) -> dict[str, any]:
    """Maps the internal Order object to Angel One placeOrder parameters."""

    # **Critical Mappings - Verify with Angel One Docs!**
    transaction_type_map = {"BUY": "BUY", "SELL": "SELL"}
    order_type_map = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "SL": "STOPLOSS_LIMIT",  # Corresponds to SL order type
        "SL-M": "STOPLOSS_MARKET",  # Corresponds to SL-M order type
    }
    # Product type mapping needs careful consideration based on user intent & broker rules
    product_type_map = {
        "DELIVERY": "DELIVERY",  # CNC in Zerodha
        "INTRADAY": "INTRADAY",  # MIS in Zerodha
        "MARGIN": "MARGIN",  # NRML in Zerodha Futures/Options, MTF for Equity? Check Angel Docs.
        "NORMAL": "NORMAL",  # Often for F&O overnight
        "CARRYFORWARD": "CARRYFORWARD",  # Specific to Angel One? Check usage.
        "BO": "BRACKET",  # Bracket Order
        "CO": "COVER",  # Cover Order
    }
    # Variety mapping is also key for Angel One
    variety_map = {
        "NORMAL": "NORMAL",  # Regular order
        "STOPLOSS": "STOPLOSS",  # Used for SL/SL-M orders - CHECK if this should be set based on order_type instead
        "AMO": "AMO",  # After Market Order
        "ROBO": "ROBO",  # Robo Order (Bracket Order in Angel One?)
    }
    # Duration mapping
    duration_map = {
        "DAY": "DAY",  # Valid for the day
        "IOC": "IOC",  # Immediate or Cancel
    }

    params = {
        "variety": variety_map.get(
            order.variety, "NORMAL"
        ),  # Default to NORMAL if not specified or map based on order_type/product_type
        "tradingsymbol": order.symbol,  # e.g., "SBIN-EQ" or "NIFTY25MAY2518500CE"
        "symboltoken": "",  # Will be fetched below
        "transactiontype": transaction_type_map.get(order.side),
        "exchange": order.exchange,  # e.g., "NSE", "NFO", "MCX"
        "ordertype": order_type_map.get(order.order_type),
        "producttype": product_type_map.get(order.product_type),
        "duration": "DAY",  # Defaulting to DAY, make configurable if needed
        "quantity": str(order.quantity),  # API expects string quantity
        "price": "0",  # Default for MARKET, SL-M
        "triggerprice": "0",  # Default if not SL/SL-M
    }

    # Add price and trigger price based on order type
    if order.order_type == "LIMIT":
        if order.price is None:
            raise ValueError("Price needed for LIMIT order")
        params["price"] = str(order.price)
    elif order.order_type == "SL":
        if order.price is None or order.trigger_price is None:
            raise ValueError("Price and Trigger Price needed for SL order")
        params["price"] = str(order.price)
        params["triggerprice"] = str(order.trigger_price)
        # params["variety"] = variety_map["STOPLOSS"] # Does variety need setting for SL? Check docs.
    elif order.order_type == "SL-M":
        if order.trigger_price is None:
            raise ValueError("Trigger Price needed for SL-M order")
        params["triggerprice"] = str(order.trigger_price)
        # params["variety"] = variety_map["STOPLOSS"] # Does variety need setting for SL-M? Check docs.

    # --- FETCH SYMBOL TOKEN ---
    # This is now implemented using Angel One's searchScrip API
    if smartapi_instance:
        try:
            # This will be called from an async context, so we need to handle it properly
            # The calling function should handle the async call
            logger.info(f"Symbol token fetching will be handled by calling function for {order.symbol}")
        except Exception as e:
            logger.error(f"Error preparing symbol token fetch for {order.symbol}: {e}")
    else:
        logger.warning(f"No SmartAPI instance provided for symbol token fetching for {order.symbol}")

    # Remove None values if the API doesn't accept them (depends on library/API)
    # params = {k: v for k, v in params.items() if v is not None}

    logger.debug(f"Mapped Angel One order params (before token fetch): {params}")
    if (
        not params["transactiontype"]
        or not params["ordertype"]
        or not params["producttype"]
    ):
        raise ValueError(
            f"Order mapping failed for side={order.side}, order_type={order.order_type}, product_type={order.product_type}"
        )

    return params


def map_angelone_positions(api_positions_data: list[dict[str, any]]) -> list[Position]:
    """Maps Angel One position book data to internal Position list."""
    positions = []
    if not api_positions_data:
        return positions

    for p in api_positions_data:
        try:
            # ** Mapping based on observed Angel One position keys - VERIFY! **
            qty = int(p.get("netqty", 0))  # Check if short positions are negative
            # Angel uses buyqty, sellqty, netqty. Use netqty.
            if qty == 0:
                continue  # Skip zero positions

            pos = Position(
                symbol=p.get("tradingsymbol"),
                exchange=p.get("exchange"),
                product_type=p.get("producttype"),  # Verify mapping if needed
                quantity=qty,
                average_price=float(
                    p.get("netavgprice", 0.0)
                ),  # Or buyavgprice/sellavgprice? Use netavgprice if available.
                last_traded_price=float(p.get("ltp", 0.0)),
                pnl=float(
                    p.get("unrealised", 0.0)
                ),  # Or 'realised'? check PnL field names
                # Add other relevant fields from Angel One position data
            )
            positions.append(pos)
        except (ValueError, TypeError, KeyError) as e:
            logger.error(
                f"Error mapping Angel One position: {p}. Error: {e}", exc_info=True
            )
            continue  # Skip this position if mapping fails
    return positions


def map_angelone_balance(api_profile_data: dict[str, any]) -> Balance:
    """Maps Angel One profile/RMS data to internal Balance object."""
    if not api_profile_data:
        raise ValueError("Received empty profile data from Angel One")

    try:
        # ** Mapping based on observed Angel One profile/RMS keys - VERIFY! **
        # Find balance details which might be nested under 'rms' or similar key
        rms_data = (
            api_profile_data  # Or api_profile_data.get('rms') depending on structure
        )
        balance = Balance(
            # Map available cash (check fields like 'availablecash', 'amount', 'balance')
            available_cash=float(rms_data.get("availablecash", 0.0)),
            # Map margin used (check fields like 'marginused', 'utiliseddebits')
            margin_used=float(
                rms_data.get("utilisedmargin", 0.0)
            ),  # Check correct field
            # Map total balance/equity (check fields like 'net', 'equity', 'collateral')
            total_balance=float(
                rms_data.get("net", 0.0)
            ),  # Check correct field for overall balance/equity
            # Map other relevant fields like collateral, exposure limits etc.
        )
        return balance
    except (ValueError, TypeError, KeyError) as e:
        logger.error(
            f"Error mapping Angel One balance from data: {api_profile_data}. Error: {e}",
            exc_info=True,
        )
        raise ValueError(f"Failed to map Angel One balance data: {e}")


def map_angelone_order_status(api_order_data: dict[str, any]) -> dict[str, any]:
    """Maps a single order detail from Angel One order book to internal status dict."""
    if not api_order_data:
        return {}

    # ** Mapping based on observed Angel One order book keys - VERIFY! **
    # Status mapping needs care (e.g., 'open' -> OPEN, 'complete' -> COMPLETE, 'rejected' -> REJECTED)
    status_map = {
        "validation pending": "PENDING",
        "open pending": "PENDING",  # Or OPEN? Check meaning
        "trigger pending": "PENDING",  # For SL orders
        "open": "OPEN",
        "complete": "COMPLETE",
        "rejected": "REJECTED",
        "cancelled": "CANCELLED",
        "modified": "OPEN",  # Modified usually means still open
        # Add all possible Angel One statuses
    }

    try:
        status = api_order_data.get("status", "").lower()
        mapped_status = status_map.get(status, "UNKNOWN")

        return {
            "broker_order_id": api_order_data.get("orderid"),
            "status": mapped_status,
            "symbol": api_order_data.get("tradingsymbol"),
            "exchange": api_order_data.get("exchange"),
            "side": api_order_data.get("transactiontype"),  # BUY/SELL
            "order_type": api_order_data.get("ordertype"),  # MARKET/LIMIT etc.
            "product_type": api_order_data.get("producttype"),
            "quantity": int(api_order_data.get("quantity", 0)),
            "filled_quantity": int(api_order_data.get("filledshares", 0)),
            "pending_quantity": int(
                api_order_data.get("unfilledshares", 0)
            ),  # If available
            "price": float(api_order_data.get("price", 0.0)),
            "trigger_price": float(api_order_data.get("triggerprice", 0.0)),
            "average_price": float(api_order_data.get("averageprice", 0.0)),
            "status_message": api_order_data.get("text")
            or api_order_data.get(
                "statusmessage"
            ),  # Check field name for rejection/status message
            "order_timestamp": api_order_data.get("orderentrytime")
            or api_order_data.get("updatetime"),  # Check timestamp field name(s)
            "variety": api_order_data.get("variety"),
            # Add any other relevant fields: disclosed_quantity, tag, etc.
        }
    except (ValueError, TypeError, KeyError) as e:
        logger.error(
            f"Error mapping Angel One order status: {api_order_data}. Error: {e}",
            exc_info=True,
        )
        return {
            "broker_order_id": api_order_data.get("orderid"),
            "status": "MAPPING_ERROR",
            "error": str(e),
        }


def map_angelone_trade_history(
    api_trade_data: list[dict[str, any]],
) -> list[dict[str, any]]:
    """Maps Angel One trade book data to internal trade history list."""
    trades = []
    if not api_trade_data:
        return trades

    for t in api_trade_data:
        try:
            # ** Mapping based on observed Angel One trade book keys - VERIFY! **
            trade = {
                "trade_id": t.get("tradeid")
                or f"{t.get('orderid')}_{t.get('fillid')}",  # Need a unique ID
                "broker_order_id": t.get("orderid"),
                "symbol": t.get("tradingsymbol"),
                "exchange": t.get("exchange"),
                "side": t.get("transactiontype"),  # BUY/SELL
                "quantity": int(
                    t.get("fillsize") or t.get("quantity")
                ),  # Check field name for fill quantity
                "price": float(
                    t.get("fillprice") or t.get("price")
                ),  # Check field name for fill price
                "product_type": t.get("producttype"),
                "order_type": t.get("ordertype"),
                "trade_timestamp": t.get("filltime")
                or t.get("tradetime"),  # Check timestamp field
                # Add other fields if available: charges, segment, etc.
            }
            trades.append(trade)
        except (ValueError, TypeError, KeyError) as e:
            logger.error(
                f"Error mapping Angel One trade: {t}. Error: {e}", exc_info=True
            )
            continue
    return trades


# Add mapping functions for other brokers as needed
