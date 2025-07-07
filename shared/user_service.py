"""
User Service - Manages user data and authentication
"""

import json
import logging
import redis
import psycopg2
from typing import List, Dict, Optional
from models_clean import User
from shared.database import get_db_session

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing users"""
    
    def __init__(self):
        # Redis connection for caching
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
    
    def get_active_users(self) -> List[Dict]:
        """Get all active users from PostgreSQL with Redis fallback"""
        try:
            # Try PostgreSQL first
            users = self._get_users_from_postgresql()
            if users:
                logger.info(f"✅ Retrieved {len(users)} active users from PostgreSQL")
                # Cache in Redis
                self._cache_users(users)
                return users
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL unavailable, trying Redis: {e}")
        
        # Fallback to Redis
        try:
            users = self._get_users_from_redis()
            if users:
                logger.info(f"✅ Retrieved {len(users)} active users from Redis cache")
                return users
        except Exception as e:
            logger.error(f"❌ Both PostgreSQL and Redis unavailable: {e}")
        
        return []
    
    def _get_users_from_postgresql(self) -> List[Dict]:
        """Get active users from PostgreSQL"""
        try:
            with get_db_session() as session:
                # Query users with status = 'ACTIVE'
                users = session.query(User).filter(User.status == 'ACTIVE').all()
                
                user_list = []
                for user in users:
                    user_dict = {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'status': user.status,
                        'role': user.role,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                        'updated_at': user.updated_at.isoformat() if user.updated_at else None
                    }
                    user_list.append(user_dict)
                
                return user_list
                
        except Exception as e:
            logger.error(f"❌ Error fetching users from PostgreSQL: {e}")
            raise
    
    def _get_users_from_redis(self) -> List[Dict]:
        """Get users from Redis cache"""
        try:
            cached_users = self.redis_client.get('active_users')
            if cached_users:
                return json.loads(cached_users)
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching users from Redis: {e}")
            return []
    
    def _cache_users(self, users: List[Dict]):
        """Cache users in Redis"""
        try:
            self.redis_client.setex('active_users', 300, json.dumps(users))  # Cache for 5 minutes
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache users in Redis: {e}")
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get a specific user by ID"""
        try:
            with get_db_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'status': user.status,
                        'role': user.role,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                        'updated_at': user.updated_at.isoformat() if user.updated_at else None
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Error fetching user {user_id}: {e}")
            return None 