"""
Main FastAPI Application

This module creates and configures the main FastAPI application with all
routers, middleware, and production-ready settings.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import get_settings
from app.core.rate_limiter import rate_limiter, RateLimitType
from app.api.health import router as health_router
from app.api.strategy_management import router as strategy_router

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting Trading Engine API...")
    
    # Initialize services
    try:
        # Rate limiter is already imported
        logger.info("✅ Rate limiter initialized")
        
        # Add any other startup tasks here
        logger.info("✅ Trading Engine API started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start API: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("⏹️ Shutting down Trading Engine API...")
    logger.info("✅ Trading Engine API shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Trading Engine API",
    description="Professional trading engine with multi-broker support, strategy management, and real-time monitoring",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Security middleware
if settings.environment == "production":
    # Trust only specific hosts in production
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with your actual domains
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Global rate limiting middleware."""
    try:
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Check rate limit
        allowed = await rate_limiter.check_rate_limit(
            client_ip, 
            RateLimitType.API_ENDPOINT, 
            1
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later."
                }
            )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        logger.error(f"Rate limiting middleware error: {e}")
        # Continue without rate limiting if there's an error
        return await call_next(request)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }
        )

# Include routers
app.include_router(health_router, tags=["Health & Monitoring"])
app.include_router(strategy_router, prefix="/api/v1", tags=["Strategy Management"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Trading Engine API",
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.debug else "disabled",
        "health_check": "/health"
    }

# API info endpoint
@app.get("/info", tags=["Root"])
async def api_info():
    """Get API information and capabilities."""
    return {
        "api": {
            "name": "Trading Engine API",
            "version": "1.0.0",
            "environment": settings.environment,
            "debug": settings.debug
        },
        "features": {
            "multi_broker_support": True,
            "real_time_monitoring": True,
            "strategy_management": True,
            "risk_management": True,
            "notification_system": True,
            "rate_limiting": True,
            "circuit_breakers": True
        },
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "metrics": "/metrics",
            "trading_metrics": "/metrics/trading",
            "strategies": "/api/v1/strategies",
            "documentation": "/docs" if settings.debug else "disabled"
        }
    } 