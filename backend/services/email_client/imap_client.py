"""Generic IMAP client implementation for all providers."""
import imaplib
import email
from email.header import decode_header
from datetime import date, datetime
from typing import List, Optional
import re

from services.email_client.base_client import BaseEmailClient, RawEmail
from utils.config import EMAIL_PROVIDERS


class ImapClient(BaseEmailClient):
    """Generic IMAP client that works with any email provider."""

    def __init__(self, email_addr: str, app_password: str, provider_key: str):
        super().__init__(email_addr, app_password)
        self.imap: Optional[imaplib.IMAP4_SSL] = None
        self.provider_key = provider_key
        self.provider_config = EMAIL_PROVIDERS.get(provider_key, EMAIL_PROVIDERS["gmail"])

    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            self.imap = imaplib.IMAP4_SSL(
                self.provider_config["imap_server"],
                self.provider_config["imap_port"]
            )
            self.imap.login(self.email, self.app_password)
            self.imap.select("INBOX")
            self.connected = True
            return True
        except imaplib.IMAP4.error as e:
            print(f"IMAP login error: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from email server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
            finally:
                self.imap = None
                self.connected = False

    def search_emails(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com"
    ) -> List[str]:
        """Search for emails within date range from specified sender."""
        if not self.imap or not self.connected:
            return []

        # Format dates for IMAP search (DD-Mon-YYYY)
        start_str = start_date.strftime("%d-%b-%Y")
        end_str = end_date.strftime("%d-%b-%Y")

        # Build search criteria
        search_criteria = f'(FROM "{sender_filter}" SINCE "{start_str}" BEFORE "{end_str}")'

        try:
            status, messages = self.imap.search(None, search_criteria)
            if status == "OK" and messages[0]:
                return messages[0].decode().split()
            return []
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def fetch_email(self, uid: str) -> Optional[RawEmail]:
        """Fetch a single email by UID."""
        if not self.imap or not self.connected:
            return None

        try:
            status, msg_data = self.imap.fetch(uid.encode() if isinstance(uid, str) else uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                return None

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode subject
            subject = self._decode_header(msg.get("Subject", ""))

            # Decode sender
            sender = self._decode_header(msg.get("From", ""))

            # Parse date
            date_str = msg.get("Date", "")
            email_date = self._parse_date(date_str)

            # Extract body
            body_html = ""
            body_text = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue

                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            decoded = payload.decode(charset, errors='replace')

                            if content_type == "text/html":
                                body_html = decoded
                            elif content_type == "text/plain":
                                body_text = decoded
                    except Exception:
                        continue
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        decoded = payload.decode(charset, errors='replace')

                        if msg.get_content_type() == "text/html":
                            body_html = decoded
                        else:
                            body_text = decoded
                except Exception:
                    pass

            return RawEmail(
                uid=uid,
                subject=subject,
                sender=sender,
                date=email_date,
                body_html=body_html,
                body_text=body_text
            )

        except Exception as e:
            print(f"Fetch error for UID {uid}: {e}")
            return None

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
            else:
                decoded_parts.append(part)
        return " ".join(decoded_parts)

    def _parse_date(self, date_str: str) -> date:
        """Parse email date string to date object."""
        if not date_str:
            return date.today()

        # Common email date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
        ]

        # Clean up the date string
        date_str = re.sub(r'\s+\([^)]+\)', '', date_str)  # Remove timezone names in parentheses

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date()
            except ValueError:
                continue

        return date.today()
