"""
FastAPI Trading Backend Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from .models import HealthResponse
from .services.trading_service import TradingService
from .routes import strategies, user_configs, orders, positions, trades

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global trading service instance
trading_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global trading_service
    
    # Startup
    logger.info("🚀 Starting Trading Backend API...")
    try:
        trading_service = TradingService()
        await trading_service.initialize()
        logger.info("✅ Trading service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize trading service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trading Backend API...")
    if trading_service and trading_service.order_manager:
        await trading_service.order_manager.close()
    logger.info("✅ Trading Backend API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Trading Backend API",
    description="API for managing trading strategies, orders, and user configurations",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(strategies.router)
app.include_router(user_configs.router)
app.include_router(orders.router)
app.include_router(positions.router)
app.include_router(trades.router)

@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Backend API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    global trading_service
    
    try:
        if trading_service:
            health_data = trading_service.get_health_status()
        else:
            health_data = {
                "status": "unhealthy",
                "timestamp": datetime.utcnow(),
                "database_connected": False,
                "redis_connected": False,
                "trading_system_active": False
            }
        
        return HealthResponse(**health_data)
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database_connected=False,
            redis_connected=False,
            trading_system_active=False
        )

@app.get("/api/docs", tags=["docs"])
async def get_docs():
    """Get API documentation"""
    return {
        "message": "API Documentation",
        "swagger_ui": "/docs",
        "redoc": "/redoc",
        "openapi_json": "/openapi.json"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 