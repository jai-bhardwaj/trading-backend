"""
Secure Authentication Module for Trading System
JWT-based authentication with rate limiting and security features
"""

import jwt
import hashlib
import secrets
import time
import redis.asyncio as redis
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

class TokenData(BaseModel):
    """JWT token data structure"""
    user_id: str
    email: str
    permissions: List[str]
    token_type: str  # "access" or "refresh"
    exp: int
    iat: int
    jti: str  # JWT ID for revocation

class SecurityConfig:
    """Security configuration"""
    JWT_SECRET_KEY = secrets.token_urlsafe(32)  # Generate secure secret key
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_COOLDOWN_MINUTES = 15
    API_RATE_LIMIT_PER_MINUTE = 60
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

class SecurityHeaders:
    """Security headers management class"""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers"""
        return SecurityConfig.SECURITY_HEADERS.copy()
    
    @staticmethod
    def apply_headers(response, headers: Dict[str, str] = None):
        """Apply security headers to response"""
        headers_to_apply = headers or SecurityConfig.SECURITY_HEADERS
        for header_name, header_value in headers_to_apply.items():
            response.headers[header_name] = header_value
        return response

class RateLimiter:
    """Rate limiting functionality"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.redis_client = None
        self.config = SecurityConfig()
        
        # In-memory fallback
        self.requests = {}
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis_client.ping()
            logger.info("✅ RateLimiter Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable for rate limiting, using in-memory fallback: {e}")
            self.redis_client = None
    
    async def check_rate_limit(self, identifier: str, limit: int = 60, window: int = 60) -> bool:
        """Check if request is within rate limits"""
        current_time = int(time.time())
        
        try:
            if self.redis_client:
                key = f"rate_limit:{identifier}"
                async with self.redis_client.pipeline() as pipe:
                    pipe.zremrangebyscore(key, 0, current_time - window)
                    pipe.zadd(key, {str(current_time): current_time})
                    pipe.zcard(key)
                    pipe.expire(key, window)
                    
                    results = await pipe.execute()
                    request_count = results[2]
                    
                return request_count <= limit
            else:
                # In-memory fallback
                requests = self.requests.get(identifier, [])
                requests = [t for t in requests if current_time - t < window]
                requests.append(current_time)
                self.requests[identifier] = requests
                
                return len(requests) <= limit
                
        except Exception as e:
            logger.error(f"❌ Rate limit check error: {e}")
            return True

class AuthManager:
    """Secure JWT-based authentication system"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.config = SecurityConfig()
        self.redis_url = redis_url
        self.redis_client = None
        
        # In-memory fallback for rate limiting (if Redis unavailable)
        self.login_attempts = {}
        self.api_requests = {}
        
    async def initialize(self):
        """Initialize Redis connection for session management"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis_client.ping()
            logger.info("✅ Authentication Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable for auth, using in-memory fallback: {e}")
            self.redis_client = None
    
    def create_access_token(self, user_id: str, email: str, permissions: List[str] = None) -> str:
        """Create secure JWT access token"""
        if permissions is None:
            permissions = ["user:read", "user:trade"]
        
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        token_data = {
            "user_id": user_id,
            "email": email,
            "permissions": permissions,
            "token_type": "access",
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": secrets.token_urlsafe(16)  # Unique token ID
        }
        
        return jwt.encode(
            token_data, 
            self.config.JWT_SECRET_KEY, 
            algorithm=self.config.JWT_ALGORITHM
        )
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create refresh token for long-term authentication"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        
        token_data = {
            "user_id": user_id,
            "email": email,
            "permissions": ["token:refresh"],
            "token_type": "refresh", 
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": secrets.token_urlsafe(16)
        }
        
        return jwt.encode(
            token_data,
            self.config.JWT_SECRET_KEY,
            algorithm=self.config.JWT_ALGORITHM
        )
    
    async def validate_token(self, token: str) -> Optional[TokenData]:
        """Validate JWT token with security checks"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.config.JWT_SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM]
            )
            
            # Check if token is revoked
            if await self._is_token_revoked(payload.get("jti")):
                logger.warning(f"🚫 Revoked token used: {payload.get('jti')}")
                return None
            
            # Validate token structure
            required_fields = ["user_id", "email", "permissions", "token_type", "exp", "iat", "jti"]
            if not all(field in payload for field in required_fields):
                logger.warning(f"🚫 Invalid token structure")
                return None
            
            # Create token data object
            token_data = TokenData(
                user_id=payload["user_id"],
                email=payload["email"],
                permissions=payload["permissions"],
                token_type=payload["token_type"],
                exp=payload["exp"],
                iat=payload["iat"],
                jti=payload["jti"]
            )
            
            return token_data
            
        except jwt.ExpiredSignatureError:
            logger.warning("🚫 Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"🚫 Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            return None
    
    async def revoke_token(self, jti: str, expire_time: int = None):
        """Revoke a token by adding it to blacklist"""
        if expire_time is None:
            expire_time = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
        
        try:
            if self.redis_client:
                await self.redis_client.setex(
                    f"revoked_token:{jti}",
                    expire_time - int(datetime.now(timezone.utc).timestamp()),
                    "revoked"
                )
            else:
                # In-memory fallback
                self.revoked_tokens = getattr(self, 'revoked_tokens', {})
                self.revoked_tokens[jti] = expire_time
                
        except Exception as e:
            logger.error(f"❌ Error revoking token: {e}")
    
    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        try:
            if self.redis_client:
                result = await self.redis_client.get(f"revoked_token:{jti}")
                return result is not None
            else:
                # In-memory fallback
                revoked_tokens = getattr(self, 'revoked_tokens', {})
                expire_time = revoked_tokens.get(jti)
                if expire_time and expire_time > int(datetime.now(timezone.utc).timestamp()):
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ Error checking token revocation: {e}")
            return False
    
    async def check_rate_limit(self, identifier: str, request_type: str = "api") -> bool:
        """Check if request is within rate limits"""
        try:
            current_time = int(time.time())
            
            if request_type == "login":
                # Login rate limiting
                key = f"login_attempts:{identifier}"
                window_seconds = self.config.LOGIN_COOLDOWN_MINUTES * 60
                max_attempts = self.config.MAX_LOGIN_ATTEMPTS
            else:
                # API rate limiting
                key = f"api_requests:{identifier}"
                window_seconds = 60  # 1 minute window
                max_attempts = self.config.API_RATE_LIMIT_PER_MINUTE
            
            if self.redis_client:
                # Use Redis sliding window
                async with self.redis_client.pipeline() as pipe:
                    # Remove old entries
                    pipe.zremrangebyscore(key, 0, current_time - window_seconds)
                    # Add current request
                    pipe.zadd(key, {str(current_time): current_time})
                    # Count requests in window
                    pipe.zcard(key)
                    # Set expiry
                    pipe.expire(key, window_seconds)
                    
                    results = await pipe.execute()
                    request_count = results[2]
                    
                return request_count <= max_attempts
            else:
                # In-memory fallback
                if request_type == "login":
                    attempts = self.login_attempts.get(identifier, [])
                else:
                    attempts = self.api_requests.get(identifier, [])
                
                # Clean old attempts
                attempts = [t for t in attempts if current_time - t < window_seconds]
                
                # Add current attempt
                attempts.append(current_time)
                
                # Store back
                if request_type == "login":
                    self.login_attempts[identifier] = attempts
                else:
                    self.api_requests[identifier] = attempts
                
                return len(attempts) <= max_attempts
                
        except Exception as e:
            logger.error(f"❌ Rate limit check error: {e}")
            return True  # Allow on error to prevent service disruption
    
    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct IP
        return request.client.host if request.client else "unknown"
    
    def hash_api_key(self, api_key: str) -> str:
        """Securely hash API key for storage"""
        salt = secrets.token_hex(16)
        hash_value = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_value.hex()}"
    
    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify API key against stored hash"""
        try:
            salt, hash_value = stored_hash.split(':')
            computed_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt.encode(), 100000)
            return computed_hash.hex() == hash_value
        except Exception:
            return False

# Global authenticator instance
_authenticator = None

async def get_authenticator() -> AuthManager:
    """Get global authenticator instance"""
    global _authenticator
    if _authenticator is None:
        _authenticator = AuthManager()
        await _authenticator.initialize()
    return _authenticator

def get_auth_manager() -> AuthManager:
    """Get global auth manager instance (synchronous version)"""
    global _authenticator
    if _authenticator is None:
        _authenticator = AuthManager()
        # Note: Redis initialization will happen on first use
    return _authenticator

# Security middleware
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    for header_name, header_value in SecurityConfig.SECURITY_HEADERS.items():
        response.headers[header_name] = header_value
    
    return response

# Rate limiting decorator
def rate_limit(request_type: str = "api"):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                authenticator = await get_authenticator()
                client_id = authenticator.get_client_identifier(request)
                
                if not await authenticator.check_rate_limit(client_id, request_type):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Try again later."
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 