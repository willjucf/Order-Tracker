"""Email provider registry and factory."""
from typing import Optional, Dict

from services.email_client.base_client import BaseEmailClient
from services.email_client.imap_client import ImapClient
from utils.config import EMAIL_PROVIDERS


def get_client(
    provider: str,
    email: str,
    app_password: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    use_ssl: Optional[bool] = None,
) -> Optional[BaseEmailClient]:
    """
    Factory function to get an email client for the specified provider.

    Args:
        provider: Provider key (e.g., 'gmail', 'outlook')
        email: Email address
        app_password: App password for authentication
        host: Optional IMAP host override (only honored for custom_connection providers)
        port: Optional IMAP port override (only honored for custom_connection providers)
        use_ssl: Optional TLS/SSL override (only honored for custom_connection providers).
            AYCD's local IMAP server is plaintext (False); its UpLink remote endpoint is
            typically TLS (True).

    Returns:
        Email client instance or None if provider not found/disabled
    """
    provider = provider.lower()

    # Check if provider is configured and enabled
    if provider not in EMAIL_PROVIDERS:
        print(f"Unknown provider: {provider}")
        return None

    config = EMAIL_PROVIDERS[provider]
    if not config.get("enabled", False):
        print(f"Provider not enabled: {provider}")
        return None

    # host/port are only user-overridable for custom_connection providers (e.g. AYCD's
    # local IMAP server on a user-specific port). Ignore them for fixed providers so a
    # stray value can't repoint Gmail/iCloud/etc. at the wrong server.
    if config.get("custom_connection"):
        return ImapClient(email, app_password, provider, host=host, port=port, use_ssl=use_ssl)
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
