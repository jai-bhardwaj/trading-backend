"""
FastAPI Trading Backend Application
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Dict, Any

from .models import HealthResponse
from .services.trading_service import TradingService
from .routes import strategies, user_configs, orders, positions, trades, marketplace, user
from . import dependencies

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppState:
    """Application state container"""
    def __init__(self):
        self.trading_service: TradingService = None
        self.initialized: bool = False

app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global app_state
    
    # Startup
    logger.info("🚀 Starting Trading Backend API...")
    try:
        app_state.trading_service = TradingService()
        await app_state.trading_service.initialize()
        app_state.initialized = True
        logger.info("✅ Trading service initialized successfully")
        
        # Store in app state as well for direct access
        app.state.trading_service = app_state.trading_service
        app.state.initialized = True
        
        # Set the app state in dependencies module
        dependencies.set_app_state(app_state)
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize trading service: {e}")
        app_state.initialized = False
        # Don't raise - let the app start but mark as unhealthy
        logger.warning("⚠️ API will start but trading service is unavailable")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trading Backend API...")
    if app_state.trading_service and app_state.trading_service.order_manager:
        try:
            await app_state.trading_service.order_manager.close()
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    app_state.trading_service = None
    app_state.initialized = False
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

# Include routers with dependency injection
app.include_router(strategies.router)
app.include_router(user_configs.router)
app.include_router(orders.router)
app.include_router(positions.router)
app.include_router(trades.router)
app.include_router(marketplace.router)
app.include_router(user.router)

@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Backend API",
        "version": "1.0.0",
        "status": "running",
        "trading_service_initialized": app_state.initialized
    }

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint"""
    try:
        if app_state.trading_service and app_state.initialized:
            health_data = app_state.trading_service.get_health_status()
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