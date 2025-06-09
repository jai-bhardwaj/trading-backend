import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from app.database import get_database_manager
from app.models.base import Order, OrderStatus, OrderSide, OrderType, ProductType
from app.queue.redis_client import get_redis_connection
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

SYNC_INTERVAL = 1  # seconds
REDIS_PENDING_SET = "orders:pending_sync"
REDIS_ORDER_PREFIX = "order:"
BATCH_SIZE = 10  # Process up to 10 orders per batch

def convert_redis_to_db_fields(redis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Redis hash values to proper DB field types"""
    converted = {}
    
    # Decode bytes to strings if needed
    decoded_data = {}
    for key, value in redis_data.items():
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        decoded_data[key] = value
    
    # String fields (direct copy) - only include valid Order model fields
    string_fields = ['id', 'user_id', 'symbol', 'exchange', 'broker_order_id', 
                    'status_message', 'variety', 'notes']
    for field in string_fields:
        if field in decoded_data:
            converted[field] = decoded_data[field]
    
    # Integer fields
    int_fields = ['quantity', 'filled_quantity']
    for field in int_fields:
        if field in decoded_data:
            try:
                converted[field] = int(decoded_data[field])
            except (ValueError, TypeError):
                logger.warning(f"Invalid integer value for {field}: {decoded_data[field]}")
    
    # Float fields
    float_fields = ['price', 'trigger_price', 'average_price']
    for field in float_fields:
        if field in decoded_data:
            try:
                converted[field] = float(decoded_data[field])
            except (ValueError, TypeError):
                logger.warning(f"Invalid float value for {field}: {decoded_data[field]}")
    
    # Enum fields - handle string to enum conversion
    if 'side' in decoded_data:
        try:
            converted['side'] = OrderSide(decoded_data['side'])
        except ValueError:
            logger.warning(f"Invalid OrderSide: {decoded_data['side']}")
    
    if 'order_type' in decoded_data:
        try:
            converted['order_type'] = OrderType(decoded_data['order_type'])
        except ValueError:
            logger.warning(f"Invalid OrderType: {decoded_data['order_type']}")
    
    if 'product_type' in decoded_data:
        try:
            converted['product_type'] = ProductType(decoded_data['product_type'])
        except ValueError:
            logger.warning(f"Invalid ProductType: {decoded_data['product_type']}")
    
    if 'status' in decoded_data:
        try:
            converted['status'] = OrderStatus(decoded_data['status'])
        except ValueError:
            logger.warning(f"Invalid OrderStatus: {decoded_data['status']}")
    
    # DateTime fields
    datetime_fields = ['placed_at', 'executed_at', 'cancelled_at', 'created_at', 'updated_at']
    for field in datetime_fields:
        if field in decoded_data:
            try:
                converted[field] = datetime.fromisoformat(decoded_data[field].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid datetime value for {field}: {decoded_data[field]}")
    
    return converted

async def sync_orders_batch(db_manager, redis_client, order_ids: List[str]) -> int:
    """Sync a batch of orders from Redis to DB"""
    synced_count = 0
    
    async with db_manager.get_async_session() as session:
        for order_id in order_ids:
            try:
                # Decode bytes to string if needed
                if isinstance(order_id, bytes):
                    order_id = order_id.decode('utf-8')
                
                order_key = f"{REDIS_ORDER_PREFIX}{order_id}"
                order_data = redis_client.hgetall(order_key)
                
                if not order_data:
                    # Order not found in Redis, remove from pending set
                    logger.warning(f"No data found for order {order_id}, removing from pending set")
                    redis_client.srem(REDIS_PENDING_SET, order_id)
                    continue
                
                # Convert Redis hash to proper DB types
                converted_data = convert_redis_to_db_fields(order_data)
                
                if not converted_data:
                    logger.warning(f"No valid data to sync for order {order_id}")
                    redis_client.srem(REDIS_PENDING_SET, order_id)
                    continue
                
                # Get or create order in DB
                db_order = await session.get(Order, order_id)
                
                if db_order:
                    # Update existing order
                    for key, value in converted_data.items():
                        if hasattr(db_order, key):
                            setattr(db_order, key, value)
                    logger.debug(f"Updated order {order_id} in DB")
                else:
                    # Create new order - ensure required fields are present
                    if 'id' not in converted_data:
                        converted_data['id'] = order_id
                    
                    # Set default values for required fields if missing
                    required_defaults = {
                        'user_id': 'unknown',
                        'symbol': 'UNKNOWN',
                        'exchange': 'UNKNOWN',
                        'side': OrderSide.BUY,
                        'order_type': OrderType.MARKET,
                        'product_type': ProductType.INTRADAY,
                        'quantity': 0,
                        'status': OrderStatus.PENDING
                    }
                    
                    for field, default_value in required_defaults.items():
                        if field not in converted_data:
                            converted_data[field] = default_value
                    
                    db_order = Order(**converted_data)
                    session.add(db_order)
                    logger.debug(f"Created new order {order_id} in DB")
                
                # Mark as synced
                redis_client.srem(REDIS_PENDING_SET, order_id)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync order {order_id}: {e}")
                # Don't remove from pending set - will retry next time
                continue
        
        try:
            await session.commit()
            logger.info(f"✅ Successfully synced {synced_count} orders to DB")
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to commit order batch: {e}")
            await session.rollback()
            # Re-add failed orders to pending set
            for order_id in order_ids:
                redis_client.sadd(REDIS_PENDING_SET, order_id)
            synced_count = 0
    
    return synced_count

async def db_sync_worker():
    """DB sync worker - the ONLY process that writes to the database"""
    logger.info("🔄 Starting DB sync worker (SINGLE DB CONNECTION)")
    
    db_manager = get_database_manager()
    redis_client = get_redis_connection()
    total_synced = 0
    
    while True:
        try:
            # Get pending order IDs
            order_ids = list(redis_client.smembers(REDIS_PENDING_SET))
            
            if order_ids:
                # Process in batches
                for i in range(0, len(order_ids), BATCH_SIZE):
                    batch = order_ids[i:i + BATCH_SIZE]
                    synced = await sync_orders_batch(db_manager, redis_client, batch)
                    total_synced += synced
                
                if len(order_ids) > 0:
                    logger.info(f"📊 DB Sync: {len(order_ids)} pending, {total_synced} total synced")
            
            await asyncio.sleep(SYNC_INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ DB sync worker error: {e}")
            await asyncio.sleep(SYNC_INTERVAL * 5)  # Wait longer on error 