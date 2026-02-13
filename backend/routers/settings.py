"""User settings/preferences router - stored in appdata."""
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from utils.config import get_app_data_dir

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_FILE = get_app_data_dir() / "settings.json"


def _load_settings() -> dict:
    """Load settings from JSON file."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_settings(data: dict):
    """Save settings to JSON file."""
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


class SettingsUpdate(BaseModel):
    username: Optional[str] = None
    theme: Optional[str] = None
    panelOpacity: Optional[float] = None


@router.get("")
def get_settings():
    """Get all user settings."""
    return _load_settings()


@router.put("")
def update_settings(update: SettingsUpdate):
    """Update user settings (partial update)."""
    settings = _load_settings()
    for key, value in update.model_dump(exclude_none=True).items():
        settings[key] = value
    _save_settings(settings)
    return settings
