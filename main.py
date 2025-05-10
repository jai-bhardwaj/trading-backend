# main.py
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

# Import settings and logger from config
from config import settings, logger

# Import API routers
from app.api.endpoints import orders as orders_router
from app.api.endpoints import portfolio as portfolio_router

# --- Application Lifespan Management (Optional but Recommended) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("--- Application Startup ---")
    logger.info(f"Project Name: {settings.PROJECT_NAME}")
    # You could pre-initialize certain non-user-specific resources here if needed
    # e.g., connect to a database, load market metadata
    # Broker connections are handled per-user on demand by dependencies
    logger.info("Broker initialization will happen on first request per user/broker.")
    logger.info("Application ready.")
    yield
    # Code to run on shutdown
    logger.info("--- Application Shutdown ---")
    # Add cleanup logic here (e.g., close database connections, release resources)
    # Note: In-memory broker sessions (_user_sessions in angelone.py) will be lost.
    logger.info("Shutdown complete.")

# --- FastAPI Application Instance ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Use the lifespan context manager
)

# --- API Routers Inclusion ---
app.include_router(
    orders_router.router,
    prefix=f"{settings.API_V1_STR}/orders",
    tags=["Orders"]
)
app.include_router(
    portfolio_router.router,
    prefix=f"{settings.API_V1_STR}/portfolio",
    tags=["Portfolio & Balance"]
)
# Add other routers here (e.g., users, strategies) when implemented

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """Basic endpoint to check if the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}. Docs available at /docs"}

# --- Custom Exception Handler for Validation Errors (Optional) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the validation error details
    logger.warning(f"Request validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

# --- General Exception Handler (Optional) ---
# Catches unhandled errors - use with caution, might hide specific issues
# @app.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception):
#     logger.exception(f"Unhandled exception during request processing: {exc}")
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "An internal server error occurred."},
#     )


# --- How to Run ---
# 1. Create and populate your .env file with Angel One credentials.
# 2. Install requirements: pip install -r requirements.txt
# 3. Run using Uvicorn: uvicorn main:app --reload --host 0.0.0.0 --port 8000
#    (Use --host 0.0.0.0 if you need to access it from other devices on your network)
# 4. Access the API documentation at http://127.0.0.1:8000/docs