import asyncio
import redis
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RedisOptimizer:
    """Redis optimization utilities for high-performance trading operations"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.pipeline_cache = {}
        self.batch_operations = []
        self.last_pipeline_flush = datetime.now()
        self.stats = {
            'pipeline_operations': 0,
            'batch_operations': 0,
            'memory_optimizations': 0
        }
    
    def get_pipeline(self, transaction=True):
        """Get a Redis pipeline for batch operations"""
        return self.redis_client.pipeline(transaction=transaction)
    
    async def batch_hash_operations(self, operations: List[Dict[str, Any]], max_batch_size: int = 100):
        """Batch multiple hash operations for better performance"""
        results = []
        
        for i in range(0, len(operations), max_batch_size):
            batch = operations[i:i + max_batch_size]
            
            pipeline = self.get_pipeline()
            for op in batch:
                op_type = op['type']
                key = op['key']
                
                if op_type == 'hset':
                    pipeline.hset(key, mapping=op['data'])
                elif op_type == 'hget':
                    pipeline.hget(key, op['field'])
                elif op_type == 'hgetall':
                    pipeline.hgetall(key)
                elif op_type == 'hdel':
                    pipeline.hdel(key, *op['fields'])
            
            batch_results = pipeline.execute()
            results.extend(batch_results)
            self.stats['pipeline_operations'] += 1
        
        self.stats['batch_operations'] += len(operations)
        return results
    
    def compress_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress order data to reduce Redis memory usage"""
        compressed = {}
        
        # Use shorter field names to save memory
        field_mapping = {
            'order_id': 'oid',
            'user_id': 'uid',
            'symbol': 'sym',
            'exchange': 'ex',
            'order_type': 'ot',
            'product_type': 'pt',
            'quantity': 'qty',
            'price': 'px',
            'status': 'st',
            'created_at': 'cat',
            'updated_at': 'uat'
        }
        
        for long_name, short_name in field_mapping.items():
            if long_name in order_data:
                value = order_data[long_name]
                
                # Convert datetime to timestamp for space efficiency
                if isinstance(value, datetime):
                    compressed[short_name] = int(value.timestamp())
                # Convert enums to string codes
                elif hasattr(value, 'value'):
                    compressed[short_name] = value.value
                else:
                    compressed[short_name] = value
        
        self.stats['memory_optimizations'] += 1
        return compressed
    
    def decompress_order_data(self, compressed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decompress order data back to original format"""
        field_mapping = {
            'oid': 'order_id',
            'uid': 'user_id',
            'sym': 'symbol',
            'ex': 'exchange',
            'ot': 'order_type',
            'pt': 'product_type',
            'qty': 'quantity',
            'px': 'price',
            'st': 'status',
            'cat': 'created_at',
            'uat': 'updated_at'
        }
        
        decompressed = {}
        for short_name, long_name in field_mapping.items():
            if short_name in compressed_data:
                value = compressed_data[short_name]
                
                # Convert timestamp back to datetime
                if long_name in ['created_at', 'updated_at'] and isinstance(value, (int, float)):
                    decompressed[long_name] = datetime.fromtimestamp(value)
                else:
                    decompressed[long_name] = value
        
        return decompressed
    
    async def optimized_multi_get(self, keys: List[str], key_prefix: str = "") -> Dict[str, Any]:
        """Get multiple keys efficiently using pipeline"""
        if not keys:
            return {}
        
        full_keys = [f"{key_prefix}{key}" for key in keys] if key_prefix else keys
        
        pipeline = self.get_pipeline()
        for key in full_keys:
            pipeline.hgetall(key)
        
        results = pipeline.execute()
        self.stats['pipeline_operations'] += 1
        
        # Combine results with original keys
        result_dict = {}
        for i, key in enumerate(keys):
            if results[i]:
                result_dict[key] = results[i]
        
        return result_dict
    
    async def optimized_multi_set(self, data: Dict[str, Dict[str, Any]], key_prefix: str = "") -> bool:
        """Set multiple hash keys efficiently using pipeline"""
        if not data:
            return True
        
        try:
            pipeline = self.get_pipeline()
            for key, value in data.items():
                full_key = f"{key_prefix}{key}" if key_prefix else key
                pipeline.hset(full_key, mapping=value)
            
            pipeline.execute()
            self.stats['pipeline_operations'] += 1
            return True
        except Exception as e:
            logger.error(f"Bulk set operation failed: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get Redis optimization performance statistics"""
        return {
            'pipeline_operations': self.stats['pipeline_operations'],
            'batch_operations': self.stats['batch_operations'],
            'memory_optimizations': self.stats['memory_optimizations'],
            'avg_ops_per_pipeline': (
                self.stats['batch_operations'] / max(1, self.stats['pipeline_operations'])
            )
        }

class RedisConnectionPool:
    """Optimized Redis connection pool for high-concurrency trading"""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 max_connections: int = 50,
                 decode_responses: bool = True):
        
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            max_connections=max_connections,
            decode_responses=decode_responses,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30
        )
        
        self.client = redis.Redis(connection_pool=self.pool)
        self.optimizer = RedisOptimizer(self.client)
        
        logger.info(f"✅ Redis connection pool initialized: {max_connections} max connections")
    
    def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        return self.client
    
    def get_optimizer(self) -> RedisOptimizer:
        """Get Redis optimizer instance"""
        return self.optimizer
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        try:
            available = len(self.pool._available_connections) if hasattr(self.pool, '_available_connections') else 0
            in_use = len(self.pool._in_use_connections) if hasattr(self.pool, '_in_use_connections') else 0
            created = getattr(self.pool, '_created_connections', 0)
            if hasattr(created, '__len__'):
                created = len(created)
        except:
            available = in_use = created = 0
        
        return {
            'max_connections': self.pool.max_connections,
            'created_connections': created,
            'available_connections': available,
            'in_use_connections': in_use
        }
    
    def close(self):
        """Close connection pool"""
        self.pool.disconnect()
        logger.info("🔒 Redis connection pool closed")

# Global optimized Redis instance
_redis_pool: Optional[RedisConnectionPool] = None

def get_optimized_redis() -> RedisConnectionPool:
    """Get the global optimized Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = RedisConnectionPool()
    return _redis_pool

def close_optimized_redis():
    """Close the global Redis connection pool"""
    global _redis_pool
    if _redis_pool:
        _redis_pool.close()
        _redis_pool = None 