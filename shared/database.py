"""
Centralized Database Connection Manager
Provides a single point of database access for the entire system
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Centralized database connection manager"""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection with connection pooling"""
        try:
            # Database URL from environment variable only
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                logger.error("❌ DATABASE_URL environment variable not set")
                raise ValueError("DATABASE_URL environment variable is required")
            
            # Create engine with connection pooling
            self._engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=5,  # Number of connections to maintain
                max_overflow=10,  # Additional connections that can be created
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False  # Set to True for SQL debugging
            )
            
            # Create session factory
            self._session_factory = sessionmaker(bind=self._engine)
            
            # Create scoped session for thread safety
            self._scoped_session = scoped_session(self._session_factory)
            
            logger.info("✅ Database connection manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connection manager: {e}")
            raise
    
    @property
    def engine(self):
        """Get the database engine"""
        return self._engine
    
    @property
    def session_factory(self):
        """Get the session factory"""
        return self._session_factory
    
    @property
    def scoped_session(self):
        """Get the scoped session (thread-safe)"""
        return self._scoped_session
    
    @contextmanager
    def get_session(self) -> Generator:
        """Get a database session with automatic cleanup"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_scoped_session(self) -> Generator:
        """Get a scoped database session with automatic cleanup"""
        session = self._scoped_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Database scoped session error: {e}")
            raise
        finally:
            self._scoped_session.remove()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close all database connections"""
        try:
            if self._engine:
                self._engine.dispose()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for easy access
def get_db_session():
    """Get a database session"""
    return db_manager.get_session()

def get_db_scoped_session():
    """Get a scoped database session"""
    return db_manager.get_scoped_session()

def get_db_engine():
    """Get the database engine"""
    return db_manager.engine

def test_db_connection():
    """Test database connection"""
    return db_manager.test_connection()

def close_db_connections():
    """Close all database connections"""
    db_manager.close() 