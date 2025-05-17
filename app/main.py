# main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.database import SessionLocal, engine
from app.models import (
    Base as AppBase,
    User as UserModel,
    Strategy as StrategyModel,
    Order as OrderModel,
)
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    StrategyBase,
    StrategyCreate,
    Strategy,
    StrategyUpdate,
    OrderBase,
    OrderCreate,
    OrderUpdate,
    Order as OrderSchema,
    OrderResponse,
)
import os
from dotenv import load_dotenv
import uuid
from sqlalchemy import func

# Import API routers
from app.api.endpoints import orders as orders_router
from app.api.endpoints import portfolio as portfolio_router

# Import settings and logger from config
from config import logger, settings
from app.core.config import settings as core_settings
from app.api.dependencies.auth import get_current_user

load_dotenv()

# Create tables
try:
    AppBase.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")
    raise


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
    lifespan=lifespan,  # Use the lifespan context manager
)

# --- API Routers Inclusion ---
app.include_router(orders_router.router, prefix="/orders", tags=["Orders"])
app.include_router(
    portfolio_router.router,
    prefix=f"{settings.API_V1_STR}/portfolio",
    tags=["Portfolio & Balance"],
)
# Add other routers here (e.g., users, strategies) when implemented


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """Basic endpoint to check if the API is running."""
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME}. Docs available at /docs"
    }


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


# --- Security Configuration ---
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=False,  # Don't allow credentials since we're using Authorization header
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class User(BaseModel):
    id: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class StrategyBase(BaseModel):
    name: str
    margin: float
    marginType: str
    basePrice: float
    status: str


class StrategyCreate(StrategyBase):
    pass


class Strategy(StrategyBase):
    id: str
    lastUpdated: datetime
    user_id: str

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(db: Session, username_or_email: str, password: str):
    try:
        # Try to find user by username first
        user = db.query(UserModel).filter(UserModel.id == username_or_email).first()
        if not user:
            # Try to find user by email
            user = (
                db.query(UserModel).filter(UserModel.email == username_or_email).first()
            )
        if not user:
            logger.warning(f"User not found: {username_or_email}")
            return False
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {username_or_email}")
            return False
        logger.info(f"User authenticated successfully: {username_or_email}")
        return user
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating access token",
        )


@app.post("/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    try:
        logger.info(f"Attempting login for user: {form_data.username}")
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            logger.warning(f"Login failed for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        logger.info(f"Login successful for user: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as he:
        logger.error(f"HTTP Exception in login: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error in user login: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}",
        )


def create_default_strategies(db: Session, user_id: str):
    """Create default strategies for a new user."""
    default_strategies = [
        {
            "name": "Moving Average Crossover",
            "margin": 100000.0,
            "marginType": "rupees",
            "basePrice": 1000.0,
            "status": "active",
            "user_id": user_id,
            "lastUpdated": datetime.utcnow().isoformat(),
        },
        {
            "name": "RSI Strategy",
            "margin": 5.0,
            "marginType": "percentage",
            "basePrice": 1000.0,
            "status": "inactive",
            "user_id": user_id,
            "lastUpdated": datetime.utcnow().isoformat(),
        },
        {
            "name": "MACD Strategy",
            "margin": 150000.0,
            "marginType": "rupees",
            "basePrice": 1000.0,
            "status": "inactive",
            "user_id": user_id,
            "lastUpdated": datetime.utcnow().isoformat(),
        },
    ]

    for strategy_data in default_strategies:
        strategy = StrategyModel(**strategy_data)
        db.add(strategy)

    try:
        db.commit()
        logger.info(f"Created default strategies for user {user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating default strategies: {e}")
        raise


@app.post("/auth/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if user already exists
        db_user = (
            db.query(UserModel).filter(UserModel.username == user.username).first()
        )
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = UserModel(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create default strategies for the new user
        create_default_strategies(db, db_user.username)

        return db_user
    except HTTPException as he:
        logger.error(f"HTTP Exception in user registration: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error in user registration: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


# Strategy endpoints
@app.get("/strategies", response_model=List[Strategy])
async def get_strategies(
    current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        logger.info(f"Getting strategies for user {current_user.id}")
        strategies = (
            db.query(StrategyModel)
            .filter(
                (StrategyModel.user_id == current_user.id)
                | (StrategyModel.user_id == "system")
            )
            .all()
        )
        logger.info(f"Found {len(strategies)} strategies")
        for strategy in strategies:
            logger.info(
                f"Strategy: {strategy.name} (ID: {strategy.id}, User: {strategy.user_id})"
            )
        return [strategy.to_dict() for strategy in strategies]
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategies: {str(e)}",
        )


@app.put("/strategies/{strategy_id}", response_model=Strategy)
async def update_strategy(
    strategy_id: str,
    strategy_update: StrategyUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        logger.info(f"Updating strategy {strategy_id} for user {current_user.id}")
        logger.info(f"Update data: {strategy_update.dict(exclude_unset=True)}")

        db_strategy = (
            db.query(StrategyModel)
            .filter(
                StrategyModel.id == strategy_id,
                (StrategyModel.user_id == current_user.id)
                | (StrategyModel.user_id == "system"),
            )
            .first()
        )

        if not db_strategy:
            logger.warning(
                f"Strategy {strategy_id} not found for user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Strategy not found")

        update_data = strategy_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_strategy, key, value)

        db_strategy.lastUpdated = datetime.utcnow()
        db.commit()
        db.refresh(db_strategy)

        logger.info(f"Successfully updated strategy {strategy_id}")
        return db_strategy.to_dict()
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating strategy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating strategy: {str(e)}",
        )


@app.post("/square-off/strategy/{strategy_id}", response_model=dict)
async def square_off_strategy(
    strategy_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        logger.info(f"Squaring off strategy {strategy_id} for user {current_user.id}")

        db_strategy = (
            db.query(StrategyModel)
            .filter(
                StrategyModel.id == strategy_id,
                (StrategyModel.user_id == current_user.id)
                | (StrategyModel.user_id == "system"),
            )
            .first()
        )

        if not db_strategy:
            logger.warning(
                f"Strategy {strategy_id} not found for user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Add your square-off logic here
        # For now, we'll just return a success message
        logger.info(f"Successfully squared off strategy {strategy_id}")
        return {"message": f"Strategy {strategy_id} squared off successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error squaring off strategy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error squaring off strategy: {str(e)}",
        )


@app.post("/square-off/all", response_model=dict)
async def square_off_all_strategies(
    current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        logger.info(f"Squaring off all strategies for user {current_user.id}")

        strategies = (
            db.query(StrategyModel)
            .filter(
                (StrategyModel.user_id == current_user.id)
                | (StrategyModel.user_id == "system")
            )
            .all()
        )

        if not strategies:
            logger.warning(f"No strategies found for user {current_user.id}")
            return {"message": "No strategies found to square off"}

        # Add your square-off-all logic here
        logger.info(f"Successfully squared off {len(strategies)} strategies")
        return {"message": f"Successfully squared off {len(strategies)} strategies"}
    except Exception as e:
        logger.error(f"Error squaring off all strategies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error squaring off all strategies: {str(e)}",
        )


@app.post("/strategies/initialize", response_model=List[Strategy])
async def initialize_strategies(
    current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Initialize default strategies for the current user."""
    try:
        # Check if user already has strategies
        existing_strategies = (
            db.query(StrategyModel)
            .filter(StrategyModel.user_id == current_user.id)
            .first()
        )

        if existing_strategies:
            raise HTTPException(
                status_code=400,
                detail="User already has strategies. Cannot initialize again.",
            )

        create_default_strategies(db, current_user.id)

        # Return the newly created strategies
        strategies = (
            db.query(StrategyModel)
            .filter(StrategyModel.user_id == current_user.id)
            .all()
        )
        return strategies
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error initializing strategies: {e}")
        raise HTTPException(status_code=500, detail="Error initializing strategies")


# --- How to Run ---
# 1. Create and populate your .env file with Angel One credentials.
# 2. Install requirements: pip install -r requirements.txt
# 3. Run using Uvicorn: uvicorn main:app --reload --host 0.0.0.0 --port 8000
#    (Use --host 0.0.0.0 if you need to access it from other devices on your network)
# 4. Access the API documentation at http://127.0.0.1:8000/docs
