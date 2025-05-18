from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
import logging
# from app.models.user import User  # Removed to fix circular import
# import Strategy, Order from their correct modules if needed

logger = logging.getLogger(__name__)

# Use DATABASE_URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create engine with connection pooling and timeout settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
)

# Create session factory with proper settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent expired object issues
)

# Create declarative base
Base = declarative_base()


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


def init_db():
    """Initialize database by creating all tables"""
    try:
        # Import all models here so they are registered with Base
        from app.models.user import User
        from app.models.strategy import Strategy
        from app.models.order import Order
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


# Initialize database on module import
init_db()
