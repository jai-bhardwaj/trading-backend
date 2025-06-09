"""
API Module
Exposes FastAPI application factory and routers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

def create_app() -> FastAPI:
    """
    Application factory for creating FastAPI app
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    try:
        from .main import router as main_router
        app.include_router(main_router, prefix="/api/v1")
    except ImportError:
        pass
    
    try:
        from .health import router as health_router
        app.include_router(health_router, prefix="/health")
    except ImportError:
        pass
    
    try:
        from .strategy_management import router as strategy_router
        app.include_router(strategy_router, prefix="/api/v1/strategies")
    except ImportError:
        pass
    
    try:
        from .multi_user_brokers import router as broker_router
        app.include_router(broker_router, prefix="/api/v1/brokers")
    except ImportError:
        pass
    
    return app 