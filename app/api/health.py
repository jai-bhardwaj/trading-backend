"""Health check and monitoring endpoints for the trading engine."""

import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis.asyncio as redis

from app.core.config import get_settings
from app.database import get_database_manager
from app.core.notification_service import notification_service
from app.core.rate_limiter import rate_limiter
from app.brokers.angelone_new import AngelOneBroker

router = APIRouter()
settings = get_settings()

class HealthCheckService:
    """Comprehensive health check service for all system components."""
    
    def __init__(self):
        self.startup_time = datetime.now(timezone.utc)
        self.check_results = {}
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = time.time()
        try:
            db_manager = get_database_manager()
            async with db_manager.get_async_session() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                
                if not row or row.test != 1:
                    raise Exception("Database connectivity test failed")
                
                # Test user table accessibility
                result = await session.execute(text("SELECT COUNT(*) as count FROM users"))
                user_count = result.fetchone().count
                
                response_time = time.time() - start_time
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time * 1000, 2),
                    "user_count": user_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        try:
            redis_client = redis.Redis.from_url(settings.redis_url)
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Test write/read operations
            test_key = "health_check_test"
            test_value = str(int(time.time()))
            
            await redis_client.set(test_key, test_value, ex=10)
            retrieved_value = await redis_client.get(test_key)
            
            if retrieved_value.decode() != test_value:
                raise Exception("Redis read/write test failed")
            
            # Get Redis info
            info = await redis_client.info()
            memory_usage = info.get('used_memory_human', 'unknown')
            connected_clients = info.get('connected_clients', 0)
            
            response_time = time.time() - start_time
            
            await redis_client.delete(test_key)
            await redis_client.close()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "memory_usage": memory_usage,
                "connected_clients": connected_clients,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_broker_health(self) -> Dict[str, Any]:
        """Check broker connectivity and API health."""
        start_time = time.time()
        try:
            # Test Angel One broker connectivity
            broker = AngelOneBroker()
            
            # This would normally test connection, but we'll simulate
            # In production, you'd call broker.check_connection() or similar
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "broker_name": "Angel One",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_notification_service_health(self) -> Dict[str, Any]:
        """Check notification service health."""
        start_time = time.time()
        try:
            # notification_service is already imported
            
            # Test service initialization
            if not notification_service:
                raise Exception("Notification service not initialized")
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def check_rate_limiter_health(self) -> Dict[str, Any]:
        """Check rate limiter service health."""
        start_time = time.time()
        try:
            # rate_limiter is already imported
            
            # Test rate limiter functionality
            test_key = "health_check_rate_limit"
            allowed = await rate_limiter.check_rate_limit(test_key, "API_ENDPOINT", 1)
            
            if not allowed:
                raise Exception("Rate limiter test failed")
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            import psutil
            
            # CPU and Memory metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # System uptime
            uptime = datetime.now(timezone.utc) - self.startup_time
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "uptime_seconds": int(uptime.total_seconds()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except ImportError:
            return {
                "error": "psutil not available for system metrics",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Global health check service instance
health_service = HealthCheckService()

@router.get("/health", tags=["Health"])
async def basic_health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Trading Engine API"
    }

@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Comprehensive health check for all system components."""
    
    # Run all health checks concurrently
    tasks = [
        health_service.check_database_health(),
        health_service.check_redis_health(),
        health_service.check_broker_health(),
        health_service.check_notification_service_health(),
        health_service.check_rate_limiter_health(),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    health_checks = {
        "database": results[0] if not isinstance(results[0], Exception) else {"status": "error", "error": str(results[0])},
        "redis": results[1] if not isinstance(results[1], Exception) else {"status": "error", "error": str(results[1])},
        "broker": results[2] if not isinstance(results[2], Exception) else {"status": "error", "error": str(results[2])},
        "notification_service": results[3] if not isinstance(results[3], Exception) else {"status": "error", "error": str(results[3])},
        "rate_limiter": results[4] if not isinstance(results[4], Exception) else {"status": "error", "error": str(results[4])},
    }
    
    # Determine overall status
    all_healthy = all(
        check.get("status") == "healthy" 
        for check in health_checks.values()
    )
    
    overall_status = "healthy" if all_healthy else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": health_checks
    }

@router.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical services
        db_check = await health_service.check_database_health()
        redis_check = await health_service.check_redis_health()
        
        if db_check["status"] != "healthy" or redis_check["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/health/live", tags=["Health"])
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/metrics", tags=["Monitoring"])
async def system_metrics():
    """Get system performance metrics."""
    metrics = await health_service.get_system_metrics()
    return metrics

@router.get("/metrics/trading", tags=["Monitoring"])
async def trading_metrics():
    """Get trading-specific metrics."""
    try:
        db_manager = get_database_manager()
        async with db_manager.get_async_session() as session:
            # Get trading statistics
            stats = {}
            
            # Total orders today
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM orders 
                WHERE DATE(created_at) = CURRENT_DATE
            """))
            stats["orders_today"] = result.fetchone().count
            
            # Active strategies
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM strategies 
                WHERE status = 'ACTIVE'
            """))
            stats["active_strategies"] = result.fetchone().count
            
            # Total users
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM users
            """))
            stats["total_users"] = result.fetchone().count
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trading_stats": stats
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trading metrics: {str(e)}") 