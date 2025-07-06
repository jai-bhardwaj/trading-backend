"""
Performance Optimization Module
Provides connection pooling, caching strategies, and performance monitoring
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import redis.asyncio as redis
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ConnectionPool:
    """Optimized connection pooling"""
    
    def __init__(self, pool_size: int = 10, max_overflow: int = 20):
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.active_connections = 0
        self.connection_pool = asyncio.Queue(maxsize=pool_size + max_overflow)
    
    async def get_connection(self) -> Any:
        """Get connection from pool"""
        try:
            if self.active_connections < self.pool_size:
                self.active_connections += 1
                return await self._create_connection()
            else:
                return await self.connection_pool.get()
        except asyncio.QueueEmpty:
            if self.active_connections < self.pool_size + self.max_overflow:
                self.active_connections += 1
                return await self._create_connection()
            else:
                raise Exception("Connection pool exhausted")
    
    async def return_connection(self, connection: Any):
        """Return connection to pool"""
        try:
            self.connection_pool.put_nowait(connection)
        except asyncio.QueueFull:
            await self._close_connection(connection)
            self.active_connections -= 1
    
    async def _create_connection(self) -> Any:
        """Create new connection - override in subclasses"""
        raise NotImplementedError
    
    async def _close_connection(self, connection: Any):
        """Close connection - override in subclasses"""
        raise NotImplementedError

class CacheManager:
    """Advanced caching with multiple strategies"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.local_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0}
    
    async def get_or_set(self, key: str, fetch_func: Callable, ttl: int = 300) -> Any:
        """Get from cache or fetch and store"""
        # Try local cache first
        if key in self.local_cache:
            data, timestamp = self.local_cache[key]
            if time.time() - timestamp < 60:  # 1 minute local cache
                self.cache_stats["hits"] += 1
                return data
        
        # Try Redis cache
        cached_data = await self.redis_client.get(key)
        if cached_data:
            self.cache_stats["hits"] += 1
            data = self._deserialize(cached_data)
            self.local_cache[key] = (data, time.time())
            return data
        
        # Fetch fresh data
        self.cache_stats["misses"] += 1
        data = await fetch_func()
        
        # Store in both caches
        await self.redis_client.setex(key, ttl, self._serialize(data))
        self.local_cache[key] = (data, time.time())
        
        return data
    
    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        keys = await self.redis_client.keys(pattern)
        if keys:
            await self.redis_client.delete(*keys)
        
        # Clear local cache entries
        for key in list(self.local_cache.keys()):
            if pattern.replace("*", "") in key:
                del self.local_cache[key]
    
    def _serialize(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        import json
        return json.dumps(data)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize data from Redis storage"""
        import json
        return json.loads(data)
    
    def get_stats(self) -> Dict:
        """Get cache performance statistics"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total if total > 0 else 0
        
        return {
            **self.cache_stats,
            "hit_rate": hit_rate,
            "local_cache_size": len(self.local_cache)
        }

class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def record_metric(self, name: str, value: float, tags: Dict = None):
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        metric = {
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        }
        self.metrics[name].append(metric)
        
        # Keep only last 1000 metrics
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_system_metrics(self) -> Dict:
        """Get current system performance metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "disk_percent": disk.percent,
            "disk_free": disk.free,
            "uptime": time.time() - self.start_time
        }
    
    def get_metric_stats(self, name: str) -> Dict:
        """Get statistics for a specific metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = [m["value"] for m in self.metrics[name]]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else 0
        }
    
    def get_all_metrics(self) -> Dict:
        """Get all collected metrics"""
        return {
            "system": self.get_system_metrics(),
            "metrics": {name: self.get_metric_stats(name) for name in self.metrics.keys()}
        }

class AsyncOptimizer:
    """Async operation optimization utilities"""
    
    @staticmethod
    async def batch_process(items: list, process_func: Callable, batch_size: int = 10):
        """Process items in batches for better performance"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [process_func(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    @staticmethod
    async def with_timeout(func: Callable, timeout: float = 30.0):
        """Execute function with timeout"""
        try:
            return await asyncio.wait_for(func, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Function timed out after {timeout} seconds")
            raise
    
    @staticmethod
    def async_retry(max_retries: int = 3, delay: float = 1.0):
        """Decorator for async retry logic"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt == max_retries:
                            raise last_exception
                        
                        await asyncio.sleep(delay * (2 ** attempt))
                
                raise last_exception
            return wrapper
        return decorator

class DatabaseOptimizer:
    """Database performance optimization"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.query_cache = {}
        self.query_stats = {}
    
    async def execute_batch(self, queries: list) -> list:
        """Execute multiple queries in batch"""
        async with self.db_pool.acquire() as conn:
            results = []
            for query, params in queries:
                start_time = time.time()
                result = await conn.execute(query, *params)
                execution_time = time.time() - start_time
                
                self._record_query_stats(query, execution_time)
                results.append(result)
            
            return results
    
    async def execute_with_cache(self, query: str, params: tuple, ttl: int = 300):
        """Execute query with result caching"""
        cache_key = f"query:{hash(query + str(params))}"
        
        # Try cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Execute query
        start_time = time.time()
        async with self.db_pool.acquire() as conn:
            result = await conn.fetch(query, *params)
        execution_time = time.time() - start_time
        
        self._record_query_stats(query, execution_time)
        
        # Cache result
        await self._cache_result(cache_key, result, ttl)
        
        return result
    
    def _record_query_stats(self, query: str, execution_time: float):
        """Record query performance statistics"""
        if query not in self.query_stats:
            self.query_stats[query] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "min_time": float('inf'),
                "max_time": 0
            }
        
        stats = self.query_stats[query]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)
    
    async def _get_cached_result(self, cache_key: str):
        """Get cached query result"""
        # Implementation depends on your cache system
        pass
    
    async def _cache_result(self, cache_key: str, result: Any, ttl: int):
        """Cache query result"""
        # Implementation depends on your cache system
        pass
    
    def get_query_stats(self) -> Dict:
        """Get query performance statistics"""
        return self.query_stats

# Performance decorators
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record metric
                monitor = PerformanceMonitor()
                monitor.record_metric(metric_name, execution_time)
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Record error metric
                monitor = PerformanceMonitor()
                monitor.record_metric(f"{metric_name}_error", execution_time)
                
                raise e
        return wrapper
    return decorator

def cache_result(ttl: int = 300):
    """Decorator to cache function results"""
    def decorator(func):
        cache_manager = None
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal cache_manager
            if cache_manager is None:
                # Initialize cache manager (you'll need to pass redis client)
                pass
            
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            return await cache_manager.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl
            )
        return wrapper
    return decorator 