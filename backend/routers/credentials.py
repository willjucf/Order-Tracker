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


@router.get("", response_model=List[CredentialOut])
def get_credentials():
    """Get all saved credentials (no passwords returned)."""
    credentials = Credential.get_all()
    return [CredentialOut(email=c.email, provider=c.provider) for c in credentials]


@router.get("/with-password")
def get_credentials_with_password():
    """Get saved credentials with decrypted password (for auto-fill)."""
    credentials = Credential.get_all()
    if not credentials:
        return None
    cred = credentials[0]
    password = decrypt_password(cred.app_password_encrypted) if cred.app_password_encrypted else ""
    return {
        "email": cred.email,
        "provider": cred.provider,
        "password": password
    }


@router.post("")
def save_credentials(req: CredentialSaveRequest):
    """Save email credentials."""
    if req.remember:
        cred = Credential(
            email=req.email,
            provider=req.provider,
            app_password_encrypted=encrypt_password(req.password)
        )
        cred.save()
        return {"success": True}
    else:
        Credential.delete_all()
        return {"success": True}


@router.delete("")
def delete_credentials():
    """Delete all saved credentials."""
    Credential.delete_all()
    return {"success": True}
