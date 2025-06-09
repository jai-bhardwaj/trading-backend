import asyncio
import logging
import json
import gzip
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict
from app.database import get_database_manager
from app.models.base import Order, OrderStatus, OrderSide, OrderType, ProductType
from app.queue.redis_client import get_redis_connection
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Configuration
BASE_SYNC_INTERVAL = 0.5  # Base interval in seconds
MAX_SYNC_INTERVAL = 5.0   # Maximum interval during low activity
MIN_SYNC_INTERVAL = 0.1   # Minimum interval during high activity
BATCH_SIZE = 50          # Increased batch size for better throughput
REDIS_PENDING_SET = "orders:pending_sync"
REDIS_ORDER_PREFIX = "order:"
REDIS_CHANGELOG_PREFIX = "order_changelog:"
COMPRESSION_THRESHOLD = 1024  # Compress data larger than 1KB

class OptimizedDBSyncWorker:
    """Highly optimized DB sync worker with multiple performance enhancements"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.redis_client = get_redis_connection()
        self.total_synced = 0
        self.sync_times = []
        self.current_interval = BASE_SYNC_INTERVAL
        self.last_activity_time = time.time()
        
        # Performance metrics
        self.metrics = {
            'total_processed': 0,
            'total_errors': 0,
            'avg_sync_time': 0,
            'avg_batch_size': 0,
            'pipeline_ops': 0,
            'compression_saved': 0
        }
    
    def _adaptive_sync_interval(self, pending_count: int, processing_time: float) -> float:
        """Dynamically adjust sync interval based on load and performance"""
        
        # Increase frequency during high activity
        if pending_count > 20:
            self.current_interval = max(MIN_SYNC_INTERVAL, self.current_interval * 0.8)
        elif pending_count > 5:
            self.current_interval = max(BASE_SYNC_INTERVAL, self.current_interval * 0.9)
        else:
            # Decrease frequency during low activity
            self.current_interval = min(MAX_SYNC_INTERVAL, self.current_interval * 1.1)
        
        # Adjust based on processing time
        if processing_time > 1.0:  # If taking too long, slow down
            self.current_interval = min(MAX_SYNC_INTERVAL, self.current_interval * 1.2)
        elif processing_time < 0.1:  # If very fast, can speed up
            self.current_interval = max(MIN_SYNC_INTERVAL, self.current_interval * 0.9)
        
        return self.current_interval
    
    def _compress_large_data(self, data: str) -> bytes:
        """Compress large data to save Redis memory"""
        if len(data) > COMPRESSION_THRESHOLD:
            compressed = gzip.compress(data.encode('utf-8'))
            self.metrics['compression_saved'] += len(data) - len(compressed)
            return b'compressed:' + compressed
        return data.encode('utf-8')
    
    def _decompress_data(self, data: bytes) -> str:
        """Decompress data if needed"""
        if data.startswith(b'compressed:'):
            return gzip.decompress(data[11:]).decode('utf-8')
        return data.decode('utf-8') if isinstance(data, bytes) else data
    
    async def _get_pending_orders_optimized(self) -> List[str]:
        """Get pending orders using Redis pipeline for better performance"""
        pipeline = self.redis_client.pipeline()
        
        # Use pipeline to get all pending orders and their data in one operation
        pipeline.smembers(REDIS_PENDING_SET)
        
        results = pipeline.execute()
        order_ids = []
        
        for order_id in results[0]:
            if isinstance(order_id, bytes):
                order_id = order_id.decode('utf-8')
            order_ids.append(order_id)
        
        self.metrics['pipeline_ops'] += 1
        return order_ids[:BATCH_SIZE]  # Limit batch size
    
    async def _bulk_fetch_order_data(self, order_ids: List[str]) -> Dict[str, Dict]:
        """Fetch multiple order data using Redis pipeline for maximum efficiency"""
        if not order_ids:
            return {}
        
        pipeline = self.redis_client.pipeline()
        
        # Batch fetch all order data
        for order_id in order_ids:
            order_key = f"{REDIS_ORDER_PREFIX}{order_id}"
            changelog_key = f"{REDIS_CHANGELOG_PREFIX}{order_id}"
            pipeline.hgetall(order_key)
            pipeline.hgetall(changelog_key)  # Get changelog for partial updates
        
        results = pipeline.execute()
        orders_data = {}
        
        # Process results in pairs (order_data, changelog_data)
        for i, order_id in enumerate(order_ids):
            order_data = results[i * 2]
            changelog_data = results[i * 2 + 1]
            
            if order_data:
                orders_data[order_id] = {
                    'data': order_data,
                    'changelog': changelog_data or {}
                }
        
        self.metrics['pipeline_ops'] += 1
        return orders_data
    
    def _convert_redis_to_db_fields_optimized(self, redis_data: Dict[str, Any], changelog: Dict[str, Any] = None) -> Dict[str, Any]:
        """Optimized field conversion with partial update support"""
        converted = {}
        
        # If we have changelog, only process changed fields
        if changelog:
            changed_fields = set(changelog.keys())
        else:
            changed_fields = set(redis_data.keys())
        
        # Decode bytes to strings efficiently
        decoded_data = {}
        for key, value in redis_data.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            decoded_data[key] = value
        
        # Only process changed fields for efficiency
        string_fields = {'id', 'user_id', 'symbol', 'exchange', 'broker_order_id', 
                        'status_message', 'variety', 'notes'}
        for field in string_fields.intersection(changed_fields):
            if field in decoded_data:
                converted[field] = decoded_data[field]
        
        # Integer fields
        int_fields = {'quantity', 'filled_quantity'}
        for field in int_fields.intersection(changed_fields):
            if field in decoded_data:
                try:
                    converted[field] = int(decoded_data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid integer value for {field}: {decoded_data[field]}")
        
        # Float fields
        float_fields = {'price', 'trigger_price', 'average_price'}
        for field in float_fields.intersection(changed_fields):
            if field in decoded_data:
                try:
                    converted[field] = float(decoded_data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid float value for {field}: {decoded_data[field]}")
        
        # Enum fields
        enum_mappings = {
            'side': OrderSide,
            'order_type': OrderType,
            'product_type': ProductType,
            'status': OrderStatus
        }
        
        for field, enum_class in enum_mappings.items():
            if field in changed_fields and field in decoded_data:
                try:
                    converted[field] = enum_class(decoded_data[field])
                except ValueError:
                    logger.warning(f"Invalid {enum_class.__name__}: {decoded_data[field]}")
        
        # DateTime fields
        datetime_fields = {'placed_at', 'executed_at', 'cancelled_at', 'created_at', 'updated_at'}
        for field in datetime_fields.intersection(changed_fields):
            if field in decoded_data:
                try:
                    converted[field] = datetime.fromisoformat(decoded_data[field].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid datetime value for {field}: {decoded_data[field]}")
        
        return converted
    
    async def _bulk_sync_orders(self, orders_data: Dict[str, Dict]) -> int:
        """Bulk sync orders with optimized database operations"""
        if not orders_data:
            return 0
        
        synced_count = 0
        batch_updates = []
        batch_inserts = []
        
        async with self.db_manager.get_async_session() as session:
            # First, check which orders exist (bulk query)
            order_ids = list(orders_data.keys())
            existing_orders = await session.execute(
                select(Order.id).where(Order.id.in_(order_ids))
            )
            existing_ids = {row.id for row in existing_orders}
            
            for order_id, order_info in orders_data.items():
                try:
                    order_data = order_info['data']
                    changelog = order_info['changelog']
                    
                    converted_data = self._convert_redis_to_db_fields_optimized(order_data, changelog)
                    
                    if not converted_data:
                        continue
                    
                    if order_id in existing_ids:
                        # Prepare for bulk update
                        converted_data['id'] = order_id
                        batch_updates.append(converted_data)
                    else:
                        # Prepare for bulk insert
                        self._set_required_defaults(converted_data, order_id)
                        batch_inserts.append(converted_data)
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to prepare order {order_id}: {e}")
                    continue
            
            # Execute bulk operations
            try:
                if batch_updates:
                    await session.execute(
                        update(Order),
                        batch_updates
                    )
                
                if batch_inserts:
                    session.add_all([Order(**data) for data in batch_inserts])
                
                await session.commit()
                
                # Clear from Redis using pipeline
                pipeline = self.redis_client.pipeline()
                for order_id in orders_data.keys():
                    pipeline.srem(REDIS_PENDING_SET, order_id)
                    pipeline.delete(f"{REDIS_CHANGELOG_PREFIX}{order_id}")
                pipeline.execute()
                
                logger.info(f"✅ Bulk synced {synced_count} orders ({len(batch_updates)} updates, {len(batch_inserts)} inserts)")
                
            except SQLAlchemyError as e:
                logger.error(f"❌ Failed to commit order batch: {e}")
                await session.rollback()
                synced_count = 0
        
        return synced_count
    
    def _set_required_defaults(self, converted_data: Dict[str, Any], order_id: str):
        """Set required defaults for new orders"""
        if 'id' not in converted_data:
            converted_data['id'] = order_id
        
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
    
    def _update_metrics(self, sync_time: float, batch_size: int):
        """Update performance metrics"""
        self.sync_times.append(sync_time)
        if len(self.sync_times) > 100:  # Keep last 100 measurements
            self.sync_times = self.sync_times[-100:]
        
        self.metrics['total_processed'] += batch_size
        self.metrics['avg_sync_time'] = sum(self.sync_times) / len(self.sync_times)
        self.metrics['avg_batch_size'] = (self.metrics['avg_batch_size'] * 0.9) + (batch_size * 0.1)
    
    async def run_optimized_sync_worker(self):
        """Main optimized sync worker loop"""
        logger.info("🚀 Starting OPTIMIZED DB sync worker (High Performance Mode)")
        
        while True:
            try:
                start_time = time.time()
                
                # Get pending orders efficiently
                order_ids = await self._get_pending_orders_optimized()
                
                if order_ids:
                    # Bulk fetch order data
                    orders_data = await self._bulk_fetch_order_data(order_ids)
                    
                    # Bulk sync to database
                    synced = await self._bulk_sync_orders(orders_data)
                    self.total_synced += synced
                    
                    processing_time = time.time() - start_time
                    self._update_metrics(processing_time, len(order_ids))
                    
                    if synced > 0:
                        logger.info(f"📊 Optimized Sync: {synced} orders in {processing_time:.3f}s | "
                                  f"Total: {self.total_synced} | "
                                  f"Avg: {self.metrics['avg_sync_time']:.3f}s | "
                                  f"Pipeline ops: {self.metrics['pipeline_ops']}")
                    
                    # Adaptive interval based on load and performance
                    next_interval = self._adaptive_sync_interval(len(order_ids), processing_time)
                else:
                    # No pending orders, use base interval
                    next_interval = self.current_interval
                
                await asyncio.sleep(next_interval)
                
            except Exception as e:
                logger.error(f"❌ Optimized sync worker error: {e}")
                self.metrics['total_errors'] += 1
                await asyncio.sleep(BASE_SYNC_INTERVAL * 2)

# Factory function to create optimized worker
async def optimized_db_sync_worker():
    """Factory function to create and run optimized DB sync worker"""
    worker = OptimizedDBSyncWorker()
    await worker.run_optimized_sync_worker() 