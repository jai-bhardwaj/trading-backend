#!/usr/bin/env python3
"""
API Gateway - Routes requests to appropriate microservices
Handles authentication, rate limiting, and service discovery
"""

import asyncio
import logging
import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from typing import Dict, Optional
import os
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for microservices"""
    USER_SERVICE_URL: str = "http://localhost:8001"
    MARKET_DATA_SERVICE_URL: str = "http://localhost:8002" 
    STRATEGY_ENGINE_URL: str = "http://localhost:8003"
    ORDER_SERVICE_URL: str = "http://localhost:8004"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8005"

class ServiceRegistry:
    """Service discovery and health monitoring"""
    
    def __init__(self):
        self.services = ServiceConfig()
        self.service_health = {}
        self.circuit_breakers = {}
        
    async def check_service_health(self, service_name: str, url: str) -> bool:
        """Check if a service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/health")
                is_healthy = response.status_code == 200
                self.service_health[service_name] = {
                    "healthy": is_healthy,
                    "last_check": time.time(),
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                }
                return is_healthy
        except Exception as e:
            logger.warning(f"Service {service_name} health check failed: {e}")
            self.service_health[service_name] = {
                "healthy": False,
                "last_check": time.time(),
                "error": str(e)
            }
            return False
    
    async def get_healthy_service_url(self, service_name: str) -> Optional[str]:
        """Get URL for a healthy service instance"""
        service_mapping = {
            "user": self.services.USER_SERVICE_URL,
            "market_data": self.services.MARKET_DATA_SERVICE_URL,
            "strategy": self.services.STRATEGY_ENGINE_URL,
            "order": self.services.ORDER_SERVICE_URL,
            "notification": self.services.NOTIFICATION_SERVICE_URL
        }
        
        url = service_mapping.get(service_name)
        if not url:
            return None
            
        # Check health before routing
        is_healthy = await self.check_service_health(service_name, url)
        return url if is_healthy else None

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
        
    def is_allowed(self, client_ip: str, limit_per_minute: int = 100) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
            
        # Clean old requests
        self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] if req_time > minute_ago]
        
        # Check limit
        if len(self.requests[client_ip]) >= limit_per_minute:
            return False
            
        self.requests[client_ip].append(now)
        return True

# Initialize components
app = FastAPI(
    title="Pinnacle Trading System - API Gateway",
    description="Microservices Gateway for Trading Platform",
    version="2.0.0"
)

service_registry = ServiceRegistry()
rate_limiter = RateLimiter()
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting"""
    client_ip = request.client.host
    
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
    
    response = await call_next(request)
    return response

@app.get("/")
async def gateway_info():
    """Gateway information and service status"""
    return {
        "service": "Pinnacle Trading System - API Gateway",
        "version": "2.0.0",
        "architecture": "Microservices",
        "status": "operational",
        "services": service_registry.service_health,
        "endpoints": {
            "authentication": "/auth/*",
            "marketplace": "/marketplace",
            "user": "/user/*", 
            "trading": "/trading/*",
            "admin": "/admin/*"
        }
    }

@app.get("/health")
async def health_check():
    """Gateway health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": service_registry.service_health
    }

# Authentication proxy
@app.post("/auth/login")
async def login_proxy(request: Request):
    """Proxy authentication to user service"""
    user_service_url = await service_registry.get_healthy_service_url("user")
    if not user_service_url:
        raise HTTPException(status_code=503, detail="User service unavailable")
    
    body = await request.body()
    headers = dict(request.headers)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{user_service_url}/auth/login",
            content=body,
            headers=headers
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)

# Market data proxy
@app.get("/market/realtime/{symbol}")
async def market_data_proxy(symbol: str):
    """Proxy market data requests"""
    market_service_url = await service_registry.get_healthy_service_url("market_data")
    if not market_service_url:
        raise HTTPException(status_code=503, detail="Market data service unavailable")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{market_service_url}/realtime/{symbol}")
        return JSONResponse(content=response.json(), status_code=response.status_code)

# Strategy proxy
@app.get("/marketplace")
async def marketplace_proxy():
    """Proxy marketplace requests to strategy service"""
    strategy_service_url = await service_registry.get_healthy_service_url("strategy")
    if not strategy_service_url:
        raise HTTPException(status_code=503, detail="Strategy service unavailable")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{strategy_service_url}/marketplace")
        return JSONResponse(content=response.json(), status_code=response.status_code)

# User dashboard proxy
@app.get("/user/dashboard")
async def dashboard_proxy(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Proxy user dashboard requests"""
    user_service_url = await service_registry.get_healthy_service_url("user")
    if not user_service_url:
        raise HTTPException(status_code=503, detail="User service unavailable")
    
    headers = {"Authorization": f"Bearer {credentials.credentials}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{user_service_url}/dashboard", headers=headers)
        return JSONResponse(content=response.json(), status_code=response.status_code)

# Order management proxy
@app.post("/trading/orders")
async def orders_proxy(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Proxy order placement to order service"""
    order_service_url = await service_registry.get_healthy_service_url("order")
    if not order_service_url:
        raise HTTPException(status_code=503, detail="Order service unavailable")
    
    body = await request.body()
    headers = {"Authorization": f"Bearer {credentials.credentials}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{order_service_url}/orders",
            content=body,
            headers=headers
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)

@app.on_event("startup")
async def startup_event():
    """Initialize gateway and check service health"""
    logger.info("🚀 API Gateway starting up...")
    
    # Initial health check of all services
    service_mapping = {
        "user": service_registry.services.USER_SERVICE_URL,
        "market_data": service_registry.services.MARKET_DATA_SERVICE_URL,
        "strategy": service_registry.services.STRATEGY_ENGINE_URL,
        "order": service_registry.services.ORDER_SERVICE_URL,
        "notification": service_registry.services.NOTIFICATION_SERVICE_URL
    }
    
    for service_name, service_url in service_mapping.items():
        await service_registry.check_service_health(service_name, service_url)
    
    logger.info("✅ API Gateway ready")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 