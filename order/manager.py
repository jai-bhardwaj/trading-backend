"""
Order Manager - Handles order execution and management
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from smartapi import SmartConnect
import pyotp
import os
from dotenv import load_dotenv
import re
import json
from models_clean import Order as DBOrder, UserStrategyConfig
from shared.database import get_db_session
from .mock_broker import MockBroker

load_dotenv()

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    """Order structure"""
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    strategy_id: str
    created_at: datetime
    broker_order_id: Optional[str] = None
    filled_quantity: int = 0
    filled_price: float = 0.0
    error_message: Optional[str] = None

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls_per_minute = max_calls_per_minute
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        async with self.lock:
            now = time.time()
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls if now - call_time < 60]
            
            if len(self.calls) >= self.max_calls_per_minute:
                # Wait until we can make another call
                wait_time = 60 - (now - self.calls[0]) + 1
                logger.warning(f"⚠️ Rate limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                # Recursive call after waiting
                return await self.wait_if_needed()
            
            self.calls.append(now)

class AngelOneBroker:
    """Angel One broker integration with rate limiting"""
    
    def __init__(self):
        self.api_key = os.getenv("ANGEL_ONE_API_KEY")
        self.client_code = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.password = os.getenv("ANGEL_ONE_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET")
        
        if not all([self.api_key, self.client_code, self.password, self.totp_secret]):
            raise ValueError("Missing Angel One environment variables")
        
        self.smart_api = None
        self.session = None
        self.rate_limiter = RateLimiter(max_calls_per_minute=20)  # Conservative for initialization
        self._last_login_time = 0
        self._session_valid_until = 0
    
    async def initialize(self):
        """Initialize the broker with retry logic"""
        max_retries = 3
        retry_delay = 30  # Start with 30 seconds
        
        for attempt in range(max_retries):
            try:
                await self._initialize_with_rate_limit()
                logger.info("✅ Angel One broker initialized successfully")
                return
            except Exception as e:
                error_msg = str(e)
                if "Access denied because of exceeding access rate" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("❌ Max retries reached for rate limit")
                        raise
                else:
                    logger.error(f"❌ Failed to initialize Angel One broker: {e}")
                    raise
        
        raise Exception("Failed to initialize broker after all retries")
    
    async def _initialize_with_rate_limit(self):
        """Initialize with rate limiting"""
        logger.info("🔐 [Broker] Waiting for rate limit before login...")
        await self.rate_limiter.wait_if_needed()
        
        # Initialize SmartAPI
        logger.info("🔐 [Broker] Initializing SmartAPI...")
        self.smart_api = SmartConnect(api_key=self.api_key)
        
        # Generate TOTP
        logger.info("🔐 [Broker] Generating TOTP...")
        totp = pyotp.TOTP(self.totp_secret).now()
        
        # Login
        logger.info("🔐 [Broker] Logging in to Angel One...")
        loop = asyncio.get_running_loop()
        self.session = await loop.run_in_executor(
            None, 
            lambda: self.smart_api.generateSession(self.client_code, self.password, totp)
        )
        
        # Set session validity (Angel One sessions typically last 24 hours)
        self._last_login_time = time.time()
        self._session_valid_until = self._last_login_time + (23 * 3600)  # 23 hours
    
    async def _ensure_session_valid(self):
        """Ensure session is still valid, re-login if needed"""
        if time.time() > self._session_valid_until:
            logger.info("🔄 Session expired, re-logging in")
            await self._initialize_with_rate_limit()
    
    async def place_order(self, order: Order) -> Dict:
        """Place order with Angel One with rate limiting"""
        try:
            await self._ensure_session_valid()
            
            # Get symbol token
            symbol_token = self._get_symbol_token(order.symbol)
            if not symbol_token:
                return {
                    "status": "error",
                    "error": f"Symbol token not found for {order.symbol}",
                    "message": "Invalid symbol"
                }
            
            # Wait for rate limit
            await self.rate_limiter.wait_if_needed()
            
            # Prepare order parameters
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": order.symbol,
                "symboltoken": symbol_token,
                "transactiontype": order.side.value,
                "exchange": "NSE",
                "ordertype": order.order_type.value,
                "producttype": "INTRADAY",  # Use INTRADAY for day trading
                "duration": "DAY",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(order.quantity)  # Ensure quantity is string
            }
            
            # Only add price for limit orders, not market orders
            if order.order_type == OrderType.MARKET:
                order_params["price"] = "0"  # Market orders use 0 for price
            else:
                order_params["price"] = str(order.price)  # Limit orders need actual price
            
            logger.info(f"🔧 Order params for {order.symbol}: {order_params}")
            
            # Place order
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.smart_api.placeOrder(order_params)
            )
            logger.debug(f"Raw placeOrder result: {result} (type: {type(result)})")
            
            # Handle different response types
            if isinstance(result, int):
                # Check if this is a large integer that looks like an order ID (starts with date)
                if result > 1000000:  # Large numbers are likely order IDs
                    logger.info(f"✅ Order placed successfully with ID: {result}")
                    return {
                        "status": "success",
                        "broker_order_id": str(result),
                        "message": "Order placed successfully"
                    }
                else:
                    # Small integers are error codes
                    error_messages = {
                        0: "Success",
                        1: "Invalid parameters",
                        2: "Session expired",
                        3: "Rate limit exceeded",
                        4: "Insufficient funds",
                        5: "Invalid symbol",
                        6: "Market closed",
                        7: "Order rejected by exchange",
                        8: "Technical error",
                        9: "Network error"
                    }
                    error_msg = error_messages.get(result, f"Unknown error code: {result}")
                    logger.error(f"❌ Order placement failed with error code {result}: {error_msg}")
                    logger.info(f"🔍 Full order details: {order_params}")
                    return {
                        "status": "error",
                        "error": f"Broker error code {result}: {error_msg}",
                        "message": "Order placement failed"
                    }
            elif isinstance(result, str):
                # If the result looks like an order ID, treat as success
                if re.match(r"^[0-9A-Fa-f]{12,}[A-Z]{2}$", result):
                    logger.info(f"✅ Order placed successfully: {result}")
                    return {
                        "status": "success",
                        "broker_order_id": result,
                        "message": "Order placed successfully"
                    }
                # Otherwise, try to parse as JSON
                try:
                    result = json.loads(result)
                except Exception as e:
                    logger.error(f"❌ Could not parse placeOrder result as JSON: {e}")
                    return {
                        "status": "error",
                        "error": f"Invalid response from broker: {result}",
                        "message": "Order placement failed"
                    }
            
            # Handle dictionary response
            if isinstance(result, dict):
                if result.get("status"):
                    logger.info(f"✅ Order placed successfully: {result.get('data', {}).get('orderid')}")
                    return {
                        "status": "success",
                        "broker_order_id": result.get("data", {}).get("orderid"),
                        "message": "Order placed successfully"
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"❌ Order placement failed: {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "message": "Order placement failed"
                    }
            else:
                # Unknown response type
                logger.error(f"❌ Unknown response type from broker: {type(result)}, value: {result}")
                return {
                    "status": "error",
                    "error": f"Unknown response type: {type(result)}, value: {result}",
                    "message": "Order placement failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Order placement failed"
            }
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for a symbol from CSV configuration"""
        # Load symbol configurations from CSV
        if not hasattr(self, '_symbol_configs'):
            try:
                from shared.config import ConfigLoader
                config_loader = ConfigLoader()
                self._symbol_configs = config_loader.load_symbols()
                logger.info(f"✅ Loaded {len(self._symbol_configs)} symbol configurations for broker")
            except Exception as e:
                logger.error(f"❌ Error loading symbol configurations: {e}")
                self._symbol_configs = {}
        
        symbol_config = self._symbol_configs.get(symbol)
        if symbol_config:
            return symbol_config.token
        else:
            logger.error(f"❌ Symbol token not found for {symbol}")
            return ""
    
    async def close(self):
        """Close the broker connection"""
        if self.smart_api:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.smart_api.logout)
                logger.info("✅ Angel One broker closed")
            except Exception as e:
                logger.error(f"❌ Error closing Angel One broker: {e}")

class OrderManager:
    """Manages order execution"""
    
    def __init__(self, paper_trading: bool = True):
        self.paper_trading = paper_trading
        self.broker = MockBroker() if paper_trading else AngelOneBroker()
        self.orders = {}
        
    async def initialize(self):
        """Initialize order manager"""
        try:
            if self.broker:
                await self.broker.initialize()
            logger.info("✅ Order manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize order manager: {e}")
            raise
    
    def _save_order_to_db(self, order: Order) -> bool:
        """Save order to database"""
        try:
            with get_db_session() as session:
                # Check if order already exists
                existing_order = session.query(DBOrder).filter(DBOrder.id == order.order_id).first()
                if existing_order:
                    logger.warning(f"⚠️ Order {order.order_id} already exists in database, updating instead")
                    # Update existing order
                    existing_order.status = order.status.value
                    existing_order.brokerOrderId = order.broker_order_id
                    existing_order.filledQuantity = order.filled_quantity
                    existing_order.averagePrice = order.filled_price
                    existing_order.statusMessage = order.error_message
                    existing_order.updatedAt = datetime.now()
                    session.commit()
                    logger.info(f"✅ Order {order.order_id} updated in database")
                    return True
                
                # Create new order
                db_order = DBOrder(
                    id=order.order_id,  # Use order_id as the primary key
                    userId=order.user_id,  # Use camelCase column name
                    symbol=order.symbol,
                    exchange="NSE",  # Default exchange
                    side=order.side.value,
                    orderType=order.order_type.value,  # Use camelCase column name
                    productType="INTRADAY",  # Use INTRADAY to match broker API expectations
                    quantity=order.quantity,
                    price=order.price,
                    status=order.status.value,
                    strategyId=order.strategy_id,  # Use camelCase column name
                    createdAt=order.created_at,  # Use camelCase column name
                    brokerOrderId=order.broker_order_id,  # Use camelCase column name
                    filledQuantity=order.filled_quantity,  # Use camelCase column name
                    averagePrice=order.filled_price,  # Use camelCase column name
                    statusMessage=order.error_message  # Use camelCase column name
                )
                session.add(db_order)
                session.commit()
                logger.info(f"✅ Order {order.order_id} saved to database")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save order to database: {e}")
            return False
    
    def _get_user_strategy_config(self, user_id, strategy_id):
        with get_db_session() as session:
            config = session.query(UserStrategyConfig).filter_by(
                user_id=user_id,
                strategy_id=strategy_id
            ).first()
            
            if config:
                # Extract data while session is active to avoid session issues
                return {
                    'enabled': config.enabled,
                    'risk_limits': config.risk_limits or {},
                    'order_preferences': config.order_preferences or {}
                }
            return None

    def _check_user_strategy_rules(self, user_id, strategy_id, order_request):
        config = self._get_user_strategy_config(user_id, strategy_id)
        if not config or not config['enabled']:
            logger.info(f"🚫 Strategy {strategy_id} is disabled for user {user_id}")
            return False, "Strategy disabled for user"
        # Check order preferences (e.g., min_confidence)
        min_conf = config['order_preferences'].get('min_confidence', 0.0)
        if 'confidence' in order_request and order_request['confidence'] < min_conf:
            logger.info(f"🚫 Order confidence {order_request['confidence']} below min_confidence {min_conf} for user {user_id}, strategy {strategy_id}")
            return False, f"Order confidence below min_confidence ({min_conf})"
        # Check risk limits (e.g., max_position_size)
        max_pos = config['risk_limits'].get('max_position_size')
        if max_pos is not None:
            # TODO: Query current position for user/strategy and check
            # For now, just log the check
            logger.info(f"ℹ️ Would check max_position_size {max_pos} for user {user_id}, strategy {strategy_id}")
        # Add more checks as needed
        return True, None
    
    async def execute_order(self, order_request: Dict) -> Dict:
        """Execute an order"""
        try:
            user_id = order_request["user_id"]
            strategy_id = order_request.get("strategy_id", "unknown")
            # User-strategy config checks
            ok, reason = self._check_user_strategy_rules(user_id, strategy_id, order_request)
            if not ok:
                return {
                    "status": "rejected",
                    "error": reason,
                    "message": f"Order rejected: {reason}"
                }
            # Create order object with unique ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            order = Order(
                order_id=f"ORD_{timestamp}_{order_request['user_id']}",
                user_id=order_request["user_id"],
                symbol=order_request["symbol"],
                side=OrderSide(order_request["side"]),
                order_type=OrderType(order_request["order_type"]),
                quantity=order_request["quantity"],
                price=order_request.get("price", 0.0),
                status=OrderStatus.PENDING,
                strategy_id=order_request.get("strategy_id", "unknown"),
                created_at=datetime.now()
            )
            
            # Store order in memory
            self.orders[order.order_id] = order
            
            logger.info(f"📝 Created order {order.order_id} for user {order.user_id}")
            
            # Execute order
            if self.paper_trading:
                result = await self.broker.place_order(order)
            else:
                result = await self.broker.place_order(order)
            
            # Update order status
            if result["status"] == "success":
                order.status = OrderStatus.PLACED
                order.broker_order_id = result.get("broker_order_id")
                
                # For mock broker, the order will be filled asynchronously
                # We'll update the order status when it gets filled
                logger.info(f"✅ Order {order.order_id} placed successfully")
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = result.get("error", "Unknown error")
                logger.error(f"❌ Order {order.order_id} rejected: {order.error_message}")
            
            # Save to database
            self._save_order_to_db(order)
            
            return {
                "order_id": order.order_id,
                "status": order.status.value,
                "broker_order_id": order.broker_order_id,
                "message": result.get("message", "Order processed"),
                "filled_price": order.filled_price,
                "filled_quantity": order.filled_quantity,
                "market_price": result.get("market_price")
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Order execution failed"
            }
    
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status"""
        # First check our local orders
        local_order = self.orders.get(order_id)
        if not local_order:
            return None
        
        # If using mock broker, check for updates
        if self.paper_trading and self.broker:
            mock_order = self.broker.get_order_status(order_id)
            if mock_order and mock_order.status != local_order.status:
                # Update local order with mock broker status
                local_order.status = mock_order.status
                local_order.filled_price = mock_order.filled_price
                local_order.filled_quantity = mock_order.filled_quantity
                local_order.error_message = mock_order.error_message
                
                # Save updated status to database
                self._save_order_to_db(local_order)
                
                logger.info(f"🔄 Updated order {order_id} status to {local_order.status.value}")
        
        return local_order
    
    async def get_user_orders(self, user_id: str) -> List[Order]:
        """Get orders for a user"""
        return [order for order in self.orders.values() if order.user_id == user_id]
    
    async def close(self):
        """Close order manager"""
        if self.broker:
            await self.broker.close()
        logger.info("✅ Order manager closed") 