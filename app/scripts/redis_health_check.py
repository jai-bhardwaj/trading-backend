import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    r = redis.from_url(redis_url)
    pong = r.ping()
    if pong:
        print("✅ Redis connection successful.")
    else:
        print("❌ Redis connection failed (no PONG).")
        exit(1)
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    exit(1) 