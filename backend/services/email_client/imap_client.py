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

    def __init__(
        self,
        email_addr: str,
        app_password: str,
        provider_key: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_ssl: Optional[bool] = None,
    ):
        super().__init__(email_addr, app_password)
        self.imap: Optional[imaplib.IMAP4] = None
        self.provider_key = provider_key
        self.provider_config = EMAIL_PROVIDERS.get(provider_key, EMAIL_PROVIDERS["gmail"])
        # host/port/use_ssl may be overridden per-connection (AYCD Inbox runs a local IMAP
        # server on a user-specific port with TLS off). Fall back to the provider defaults.
        self.host = host or self.provider_config["imap_server"]
        self.port = int(port) if port else self.provider_config["imap_port"]
        self.use_ssl = self.provider_config.get("use_ssl", True) if use_ssl is None else use_ssl

    def connect(self) -> bool:
        """Connect to IMAP server."""
        self.last_error = ""
        try:
            imap_cls = imaplib.IMAP4_SSL if self.use_ssl else imaplib.IMAP4
            self.imap = imap_cls(
                self.host,
                self.port,
                timeout=60,  # bounded, but generous for slow tunnels (AYCD UpLink) so a
                             # multi-email FETCH batch doesn't clip mid-transfer
            )
            self.imap.login(self.email, self.app_password)
            self._select_search_folder()
            self.connected = True
            return True
        except imaplib.IMAP4.error as e:
            # Reached the server, but it rejected the login (bad user/password/state).
            self.last_error = f"IMAP server reached but rejected login: {e}"
            print(f"IMAP login error: {e}")
            self.connected = False
            return False
        except OSError as e:
            # Never reached the server: refused, timed out, host unknown, etc.
            # (ConnectionRefusedError, TimeoutError, socket.gaierror are all OSError.)
            self.last_error = (
                f"Could not reach IMAP server at {self.host}:{self.port} ({e}). "
                f"Check the AYCD IMAP Server is enabled (Status: Running) and reachable "
                f"from this machine, and that the host/port match."
            )
            print(f"Connection error: {e}")
            self.connected = False
            return False
        except Exception as e:
            self.last_error = f"Connection error: {e}"
            print(f"Connection error: {e}")
            self.connected = False
            return False

    def ensure_connected(self) -> bool:
        """Verify the connection is alive, transparently reconnecting if it is stale.

        IMAP servers silently drop idle connections after a few minutes, but
        ``self.connected`` stays True and the socket still looks open. A lightweight
        NOOP round-trip detects the dead connection so clicking Scan a second time can
        reconnect on its own (and pick up any newly-arrived email) instead of failing
        until the user manually disconnects and reconnects.
        """
        if self.imap is not None:
            try:
                status, _ = self.imap.noop()
                if status == "OK":
                    # Re-select the search folder so the view reflects newly-arrived mail.
                    self._select_search_folder()
                    self.connected = True
                    return True
            except Exception:
                pass  # connection is dead — fall through and reconnect

        # Stale or never connected — tear down cleanly and reconnect with stored creds.
        try:
            if self.imap is not None:
                self.imap.logout()
        except Exception:
            pass
        self.imap = None
        self.connected = False
        return self.connect()

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

    def _select_search_folder(self):
        """Select the mailbox to search over.

        Gmail (and any server exposing an ``\\All`` special-use mailbox) keeps archived
        and older messages out of INBOX — only in "All Mail". Order confirmations for
        preorders are often placed weeks/months earlier and have since been archived, so
        searching INBOX alone misses them. Prefer the ``\\All`` mailbox when present and
        fall back to INBOX for providers that don't have one.
        """
        # readonly=True issues EXAMINE, not SELECT. This app only reads mail, so it never
        # needs write access — and AYCD Inbox's Unified Inbox (inbox@aycd.me) is a
        # read-only mailbox that rejects a read-write SELECT ("INBOX is not writable").
        # EXAMINE also means scans don't mark the user's emails as \Seen.
        folder = self._resolve_search_folder()
        try:
            status, _ = self.imap.select(folder, readonly=True)
            if status == "OK":
                return
        except Exception:
            pass
        self.imap.select("INBOX", readonly=True)

    def _resolve_search_folder(self) -> str:
        """Return the IMAP mailbox name to search (quoted if it contains spaces).

        Looks for the server's ``\\All`` special-use mailbox (Gmail's "All Mail",
        locale-independent). Returns "INBOX" if none is advertised.
        """
        try:
            status, folders = self.imap.list()
            if status == "OK" and folders:
                for raw in folders:
                    line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
                    # LIST line looks like: (\HasNoChildren \All) "/" "[Gmail]/All Mail"
                    if "\\All" in line:
                        m = re.search(r'"([^"]+)"\s*$', line) or re.search(r'(\S+)\s*$', line)
                        if m:
                            name = m.group(1)
                            return f'"{name}"' if " " in name else name
        except Exception:
            pass
        return "INBOX"

    def search_emails(
        self,
        start_date: date,
        end_date: date,
        sender_filter: str = "walmart.com",
        subject_hints: Optional[List[str]] = None,
    ) -> List[str]:
        """Search for emails within a date range, robust to forwarded/rewritten senders.

        A sender-filtered query alone silently misses forwarded mail: iCloud "Hide My
        Email" rewrites the From address (e.g. ``info@em.pokemon.com`` ->
        ``info_at_em_pokemon_com_...@icloud.com``) and Gmail's IMAP search is token-based,
        so ``FROM "pokemon"`` never matches the "pokemon" buried inside ``em_pokemon_com``.
        A subject-based query (sender-agnostic) catches those forwarded emails; the
        parser's ``can_parse()`` does the final sender check downstream.

        Queries are tried in **priority tiers**; the first tier that returns anything wins
        (results within a tier are unioned/deduped). Later tiers are only a fallback:

          Tier 1 (when subject_hints given) — narrow, subject-based:
            - subject + date              (sender-agnostic — catches forwarded/rewritten)
            - FROM + date + subject hints (specific, when the sender filter is reliable)
          Tier 2 — sender-only: FROM + date
          Tier 3 — date only (last resort; can_parse filters by sender later)

        Why tiers instead of one big union: a store's subject hints line up 1:1 with what
        its parser can actually parse, so Tier 1 already finds every parseable order. The
        broad ``FROM + date`` query (Tier 2) additionally drags in *all* marketing mail
        from that sender — hundreds of unparseable emails per week on a large inbox — which
        is pure fetch overhead and, over a slow link (e.g. AYCD UpLink), causes bulk
        fetches to time out and silently drop the real orders. Tier 1 keeps the fetch set
        tiny (only order emails); Tier 2 only kicks in when there are no hints or the
        subject search matched nothing.
        """
        if not self.imap or not self.connected:
            return []

        start_str = start_date.strftime("%d-%b-%Y")
        end_str = end_date.strftime("%d-%b-%Y")
        date_clause = f'SINCE "{start_str}" BEFORE "{end_str}"'

        tiers: List[List[str]] = []
        if subject_hints:
            subject_part = self._build_subject_query(subject_hints)
            tiers.append([
                f'({date_clause} {subject_part})',
                f'(FROM "{sender_filter}" {date_clause} {subject_part})',
            ])
        tiers.append([f'(FROM "{sender_filter}" {date_clause})'])
        tiers.append([f'({date_clause})'])

        for tier in tiers:
            collected = set()
            for query in tier:
                try:
                    status, messages = self.imap.search(None, query)
                    if status == "OK" and messages and messages[0]:
                        collected.update(messages[0].decode().split())
                except Exception:
                    continue
            if collected:
                return sorted(collected, key=lambda x: int(x) if x.isdigit() else 0)

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
            conn = ImapClient(
                self.email, self.app_password, self.provider_key,
                host=self.host, port=self.port, use_ssl=self.use_ssl,
            )
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
