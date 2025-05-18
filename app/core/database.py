from redis import Redis
from rq import Queue
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
import logging
import uuid
# from app.models.user import User  # Removed to fix circular import
# import Strategy, Order from their correct modules if needed

logger = logging.getLogger(__name__)

load_dotenv()

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Redis setup with error handling
try:
    redis_conn = Redis.from_url(REDIS_URL)
    order_queue = Queue("default", connection=redis_conn)
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    raise

# Create declarative base
Base = declarative_base()

# Create engine with connection pooling and timeout settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=True  # Enable SQL logging for debugging
)

# Create session factory with proper settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent expired object issues
)

def get_db() -> Session:
    """Get database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# Import all models here to ensure they're registered with Base
# from app.models import Strategy, Order  # Removed old import


def init_redis():
    """Initialize Redis connection and verify it's working"""
    try:
        redis_conn.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise

def init_db():
    """Initialize database by creating all tables"""
    try:
        # Import all models here so they are registered with Base
        from app.models.user import User
        from app.models.strategy import Strategy
        from app.models.order import Order
        
        # Drop all tables first to ensure clean state
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def generate_uuid() -> str:
    """Generate a UUID string for model IDs"""
    return str(uuid.uuid4())
