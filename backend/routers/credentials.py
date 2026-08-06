"""Credentials management router."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from services.database.models import Credential
from utils.crypto import encrypt_password, decrypt_password

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


class CredentialOut(BaseModel):
    email: str
    provider: str


class CredentialSaveRequest(BaseModel):
    email: str
    provider: str
    password: str
    remember: bool = True
    # Only used by custom_connection providers (e.g. AYCD Inbox's local IMAP server).
    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: Optional[bool] = None


@router.get("", response_model=List[CredentialOut])
def get_credentials():
    """Get all saved credentials (no passwords returned)."""
    credentials = Credential.get_all()
    return [CredentialOut(email=c.email, provider=c.provider) for c in credentials]


@router.get("/with-password")
def get_credentials_with_password(provider: Optional[str] = None):
    """Get saved credentials with decrypted password (for auto-fill).

    With no ``provider``, returns the most recently saved credential (used on startup).
    With a ``provider``, returns that provider's most recent saved credential (or null),
    so switching the provider dropdown recalls the matching login instead of leaving
    another provider's values in the fields.
    """
    if provider:
        cred = Credential.get_by_provider(provider)
    else:
        credentials = Credential.get_all()
        cred = credentials[0] if credentials else None
    if not cred:
        return None
    password = decrypt_password(cred.app_password_encrypted) if cred.app_password_encrypted else ""
    return {
        "email": cred.email,
        "provider": cred.provider,
        "password": password,
        "host": cred.host,
        "port": cred.port,
        "use_ssl": cred.use_ssl,
    }


@router.post("")
def save_credentials(req: CredentialSaveRequest):
    """Save email credentials."""
    if req.remember:
        cred = Credential(
            email=req.email,
            provider=req.provider,
            app_password_encrypted=encrypt_password(req.password),
            host=req.host,
            port=req.port,
            use_ssl=req.use_ssl,
        )
        cred.save()
        return {"success": True}
    else:
        # Forget only this login, not every provider's saved credentials.
        Credential.delete_by_email(req.email)
        return {"success": True}


@router.delete("")
def delete_credentials():
    """Delete all saved credentials."""
    Credential.delete_all()
    return {"success": True}
