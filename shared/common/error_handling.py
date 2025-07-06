"""
Error Handling and Resilience Module
Provides circuit breakers, retry mechanisms, and graceful degradation
"""

import asyncio
import logging
import time
from typing import Callable, Any, Optional, Dict
from functools import wraps
from enum import Enum
import httpx

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker pattern for service calls"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker reset to CLOSED")
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

class RetryHandler:
    """Retry mechanism with exponential backoff"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded")
                    raise last_exception
                
                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        raise last_exception

class GracefulDegradation:
    """Graceful degradation for service failures"""
    
    def __init__(self, fallback_func: Optional[Callable] = None):
        self.fallback_func = fallback_func
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with graceful degradation"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed, using fallback: {e}")
            if self.fallback_func:
                return await self.fallback_func(*args, **kwargs)
            raise e

class ServiceHealthMonitor:
    """Monitor service health and performance"""
    
    def __init__(self):
        self.health_checks = {}
        self.performance_metrics = {}
    
    async def check_service_health(self, service_name: str, health_url: str) -> Dict:
        """Check service health with timeout"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                response_time = time.time() - start_time
                
                is_healthy = response.status_code == 200
                
                self.health_checks[service_name] = {
                    "healthy": is_healthy,
                    "response_time": response_time,
                    "last_check": time.time(),
                    "status_code": response.status_code
                }
                
                return self.health_checks[service_name]
                
        except Exception as e:
            response_time = time.time() - start_time
            self.health_checks[service_name] = {
                "healthy": False,
                "response_time": response_time,
                "last_check": time.time(),
                "error": str(e)
            }
            return self.health_checks[service_name]
    
    def get_service_status(self, service_name: str) -> Optional[Dict]:
        """Get cached service status"""
        return self.health_checks.get(service_name)
    
    def get_all_services_status(self) -> Dict:
        """Get status of all monitored services"""
        return self.health_checks

# Decorators for easy use
def with_circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """Decorator to add circuit breaker to function"""
    def decorator(func):
        circuit_breaker = CircuitBreaker(failure_threshold, recovery_timeout)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to add retry logic to function"""
    def decorator(func):
        retry_handler = RetryHandler(max_retries, base_delay)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_handler.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator

def with_graceful_degradation(fallback_func: Optional[Callable] = None):
    """Decorator to add graceful degradation to function"""
    def decorator(func):
        degradation = GracefulDegradation(fallback_func)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await degradation.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator 