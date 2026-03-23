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

    def fetch_emails_batch(
        self,
        uids: List[str],
        batch_size: int = 50,
        progress_callback=None,
        subject_filter=None,
    ) -> List[RawEmail]:
        """
        Fetch multiple emails by UID list.
        Default implementation fetches one at a time; subclasses should override for batching.
        subject_filter(subject: str) -> bool: optional callable to skip irrelevant emails.
        """
        results = []
        total = len(uids)
        for i, uid in enumerate(uids):
            em = self.fetch_email(uid)
            if em:
                if subject_filter is None or subject_filter(em.subject):
                    results.append(em)
            if progress_callback:
                progress_callback(i + 1, total)
        return results

    def search_and_fetch(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com",
        progress_callback=None,
        subject_filter=None,
        subject_hints=None,
    ) -> List[RawEmail]:
        """
        Search and fetch all emails in date range.
        progress_callback(current, total) is called for progress updates.
        subject_filter(subject: str) -> bool: optional callable to skip irrelevant emails.
        subject_hints: list of subject substrings for server-side IMAP filtering.
        """
        uids = self.search_emails(start_date, end_date, sender_filter)
        return self.fetch_emails_batch(
            uids,
            progress_callback=progress_callback,
            subject_filter=subject_filter,
        )
