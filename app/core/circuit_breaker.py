"""Circuit breaker pattern implementation for fault tolerance."""

import asyncio
import time
import logging
from typing import Any, Callable, Dict, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls are failing
    HALF_OPEN = "half_open"  # Testing if circuit can close

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5       # Number of failures before opening
    recovery_timeout: int = 60       # Seconds to wait before attempting recovery
    expected_exception: type = Exception  # Exception type to catch
    success_threshold: int = 3       # Successful calls needed to close from half-open
    timeout: int = 30               # Timeout for individual calls
    name: str = "default"           # Circuit breaker name

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass

class CircuitBreaker:
    """Circuit breaker implementation with Redis state persistence."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.redis_client = None
        self._redis_key = f"circuit_breaker:{config.name}"
        
    async def _get_redis_client(self):
        """Get Redis client for state persistence."""
        if not self.redis_client:
            self.redis_client = redis.Redis.from_url(settings.redis_url)
        return self.redis_client
    
    async def _get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state from Redis."""
        try:
            redis_client = await self._get_redis_client()
            state_data = await redis_client.hgetall(self._redis_key)
            
            if not state_data:
                # Default state
                return {
                    "state": CircuitState.CLOSED.value,
                    "failure_count": 0,
                    "success_count": 0,
                    "last_failure_time": 0,
                    "last_success_time": 0
                }
            
            return {
                "state": state_data.get(b"state", CircuitState.CLOSED.value).decode(),
                "failure_count": int(state_data.get(b"failure_count", 0)),
                "success_count": int(state_data.get(b"success_count", 0)),
                "last_failure_time": float(state_data.get(b"last_failure_time", 0)),
                "last_success_time": float(state_data.get(b"last_success_time", 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get circuit breaker state: {e}")
            return {
                "state": CircuitState.CLOSED.value,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "last_success_time": 0
            }
    
    async def _update_state(self, state_data: Dict[str, Any]):
        """Update circuit breaker state in Redis."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.hset(self._redis_key, mapping={
                "state": state_data["state"],
                "failure_count": state_data["failure_count"],
                "success_count": state_data["success_count"],
                "last_failure_time": state_data["last_failure_time"],
                "last_success_time": state_data["last_success_time"]
            })
            # Set expiration to prevent memory leaks
            await redis_client.expire(self._redis_key, 3600 * 24)  # 24 hours
            
        except Exception as e:
            logger.error(f"Failed to update circuit breaker state: {e}")
    
    async def _should_attempt_reset(self, state_data: Dict[str, Any]) -> bool:
        """Check if we should attempt to reset the circuit."""
        if state_data["state"] != CircuitState.OPEN.value:
            return False
        
        time_since_failure = time.time() - state_data["last_failure_time"]
        return time_since_failure >= self.config.recovery_timeout
    
    async def _record_success(self, state_data: Dict[str, Any]):
        """Record a successful call."""
        state_data["success_count"] += 1
        state_data["last_success_time"] = time.time()
        
        if state_data["state"] == CircuitState.HALF_OPEN.value:
            if state_data["success_count"] >= self.config.success_threshold:
                # Close the circuit
                logger.info(f"Circuit breaker '{self.config.name}' closing - recovery successful")
                state_data["state"] = CircuitState.CLOSED.value
                state_data["failure_count"] = 0
                state_data["success_count"] = 0
        elif state_data["state"] == CircuitState.CLOSED.value:
            # Reset failure count on success
            state_data["failure_count"] = 0
        
        await self._update_state(state_data)
    
    async def _record_failure(self, state_data: Dict[str, Any], exception: Exception):
        """Record a failed call."""
        state_data["failure_count"] += 1
        state_data["last_failure_time"] = time.time()
        state_data["success_count"] = 0  # Reset success count
        
        if state_data["state"] == CircuitState.CLOSED.value:
            if state_data["failure_count"] >= self.config.failure_threshold:
                # Open the circuit
                logger.warning(f"Circuit breaker '{self.config.name}' opening - failure threshold reached")
                state_data["state"] = CircuitState.OPEN.value
        elif state_data["state"] == CircuitState.HALF_OPEN.value:
            # Go back to open state
            logger.warning(f"Circuit breaker '{self.config.name}' back to open - recovery failed")
            state_data["state"] = CircuitState.OPEN.value
        
        await self._update_state(state_data)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        state_data = await self._get_state()
        
        # Check if we should attempt reset
        if await self._should_attempt_reset(state_data):
            logger.info(f"Circuit breaker '{self.config.name}' attempting recovery")
            state_data["state"] = CircuitState.HALF_OPEN.value
            state_data["success_count"] = 0
            await self._update_state(state_data)
        
        # Check current state
        if state_data["state"] == CircuitState.OPEN.value:
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.config.name}' is open"
            )
        
        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            await self._record_success(state_data)
            return result
            
        except self.config.expected_exception as e:
            await self._record_failure(state_data, e)
            raise
        except asyncio.TimeoutError as e:
            await self._record_failure(state_data, e)
            raise
        except Exception as e:
            # Don't count unexpected exceptions as circuit breaker failures
            logger.error(f"Unexpected exception in circuit breaker: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        state_data = await self._get_state()
        return {
            "name": self.config.name,
            "state": state_data["state"],
            "failure_count": state_data["failure_count"],
            "success_count": state_data["success_count"],
            "last_failure_time": datetime.fromtimestamp(state_data["last_failure_time"]).isoformat() if state_data["last_failure_time"] > 0 else None,
            "last_success_time": datetime.fromtimestamp(state_data["last_success_time"]).isoformat() if state_data["last_success_time"] > 0 else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }
    
    async def reset(self):
        """Manually reset circuit breaker to closed state."""
        state_data = {
            "state": CircuitState.CLOSED.value,
            "failure_count": 0,
            "success_count": 0,
            "last_failure_time": 0,
            "last_success_time": time.time()
        }
        await self._update_state(state_data)
        logger.info(f"Circuit breaker '{self.config.name}' manually reset")

class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig(name=name)
            self.circuit_breakers[name] = CircuitBreaker(config)
        return self.circuit_breakers[name]
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        stats = {}
        for name, cb in self.circuit_breakers.items():
            stats[name] = await cb.get_stats()
        return stats
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self.circuit_breakers.values():
            await cb.reset()

# Global circuit breaker manager
_circuit_breaker_manager = None

def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager."""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager

# Pre-configured circuit breakers for common use cases
def get_broker_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for broker API calls."""
    config = CircuitBreakerConfig(
        name="broker_api",
        failure_threshold=3,
        recovery_timeout=120,  # 2 minutes
        timeout=30,
        success_threshold=2
    )
    return get_circuit_breaker_manager().get_circuit_breaker("broker_api", config)

def get_database_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for database calls."""
    config = CircuitBreakerConfig(
        name="database",
        failure_threshold=5,
        recovery_timeout=60,
        timeout=10,
        success_threshold=3
    )
    return get_circuit_breaker_manager().get_circuit_breaker("database", config)

def get_external_api_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for external API calls."""
    config = CircuitBreakerConfig(
        name="external_api",
        failure_threshold=3,
        recovery_timeout=180,  # 3 minutes
        timeout=15,
        success_threshold=2
    )
    return get_circuit_breaker_manager().get_circuit_breaker("external_api", config)

# Decorator for easy circuit breaker usage
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to add circuit breaker protection to async functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cb = get_circuit_breaker_manager().get_circuit_breaker(name, config)
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator 