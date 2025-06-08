"""
Rate Limiting System for Trading Engine
Implements distributed rate limiting using Redis for API endpoints and broker calls.
"""

import asyncio
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis

from app.database import get_database_manager

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit types"""
    API_ENDPOINT = "api_endpoint"
    BROKER_API = "broker_api"
    USER_ACTION = "user_action"
    ORDER_PLACEMENT = "order_placement"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    time_window_seconds: int
    burst_allowance: int = 0  # Additional requests allowed in burst
    
    
@dataclass
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining_requests: int
    reset_time: float
    retry_after: Optional[float] = None


class RateLimiter:
    """
    Redis-based distributed rate limiter with sliding window algorithm
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.initialized = False
        
        # Default rate limit configurations
        self.default_configs = {
            RateLimitType.API_ENDPOINT: RateLimitConfig(
                max_requests=100,
                time_window_seconds=60,
                burst_allowance=20
            ),
            RateLimitType.BROKER_API: RateLimitConfig(
                max_requests=30,
                time_window_seconds=60,
                burst_allowance=5
            ),
            RateLimitType.USER_ACTION: RateLimitConfig(
                max_requests=50,
                time_window_seconds=60,
                burst_allowance=10
            ),
            RateLimitType.ORDER_PLACEMENT: RateLimitConfig(
                max_requests=10,
                time_window_seconds=60,
                burst_allowance=2
            )
        }
    
    async def initialize(self):
        """Initialize the rate limiter"""
        try:
            self.redis_client = await get_database_manager().get_redis()
            self.initialized = True
            logger.info("Rate limiter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {e}")
            raise
    
    async def check_rate_limit(
        self,
        key: str,
        limit_type: RateLimitType,
        config: Optional[RateLimitConfig] = None
    ) -> RateLimitResult:
        """
        Check if request is within rate limit
        
        Args:
            key: Unique identifier for the rate limit (e.g., user_id, api_key)
            limit_type: Type of rate limit to apply
            config: Custom rate limit configuration (optional)
            
        Returns:
            RateLimitResult: Result of rate limit check
        """
        if not self.initialized:
            await self.initialize()
        
        # Use provided config or default
        rate_config = config or self.default_configs.get(limit_type)
        if not rate_config:
            logger.warning(f"No rate limit config found for {limit_type}")
            return RateLimitResult(allowed=True, remaining_requests=1000, reset_time=time.time())
        
        # Create Redis key
        redis_key = f"rate_limit:{limit_type.value}:{key}"
        current_time = time.time()
        window_start = current_time - rate_config.time_window_seconds
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(redis_key, rate_config.time_window_seconds + 60)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Count after removing expired entries
            
            # Calculate remaining requests
            max_allowed = rate_config.max_requests + rate_config.burst_allowance
            remaining = max(0, max_allowed - current_count - 1)  # -1 for current request
            
            # Check if limit exceeded
            if current_count >= max_allowed:
                # Remove the request we just added since it's rejected
                await self.redis_client.zrem(redis_key, str(current_time))
                
                # Calculate retry after time
                retry_after = rate_config.time_window_seconds
                
                return RateLimitResult(
                    allowed=False,
                    remaining_requests=0,
                    reset_time=current_time + rate_config.time_window_seconds,
                    retry_after=retry_after
                )
            
            return RateLimitResult(
                allowed=True,
                remaining_requests=remaining,
                reset_time=current_time + rate_config.time_window_seconds
            )
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {redis_key}: {e}")
            # On error, allow the request (fail open)
            return RateLimitResult(allowed=True, remaining_requests=1000, reset_time=current_time)
    
    async def reset_rate_limit(self, key: str, limit_type: RateLimitType):
        """Reset rate limit for a specific key"""
        if not self.initialized:
            await self.initialize()
        
        redis_key = f"rate_limit:{limit_type.value}:{key}"
        try:
            await self.redis_client.delete(redis_key)
            logger.info(f"Rate limit reset for {redis_key}")
        except Exception as e:
            logger.error(f"Error resetting rate limit for {redis_key}: {e}")
    
    async def get_rate_limit_status(self, key: str, limit_type: RateLimitType) -> Dict:
        """Get current rate limit status without incrementing counter"""
        if not self.initialized:
            await self.initialize()
        
        redis_key = f"rate_limit:{limit_type.value}:{key}"
        rate_config = self.default_configs.get(limit_type)
        
        if not rate_config:
            return {"error": "No config found"}
        
        try:
            current_time = time.time()
            window_start = current_time - rate_config.time_window_seconds
            
            # Clean up expired entries and count
            await self.redis_client.zremrangebyscore(redis_key, 0, window_start)
            current_count = await self.redis_client.zcard(redis_key)
            
            max_allowed = rate_config.max_requests + rate_config.burst_allowance
            remaining = max(0, max_allowed - current_count)
            
            return {
                "current_requests": current_count,
                "max_requests": max_allowed,
                "remaining_requests": remaining,
                "reset_time": current_time + rate_config.time_window_seconds,
                "window_seconds": rate_config.time_window_seconds
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status for {redis_key}: {e}")
            return {"error": str(e)}


# Global rate limiter instance
rate_limiter = RateLimiter()


# Decorator for rate limiting functions
def rate_limit(limit_type: RateLimitType, key_func=None, config: Optional[RateLimitConfig] = None):
    """
    Decorator for rate limiting functions
    
    Args:
        limit_type: Type of rate limit to apply
        key_func: Function to extract rate limit key from function arguments
        config: Custom rate limit configuration
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract rate limit key
            if key_func:
                limit_key = key_func(*args, **kwargs)
            else:
                # Use function name as default key
                limit_key = f"{func.__module__}.{func.__name__}"
            
            # Check rate limit
            result = await rate_limiter.check_rate_limit(limit_key, limit_type, config)
            
            if not result.allowed:
                from app.brokers.base import RateLimitError
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {result.retry_after} seconds",
                    error_code="RATE_LIMIT_EXCEEDED"
                )
            
            # Execute the function
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions
async def check_api_rate_limit(user_id: str) -> RateLimitResult:
    """Check API rate limit for a user"""
    return await rate_limiter.check_rate_limit(user_id, RateLimitType.API_ENDPOINT)


async def check_order_rate_limit(user_id: str) -> RateLimitResult:
    """Check order placement rate limit for a user"""
    return await rate_limiter.check_rate_limit(user_id, RateLimitType.ORDER_PLACEMENT)


async def check_broker_rate_limit(broker_name: str) -> RateLimitResult:
    """Check broker API rate limit"""
    return await rate_limiter.check_rate_limit(broker_name, RateLimitType.BROKER_API) 