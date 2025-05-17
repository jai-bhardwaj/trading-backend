# # main.py
# import logging
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, Request, status, Depends, HTTPException
# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta
# from typing import Optional
# from jose import JWTError, jwt
# from passlib.context import CryptContext
# from pydantic import BaseModel
# from database import SessionLocal, engine
# import models
# import os
# from dotenv import load_dotenv

# # Import API routers
# from app.api.endpoints import orders as orders_router
# from app.api.endpoints import portfolio as portfolio_router

# # Import settings and logger from config
# from config import logger, settings

# load_dotenv()

# # Create tables
# models.Base.metadata.create_all(bind=engine)


# # --- Application Lifespan Management (Optional but Recommended) ---
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Code to run on startup
#     logger.info("--- Application Startup ---")
#     logger.info(f"Project Name: {settings.PROJECT_NAME}")
#     # You could pre-initialize certain non-user-specific resources here if needed
#     # e.g., connect to a database, load market metadata
#     # Broker connections are handled per-user on demand by dependencies
#     logger.info("Broker initialization will happen on first request per user/broker.")
#     logger.info("Application ready.")
#     yield
#     # Code to run on shutdown
#     logger.info("--- Application Shutdown ---")
#     # Add cleanup logic here (e.g., close database connections, release resources)
#     # Note: In-memory broker sessions (_user_sessions in angelone.py) will be lost.
#     logger.info("Shutdown complete.")


# # --- FastAPI Application Instance ---
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     openapi_url=f"{settings.API_V1_STR}/openapi.json",
#     lifespan=lifespan,  # Use the lifespan context manager
# )

# # --- API Routers Inclusion ---
# app.include_router(
#     orders_router.router, prefix=f"{settings.API_V1_STR}/orders", tags=["Orders"]
# )
# app.include_router(
#     portfolio_router.router,
#     prefix=f"{settings.API_V1_STR}/portfolio",
#     tags=["Portfolio & Balance"],
# )
# # Add other routers here (e.g., users, strategies) when implemented


# # --- Root Endpoint ---
# @app.get("/", tags=["Root"])
# async def read_root():
#     """Basic endpoint to check if the API is running."""
#     return {
#         "message": f"Welcome to the {settings.PROJECT_NAME}. Docs available at /docs"
#     }


# # --- Custom Exception Handler for Validation Errors (Optional) ---
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     # Log the validation error details
#     logger.warning(f"Request validation error: {exc.errors()}")
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content={"detail": exc.errors()},
#     )


# # --- General Exception Handler (Optional) ---
# # Catches unhandled errors - use with caution, might hide specific issues
# # @app.exception_handler(Exception)
# # async def general_exception_handler(request: Request, exc: Exception):
# #     logger.exception(f"Unhandled exception during request processing: {exc}")
# #     return JSONResponse(
# #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
# #         content={"detail": "An internal server error occurred."},
# #     )


# # --- Security Configuration ---
# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # Add your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Security
# SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# # Dependency
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# class Token(BaseModel):
#     access_token: str
#     token_type: str


# class TokenData(BaseModel):
#     username: Optional[str] = None


# class UserCreate(BaseModel):
#     username: str
#     email: str
#     password: str


# class User(BaseModel):
#     username: str
#     email: str
#     is_active: bool

#     class Config:
#         from_attributes = True


# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)


# def get_password_hash(password):
#     return pwd_context.hash(password)


# def authenticate_user(db: Session, username_or_email: str, password: str):
#     # Try to find user by username first
#     user = (
#         db.query(models.User).filter(models.User.username == username_or_email).first()
#     )
#     if not user:
#         # If not found by username, try email
#         user = (
#             db.query(models.User).filter(models.User.email == username_or_email).first()
#         )
#     if not user:
#         return False
#     if not verify_password(password, user.hashed_password):
#         return False
#     return user


# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt


# async def get_current_user(
#     token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
# ):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_data = TokenData(username=username)
#     except JWTError:
#         raise credentials_exception
#     user = (
#         db.query(models.User)
#         .filter(models.User.username == token_data.username)
#         .first()
#     )
#     if user is None:
#         raise credentials_exception
#     return user


# @app.post("/auth/token", response_model=Token)
# async def login_for_access_token(
#     form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
# ):
#     user = authenticate_user(db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username/email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.username}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}


# @app.post("/auth/register", response_model=User)
# def register_user(user: UserCreate, db: Session = Depends(get_db)):
#     # Check if username already exists
#     db_user = (
#         db.query(models.User).filter(models.User.username == user.username).first()
#     )
#     if db_user:
#         raise HTTPException(status_code=400, detail="Username already registered")

#     # Check if email already exists
#     db_user = db.query(models.User).filter(models.User.email == user.email).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")

#     hashed_password = get_password_hash(user.password)
#     db_user = models.User(
#         username=user.username, email=user.email, hashed_password=hashed_password
#     )
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user


# @app.get("/users/me", response_model=User)
# async def read_users_me(current_user: models.User = Depends(get_current_user)):
#     return current_user


# # --- How to Run ---
# # 1. Create and populate your .env file with Angel One credentials.
# # 2. Install requirements: pip install -r requirements.txt
# # 3. Run using Uvicorn: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# #    (Use --host 0.0.0.0 if you need to access it from other devices on your network)
# # 4. Access the API documentation at http://127.0.0.1:8000/docs
