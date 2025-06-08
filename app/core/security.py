"""
Security utilities for Trading Engine
Handles encryption/decryption of sensitive data like broker credentials.
"""

import os
import base64
import logging
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialCipher:
    """
    Handles encryption and decryption of sensitive credentials
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize cipher with master key
        
        Args:
            master_key: Master encryption key (if None, will use environment variable)
        """
        self._master_key = master_key or os.getenv('MASTER_ENCRYPTION_KEY')
        if not self._master_key:
            raise ValueError("Master encryption key not provided. Set MASTER_ENCRYPTION_KEY environment variable.")
        
        self._cipher = self._create_cipher()
    
    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from master key"""
        try:
            # Create salt for key derivation (in production, store this securely)
            salt = b'trading_engine_salt_v1'  # This should be random and stored securely
            
            # Derive key from master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,  # Adjust based on security requirements
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
            return Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to create cipher: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            if not plaintext:
                return ""
            
            encrypted_bytes = self._cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        try:
            if not ciphertext:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self._cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted
        
        Args:
            data: String to check
            
        Returns:
            True if data appears encrypted
        """
        try:
            # Try to decrypt - if it works, it's encrypted
            self.decrypt(data)
            return True
        except:
            return False


# Global cipher instance
_cipher: Optional[CredentialCipher] = None


def get_cipher() -> CredentialCipher:
    """Get global cipher instance"""
    global _cipher
    if _cipher is None:
        _cipher = CredentialCipher()
    return _cipher


def encrypt_credential(credential: str) -> str:
    """
    Encrypt a credential string
    
    Args:
        credential: Credential to encrypt
        
    Returns:
        Encrypted credential
    """
    return get_cipher().encrypt(credential)


def decrypt_credential(encrypted_credential: str) -> str:
    """
    Decrypt an encrypted credential
    
    Args:
        encrypted_credential: Encrypted credential
        
    Returns:
        Decrypted credential
    """
    return get_cipher().decrypt(encrypted_credential)


def secure_broker_credentials(api_key: str, password: str, totp_secret: str) -> dict:
    """
    Encrypt broker credentials for secure storage
    
    Args:
        api_key: Broker API key
        password: Broker password
        totp_secret: TOTP secret
        
    Returns:
        Dictionary with encrypted credentials
    """
    try:
        cipher = get_cipher()
        
        return {
            'api_key': cipher.encrypt(api_key),
            'password': cipher.encrypt(password),
            'totp_secret': cipher.encrypt(totp_secret)
        }
        
    except Exception as e:
        logger.error(f"Failed to secure broker credentials: {e}")
        raise


def retrieve_broker_credentials(encrypted_credentials: dict) -> dict:
    """
    Decrypt broker credentials for use
    
    Args:
        encrypted_credentials: Dictionary with encrypted credentials
        
    Returns:
        Dictionary with decrypted credentials
    """
    try:
        cipher = get_cipher()
        
        return {
            'api_key': cipher.decrypt(encrypted_credentials['api_key']),
            'password': cipher.decrypt(encrypted_credentials['password']),
            'totp_secret': cipher.decrypt(encrypted_credentials['totp_secret'])
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve broker credentials: {e}")
        raise


def generate_master_key() -> str:
    """
    Generate a new master encryption key
    
    Returns:
        Base64 encoded master key
    """
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode()


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at the end
        
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    return mask_char * (len(data) - visible_chars) + data[-visible_chars:]


# Environment check and warnings
def check_security_configuration():
    """Check and log security configuration status"""
    try:
        # Check if master key is set
        master_key = os.getenv('MASTER_ENCRYPTION_KEY')
        if not master_key:
            logger.warning("⚠️ MASTER_ENCRYPTION_KEY not set - credential encryption will not work")
            return False
        
        # Test encryption/decryption
        cipher = CredentialCipher(master_key)
        test_data = "test_encryption"
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        
        if decrypted != test_data:
            logger.error("❌ Encryption test failed - master key may be corrupted")
            return False
        
        logger.info("✅ Security configuration validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Security configuration check failed: {e}")
        return False


# Auto-check on import in development
if os.getenv('ENVIRONMENT', 'development') == 'development':
    try:
        check_security_configuration()
    except:
        pass  # Don't fail on import in development 