#!/usr/bin/env python3
"""
User Management Service - Handles authentication, user profiles, JWT tokens
Isolated service for user management with zero dependencies on trading components
"""

import asyncio
import logging
import jwt
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import asyncpg
import redis.asyncio as redis
import os
from dataclasses import dataclass, field
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class UserServiceConfig:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/trading_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
    JWT_EXPIRY_HOURS: int = 24
    REFRESH_TOKEN_DAYS: int = 7

config = UserServiceConfig()

# Models
class LoginRequest(BaseModel):
    api_key: str
    user_id: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    permissions: List[str]

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    api_key: str
    broker_api_key: str = ""
    broker_secret: str = ""
    broker_token: str = ""
    total_capital: float = 100000.0
    risk_tolerance: str = "medium"
    enabled: bool = True
    created_at: str
    last_login: Optional[str] = None

class UserSession:
    """Manages user sessions and tokens"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        
    async def create_session(self, user_id: str) -> Dict[str, str]:
        """Create JWT tokens for user session"""
        now = datetime.utcnow()
        
        # Access token (short-lived)
        access_payload = {
            "user_id": user_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=config.JWT_EXPIRY_HOURS)
        }
        access_token = jwt.encode(access_payload, config.JWT_SECRET, algorithm="HS256")
        
        # Refresh token (long-lived)
        refresh_payload = {
            "user_id": user_id,
            "type": "refresh", 
            "iat": now,
            "exp": now + timedelta(days=config.REFRESH_TOKEN_DAYS)
        }
        refresh_token = jwt.encode(refresh_payload, config.JWT_SECRET, algorithm="HS256")
        
        # Store session in Redis
        session_key = f"session:{user_id}:{uuid.uuid4().hex[:8]}"
        session_data = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat()
        }
        
        await self.redis_client.setex(
            session_key, 
            config.REFRESH_TOKEN_DAYS * 24 * 3600,  # TTL in seconds
            json.dumps(session_data)
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    async def validate_token(self, token: str) -> Optional[str]:
        """Validate JWT token and return user_id"""
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def revoke_session(self, user_id: str, token: str):
        """Revoke user session"""
        # Find and delete session from Redis
        pattern = f"session:{user_id}:*"
        keys = await self.redis_client.keys(pattern)
        
        for key in keys:
            session_data = await self.redis_client.get(key)
            if session_data:
                session = json.loads(session_data)
                if session.get("access_token") == token:
                    await self.redis_client.delete(key)
                    break

class UserRepository:
    """Database operations for users"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def create_user_table(self):
        """Create users table if not exists"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    broker_api_key VARCHAR(100) DEFAULT '',
                    broker_secret VARCHAR(100) DEFAULT '',
                    broker_token VARCHAR(100) DEFAULT '',
                    total_capital DECIMAL(15,2) DEFAULT 100000.00,
                    risk_tolerance VARCHAR(20) DEFAULT 'medium',
                    enabled BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP
                )
            """)
    
    async def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE api_key = $1 AND enabled = true", 
                api_key
            )
            return dict(row) if row else None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", 
                user_id
            )
            return dict(row) if row else None
    
    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = NOW() WHERE user_id = $1",
                user_id
            )
    
    async def create_user(self, user_data: Dict) -> bool:
        """Create a new user"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, name, email, api_key, total_capital, risk_tolerance)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                user_data["user_id"],
                user_data["name"], 
                user_data["email"],
                user_data["api_key"],
                user_data["total_capital"],
                user_data["risk_tolerance"]
                )
                return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    async def get_all_users(self) -> List[Dict]:
        """Get all users"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE enabled = true")
            return [dict(row) for row in rows]

class MockUserRepository:
    """Mock user repository for development without database"""
    
    def __init__(self):
        # In-memory user storage for development
        self.users = {
            "trader_001": {
                "user_id": "trader_001",
                "name": "Development Trader 1",
                "email": "trader1@pinnacle.com",
                "api_key": "dev_api_key_001",
                "broker_api_key": "",
                "broker_secret": "",
                "broker_token": "",
                "total_capital": 100000.0,
                "risk_tolerance": "medium",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None
            },
            "trader_002": {
                "user_id": "trader_002", 
                "name": "Development Trader 2", 
                "email": "trader2@pinnacle.com",
                "api_key": "dev_api_key_002",
                "broker_api_key": "",
                "broker_secret": "",
                "broker_token": "",
                "total_capital": 200000.0,
                "risk_tolerance": "high",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None
            }
        }
        logger.info("✅ Mock user repository initialized with development users")
    
    async def create_user_table(self):
        """Mock table creation - no-op"""
        pass
    
    async def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key from memory"""
        for user in self.users.values():
            if user["api_key"] == api_key and user["enabled"]:
                return user.copy()
        return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID from memory"""
        return self.users.get(user_id, {}).copy() if user_id in self.users else None
    
    async def update_last_login(self, user_id: str):
        """Update last login in memory"""
        if user_id in self.users:
            self.users[user_id]["last_login"] = datetime.utcnow().isoformat()
    
    async def create_user(self, user_data: Dict) -> bool:
        """Create user in memory"""
        try:
            user_data["created_at"] = datetime.utcnow().isoformat()
            user_data["last_login"] = None
            self.users[user_data["user_id"]] = user_data.copy()
            return True
        except Exception as e:
            logger.error(f"Failed to create mock user: {e}")
            return False
    
    async def get_all_users(self) -> List[Dict]:
        """Get all users from memory"""
        return [user.copy() for user in self.users.values() if user["enabled"]]

# Initialize FastAPI app
app = FastAPI(
    title="User Management Service",
    description="Authentication and User Profile Management", 
    version="1.0.0"
)

# Global components
db_pool = None
redis_client = None
user_repo = None
user_session = None
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract current user from JWT token"""
    return await user_session.validate_token(credentials.credentials)

@app.on_event("startup")
async def startup_event():
    """Initialize database and Redis connections"""
    global db_pool, redis_client, user_repo, user_session
    
    try:
        logger.info("🚀 User Service starting up...")
        
        # Connect to Redis (required)
        redis_client = redis.from_url(config.REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Try to connect to PostgreSQL (optional for development)
        try:
            db_pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=2, max_size=10, timeout=5)
            logger.info("✅ Database connected")
            
            # Initialize components with database
        user_repo = UserRepository(db_pool)
        
        # Create tables
        await user_repo.create_user_table()
        logger.info("✅ Database tables created")
        
            # Create default users
            await create_default_users()
            
        except Exception as db_error:
            logger.warning(f"⚠️ Database connection failed: {db_error}")
            logger.info("🔄 Running in development mode without database persistence")
            
            # Initialize with mock repository
            user_repo = MockUserRepository()
            db_pool = None
        
        # Initialize user session (works with or without database)
        user_session = UserSession(redis_client)
        
        logger.info("✅ User Service ready on port 8001")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize User Service: {e}")
        raise

async def create_default_users():
    """Create default production users"""
    default_users = [
        {
            "user_id": "trader_001",
            "name": "Production Trader 1",
            "email": "trader1@pinnacle.com",
            "api_key": hashlib.sha256(f"trader_001-{uuid.uuid4()}".encode()).hexdigest()[:32],
            "total_capital": 500000.0,
            "risk_tolerance": "medium"
        },
        {
            "user_id": "trader_002", 
            "name": "Production Trader 2",
            "email": "trader2@pinnacle.com",
            "api_key": hashlib.sha256(f"trader_002-{uuid.uuid4()}".encode()).hexdigest()[:32],
            "total_capital": 1000000.0,
            "risk_tolerance": "high"
        }
    ]
    
    for user_data in default_users:
        existing_user = await user_repo.get_user_by_id(user_data["user_id"])
        if not existing_user:
            await user_repo.create_user(user_data)
            logger.info(f"Created default user: {user_data['user_id']}")

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        # Check Redis (required)
        await redis_client.ping()
        
        # Check database (optional)
        db_status = "disconnected"
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                db_status = "connected"
            except:
                db_status = "error"
        
        return {
            "status": "healthy", 
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "redis": "connected",
            "mode": "production" if db_pool else "development"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.post("/auth/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """Authenticate user and return JWT tokens"""
    try:
        # Validate API key
        user = await user_repo.get_user_by_api_key(login_request.api_key)
        if not user or user["user_id"] != login_request.user_id:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Update last login
        await user_repo.update_last_login(user["user_id"])
        
        # Create session
        tokens = await user_session.create_session(user["user_id"])
        
        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=config.JWT_EXPIRY_HOURS * 3600,
            user_id=user["user_id"],
            permissions=["trading", "dashboard", "marketplace"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.post("/auth/logout")
async def logout(current_user: str = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and revoke session"""
    await user_session.revoke_session(current_user, credentials.credentials)
    return {"message": "Logged out successfully"}

@app.get("/dashboard", response_model=UserProfile)
async def get_user_dashboard(current_user: str = Depends(get_current_user)):
    """Get user profile and dashboard data"""
    user = await user_repo.get_user_by_id(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfile(**user)

@app.get("/users")
async def get_all_users():
    """Get all users (admin endpoint)"""
    users = await user_repo.get_all_users()
    return {"users": users}

@app.get("/")
async def service_info():
    """Service information"""
    return {
        "service": "User Management Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "POST /auth/login",
            "POST /auth/logout", 
            "GET /dashboard",
            "GET /users",
            "GET /health"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 