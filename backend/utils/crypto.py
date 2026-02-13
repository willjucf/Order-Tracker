"""Encryption utilities for credential storage."""
import base64
import hashlib
import platform
from cryptography.fernet import Fernet


def get_encryption_key() -> bytes:
    """Generate a machine-specific encryption key."""
    key_material = f"{platform.node()}-walmart-tracker-key"
    key_hash = hashlib.sha256(key_material.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


def encrypt_password(password: str) -> bytes:
    """Encrypt password for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(password.encode())


def decrypt_password(encrypted: bytes) -> str:
    """Decrypt stored password."""
    try:
        fernet = Fernet(get_encryption_key())
        return fernet.decrypt(encrypted).decode()
    except Exception:
        return ""
