# integrations/crypto.py
import os
from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet():
    """Initialize the Fernet cipher with the master key from settings."""
    key = getattr(settings, "FERNET_KEY", None)
    if not key:
        raise ValueError("FERNET_KEY is missing from environment variables.")
    return Fernet(key.encode())


def encrypt_credential(value: str) -> str:
    """Encrypts a plaintext string into a secure token."""
    if not value:
        return value
    f = get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_credential(encrypted_value: str) -> str:
    """Decrypts a secure token back into plaintext."""
    if not encrypted_value:
        return encrypted_value
    f = get_fernet()
    try:
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        return ""  # Failsafe if token is corrupted
