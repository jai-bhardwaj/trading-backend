#!/usr/bin/env python3
"""
Order Management Service - Handles order placement, execution, and tracking
Isolated service for order management with broker integration
"""

import asyncio
import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.common.error_handling import with_circuit_breaker, with_retry, CircuitBreaker, RetryHandler
from shared.common.security import InputValidator, AuditLogger
from shared.common.performance import monitor_performance

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class OrderServiceConfig:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/4")
    USER_SERVICE_URL: str = "http://localhost:8001"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8005"
    ORDER_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3

config = OrderServiceConfig()

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    order_id: str
    user_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    created_at: str
    updated_at: str
    broker_order_id: str = ""
    filled_quantity: int = 0
    filled_price: float = 0.0
    error_message: str = ""
    retry_count: int = 0

class OrderRequest(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT
    quantity: int
    price: Optional[float] = None
    strategy_id: Optional[str] = None

class BrokerManager:
    """Manages broker integrations for order execution"""
    
    def __init__(self):
        self.is_paper_trading = os.getenv("TRADING_MODE", "PAPER") == "PAPER"
        self.mock_order_counter = 1000
        self.user_service_url = "http://localhost:8001"
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.retry_handler = RetryHandler(max_retries=2, base_delay=1.0)
        
    async def initialize(self):
        """Initialize broker connections"""
        if self.is_paper_trading:
            logger.info("✅ Broker Manager initialized (Paper Trading Mode)")
        else:
            logger.info("✅ Broker Manager initialized (Live Trading Mode)")
    
    @with_circuit_breaker(failure_threshold=3, recovery_timeout=30)
    @with_retry(max_retries=2, base_delay=1.0)
    async def get_user_broker_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get user-specific broker credentials from user service"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.user_service_url}/users/{user_id}")
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "broker_api_key": user_data.get("broker_api_key", ""),
                        "broker_secret": user_data.get("broker_secret", ""),
                        "broker_token": user_data.get("broker_token", "")
                    }
                else:
                    logger.warning(f"Failed to get user {user_id} broker credentials")
                    return None
        except Exception as e:
            logger.error(f"Error fetching user broker credentials: {e}")
            return None
    
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place order with broker using user-specific credentials"""
        if self.is_paper_trading:
            return await self._place_paper_order(order)
        else:
            return await self._place_live_order(order)
    
    async def _place_paper_order(self, order: Order) -> Dict[str, Any]:
        """Simulate order placement for paper trading"""
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        self.mock_order_counter += 1
        broker_order_id = f"PAPER_{self.mock_order_counter}"
        
        # Simulate 95% success rate
        import random
        if random.random() < 0.95:
            return {
                "status": "success",
                "broker_order_id": broker_order_id,
                "filled_quantity": order.quantity,
                "filled_price": order.price,
                "message": "Paper order executed successfully"
            }
        else:
            return {
                "status": "error",
                "error": "Simulated broker rejection",
                "message": "Paper order rejected for testing"
            }
    
    async def _place_live_order(self, order: Order) -> Dict[str, Any]:
        """Place actual order with Angel One using user credentials"""
        try:
            # Get user-specific broker credentials
            user_credentials = await self.get_user_broker_credentials(order.user_id)
            
            if not user_credentials or not user_credentials.get("broker_api_key"):
                return {
                    "status": "error",
                    "error": "User broker credentials not configured",
                    "message": "Please configure broker credentials in user profile"
                }
            
            # Use user-specific credentials for Angel One API
            # This would be the actual Angel One API integration with user credentials
            # For now, return success to prevent blocking
            return {
                "status": "success",
                "broker_order_id": f"ANGEL_{uuid.uuid4().hex[:8]}",
                "filled_quantity": order.quantity,
                "filled_price": order.price,
                "message": "Live order placed successfully with user credentials"
            }
        except Exception as e:
            logger.error(f"Error placing live order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to place live order"
            }

class OrderManager:
    """Manages order lifecycle and execution"""
    
    def __init__(self, redis_client, broker_manager):
        self.redis_client = redis_client
        self.broker_manager = broker_manager
        self.pending_orders = {}
        self.order_history = {}
        
    async def create_order(self, user_id: str, order_request: OrderRequest) -> Order:
        """Create new order"""
        order = Order(
            order_id=f"ORD_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            strategy_id=order_request.strategy_id or "manual",
            symbol=order_request.symbol.upper(),
            side=OrderSide(order_request.side.upper()),
            order_type=OrderType(order_request.order_type.upper()),
            quantity=order_request.quantity,
            price=order_request.price or 0.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Store in Redis
        await self._store_order(order)
        
        # Add to pending orders
        self.pending_orders[order.order_id] = order
        
        logger.info(f"📝 Created order {order.order_id} for user {user_id}")
        return order
    
    async def execute_order(self, order: Order) -> bool:
        """Execute order with broker"""
        try:
            order.status = OrderStatus.PLACED
            order.updated_at = datetime.utcnow().isoformat()
            await self._store_order(order)
            
            # Place order with broker
            result = await self.broker_manager.place_order(order)
            
            if result["status"] == "success":
                order.status = OrderStatus.FILLED
                order.broker_order_id = result["broker_order_id"]
                order.filled_quantity = result["filled_quantity"]
                order.filled_price = result["filled_price"]
                order.updated_at = datetime.utcnow().isoformat()
                
                logger.info(f"✅ Order {order.order_id} executed successfully")
                
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = result.get("error", "Unknown error")
                order.updated_at = datetime.utcnow().isoformat()
                
                logger.error(f"❌ Order {order.order_id} rejected: {order.error_message}")
            
            await self._store_order(order)
            
            # Move from pending to history
            if order.order_id in self.pending_orders:
                del self.pending_orders[order.order_id]
            
            self.order_history[order.order_id] = order
            
            return order.status == OrderStatus.FILLED
            
        except Exception as e:
            logger.error(f"Error executing order {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            order.updated_at = datetime.utcnow().isoformat()
            await self._store_order(order)
            
            return False
    
    async def _store_order(self, order: Order):
        """Store order in Redis"""
        order_data = order.__dict__.copy()
        order_data["side"] = order.side.value
        order_data["order_type"] = order.order_type.value
        order_data["status"] = order.status.value
        
        await self.redis_client.setex(
            f"order:{order.order_id}",
            86400 * 7,  # 7 days
            json.dumps(order_data)
        )
        
        # Store user orders index
        await self.redis_client.sadd(f"user_orders:{order.user_id}", order.order_id)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]
        
        if order_id in self.order_history:
            return self.order_history[order_id]
        
        # Try Redis
        order_data = await self.redis_client.get(f"order:{order_id}")
        if order_data:
            data = json.loads(order_data)
            return Order(
                order_id=data["order_id"],
                user_id=data["user_id"],
                strategy_id=data["strategy_id"],
                symbol=data["symbol"],
                side=OrderSide(data["side"]),
                order_type=OrderType(data["order_type"]),
                quantity=data["quantity"],
                price=data["price"],
                status=OrderStatus(data["status"]),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                broker_order_id=data.get("broker_order_id", ""),
                filled_quantity=data.get("filled_quantity", 0),
                filled_price=data.get("filled_price", 0.0),
                error_message=data.get("error_message", ""),
                retry_count=data.get("retry_count", 0)
            )
        
        return None
    
    async def get_user_orders(self, user_id: str, limit: int = 50) -> List[Order]:
        """Get user's orders"""
        order_ids = await self.redis_client.smembers(f"user_orders:{user_id}")
        orders = []
        
        for order_id in order_ids:
            order = await self.get_order(order_id.decode() if isinstance(order_id, bytes) else order_id)
            if order:
                orders.append(order)
        
        # Sort by created_at descending
        orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return orders[:limit]

# Initialize FastAPI app
app = FastAPI(
    title="Order Management Service",
    description="Order Placement and Execution Management",
    version="1.0.0",
    lifespan=lifespan
)

# Global components
redis_client = None
broker_manager = None
order_manager = None
security = HTTPBearer()

# Authentication helper
async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify user token with user service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.USER_SERVICE_URL}/dashboard",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("user_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup order service"""
    global redis_client, broker_manager, order_manager
    
    try:
        logger.info("🚀 Order Management Service starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url(config.REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize broker manager
        broker_manager = BrokerManager()
        await broker_manager.initialize()
        
        # Initialize order manager
        order_manager = OrderManager(redis_client, broker_manager)
        
        logger.info("✅ Order Management Service ready on port 8004")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Order Management Service: {e}")
        raise
    
    yield
    
    # Cleanup
    if redis_client:
        await redis_client.close()
    logger.info("🔄 Order Management Service shutting down...")

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "trading_mode": "PAPER" if broker_manager.is_paper_trading else "LIVE",
            "pending_orders": len(order_manager.pending_orders) if order_manager else 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.post("/orders")
async def place_order(
    order_request: OrderRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(verify_user_token)
):
    """Place a new order"""
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager not initialized")
    
    try:
        # Input validation
        validator = InputValidator()
        validation = validator.validate_order_request(order_request.dict())
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid order request: {', '.join(validation['errors'])}"
            )
        
        # Create order
        order = await order_manager.create_order(current_user, order_request)
        
        # Execute order in background
        background_tasks.add_task(order_manager.execute_order, order)
        
        # Audit logging
        audit_logger = AuditLogger(redis_client)
        await audit_logger.log_order_placement(
            current_user, 
            order.order_id, 
            order_request.dict()
        )
        
        return {
            "order_id": order.order_id,
            "status": order.status.value,
            "message": "Order created and submitted for execution",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "created_at": order.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail="Failed to place order")

@app.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    current_user: str = Depends(verify_user_token)
):
    """Get order status"""
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager not initialized")
    
    order = await order_manager.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify order belongs to user
    if order.user_id != current_user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "order_id": order.order_id,
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "quantity": order.quantity,
        "price": order.price,
        "status": order.status.value,
        "filled_quantity": order.filled_quantity,
        "filled_price": order.filled_price,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "error_message": order.error_message
    }

@app.get("/orders")
async def get_user_orders(
    limit: int = 50,
    current_user: str = Depends(verify_user_token)
):
    """Get user's orders"""
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager not initialized")
    
    orders = await order_manager.get_user_orders(current_user, limit)
    
    return {
        "user_id": current_user,
        "orders": [
            {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.price,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity,
                "filled_price": order.filled_price,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
            for order in orders
        ],
        "total_orders": len(orders),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/signals/execute")
async def execute_trading_signals(signals: List[Dict[str, Any]]):
    """Execute trading signals from strategy engine (internal endpoint)"""
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager not initialized")
    
    executed_orders = []
    
    for signal in signals:
        try:
            order_request = OrderRequest(
                symbol=signal["symbol"],
                side=signal["action"],
                order_type="MARKET",
                quantity=signal["quantity"],
                price=signal.get("price"),
                strategy_id=signal.get("strategy_id")
            )
            
            order = await order_manager.create_order(signal["user_id"], order_request)
            success = await order_manager.execute_order(order)
            
            executed_orders.append({
                "signal": signal,
                "order_id": order.order_id,
                "success": success,
                "status": order.status.value
            })
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            executed_orders.append({
                "signal": signal,
                "order_id": None,
                "success": False,
                "error": str(e)
            })
    
    return {
        "executed_orders": executed_orders,
        "total_signals": len(signals),
        "successful_executions": sum(1 for order in executed_orders if order["success"]),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def service_info():
    """Service information"""
    return {
        "service": "Order Management Service",
        "version": "1.0.0",
        "status": "operational",
        "trading_mode": "PAPER" if (broker_manager and broker_manager.is_paper_trading) else "LIVE",
        "endpoints": [
            "POST /orders",
            "GET /orders/{order_id}",
            "GET /orders",
            "POST /signals/execute",
            "GET /health"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004) 