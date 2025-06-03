"""
Database configuration and connection management for the Trading Engine.
Updated for the new cleaned live trading schema.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import redis.asyncio as redis
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and Redis connections for the trading engine."""
    
    def __init__(self):
        self.async_engine = None
        self.async_session_factory = None
        self.redis_client = None
        self._initialized = False
    
    def initialize(self, database_url: str, redis_url: str = "redis://localhost:6379"):
        """Initialize database and Redis connections."""
        try:
            # PostgreSQL connection
            self.async_engine = create_async_engine(
                database_url,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,  # Set to True for SQL debugging
            )
            
            self.async_session_factory = sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Redis connection for notifications and alerts
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            self._initialized = True
            logger.info("Database and Redis connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self):
        """Get an async database session."""
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client for real-time notifications and alerts."""
        if not self._initialized:
            raise RuntimeError("Redis not initialized")
        return self.redis_client
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of database and Redis connections."""
        health = {"database": False, "redis": False}
        
        # Check database
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                health["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check Redis
        try:
            redis_client = await self.get_redis()
            await redis_client.ping()
            health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        return health
    
    async def close(self):
        """Close all connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("All database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
async def get_async_session():
    """Get async database session."""
    async with db_manager.get_async_session() as session:
        yield session

async def get_redis():
    """Get Redis client."""
    return await db_manager.get_redis()

# Initialize database with environment variables
def init_database():
    """Initialize database connections using environment variables."""
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://user:password@localhost:5432/trading_db"
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    db_manager.initialize(database_url, redis_url)

# Redis key patterns for the new hybrid notification system
class RedisKeys:
    """Redis key patterns for the trading system."""
    
    # Real-time notifications
    USER_NOTIFICATIONS = "notifications:{user_id}:realtime"
    STRATEGY_NOTIFICATIONS = "notifications:strategy:{strategy_id}"
    SYSTEM_NOTIFICATIONS = "notifications:system"
    
    # Pub/Sub channels
    USER_CHANNEL = "user:{user_id}"
    STRATEGY_CHANNEL = "strategy:{strategy_id}"
    SYSTEM_CHANNEL = "system"
    
    # Alert processing
    PRICE_ALERTS = "alerts:price:{symbol}"
    VOLUME_ALERTS = "alerts:volume:{symbol}"
    STRATEGY_ALERTS = "alerts:strategy:{strategy_id}"
    
    # Strategy execution
    STRATEGY_COMMANDS = "commands:strategy:{strategy_id}"
    STRATEGY_STATUS = "status:strategy:{strategy_id}"
    STRATEGY_METRICS = "metrics:strategy:{strategy_id}"
    
    # Market data
    MARKET_DATA = "market:{symbol}:{exchange}"
    INSTRUMENTS = "instruments:{category}"

# Prisma-like query helpers for better compatibility
class QueryHelpers:
    """Helper functions for database queries matching Prisma patterns."""
    
    @staticmethod
    def build_where_clause(filters: Dict[str, Any]) -> str:
        """Build WHERE clause from filters dict."""
        conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f"{key} = '{value}'")
            else:
                conditions.append(f"{key} = {value}")
        
        return " AND ".join(conditions) if conditions else "1=1"
    
    @staticmethod
    def build_order_clause(order_by: Dict[str, str]) -> str:
        """Build ORDER BY clause from order dict."""
        if not order_by:
            return ""
        
        order_parts = []
        for field, direction in order_by.items():
            order_parts.append(f"{field} {direction.upper()}")
        
        return f"ORDER BY {', '.join(order_parts)}"
