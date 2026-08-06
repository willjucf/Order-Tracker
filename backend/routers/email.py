"""Email connection router."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.email_client.providers import get_client
from utils.config import EMAIL_PROVIDERS

router = APIRouter(prefix="/api/email", tags=["email"])

# Global email client state
_email_client = None
_connected_email = ""


class ConnectRequest(BaseModel):
    email: str
    password: str
    provider: str
    # Only used by custom_connection providers (e.g. AYCD Inbox's local IMAP server).
    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: Optional[bool] = None


class ConnectResponse(BaseModel):
    success: bool
    message: str


@router.post("/connect", response_model=ConnectResponse)
def connect(req: ConnectRequest):
    """Connect to email server."""
    global _email_client, _connected_email

    # Disconnect existing connection
    if _email_client:
        try:
            _email_client.disconnect()
        except Exception:
            pass

    client = get_client(
        req.provider, req.email, req.password,
        host=req.host, port=req.port, use_ssl=req.use_ssl,
    )
    if not client:
        raise HTTPException(status_code=400, detail="Provider not available")

    if client.connect():
        _email_client = client
        _connected_email = req.email
        return ConnectResponse(success=True, message="Connected!")
    else:
        detail = client.last_error or "Connection failed. Check credentials."
        raise HTTPException(status_code=401, detail=detail)


@router.post("/disconnect", response_model=ConnectResponse)
def disconnect():
    """Disconnect from email server."""
    global _email_client, _connected_email

    if _email_client:
        try:
            _email_client.disconnect()
        except Exception:
            pass
        _email_client = None
        _connected_email = ""

    return ConnectResponse(success=True, message="Disconnected")


@router.get("/status")
def status():
    """Get connection status."""
    return {
        "connected": _email_client is not None and _email_client.connected,
        "email": _connected_email
    }


def get_email_client():
    """Get the current email client (used by scan router)."""
    return _email_client


def get_connected_email():
    """Get the currently connected email address."""
    return _connected_email
