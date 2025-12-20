"""
Encryption utilities for sensitive configuration data.
"""

import os
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode
import logging

logger = logging.getLogger(__name__)


class ConfigEncryption:
    """Handles encryption/decryption of sensitive config data."""
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize encryption with key.
        
        Args:
            encryption_key: Base64-encoded Fernet key. 
                          If None, uses ENCRYPTION_KEY env var.
        """
        if encryption_key is None:
            encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if not encryption_key:
            # Generate new key if none exists (dev only!)
            logger.warning("No ENCRYPTION_KEY found, generating new key. Set this in production!")
            encryption_key = Fernet.generate_key().decode()
            logger.info(f"Generated key: {encryption_key}")
        
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return b64encode(encrypted_bytes).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""
        
        try:
            encrypted_bytes = b64decode(encrypted.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data. Key may have changed.")


# Global instance
_encryption = None


def get_encryption() -> ConfigEncryption:
    """Get or create global encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = ConfigEncryption()
    return _encryption


def encrypt_value(value: str) -> str:
    """Convenience function to encrypt a value."""
    return get_encryption().encrypt(value)


def decrypt_value(encrypted: str) -> str:
    """Convenience function to decrypt a value."""
    return get_encryption().decrypt(encrypted)
