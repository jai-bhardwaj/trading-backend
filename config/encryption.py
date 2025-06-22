"""
Production Encryption Utilities
Secure encryption/decryption for user credentials and sensitive data
"""

import os
import base64
import logging
from typing import str
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class ProductionEncryption:
    """Production-grade encryption for user credentials"""
    
    def __init__(self):
        self._fernet = None
        self._key = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with environment-based key"""
        # Get encryption key from environment
        encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if encryption_key:
            # Use provided key
            self._key = encryption_key.encode()
        else:
            # Generate key from master password + salt
            master_password = os.getenv('MASTER_PASSWORD', 'default-change-me-in-production')
            salt = os.getenv('ENCRYPTION_SALT', 'trading-backend-salt-2024').encode()
            
            if master_password == 'default-change-me-in-production':
                logger.warning("⚠️ Using default master password - change in production!")
            
            # Generate key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self._key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        
        self._fernet = Fernet(self._key)
        logger.info("✅ Encryption initialized")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            raise

# Global encryption instance
_encryption_instance = None

def get_encryption_instance() -> ProductionEncryption:
    """Get global encryption instance"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = ProductionEncryption()
    return _encryption_instance

def encrypt_user_data(data: str) -> str:
    """Encrypt user data"""
    encryption = get_encryption_instance()
    return encryption.encrypt_data(data)

def decrypt_user_data(encrypted_data: str) -> str:
    """Decrypt user data"""
    encryption = get_encryption_instance()
    return encryption.decrypt_data(encrypted_data)

# Utility functions for credential management
def encrypt_angel_one_credentials(api_key: str, password: str, totp_secret: str) -> dict:
    """Encrypt Angel One credentials for storage"""
    return {
        'encrypted_api_key': encrypt_user_data(api_key),
        'encrypted_password': encrypt_user_data(password),
        'encrypted_totp_secret': encrypt_user_data(totp_secret)
    }

def decrypt_angel_one_credentials(encrypted_creds: dict) -> dict:
    """Decrypt Angel One credentials"""
    return {
        'api_key': decrypt_user_data(encrypted_creds['encrypted_api_key']),
        'password': decrypt_user_data(encrypted_creds['encrypted_password']),
        'totp_secret': decrypt_user_data(encrypted_creds['encrypted_totp_secret'])
    } 