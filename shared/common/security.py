"""
Security Module - Enhanced authentication, authorization, and data protection
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Enhanced security management"""
    
    def __init__(self, redis_client: redis.Redis, secret_key: str):
        self.redis_client = redis_client
        self.secret_key = secret_key
        self.cipher_suite = Fernet(Fernet.generate_key())
        
    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_hex = hashed.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(hash_obj.hex(), hash_hex)
        except:
            return False
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    async def create_secure_session(self, user_id: str, permissions: List[str]) -> Dict:
        """Create secure session with enhanced security"""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        # Create JWT with minimal payload
        payload = {
            "sub": user_id,
            "sid": session_id,
            "permissions": permissions,
            "iat": now,
            "exp": now + timedelta(hours=1),  # Short-lived access token
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation
        }
        
        access_token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        
        # Store session in Redis with security metadata
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": permissions,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "ip_address": None,  # Will be set by middleware
            "user_agent": None,  # Will be set by middleware
            "is_active": True
        }
        
        await self.redis_client.setex(
            f"session:{session_id}",
            3600,  # 1 hour TTL
            str(session_data)
        )
        
        return {
            "access_token": access_token,
            "session_id": session_id,
            "expires_in": 3600
        }
    
    async def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session with enhanced checks"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            session_id = payload.get("sid")
            
            if not session_id:
                return None
            
            # Check if session is revoked
            session_data = await self.redis_client.get(f"session:{session_id}")
            if not session_data:
                return None
            
            # Update last activity
            await self.redis_client.setex(
                f"session:{session_id}",
                3600,
                session_data
            )
            
            return {
                "user_id": payload.get("sub"),
                "permissions": payload.get("permissions", []),
                "session_id": session_id
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    async def revoke_session(self, session_id: str):
        """Revoke session"""
        await self.redis_client.delete(f"session:{session_id}")

class RateLimiter:
    """Enhanced rate limiting with user-specific limits"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def is_allowed(self, user_id: str, action: str, limit: int = 100, window: int = 60) -> bool:
        """Check if user is within rate limit for specific action"""
        key = f"rate_limit:{user_id}:{action}"
        now = time.time()
        
        # Get current count
        current = await self.redis_client.get(key)
        if current:
            count = int(current)
            if count >= limit:
                return False
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        
        return True
    
    async def get_user_limits(self, user_id: str) -> Dict:
        """Get current rate limit status for user"""
        limits = {
            "orders": {"limit": 100, "window": 60},
            "api_calls": {"limit": 1000, "window": 60},
            "login_attempts": {"limit": 5, "window": 300}
        }
        
        result = {}
        for action, config in limits.items():
            key = f"rate_limit:{user_id}:{action}"
            current = await self.redis_client.get(key)
            result[action] = {
                "current": int(current) if current else 0,
                "limit": config["limit"],
                "remaining": max(0, config["limit"] - (int(current) if current else 0))
            }
        
        return result

class InputValidator:
    """Enhanced input validation and sanitization"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """Validate trading symbol"""
        if not symbol or len(symbol) > 20:
            return False
        return symbol.replace("_", "").replace("-", "").isalnum()
    
    @staticmethod
    def validate_quantity(quantity: int) -> bool:
        """Validate order quantity"""
        return isinstance(quantity, int) and 1 <= quantity <= 1000000
    
    @staticmethod
    def validate_price(price: float) -> bool:
        """Validate order price"""
        return isinstance(price, (int, float)) and 0 < price <= 100000
    
    @staticmethod
    def validate_order_request(data: Dict) -> Dict:
        """Validate complete order request"""
        errors = []
        
        if not InputValidator.validate_symbol(data.get("symbol", "")):
            errors.append("Invalid symbol")
        
        if not InputValidator.validate_quantity(data.get("quantity", 0)):
            errors.append("Invalid quantity")
        
        if not InputValidator.validate_price(data.get("price", 0)):
            errors.append("Invalid price")
        
        if data.get("side") not in ["BUY", "SELL"]:
            errors.append("Invalid order side")
        
        if data.get("order_type") not in ["MARKET", "LIMIT", "STOP_LOSS"]:
            errors.append("Invalid order type")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

class AuditLogger:
    """Security audit logging"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def log_security_event(self, event_type: str, user_id: str, details: Dict):
        """Log security event"""
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        
        # Store in Redis for audit trail
        await self.redis_client.lpush("security_audit", str(event))
        await self.redis_client.ltrim("security_audit", 0, 9999)  # Keep last 10k events
        
        logger.warning(f"Security event: {event_type} for user {user_id}")
    
    async def log_login_attempt(self, user_id: str, success: bool, ip_address: str = None):
        """Log login attempt"""
        await self.log_security_event(
            "login_attempt",
            user_id,
            {
                "success": success,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def log_order_placement(self, user_id: str, order_id: str, order_details: Dict):
        """Log order placement"""
        await self.log_security_event(
            "order_placement",
            user_id,
            {
                "order_id": order_id,
                "order_details": order_details,
                "timestamp": datetime.utcnow().isoformat()
            }
        ) 