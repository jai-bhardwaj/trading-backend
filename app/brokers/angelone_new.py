"""
Angel One Broker Implementation - Using the new extensible broker architecture

This implementation provides Angel One SmartAPI integration using the standardized
broker interface with proper error handling and database integration.
"""

import asyncio
import logging
import pyotp
from typing import List, Optional, Dict, Any
from datetime import datetime
from SmartApi import SmartConnect

from app.brokers.base import (
    BrokerInterface, BrokerOrder, BrokerPosition, BrokerBalance, BrokerTrade, MarketData,
    register_broker, AuthenticationError, OrderError, SymbolNotFoundError,
    InsufficientFundsError, RateLimitError
)
from app.models.base import BrokerName, OrderSide, OrderType, ProductType, OrderStatus
from app.brokers.mapping_utils import (
    map_order_to_angelone, map_angelone_order_status, map_angelone_positions,
    map_angelone_balance, map_angelone_trade_history, fetch_symbol_token
)

logger = logging.getLogger(__name__)

@register_broker(BrokerName.ANGEL_ONE)
class AngelOneBroker(BrokerInterface):
    """
    Angel One SmartAPI broker implementation
    
    Provides comprehensive trading functionality through Angel One's SmartAPI
    with proper error handling, session management, and standardized interfaces.
    """
    
    def __init__(self, config):
        super().__init__(config)
        self._smart_api: Optional[SmartConnect] = None
        self._session_data: Optional[Dict[str, Any]] = None
        self._session_lock = asyncio.Lock()
    
    @property
    def supported_exchanges(self) -> List[str]:
        """Angel One supported exchanges"""
        return ["NSE", "BSE", "NFO", "BFO", "MCX", "CDS"]
    
    @property
    def supported_product_types(self) -> List[ProductType]:
        """Angel One supported product types"""
        return [
            ProductType.DELIVERY,
            ProductType.INTRADAY,
            ProductType.MARGIN,
            ProductType.NORMAL,
            ProductType.CARRYFORWARD
        ]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        """Angel One supported order types"""
        return [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.SL,
            OrderType.SL_M
        ]
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Angel One SmartAPI
        
        Returns:
            bool: True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        async with self._session_lock:
            try:
                if self._smart_api and self._session_data:
                    # Check if session is still valid (you might want to add expiry check)
                    return True
                
                # Initialize SmartConnect
                self._smart_api = SmartConnect(api_key=self.config.api_key)
                
                # Generate TOTP
                if not self.config.totp_secret:
                    raise AuthenticationError("TOTP secret is required for Angel One authentication")
                
                totp = pyotp.TOTP(self.config.totp_secret).now()
                
                # Perform login in thread pool (SmartAPI is synchronous)
                session_data = await asyncio.to_thread(
                    self._perform_login,
                    self._smart_api,
                    self.config.client_id,
                    self.config.password,
                    totp
                )
                
                if not session_data or "jwtToken" not in session_data:
                    raise AuthenticationError("Failed to retrieve valid session data from Angel One")
                
                self._session_data = session_data
                self.is_authenticated = True
                
                self.logger.info(f"Angel One authentication successful for client: {self.config.client_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Angel One authentication failed: {e}")
                self._smart_api = None
                self._session_data = None
                self.is_authenticated = False
                raise AuthenticationError(f"Angel One authentication failed: {e}")
    
    def _perform_login(self, smart_api: SmartConnect, client_id: str, password: str, totp: str) -> Dict[str, Any]:
        """Synchronous login method to be called in thread pool"""
        try:
            data = smart_api.generateSession(client_id, password, totp)
            
            if data.get("status") and data.get("data"):
                return data["data"]
            else:
                error_message = data.get("message", "Unknown login error")
                error_code = data.get("errorcode", "N/A")
                raise AuthenticationError(f"Angel One login failed ({error_code}): {error_message}")
                
        except Exception as e:
            raise AuthenticationError(f"Exception during Angel One login: {e}")
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid authenticated session"""
        if not self.is_authenticated:
            await self.authenticate()
    
    async def _run_api_call(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute Angel One API call safely in thread pool
        
        Args:
            method_name: Name of the SmartAPI method to call
            *args: Arguments for the API method
            **kwargs: Keyword arguments for the API method
            
        Returns:
            API response data
            
        Raises:
            Various broker exceptions based on API response
        """
        await self._ensure_authenticated()
        
        if not hasattr(self._smart_api, method_name):
            raise AttributeError(f"SmartConnect has no method '{method_name}'")
        
        api_method = getattr(self._smart_api, method_name)
        
        try:
            result = await asyncio.to_thread(api_method, *args, **kwargs)
            
            # Handle Angel One API response format
            if isinstance(result, dict):
                if result.get("status") == True or str(result.get("status")).lower() == "success":
                    return result.get("data")
                else:
                    error_message = result.get("message", "Unknown API error")
                    error_code = result.get("errorcode", "N/A")
                    
                    # Enhanced error logging for frontend
                    error_details = {
                        "method": method_name,
                        "error_code": error_code,
                        "error_message": error_message,
                        "full_response": result,
                        "args": args,
                        "kwargs": kwargs,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Log detailed error information
                    self.logger.error(f"🚨 ANGEL ONE API ERROR: {error_details}")
                    
                    # Map specific error codes to appropriate exceptions
                    if "insufficient" in error_message.lower() or "balance" in error_message.lower():
                        self.logger.error(f"💰 INSUFFICIENT FUNDS ERROR: Available balance too low for order")
                        raise InsufficientFundsError(f"Angel One API Error ({error_code}): {error_message}")
                    elif "symbol" in error_message.lower() and ("not found" in error_message.lower() or "invalid" in error_message.lower()):
                        self.logger.error(f"🔍 SYMBOL NOT FOUND ERROR: Invalid or non-existent symbol")
                        raise SymbolNotFoundError(f"Angel One API Error ({error_code}): {error_message}")
                    elif "rate limit" in error_message.lower() or error_code == "AG8001" or "too many" in error_message.lower():
                        self.logger.error(f"⏱️ RATE LIMIT ERROR: API call limit exceeded")
                        raise RateLimitError(f"Angel One API Error ({error_code}): {error_message}")
                    elif "market" in error_message.lower() and "closed" in error_message.lower():
                        self.logger.error(f"🏪 MARKET CLOSED ERROR: Trading not allowed during market closure")
                        raise OrderError(f"Angel One API Error ({error_code}): {error_message}")
                    elif "order" in error_message.lower() and ("rejected" in error_message.lower() or "failed" in error_message.lower()):
                        self.logger.error(f"❌ ORDER REJECTION ERROR: Order validation failed")
                        raise OrderError(f"Angel One API Error ({error_code}): {error_message}")
                    elif "authentication" in error_message.lower() or "login" in error_message.lower() or error_code == "AG8002":
                        self.logger.error(f"🔐 AUTHENTICATION ERROR: Session expired or invalid")
                        raise AuthenticationError(f"Angel One API Error ({error_code}): {error_message}")
                    else:
                        self.logger.error(f"❓ UNKNOWN API ERROR: Unhandled error type")
                        raise OrderError(f"Angel One API Error ({error_code}): {error_message}")
            
            return result
            
        except Exception as e:
            if isinstance(e, (InsufficientFundsError, SymbolNotFoundError, RateLimitError, OrderError, AuthenticationError)):
                raise
            else:
                error_details = {
                    "method": method_name,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "args": args,
                    "kwargs": kwargs,
                    "timestamp": datetime.now().isoformat()
                }
                self.logger.error(f"🚨 UNEXPECTED ERROR DURING API CALL: {error_details}")
                raise OrderError(f"Failed to execute Angel One API call {method_name}: {e}")
    
    async def place_order(self, order: BrokerOrder) -> str:
        """
        Place an order with Angel One
        
        Args:
            order: BrokerOrder object with order details
            
        Returns:
            str: Broker order ID
            
        Raises:
            OrderError: If order placement fails
            InsufficientFundsError: If insufficient funds
            SymbolNotFoundError: If symbol not found
        """
        order_log_data = {
            "symbol": order.symbol,
            "exchange": order.exchange,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "product_type": order.product_type.value,
            "quantity": order.quantity,
            "price": order.price,
            "trigger_price": getattr(order, 'trigger_price', None),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"🚀 PLACING ORDER: {order_log_data}")
        
        try:
            # Validate order
            self.validate_order(order)
            
            # Fetch symbol token (required for Angel One)
            self.logger.info(f"🔍 Fetching symbol token for {order.symbol} on {order.exchange}...")
            symbol_result = await self._fetch_symbol_token(order.symbol, order.exchange)
            if not symbol_result:
                error_msg = f"Symbol {order.symbol} not found on {order.exchange}"
                self.logger.error(f"❌ ORDER REJECTED - SYMBOL NOT FOUND: {error_msg}")
                self.logger.error(f"📋 Order Details: {order_log_data}")
                raise SymbolNotFoundError(error_msg)
            
            symbol_token, trading_symbol = symbol_result
            self.logger.info(f"✅ Symbol token found: {trading_symbol} -> {symbol_token}")
            
            # Map order to Angel One format
            order_params = await asyncio.to_thread(
                map_order_to_angelone, 
                order, 
                self._smart_api
            )
            
            # Set symbol token and trading symbol
            order_params["symboltoken"] = symbol_token
            order_params["tradingsymbol"] = trading_symbol
            
            # Log the final order parameters being sent to Angel One
            self.logger.info(f"📨 Angel One Order Parameters: {order_params}")
            
            # Place order
            self.logger.info("🔄 Sending order to Angel One...")
            result_data = await self._run_api_call("placeOrder", order_params)
            
            # Extract order ID
            broker_order_id = None
            if isinstance(result_data, dict):
                broker_order_id = result_data.get("orderid")
            elif isinstance(result_data, str):
                broker_order_id = result_data
            
            if not broker_order_id:
                error_msg = "Order placement succeeded but no order ID returned"
                self.logger.error(f"❌ ORDER PLACEMENT ERROR: {error_msg}")
                self.logger.error(f"📋 Order Details: {order_log_data}")
                self.logger.error(f"📤 Angel One Response: {result_data}")
                raise OrderError(error_msg)
            
            # Log successful order placement
            success_log = {
                **order_log_data,
                "broker_order_id": broker_order_id,
                "status": "PLACED",
                "angel_one_response": result_data
            }
            self.logger.info(f"✅ ORDER PLACED SUCCESSFULLY: {success_log}")
            
            return str(broker_order_id)
            
        except InsufficientFundsError as e:
            rejection_log = {
                **order_log_data,
                "status": "REJECTED",
                "rejection_reason": "INSUFFICIENT_FUNDS",
                "error_message": str(e),
                "error_type": "InsufficientFundsError"
            }
            self.logger.error(f"❌ ORDER REJECTED - INSUFFICIENT FUNDS: {rejection_log}")
            raise
            
        except SymbolNotFoundError as e:
            rejection_log = {
                **order_log_data,
                "status": "REJECTED",
                "rejection_reason": "SYMBOL_NOT_FOUND",
                "error_message": str(e),
                "error_type": "SymbolNotFoundError"
            }
            self.logger.error(f"❌ ORDER REJECTED - SYMBOL NOT FOUND: {rejection_log}")
            raise
            
        except RateLimitError as e:
            rejection_log = {
                **order_log_data,
                "status": "REJECTED",
                "rejection_reason": "RATE_LIMIT_EXCEEDED",
                "error_message": str(e),
                "error_type": "RateLimitError"
            }
            self.logger.error(f"❌ ORDER REJECTED - RATE LIMIT: {rejection_log}")
            raise
            
        except OrderError as e:
            rejection_log = {
                **order_log_data,
                "status": "REJECTED",
                "rejection_reason": "ORDER_ERROR",
                "error_message": str(e),
                "error_type": "OrderError"
            }
            self.logger.error(f"❌ ORDER REJECTED - ORDER ERROR: {rejection_log}")
            raise
            
        except Exception as e:
            rejection_log = {
                **order_log_data,
                "status": "REJECTED",
                "rejection_reason": "UNKNOWN_ERROR",
                "error_message": str(e),
                "error_type": type(e).__name__
            }
            self.logger.error(f"❌ ORDER REJECTED - UNKNOWN ERROR: {rejection_log}")
            raise OrderError(f"Failed to place order: {e}")
    
    async def _fetch_symbol_token(self, symbol: str, exchange: str) -> Optional[tuple]:
        """Fetch symbol token using the mapping utility"""
        try:
            return await fetch_symbol_token(self._smart_api, symbol, exchange)
        except Exception as e:
            self.logger.error(f"Failed to fetch symbol token for {symbol}: {e}")
            return None
    
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        """
        Modify an existing order
        
        Args:
            order_id: Broker order ID
            **kwargs: Fields to modify (price, quantity, etc.)
            
        Returns:
            bool: True if modification successful
        """
        try:
            # Angel One modify order parameters
            modify_params = {
                "variety": kwargs.get("variety", "NORMAL"),
                "orderid": order_id
            }
            
            # Add modifiable fields
            if "price" in kwargs:
                modify_params["price"] = str(kwargs["price"])
            if "quantity" in kwargs:
                modify_params["quantity"] = str(kwargs["quantity"])
            if "trigger_price" in kwargs:
                modify_params["triggerprice"] = str(kwargs["trigger_price"])
            
            result_data = await self._run_api_call("modifyOrder", modify_params)
            
            # Check if modification was successful
            modified_order_id = result_data.get("orderid") if isinstance(result_data, dict) else None
            
            if modified_order_id == order_id:
                self.logger.info(f"Angel One order {order_id} modified successfully")
                return True
            else:
                self.logger.warning(f"Angel One order modification response unexpected: {result_data}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to modify Angel One order {order_id}: {e}")
            raise OrderError(f"Failed to modify order: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Broker order ID
            
        Returns:
            bool: True if cancellation successful
        """
        try:
            result_data = await self._run_api_call("cancelOrder", "NORMAL", order_id)
            
            # Check if cancellation was successful
            cancelled_order_id = result_data.get("orderid") if isinstance(result_data, dict) else None
            
            if cancelled_order_id == order_id:
                self.logger.info(f"Angel One order {order_id} cancelled successfully")
                return True
            else:
                self.logger.warning(f"Angel One order cancellation response unexpected: {result_data}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to cancel Angel One order {order_id}: {e}")
            raise OrderError(f"Failed to cancel order: {e}")
    
    async def get_order_status(self, order_id: str) -> BrokerOrder:
        """
        Get status of an order
        
        Args:
            order_id: Broker order ID
            
        Returns:
            BrokerOrder: Order with current status
        """
        try:
            # Get order book and find the specific order
            order_book_data = await self._run_api_call("orderBook")
            
            if isinstance(order_book_data, list):
                for order_detail in order_book_data:
                    if isinstance(order_detail, dict) and order_detail.get("orderid") == order_id:
                        # Map Angel One order to BrokerOrder
                        mapped_order = await asyncio.to_thread(map_angelone_order_status, order_detail)
                        
                        return BrokerOrder(
                            symbol=mapped_order.get("symbol", ""),
                            exchange=mapped_order.get("exchange", ""),
                            side=OrderSide(mapped_order.get("side", "BUY")),
                            order_type=OrderType(mapped_order.get("order_type", "MARKET")),
                            product_type=ProductType(mapped_order.get("product_type", "INTRADAY")),
                            quantity=int(mapped_order.get("quantity", 0)),
                            price=mapped_order.get("price"),
                            broker_order_id=order_id,
                            status=OrderStatus(mapped_order.get("status", "UNKNOWN")),
                            status_message=mapped_order.get("status_message"),
                            filled_quantity=int(mapped_order.get("filled_quantity", 0)),
                            average_price=mapped_order.get("average_price")
                        )
                
                raise OrderError(f"Order {order_id} not found in order book")
            else:
                raise OrderError("Unexpected order book data format")
                
        except Exception as e:
            self.logger.error(f"Failed to get Angel One order status for {order_id}: {e}")
            raise
    
    async def get_positions(self) -> List[BrokerPosition]:
        """
        Get all current positions
        
        Returns:
            List[BrokerPosition]: List of current positions
        """
        try:
            position_data = await self._run_api_call("position")
            
            if position_data is None:
                self.logger.info("Angel One returned no position data")
                return []
            
            if isinstance(position_data, list):
                positions = []
                mapped_positions = await asyncio.to_thread(map_angelone_positions, position_data)
                
                for pos in mapped_positions:
                    positions.append(BrokerPosition(
                        symbol=pos.symbol,
                        exchange=pos.exchange,
                        product_type=pos.product_type,
                        quantity=pos.quantity,
                        average_price=pos.average_price,
                        last_traded_price=pos.last_traded_price,
                        pnl=pos.pnl,
                        market_value=pos.market_value
                    ))
                
                return positions
            else:
                self.logger.warning(f"Unexpected position data format: {type(position_data)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get Angel One positions: {e}")
            return []
    
    async def get_balance(self) -> BrokerBalance:
        """
        Get account balance and margin information
        
        Returns:
            BrokerBalance: Current balance information
        """
        try:
            balance_data = await self._run_api_call("rmsLimit")
            
            if isinstance(balance_data, dict):
                mapped_balance = await asyncio.to_thread(map_angelone_balance, balance_data)
                
                return BrokerBalance(
                    available_cash=mapped_balance.available_cash,
                    used_margin=mapped_balance.used_margin,
                    total_balance=mapped_balance.total_balance,
                    buying_power=mapped_balance.buying_power
                )
            else:
                self.logger.warning(f"Unexpected balance data format: {type(balance_data)}")
                return BrokerBalance(
                    available_cash=0.0,
                    used_margin=0.0,
                    total_balance=0.0,
                    buying_power=0.0
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get Angel One balance: {e}")
            raise
    
    async def get_trades(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[BrokerTrade]:
        """
        Get trade history
        
        Args:
            from_date: Start date (YYYY-MM-DD format)
            to_date: End date (YYYY-MM-DD format)
            
        Returns:
            List[BrokerTrade]: List of trades
        """
        try:
            # Angel One tradeBook doesn't typically accept date filters
            trade_data = await self._run_api_call("tradeBook")
            
            if trade_data is None:
                self.logger.info("Angel One returned no trade data")
                return []
            
            if isinstance(trade_data, list):
                trades = []
                mapped_trades = await asyncio.to_thread(map_angelone_trade_history, trade_data)
                
                for trade in mapped_trades:
                    trades.append(BrokerTrade(
                        trade_id=trade.get("trade_id", ""),
                        order_id=trade.get("order_id", ""),
                        symbol=trade.get("symbol", ""),
                        exchange=trade.get("exchange", ""),
                        side=OrderSide(trade.get("side", "BUY")),
                        quantity=int(trade.get("quantity", 0)),
                        price=float(trade.get("price", 0)),
                        trade_timestamp=datetime.fromisoformat(trade.get("trade_timestamp", datetime.now().isoformat())),
                        brokerage=float(trade.get("brokerage", 0)),
                        taxes=float(trade.get("taxes", 0)),
                        total_charges=float(trade.get("total_charges", 0)),
                        net_amount=float(trade.get("net_amount", 0))
                    ))
                
                # Filter by date if provided
                if from_date or to_date:
                    filtered_trades = []
                    for trade in trades:
                        trade_date = trade.trade_timestamp.date()
                        
                        if from_date and trade_date < datetime.strptime(from_date, "%Y-%m-%d").date():
                            continue
                        if to_date and trade_date > datetime.strptime(to_date, "%Y-%m-%d").date():
                            continue
                        
                        filtered_trades.append(trade)
                    
                    return filtered_trades
                
                return trades
            else:
                self.logger.warning(f"Unexpected trade data format: {type(trade_data)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get Angel One trades: {e}")
            return []
    
    async def search_symbols(self, query: str, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for trading symbols
        
        Args:
            query: Search query (symbol name or part of it)
            exchange: Optional exchange filter
            
        Returns:
            List[Dict]: List of matching symbols with details
        """
        try:
            # Angel One searchScrip API
            search_data = await self._run_api_call("searchScrip", exchange or "NSE", query)
            
            if isinstance(search_data, list):
                symbols = []
                for item in search_data:
                    if isinstance(item, dict):
                        symbols.append({
                            "symbol": item.get("tradingsymbol", ""),
                            "name": item.get("name", ""),
                            "exchange": item.get("exch_seg", ""),
                            "token": item.get("symboltoken", ""),
                            "instrument_type": item.get("instrumenttype", ""),
                            "lot_size": item.get("lotsize", 1)
                        })
                
                return symbols
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to search Angel One symbols for '{query}': {e}")
            return []
    
    async def get_market_data(self, symbol: str, exchange: str) -> Optional[MarketData]:
        """
        Get real-time market data for a symbol
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            MarketData: Market data or None if not supported
        """
        try:
            # Fetch symbol token first
            symbol_result = await self._fetch_symbol_token(symbol, exchange)
            if not symbol_result:
                return None
            
            symbol_token, trading_symbol = symbol_result
            
            # Get LTP data
            ltp_data = await self._run_api_call("ltpData", exchange, trading_symbol, symbol_token)
            
            if isinstance(ltp_data, dict):
                return MarketData(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    open=float(ltp_data.get("open", 0)),
                    high=float(ltp_data.get("high", 0)),
                    low=float(ltp_data.get("low", 0)),
                    close=float(ltp_data.get("ltp", 0)),  # Use LTP as close price
                    volume=int(ltp_data.get("volume", 0)),
                    change=float(ltp_data.get("change", 0)),
                    change_pct=float(ltp_data.get("changepercent", 0))
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Angel One market data for {symbol}: {e}")
            return None
    
    async def disconnect(self):
        """Clean up and disconnect from Angel One"""
        async with self._session_lock:
            try:
                if self._smart_api:
                    # Angel One doesn't have explicit logout, but we can clear session
                    await asyncio.to_thread(lambda: None)  # Placeholder for any cleanup
                
                self._smart_api = None
                self._session_data = None
                self.is_authenticated = False
                
                self.logger.info("Disconnected from Angel One")
                
            except Exception as e:
                self.logger.error(f"Error during Angel One disconnect: {e}")
            
            await super().disconnect() 