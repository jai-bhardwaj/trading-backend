"""
Enterprise User Strategy Cache
High-performance, scalable user strategy mapping
Redis-based for sub-millisecond lookups
"""

import asyncio
import logging
import redis.asyncio as redis
import json
from typing import Set, List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import msgpack  # Faster than JSON for binary data
import os
import time

logger = logging.getLogger(__name__)

@dataclass
class UserStrategyMapping:
    """User strategy configuration"""
    user_id: str
    strategy_id: str
    enabled: bool
    quantity_multiplier: float = 1.0  # User-specific quantity scaling
    max_position_size: Optional[float] = None
    risk_multiplier: float = 1.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

class CacheManager:
    """Unified cache management with Redis fallback to in-memory"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.use_redis = False
        
        try:
            # Use synchronous Redis client
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection synchronously
            self.redis_client.ping()
            self.use_redis = True
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            logger.info("📝 Falling back to in-memory cache")
            self.use_redis = False
            # Don't raise exception, just use memory cache
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis and self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return self.memory_cache.get(key)
        return None
    
    def set(self, key: str, value: Any, expire_seconds: int = 3600):
        """Set value in cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.setex(key, expire_seconds, json.dumps(value))
            else:
                # Store in memory with expiry timestamp
                self.memory_cache[key] = {
                    'value': value,
                    'expires': time.time() + expire_seconds
                }
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            # Always fallback to memory cache
            self.memory_cache[key] = {
                'value': value,
                'expires': time.time() + expire_seconds
            }
            return False
    
    def delete(self, key: str):
        """Delete value from cache"""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)
            self.memory_cache.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    def cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self.memory_cache.items():
            if isinstance(data, dict) and 'expires' in data:
                if current_time > data['expires']:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

class EnterpriseUserStrategyCache:
    """
    Lightning-fast user strategy lookup system
    Optimized for 500+ users, 100+ strategies
    Sub-millisecond response times
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        self.redis_url = redis_url
        self.redis_pool = None
        self.redis_client = None
        
        # Cache keys
        self.STRATEGY_USERS_KEY = "strategy_users:{strategy_id}"  # Set of user_ids
        self.USER_STRATEGIES_KEY = "user_strategies:{user_id}"    # Set of strategy_ids  
        self.USER_CONFIG_KEY = "user_config:{user_id}:{strategy_id}"  # User-specific config
        self.CACHE_VERSION_KEY = "cache_version"
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_lookups = 0
        
        # Auto-refresh settings
        self.auto_refresh_interval = 300  # 5 minutes
        self.cache_version = 1
        
        # Cache manager
        self.cache_manager = CacheManager()
        
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            # Use async Redis client
            import redis.asyncio as aioredis
            
            self.redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis async connection established")
            
            # Initialize cache version
            current_version = await self.redis_client.get(self.CACHE_VERSION_KEY)
            if current_version:
                self.cache_version = int(current_version)
            else:
                await self.redis_client.set(self.CACHE_VERSION_KEY, self.cache_version)
            
            # Start auto-refresh task
            asyncio.create_task(self._auto_refresh_task())
            
        except Exception as e:
            logger.warning(f"⚠️ Redis async initialization failed: {e}")
            logger.info("📝 Using fallback cache manager")
            # Don't raise exception, system can work without Redis
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
        logger.info("🔍 User Strategy Cache shutdown complete")
    
    async def get_strategy_users(self, strategy_id: str) -> Set[str]:
        """
        LIGHTNING FAST: Get all users with strategy enabled
        Optimized for signal fanout - this is called most frequently
        """
        self.total_lookups += 1
        
        try:
            cache_key = self.STRATEGY_USERS_KEY.format(strategy_id=strategy_id)
            
            # Redis SET operations are O(1) for membership, O(N) for all members
            user_ids = await self.redis_client.smembers(cache_key)
            
            if user_ids:
                self.cache_hits += 1
                return set(user_ids)
            else:
                self.cache_misses += 1
                # Fallback to database if cache miss
                return await self._fallback_db_lookup(strategy_id)
                
        except Exception as e:
            logger.error(f"❌ Cache lookup failed for strategy {strategy_id}: {e}")
            return await self._fallback_db_lookup(strategy_id)
    
    async def get_user_strategies(self, user_id: str) -> Set[str]:
        """Get all strategies enabled for a user"""
        try:
            cache_key = self.USER_STRATEGIES_KEY.format(user_id=user_id)
            strategy_ids = await self.redis_client.smembers(cache_key)
            return set(strategy_ids) if strategy_ids else set()
            
        except Exception as e:
            logger.error(f"❌ Error getting user strategies for {user_id}: {e}")
            return set()
    
    async def get_user_strategy_config(self, user_id: str, strategy_id: str) -> Optional[UserStrategyMapping]:
        """Get user-specific strategy configuration"""
        try:
            cache_key = self.USER_CONFIG_KEY.format(user_id=user_id, strategy_id=strategy_id)
            config_data = await self.redis_client.get(cache_key)
            
            if config_data:
                # Using msgpack for faster deserialization
                data = msgpack.unpackb(config_data.encode('latin1'), strict_map_key=False)
                return UserStrategyMapping(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user config {user_id}:{strategy_id}: {e}")
            return None
    
    async def enable_strategy_for_user(self, user_id: str, strategy_id: str, 
                                     config: Optional[UserStrategyMapping] = None):
        """Enable strategy for user with optional configuration"""
        try:
            async with self.redis_client.pipeline() as pipe:
                # Add user to strategy's user set
                strategy_users_key = self.STRATEGY_USERS_KEY.format(strategy_id=strategy_id)
                pipe.sadd(strategy_users_key, user_id)
                
                # Add strategy to user's strategy set  
                user_strategies_key = self.USER_STRATEGIES_KEY.format(user_id=user_id)
                pipe.sadd(user_strategies_key, strategy_id)
                
                # Store user-specific configuration
                if config is None:
                    config = UserStrategyMapping(
                        user_id=user_id,
                        strategy_id=strategy_id,
                        enabled=True
                    )
                
                config_key = self.USER_CONFIG_KEY.format(user_id=user_id, strategy_id=strategy_id)
                config_data = msgpack.packb(asdict(config), use_bin_type=True)
                pipe.set(config_key, config_data.decode('latin1'))
                
                # Set expiry for cleanup (7 days)
                pipe.expire(strategy_users_key, 604800)
                pipe.expire(user_strategies_key, 604800)
                pipe.expire(config_key, 604800)
                
                await pipe.execute()
            
            logger.info(f"✅ Enabled strategy {strategy_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error enabling strategy for user: {e}")
            raise
    
    async def disable_strategy_for_user(self, user_id: str, strategy_id: str):
        """Disable strategy for user"""
        try:
            async with self.redis_client.pipeline() as pipe:
                # Remove user from strategy's user set
                strategy_users_key = self.STRATEGY_USERS_KEY.format(strategy_id=strategy_id)
                pipe.srem(strategy_users_key, user_id)
                
                # Remove strategy from user's strategy set
                user_strategies_key = self.USER_STRATEGIES_KEY.format(user_id=user_id)
                pipe.srem(user_strategies_key, strategy_id)
                
                # Remove user-specific configuration
                config_key = self.USER_CONFIG_KEY.format(user_id=user_id, strategy_id=strategy_id)
                pipe.delete(config_key)
                
                await pipe.execute()
            
            logger.info(f"✅ Disabled strategy {strategy_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error disabling strategy for user: {e}")
            raise
    
    async def bulk_update_user_strategies(self, updates: List[Dict[str, Any]]):
        """Bulk update user strategy mappings for efficiency"""
        try:
            async with self.redis_client.pipeline() as pipe:
                
                for update in updates:
                    user_id = update['user_id']
                    strategy_id = update['strategy_id']
                    enabled = update['enabled']
                    config = update.get('config')
                    
                    strategy_users_key = self.STRATEGY_USERS_KEY.format(strategy_id=strategy_id)
                    user_strategies_key = self.USER_STRATEGIES_KEY.format(user_id=user_id)
                    
                    if enabled:
                        pipe.sadd(strategy_users_key, user_id)
                        pipe.sadd(user_strategies_key, strategy_id)
                        
                        if config:
                            config_key = self.USER_CONFIG_KEY.format(user_id=user_id, strategy_id=strategy_id)
                            config_data = msgpack.packb(config, use_bin_type=True)
                            pipe.set(config_key, config_data.decode('latin1'))
                    else:
                        pipe.srem(strategy_users_key, user_id)
                        pipe.srem(user_strategies_key, strategy_id)
                        config_key = self.USER_CONFIG_KEY.format(user_id=user_id, strategy_id=strategy_id)
                        pipe.delete(config_key)
                
                await pipe.execute()
            
            logger.info(f"✅ Bulk updated {len(updates)} user strategy mappings")
            
        except Exception as e:
            logger.error(f"❌ Bulk update failed: {e}")
            raise
    
    async def refresh_from_database(self):
        """Refresh cache from database - call this when user settings change"""
        try:
            logger.info("🔄 Refreshing user strategy cache from database...")
            
            # Refresh from actual PostgreSQL database
            await self._refresh_from_database()
            
            # Increment cache version
            self.cache_version += 1
            await self.redis_client.set(self.CACHE_VERSION_KEY, self.cache_version)
            
            logger.info(f"✅ Cache refresh complete (version {self.cache_version})")
            
        except Exception as e:
            logger.error(f"❌ Cache refresh failed: {e}")
    
    async def _refresh_from_database(self):
        """Refresh cache from PostgreSQL database"""
        try:
            # Import database connection (assuming you have asyncpg setup)
            import asyncpg
            from config.database import get_database_url
            
            conn = await asyncpg.connect(get_database_url())
            
            # Query user_strategies table
            query = """
                SELECT us.user_id, us.strategy_id, us.enabled, us.quantity_multiplier, 
                       us.max_position_size, us.risk_multiplier, us.updated_at
                FROM user_strategies us
                INNER JOIN users u ON us.user_id = u.user_id 
                WHERE u.active = true AND u.trading_enabled = true
            """
            
            rows = await conn.fetch(query)
            await conn.close()
            
            # Convert to update format
            updates = []
            for row in rows:
                config = None
                if row['quantity_multiplier'] != 1.0 or row['max_position_size'] or row['risk_multiplier'] != 1.0:
                    config = {
                        'user_id': row['user_id'],
                        'strategy_id': row['strategy_id'],
                        'enabled': row['enabled'],
                        'quantity_multiplier': float(row['quantity_multiplier']),
                        'max_position_size': float(row['max_position_size']) if row['max_position_size'] else None,
                        'risk_multiplier': float(row['risk_multiplier']),
                        'last_updated': row['updated_at']
                    }
                
                updates.append({
                    'user_id': row['user_id'],
                    'strategy_id': row['strategy_id'],
                    'enabled': row['enabled'],
                    'config': config
                })
            
            # Bulk update cache
            await self.bulk_update_user_strategies(updates)
            
            logger.info(f"✅ Refreshed {len(updates)} user strategy mappings from database")
            
        except Exception as e:
            logger.error(f"❌ Database refresh failed: {e}")
            raise
    
    async def _fallback_db_lookup(self, strategy_id: str) -> Set[str]:
        """Fallback to database when cache misses"""
        try:
            logger.warning(f"⚠️ Cache miss for strategy {strategy_id}, querying database directly")
            
            import asyncpg
            from config.database import get_database_url
            
            conn = await asyncpg.connect(get_database_url())
            
            # Direct database query for this strategy
            query = """
                SELECT DISTINCT us.user_id
                FROM user_strategies us
                INNER JOIN users u ON us.user_id = u.user_id
                WHERE us.strategy_id = $1 AND us.enabled = true 
                  AND u.active = true AND u.trading_enabled = true
            """
            
            rows = await conn.fetch(query, strategy_id)
            await conn.close()
            
            user_ids = {row['user_id'] for row in rows}
            
            # Update cache for this strategy
            if user_ids:
                cache_key = self.STRATEGY_USERS_KEY.format(strategy_id=strategy_id)
                await self.redis_client.sadd(cache_key, *user_ids)
                await self.redis_client.expire(cache_key, 300)  # 5 min expiry
            
            logger.info(f"✅ Fallback lookup found {len(user_ids)} users for strategy {strategy_id}")
            return user_ids
            
        except Exception as e:
            logger.error(f"❌ Fallback database lookup failed: {e}")
            return set()
    
    async def _auto_refresh_task(self):
        """Background task to auto-refresh cache"""
        while True:
            try:
                await asyncio.sleep(self.auto_refresh_interval)
                await self.refresh_from_database()
            except Exception as e:
                logger.error(f"❌ Auto-refresh failed: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        cache_hit_rate = (self.cache_hits / self.total_lookups * 100) if self.total_lookups > 0 else 0
        
        # Get Redis memory usage
        redis_info = await self.redis_client.info('memory')
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_lookups': self.total_lookups,
            'hit_rate_percent': round(cache_hit_rate, 2),
            'cache_version': self.cache_version,
            'redis_memory_used': redis_info.get('used_memory_human', 'unknown'),
            'redis_connected_clients': redis_info.get('connected_clients', 0)
        }
    
    async def clear_cache(self):
        """Clear all cache data (use with caution)"""
        try:
            # Delete all our cache keys
            pattern_keys = [
                "strategy_users:*",
                "user_strategies:*", 
                "user_config:*",
                self.CACHE_VERSION_KEY
            ]
            
            for pattern in pattern_keys:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            # Reset counters
            self.cache_hits = 0
            self.cache_misses = 0
            self.total_lookups = 0
            
            logger.info("✅ Cache cleared successfully")
            
        except Exception as e:
            logger.error(f"❌ Cache clear failed: {e}")
            raise

# Global cache instance
_user_strategy_cache = None

async def get_user_strategy_cache() -> EnterpriseUserStrategyCache:
    """Get global cache instance"""
    global _user_strategy_cache
    if _user_strategy_cache is None:
        _user_strategy_cache = EnterpriseUserStrategyCache()
        await _user_strategy_cache.initialize()
    return _user_strategy_cache 