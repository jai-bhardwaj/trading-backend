"""
Database Manager for Trading Engine
"""

import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import get_settings
from contextlib import asynccontextmanager
import ssl
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine: Optional[object] = None
        self.session_factory: Optional[async_sessionmaker] = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            logger.info(f"Initializing database connection...")
            # Convert PostgreSQL URL to async format
            database_url = self.settings.database_url

            # Replace the database_url with the new one
            if (self.settings.database_url.startswith("postgresql://")):
                database_url = self.settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
            
            # Create connect args for asyncpg
            connect_args = {}
            
            # Handle SSL for DigitalOcean or other cloud providers
            if "sslmode=require" in database_url:
                # Remove sslmode from URL as asyncpg handles it differently
                database_url = database_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
                
                # Check if SSL certificate exists
                ssl_cert_path = "/root/ca-certificate.crt"
                if os.path.exists(ssl_cert_path):
                    ssl_context = ssl.create_default_context(cafile=ssl_cert_path)
                    connect_args["ssl"] = ssl_context
                else:
                    # Use default SSL context for cloud databases
                    connect_args["ssl"] = "require"

            self.engine = create_async_engine(
                database_url,
                echo=self.settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args=connect_args
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database connection initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session as async context manager"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        async with self.session_factory() as session:
            yield session
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

async def init_database():
    """Initialize database for compatibility"""
    db_manager = DatabaseManager()
    await db_manager.initialize()
    return db_manager
