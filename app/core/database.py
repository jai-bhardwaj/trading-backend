from redis import Redis
from rq import Queue
import os
from dotenv import load_dotenv
from app.database import Base, engine, SessionLocal, get_db
import logging

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

# Import all models here to ensure they're registered with Base
from app.models import User, Strategy, Order


def init_redis():
    """Initialize Redis connection and verify it's working"""
    try:
        redis_conn.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise
