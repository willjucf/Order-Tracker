"""Application configuration settings."""
import os
from pathlib import Path

# Application info
APP_NAME = "Order Tracker"
APP_VERSION = "1.2.3"
APP_FULL_NAME = f"{APP_NAME} by Willet"

# GitHub repo for updates
GITHUB_REPO = "willjucf/Order-Tracker"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"

# Get the app data directory for storing database and settings
def get_app_data_dir() -> Path:
    """Get the application data directory (persists across sessions)."""
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    app_dir = Path(app_data) / "WalmartOrderTracker"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

# Database path
DATABASE_PATH = get_app_data_dir() / "orders.db"

# Email provider settings
EMAIL_PROVIDERS = {
    "gmail": {
        "name": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "enabled": True
    },
    "outlook": {
        "name": "Outlook/Hotmail",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "enabled": True
    },
    "icloud": {
        "name": "iCloud",
        "imap_server": "imap.mail.me.com",
        "imap_port": 993,
        "enabled": True
    },
    "yahoo": {
        "name": "Yahoo",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "enabled": True
    },
    "aol": {
        "name": "AOL",
        "imap_server": "imap.aol.com",
        "imap_port": 993,
        "enabled": True
    }
}

# Extended search settings
EXTENDED_SEARCH_DAYS = 30  # Search for shipped/delivered emails up to X days after expected delivery

# Store configurations for sender filtering
STORE_CONFIGS = {
    "Walmart": {
        "sender_filter": "walmart",
        "enabled": True
    },
    "Sam's Club": {
        "sender_filter": "samsclub.com",
        "enabled": False
    },
    "Costco": {
        "sender_filter": "costco.com",
        "enabled": False
    },
    "Pokemon Center": {
        "sender_filter": "pokemoncenter.com",
        "enabled": False
    },
    "Amazon": {
        "sender_filter": "amazon.com",
        "enabled": False
    },
    "Target": {
        "sender_filter": "target",
        "enabled": True
    },
    "Best Buy": {
        "sender_filter": "bestbuy.com",
        "enabled": False
    }
}

# Backend server settings
BACKEND_PORT = 8420
