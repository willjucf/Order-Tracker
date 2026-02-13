"""Theme management router."""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from utils.config import get_app_data_dir

router = APIRouter(prefix="/api/themes", tags=["themes"])


def _get_backgrounds_dir() -> Path:
    """Get the backgrounds directory."""
    bg_dir = get_app_data_dir() / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    return bg_dir


@router.post("/upload-bg")
async def upload_background(file: UploadFile = File(...)):
    """Upload a custom background image."""
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Use JPEG, PNG, WebP, or GIF.")

    bg_dir = _get_backgrounds_dir()
    # Save as 'custom_bg' with original extension
    ext = Path(file.filename).suffix if file.filename else ".png"
    save_path = bg_dir / f"custom_bg{ext}"

    # Remove any existing custom backgrounds
    for existing in bg_dir.glob("custom_bg.*"):
        existing.unlink()

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {"path": str(save_path)}


@router.delete("/bg")
def delete_background():
    """Delete the custom background image."""
    bg_dir = _get_backgrounds_dir()
    for existing in bg_dir.glob("custom_bg.*"):
        existing.unlink()
    return {"success": True}


@router.get("/bg")
def get_background():
    """Get the current custom background path."""
    bg_dir = _get_backgrounds_dir()
    for existing in bg_dir.glob("custom_bg.*"):
        return {"path": str(existing)}
    return {"path": None}
