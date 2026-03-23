"""Generic IMAP client implementation for all providers."""
import imaplib
import email
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        sender_filter: str = "walmart.com",
        subject_hints: Optional[List[str]] = None,
    ) -> List[str]:
        """Search for emails within date range from specified sender.

        Uses progressive fallback:
          1. FROM + date + subject hints  (fastest — only relevant emails)
          2. FROM + date                  (if hints returned nothing or errored)
          3. date only                    (if FROM filter doesn't match sender format)
        """
        if not self.imap or not self.connected:
            return []

        start_str = start_date.strftime("%d-%b-%Y")
        end_str = end_date.strftime("%d-%b-%Y")

        queries = []

        # Most specific first: FROM + date + subject hints
        if subject_hints:
            subject_part = self._build_subject_query(subject_hints)
            queries.append(
                f'(FROM "{sender_filter}" SINCE "{start_str}" BEFORE "{end_str}" {subject_part})'
            )

        # Fallback: FROM + date only
        queries.append(f'(FROM "{sender_filter}" SINCE "{start_str}" BEFORE "{end_str}")')

        # Last resort: date only (parser's can_parse will filter by sender later)
        queries.append(f'(SINCE "{start_str}" BEFORE "{end_str}")')

        for query in queries:
            try:
                status, messages = self.imap.search(None, query)
                if status == "OK" and messages[0]:
                    return messages[0].decode().split()
            except Exception:
                continue

        return []

    def _build_subject_query(self, hints: List[str]) -> str:
        """Build a nested IMAP OR query for multiple subject substrings."""
        if len(hints) == 1:
            return f'SUBJECT "{hints[0]}"'
        return f'OR (SUBJECT "{hints[0]}") ({self._build_subject_query(hints[1:])})'

    def fetch_email(self, uid: str) -> Optional[RawEmail]:
        """Fetch a single email by UID."""
        if not self.imap or not self.connected:
            return None

        try:
            status, msg_data = self.imap.fetch(uid.encode() if isinstance(uid, str) else uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                return None

            return self._parse_raw_email(uid, msg_data[0][1])

        except Exception as e:
            print(f"Fetch error for UID {uid}: {e}")
            return None

    def fetch_emails_batch(
        self,
        uids: List[str],
        batch_size: int = 50,
        progress_callback=None,
        subject_filter=None,
        num_connections: int = 8,
    ) -> List[RawEmail]:
        """Fetch emails using multiple parallel IMAP connections.

        Each connection fetches its entire chunk in ONE FETCH command.
        Server-side subject filtering via search_emails means UIDs are already
        pre-filtered — no header round-trip needed here.
        Progress fires once per chunk (8 big jumps) rather than per email.
        """
        if not self.imap or not self.connected or not uids:
            return []

        total = len(uids)
        actual_connections = min(num_connections, total)
        chunk_size = (total + actual_connections - 1) // actual_connections
        chunks = [uids[i:i + chunk_size] for i in range(0, total, chunk_size)]

        results: List[RawEmail] = []
        lock = threading.Lock()
        fetched_count = [0]

        def fetch_chunk(chunk_uids: List[str]) -> List[RawEmail]:
            conn = ImapClient(self.email, self.app_password, self.provider_key)
            if not conn.connect():
                return []
            try:
                uid_set = ",".join(str(u) for u in chunk_uids)
                status, msg_data = conn.imap.fetch(uid_set.encode(), "(RFC822)")
                if status != "OK" or not msg_data:
                    return []

                chunk_results = []
                for item in msg_data:
                    if not isinstance(item, tuple) or len(item) < 2:
                        continue
                    raw_bytes = item[1]
                    if not isinstance(raw_bytes, bytes):
                        continue
                    hdr_str = item[0].decode() if isinstance(item[0], bytes) else str(item[0])
                    seq_match = re.search(r"^(\d+)", hdr_str)
                    seq_num = seq_match.group(1) if seq_match else chunk_uids[0]
                    em = self._parse_raw_email(seq_num, raw_bytes)
                    if em:
                        chunk_results.append(em)

                # Progress fires once per chunk, not per email
                if progress_callback:
                    with lock:
                        fetched_count[0] += len(chunk_results)
                        progress_callback(min(fetched_count[0], total), total)

                return chunk_results
            except Exception as e:
                print(f"Parallel fetch error: {e}")
                return []
            finally:
                conn.disconnect()

        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            futures = [executor.submit(fetch_chunk, chunk) for chunk in chunks]
            for future in as_completed(futures):
                results.extend(future.result())

        return results

    def search_and_fetch(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com",
        progress_callback=None,
        subject_filter=None,
        subject_hints: Optional[List[str]] = None,
    ) -> List[RawEmail]:
        """Search and fetch all emails in date range using batch IMAP requests.

        subject_hints: let the IMAP server filter by subject before returning UIDs.
        This is faster than fetching headers manually — the server does it for free.
        """
        uids = self.search_emails(
            start_date, end_date, sender_filter, subject_hints=subject_hints
        )
        if not uids:
            return []
        return self.fetch_emails_batch(uids, progress_callback=progress_callback)

    def _parse_raw_email(self, uid: str, raw_bytes: bytes) -> Optional[RawEmail]:
        """Parse raw email bytes into a RawEmail object."""
        try:
            msg = email.message_from_bytes(raw_bytes)

            subject = self._decode_header(msg.get("Subject", ""))
            sender = self._decode_header(msg.get("From", ""))
            email_date = self._parse_date(msg.get("Date", ""))

            body_html = ""
            body_text = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if "attachment" in str(part.get("Content-Disposition", "")):
                        continue
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            decoded = payload.decode(charset, errors="replace")
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
                        charset = msg.get_content_charset() or "utf-8"
                        decoded = payload.decode(charset, errors="replace")
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
                body_text=body_text,
            )
        except Exception as e:
            print(f"Parse error for UID {uid}: {e}")
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
