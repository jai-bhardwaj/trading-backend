"""
Order Manager - Handles order execution with Angel One broker
"""

import os
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from SmartApi import SmartConnect
import pyotp

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

class AngelOneBroker:
    """Angel One broker integration"""
    
    def __init__(self):
        self.api_key = os.getenv("ANGEL_ONE_API_KEY")
        self.client_code = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.password = os.getenv("ANGEL_ONE_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET")
        
        if not all([self.api_key, self.client_code, self.password, self.totp_secret]):
            raise ValueError("Missing Angel One environment variables")
        
        self.smart_api = None
        self.session = None
        self._symbol_token_map = None
        
    async def initialize(self):
        """Initialize the broker"""
        try:
            # Initialize SmartAPI
            self.smart_api = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            
            # Login
            loop = asyncio.get_running_loop()
            self.session = await loop.run_in_executor(
                None, 
                lambda: self.smart_api.generateSession(self.client_code, self.password, totp)
            )
            
            logger.info("✅ Angel One broker initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Angel One broker: {e}")
            raise
    
    async def place_order(self, order: Order) -> Dict:
        """Place order with Angel One"""
        try:
            if not self.smart_api:
                await self.initialize()
            
            # Get symbol token
            symbol_token = self._get_symbol_token(order.symbol)
            if not symbol_token:
                return {
                    "status": "error",
                    "error": f"Symbol token not found for {order.symbol}",
                    "message": "Invalid symbol"
                }
            
            # Prepare order parameters
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": order.symbol,
                "symboltoken": symbol_token,
                "transactiontype": order.side.value,
                "exchange": "NSE",
                "ordertype": order.order_type.value,
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": order.price,
                "squareoff": "0",
                "stoploss": "0",
                "quantity": order.quantity
            }
            
            # Place order
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.smart_api.placeOrder(order_params)
            )
            
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
        self.broker = None if paper_trading else AngelOneBroker()
        self.orders = {}
        
    async def initialize(self):
        """Initialize order manager"""
        try:
            if not self.paper_trading and self.broker:
                await self.broker.initialize()
            logger.info("✅ Order manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize order manager: {e}")
            raise
    
    async def execute_order(self, order_request: Dict) -> Dict:
        """Execute an order"""
        try:
            # Create order object
            order = Order(
                order_id=f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_request['user_id']}",
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
            
            # Store order
            self.orders[order.order_id] = order
            
            logger.info(f"📝 Created order {order.order_id} for user {order.user_id}")
            
            # Execute order
            if self.paper_trading:
                result = await self._execute_paper_order(order)
            else:
                result = await self.broker.place_order(order)
            
            # Update order status
            if result["status"] == "success":
                order.status = OrderStatus.PLACED
                order.broker_order_id = result.get("broker_order_id")
                logger.info(f"✅ Order {order.order_id} executed successfully")
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = result.get("error", "Unknown error")
                logger.error(f"❌ Order {order.order_id} rejected: {order.error_message}")
            
            return {
                "order_id": order.order_id,
                "status": order.status.value,
                "broker_order_id": order.broker_order_id,
                "message": result.get("message", "Order processed")
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Order execution failed"
            }
    
    async def _execute_paper_order(self, order: Order) -> Dict:
        """Execute paper trading order (simulated)"""
        # Simulate order execution
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "status": "success",
            "broker_order_id": f"PAPER_{order.order_id}",
            "message": "Paper order executed successfully"
        }
    
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status"""
        return self.orders.get(order_id)
    
    async def get_user_orders(self, user_id: str) -> List[Order]:
        """Get orders for a user"""
        return [order for order in self.orders.values() if order.user_id == user_id]
    
    async def close(self):
        """Close order manager"""
        if self.broker:
            await self.broker.close()
        logger.info("✅ Order manager closed") 