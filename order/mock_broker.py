"""
Mock Broker - Simulates order execution using live market data
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import redis.asyncio as redis
from dataclasses import dataclass
from enum import Enum

# Import shared models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import MarketDataTick
from shared.timezone import get_ist_now

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    """Order structure for mock broker"""
    order_id: str
    user_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    status: OrderStatus
    strategy_id: str
    created_at: datetime
    broker_order_id: Optional[str] = None
    filled_quantity: int = 0
    filled_price: float = 0.0
    error_message: Optional[str] = None
    timeout_at: Optional[datetime] = None

class MockBroker:
    """Mock broker that executes orders using live market data"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.redis_client = None
        self.running = False
        
        # Order management
        self.pending_orders: Dict[str, Order] = {}
        self.filled_orders: Dict[str, Order] = {}
        
        # Market data
        self.market_data_buffer: Dict[str, List[MarketDataTick]] = {}
        self.latest_ticks: Dict[str, MarketDataTick] = {}
        self.max_buffer_size = 100
        
        # Configuration
        self.timeout_seconds = int(os.getenv("MOCK_BROKER_TIMEOUT", "60"))
        self.retry_interval = float(os.getenv("MOCK_BROKER_RETRY_INTERVAL", "0.5"))
        
        # Background tasks
        self.matching_task = None
        self.market_data_task = None
        
        # Consumer group for market data
        self.consumer_group = "mock_broker_consumers"
        self.consumer_name = f"mock_broker_{os.getpid()}_{id(self)}"
        
        logger.info(f"🔧 MockBroker initialized with timeout={self.timeout_seconds}s, retry_interval={self.retry_interval}s")
    
    async def initialize(self):
        """Initialize the mock broker"""
        try:
            # Connect to Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ MockBroker connected to Redis")
            
            # Start background tasks
            self.running = True
            self.matching_task = asyncio.create_task(self._order_matching_loop())
            self.market_data_task = asyncio.create_task(self._market_data_loop())
            
            logger.info("✅ MockBroker initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MockBroker: {e}")
            raise
    
    async def place_order(self, order: Order) -> Dict:
        """Place an order for execution"""
        try:
            # Set timeout
            order.timeout_at = datetime.now() + timedelta(seconds=self.timeout_seconds)
            order.status = OrderStatus.PLACED
            order.broker_order_id = f"MOCK_{order.order_id}"
            
            # Add to pending orders
            self.pending_orders[order.order_id] = order
            
            # Start consuming market data for this symbol if not already
            await self._ensure_symbol_subscription(order.symbol)
            
            logger.info(f"📝 MockBroker placed order {order.order_id} for {order.symbol} {order.side.value} @ {order.price}")
            
            return {
                "status": "success",
                "broker_order_id": order.broker_order_id,
                "message": "Order placed with mock broker",
                "filled_price": None,
                "filled_quantity": 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to place order with mock broker"
            }
    
    async def _ensure_symbol_subscription(self, symbol: str):
        """Ensure we're subscribed to market data for this symbol"""
        if symbol not in self.market_data_buffer:
            self.market_data_buffer[symbol] = []
            logger.info(f"📊 Started tracking market data for {symbol}")
    
    async def _market_data_loop(self):
        """Background task to consume market data"""
        logger.info("🚀 Starting market data consumption loop")
        
        while self.running:
            try:
                # Get symbols we're tracking
                symbols = list(self.market_data_buffer.keys())
                if not symbols:
                    await asyncio.sleep(1)
                    continue
                
                # Read from market data streams
                stream_names = [f"market_data_stream:{symbol}" for symbol in symbols]
                
                # Create consumer groups if they don't exist
                for stream_name in stream_names:
                    try:
                        await self.redis_client.xgroup_create(
                            stream_name,
                            self.consumer_group,
                            id="0",
                            mkstream=True
                        )
                    except Exception as e:
                        if "BUSYGROUP" not in str(e):
                            logger.warning(f"⚠️ Could not create consumer group for {stream_name}: {e}")
                
                # Read messages
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {stream_name: ">" for stream_name in stream_names},
                    count=10,
                    block=1000
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_market_data_message(stream_name, message_id, fields)
                
            except Exception as e:
                logger.error(f"❌ Error in market data loop: {e}")
                await asyncio.sleep(5)
    
    async def _process_market_data_message(self, stream_name: str, message_id: str, fields: Dict):
        """Process a market data message"""
        try:
            # Convert bytes to strings
            processed_fields = {}
            for key, value in fields.items():
                if isinstance(key, bytes):
                    key = key.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                processed_fields[key] = value
            
            # Parse tick data
            tick = self._parse_tick_data(processed_fields)
            if not tick:
                return
            
            symbol = tick.symbol
            
            # Update buffer
            if symbol not in self.market_data_buffer:
                self.market_data_buffer[symbol] = []
            
            self.market_data_buffer[symbol].append(tick)
            
            # Keep buffer size manageable
            if len(self.market_data_buffer[symbol]) > self.max_buffer_size:
                self.market_data_buffer[symbol] = self.market_data_buffer[symbol][-self.max_buffer_size:]
            
            # Update latest tick
            self.latest_ticks[symbol] = tick
            
            # Acknowledge message
            await self.redis_client.xack(stream_name, self.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"❌ Error processing market data message: {e}")
    
    def _parse_tick_data(self, fields: Dict[str, str]) -> Optional[MarketDataTick]:
        """Parse tick data from Redis fields"""
        try:
            symbol = fields.get('symbol', 'UNKNOWN')
            
            # Parse numeric fields
            ltp = float(fields.get('ltp', '0'))
            change = float(fields.get('change', '0'))
            change_percent = float(fields.get('change_percent', '0'))
            high = float(fields.get('high', '0'))
            low = float(fields.get('low', '0'))
            volume = int(fields.get('volume', '0'))
            bid = float(fields.get('bid', '0'))
            ask = float(fields.get('ask', '0'))
            open_price = float(fields.get('open', '0'))
            close = float(fields.get('close', '0'))
            
            # Parse timestamps
            timestamp_str = fields.get('timestamp', '')
            exchange_timestamp_str = fields.get('exchange_timestamp', '')
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = get_ist_now()
            
            try:
                exchange_timestamp = datetime.fromisoformat(exchange_timestamp_str.replace('Z', '+00:00'))
            except:
                exchange_timestamp = timestamp
            
            return MarketDataTick(
                symbol=symbol,
                token=fields.get('token', ''),
                ltp=ltp,
                change=change,
                change_percent=change_percent,
                high=high,
                low=low,
                volume=volume,
                bid=bid,
                ask=ask,
                open=open_price,
                close=close,
                timestamp=timestamp,
                exchange_timestamp=exchange_timestamp,
                raw_data=fields
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing tick data: {e}")
            return None
    
    async def _order_matching_loop(self):
        """Background task to match orders with market data"""
        logger.info("🚀 Starting order matching loop")
        
        while self.running:
            try:
                if not self.pending_orders:
                    await asyncio.sleep(self.retry_interval)
                    continue
                
                # Process each pending order
                orders_to_remove = []
                
                for order_id, order in self.pending_orders.items():
                    try:
                        # Check if order has timed out
                        if order.timeout_at and datetime.now() > order.timeout_at:
                            logger.warning(f"⏰ Order {order_id} timed out")
                            order.status = OrderStatus.REJECTED
                            order.error_message = "Order timeout"
                            orders_to_remove.append(order_id)
                            continue
                        
                        # Try to match the order
                        matched = await self._try_match_order(order)
                        if matched:
                            orders_to_remove.append(order_id)
                    
                    except Exception as e:
                        logger.error(f"❌ Error matching order {order_id}: {e}")
                        order.status = OrderStatus.REJECTED
                        order.error_message = str(e)
                        orders_to_remove.append(order_id)
                
                # Remove processed orders
                for order_id in orders_to_remove:
                    order = self.pending_orders.pop(order_id, None)
                    if order:
                        self.filled_orders[order_id] = order
                
                await asyncio.sleep(self.retry_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in order matching loop: {e}")
                await asyncio.sleep(5)
    
    async def _try_match_order(self, order: Order) -> bool:
        """Try to match an order with current market data"""
        try:
            symbol = order.symbol
            
            # Get latest tick for this symbol
            latest_tick = self.latest_ticks.get(symbol)
            if not latest_tick:
                logger.debug(f"⚠️ No market data available for {symbol}")
                return False
            
            # Check if we can fill the order
            fill_price = None
            
            if order.side == OrderSide.BUY:
                # For BUY orders: fill if ask price <= signal price
                if latest_tick.ask > 0 and latest_tick.ask <= order.price:
                    fill_price = latest_tick.ask
                    logger.info(f"✅ BUY order {order.order_id} matched: ask={latest_tick.ask} <= signal_price={order.price}")
            
            elif order.side == OrderSide.SELL:
                # For SELL orders: fill if bid price >= signal price
                if latest_tick.bid > 0 and latest_tick.bid >= order.price:
                    fill_price = latest_tick.bid
                    logger.info(f"✅ SELL order {order.order_id} matched: bid={latest_tick.bid} >= signal_price={order.price}")
            
            if fill_price:
                # Fill the order
                order.status = OrderStatus.FILLED
                order.filled_price = fill_price
                order.filled_quantity = order.quantity
                order.broker_order_id = f"MOCK_FILLED_{order.order_id}"
                
                logger.info(f"🎯 Order {order.order_id} FILLED: {order.side.value} {order.quantity} @ {fill_price}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error trying to match order {order.order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status"""
        return self.pending_orders.get(order_id) or self.filled_orders.get(order_id)
    
    def get_user_orders(self, user_id: str) -> List[Order]:
        """Get orders for a user"""
        all_orders = list(self.pending_orders.values()) + list(self.filled_orders.values())
        return [order for order in all_orders if order.user_id == user_id]
    
    async def close(self):
        """Close the mock broker"""
        try:
            self.running = False
            
            # Cancel background tasks
            if self.matching_task:
                self.matching_task.cancel()
            if self.market_data_task:
                self.market_data_task.cancel()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("✅ MockBroker closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing MockBroker: {e}")
