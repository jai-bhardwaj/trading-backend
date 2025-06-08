import os
import logging
import redis
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    r = redis.from_url(redis_url)
    pong = r.ping()
    if pong:
        logger.info("✅ Redis connection successful.")
    else:
        logger.error("❌ Redis connection failed (no PONG).")
        exit(1)
except Exception as e:
    logger.error(f"❌ Redis connection failed: {e}")
    exit(1) 