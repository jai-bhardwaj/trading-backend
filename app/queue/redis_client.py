"""
Redis Client Configuration

Provides Redis connection management and configuration for the trading engine.
"""

import os
import redis
import logging
from typing import Optional
from redis.connection import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

class RedisConfig:
    """Redis configuration settings"""
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD")
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))
        self.socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", 30.0))
        self.socket_connect_timeout = float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 30.0))
        self.retry_on_timeout = True
        self.health_check_interval = 30

class RedisClient:
    """Redis client with connection pooling and health monitoring"""
    
    def __init__(self, config: Optional[RedisConfig] = None):
        self.config = config or RedisConfig()
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        
    def connect(self) -> bool:
        """Establish Redis connection"""
        try:
            # Create connection pool
            self._pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            self._is_connected = True
            
            logger.info(f"✅ Connected to Redis at {self.config.host}:{self.config.port}")
            return True
            
        except (ConnectionError, RedisTimeoutError) as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to Redis: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """Close Redis connection"""
        if self._pool:
            self._pool.disconnect()
        self._is_connected = False
        logger.info("🔌 Disconnected from Redis")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self._is_connected or not self._client:
            return False
        
        try:
            self._client.ping()
            return True
        except:
            self._is_connected = False
            return False
    
    def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self.is_connected():
            if not self.connect():
                raise ConnectionError("Unable to connect to Redis")
        
        return self._client
    
    def health_check(self) -> dict:
        """Perform Redis health check"""
        try:
            client = self.get_client()
            
            # Basic connectivity test
            ping_result = client.ping()
            
            # Get Redis info
            info = client.info()
            
            # Memory usage
            memory_used = info.get('used_memory_human', 'Unknown')
            memory_peak = info.get('used_memory_peak_human', 'Unknown')
            
            # Connection stats
            connected_clients = info.get('connected_clients', 0)
            
            return {
                'status': 'healthy' if ping_result else 'unhealthy',
                'connected': self._is_connected,
                'memory_used': memory_used,
                'memory_peak': memory_peak,
                'connected_clients': connected_clients,
                'redis_version': info.get('redis_version', 'Unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }

# Global Redis client instance
redis_config = RedisConfig()
redis_client = RedisClient(redis_config)

def get_redis_connection() -> redis.Redis:
    """Get Redis connection (convenience function)"""
    return redis_client.get_client()

def ensure_redis_connection():
    """Ensure Redis connection is established"""
    if not redis_client.is_connected():
        redis_client.connect()

# Initialize connection on import
try:
    redis_client.connect()
except Exception as e:
    logger.warning(f"⚠️ Redis not available on startup: {e}")
    logger.info("📝 Redis will be connected when first accessed") 