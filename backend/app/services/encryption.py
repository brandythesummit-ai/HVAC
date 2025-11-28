"""Credential encryption utilities using Fernet."""
from cryptography.fernet import Fernet
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self):
        """Initialize with encryption key from settings."""
        self.cipher = Fernet(settings.encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string."""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string."""
        if not ciphertext:
            return ""
        decrypted = self.cipher.decrypt(ciphertext.encode())
        return decrypted.decode()


# Global encryption service instance
encryption_service = EncryptionService()
