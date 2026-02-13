"""Abstract base class for email clients."""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RawEmail:
    """Represents a raw email fetched from the server."""
    uid: str
    subject: str
    sender: str
    date: date
    body_html: str
    body_text: str


class BaseEmailClient(ABC):
    """Abstract base class for email provider clients."""

    def __init__(self, email: str, app_password: str):
        self.email = email
        self.app_password = app_password
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the email server. Returns True on success."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from the email server."""
        pass

    @abstractmethod
    def search_emails(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com"
    ) -> List[str]:
        """
        Search for emails within date range from specified sender.
        Returns list of email UIDs.
        """
        pass

    @abstractmethod
    def fetch_email(self, uid: str) -> Optional[RawEmail]:
        """Fetch a single email by UID."""
        pass

    def search_and_fetch(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com",
        progress_callback=None
    ) -> List[RawEmail]:
        """
        Search and fetch all emails in date range.
        progress_callback(current, total) is called for progress updates.
        """
        uids = self.search_emails(start_date, end_date, sender_filter)
        emails = []
        total = len(uids)

        for i, uid in enumerate(uids):
            email = self.fetch_email(uid)
            if email:
                emails.append(email)
            if progress_callback:
                progress_callback(i + 1, total)

        return emails
