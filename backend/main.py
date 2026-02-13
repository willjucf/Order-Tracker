"""FastAPI backend for Order Tracker."""
import sys
import os
import urllib.request
import json

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from services.database.db import init_database
from utils.config import APP_VERSION, GITHUB_REPO, GITHUB_RELEASES_URL, EMAIL_PROVIDERS, STORE_CONFIGS

from routers import email, scan, data, credentials, themes, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_database()
    yield


app = FastAPI(
    title="Order Tracker API",
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS - allow Electron renderer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(email.router)
app.include_router(scan.router)
app.include_router(data.router)
app.include_router(credentials.router)
app.include_router(themes.router)
app.include_router(settings.router)


@app.get("/api/providers")
def get_providers():
    """Get available email providers."""
    return {
        key: {"name": config["name"], "enabled": config["enabled"]}
        for key, config in EMAIL_PROVIDERS.items()
    }


@app.get("/api/stores")
def get_stores():
    """Get available stores."""
    return {
        name: {"senderFilter": config["sender_filter"], "enabled": config["enabled"]}
        for name, config in STORE_CONFIGS.items()
    }


@app.get("/api/update-check")
def check_for_updates():
    """Check GitHub for new releases."""
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'OrderTracker'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            release_data = json.loads(response.read().decode('utf-8'))
            latest_version = release_data.get('tag_name', '').lstrip('v')

            if latest_version and _is_newer(latest_version, APP_VERSION):
                return {
                    "updateAvailable": True,
                    "latestVersion": latest_version,
                    "downloadUrl": GITHUB_RELEASES_URL,
                }
    except Exception:
        pass

    return {
        "updateAvailable": False,
        "latestVersion": APP_VERSION,
        "downloadUrl": GITHUB_RELEASES_URL,
    }


@app.get("/api/backgrounds/{filename}")
def serve_background(filename: str):
    """Serve background image files."""
    from utils.config import get_app_data_dir
    file_path = get_app_data_dir() / "backgrounds" / filename
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "Not found"}


def _is_newer(latest: str, current: str) -> bool:
    """Compare version strings."""
    try:
        latest_parts = [int(x) for x in latest.split('.')]
        current_parts = [int(x) for x in current.split('.')]
        while len(latest_parts) < len(current_parts):
            latest_parts.append(0)
        while len(current_parts) < len(latest_parts):
            current_parts.append(0)
        return latest_parts > current_parts
    except ValueError:
        return False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8420)
