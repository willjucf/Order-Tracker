"""Email provider registry and factory."""
from typing import Optional, Dict

from services.email_client.base_client import BaseEmailClient
from services.email_client.imap_client import ImapClient
from utils.config import EMAIL_PROVIDERS


def get_client(provider: str, email: str, app_password: str) -> Optional[BaseEmailClient]:
    """
    Factory function to get an email client for the specified provider.

    Args:
        provider: Provider key (e.g., 'gmail', 'outlook')
        email: Email address
        app_password: App password for authentication

    Returns:
        Email client instance or None if provider not found/disabled
    """
    provider = provider.lower()

    # Check if provider is configured and enabled
    if provider not in EMAIL_PROVIDERS:
        print(f"Unknown provider: {provider}")
        return None

    if not EMAIL_PROVIDERS[provider].get("enabled", False):
        print(f"Provider not enabled: {provider}")
        return None

    # Create and return the generic IMAP client with provider config
    return ImapClient(email, app_password, provider)


def get_enabled_providers() -> Dict[str, dict]:
    """Get all enabled email providers."""
    return {
        key: config
        for key, config in EMAIL_PROVIDERS.items()
        if config.get("enabled", False)
    }


def get_all_providers() -> Dict[str, dict]:
    """Get all configured email providers (enabled and disabled)."""
    return EMAIL_PROVIDERS.copy()
