"""Target email parser implementation."""
import re
from datetime import date, datetime
from typing import Optional, List
from bs4 import BeautifulSoup

from services.parsers.base_parser import BaseParser, ParsedOrder, ParsedItem
from services.email_client.base_client import RawEmail

try:
    import lxml
    HTML_PARSER = 'lxml'
except ImportError:
    HTML_PARSER = 'html.parser'


class TargetParser(BaseParser):
    """Parser for Target order emails."""

    # Subject patterns for email type detection
    SUBJECT_HINTS = [
        "Thanks for shopping with us",
        "are about to ship",
        "Items have arrived",
        "had to cancel",
        "prepping your preorder",
    ]

    # Order number: 12-16 digits (Target uses 15-digit order numbers)
    _ORDER_NUM_SUBJECT = re.compile(r'#:?(\d{12,16})')
    _ORDER_NUM_BODY = re.compile(r'(?:order|Order)\s*#:?\s*(\d{12,16})')

    # Prices
    _TOTAL_CLASS = 'order-total-price'  # CSS class on the <h3> element
    _PAYMENT_PATTERN = re.compile(r'payment\s+of\s+\$(\d+\.\d{2})', re.IGNORECASE)
    _TOTAL_FALLBACK = re.compile(r'(?:order\s+total|total)[:\s]*\$(\d+\.\d{2})', re.IGNORECASE)
    _PRICE_EA = re.compile(r'\$(\d+\.?\d*)\s*/\s*ea', re.IGNORECASE)
    _QTY = re.compile(r'Qty:?\s*(\d+)', re.IGNORECASE)
    _AMOUNT = re.compile(r'\$(\d+\.\d{2})')

    # Dates
    _ARRIVES = re.compile(
        r'Arrives?\s+(?:\w+,?\s+)?'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2})',
        re.IGNORECASE,
    )
    _DELIVERED_DATE = re.compile(
        r'Delivered\s+'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s*\d{0,4})',
        re.IGNORECASE,
    )
    _ORDER_DATE = re.compile(
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+\d{1,2},?\s+\d{4})',
        re.IGNORECASE,
    )
    _WHITESPACE = re.compile(r'\s+')

    # Product image pattern (GUEST_ images on target.scene7.com)
    _GUEST_IMG = re.compile(r'GUEST_')
    _SCENE7_IMG = re.compile(r'target\.scene7\.com')

    def get_store_name(self) -> str:
        return "Target"

    def can_parse(self, email: RawEmail) -> bool:
        return 'target' in email.sender.lower() or 'target' in email.subject.lower()

    def detect_email_type(self, subject: str) -> str:
        subject_lower = subject.lower()

        if 'had to cancel' in subject_lower or 'was canceled' in subject_lower:
            return 'cancelled'
        if 'items have arrived' in subject_lower:
            return 'delivered'
        if 'about to ship' in subject_lower or 'prepping your preorder' in subject_lower:
            return 'shipped'
        if 'thanks for shopping' in subject_lower:
            return 'confirmation'

        return 'unknown'

    def parse(self, email: RawEmail) -> Optional[ParsedOrder]:
        if not self.can_parse(email):
            return None

        email_type = self.detect_email_type(email.subject)
        if email_type == 'unknown':
            return None

        body = email.body_html or email.body_text
        order_number = self._extract_order_number(email.subject, body)
        if not order_number:
            return None

        parsed = ParsedOrder(order_number=order_number, email_type=email_type)

        if email_type == 'confirmation':
            self._parse_confirmation(parsed, body, email.date)
        elif email_type == 'shipped':
            parsed.shipped_date = email.date
            self._parse_shipped(parsed, body)
        elif email_type == 'delivered':
            parsed.delivered_date = email.date
            self._parse_delivered(parsed, body, email.date)
        elif email_type == 'cancelled':
            pass  # Cancel emails have no amounts or items

        return parsed

    def _extract_order_number(self, subject: str, body: str) -> Optional[str]:
        m = self._ORDER_NUM_SUBJECT.search(subject)
        if m:
            return m.group(1)
        m = self._ORDER_NUM_BODY.search(body)
        if m:
            return m.group(1)
        return None

    def _parse_confirmation(self, parsed: ParsedOrder, body: str, email_date: date):
        parsed.order_date = self._extract_order_date(body) or email_date
        parsed.expected_delivery_date = self._extract_arrives_date(body)
        parsed.total_amount = self._extract_total(body)
        parsed.items = self._extract_items(body)

    def _parse_shipped(self, parsed: ParsedOrder, body: str):
        parsed.total_amount = self._extract_payment_amount(body)
        parsed.expected_delivery_date = self._extract_arrives_date(body)
        parsed.order_date = self._extract_order_date(body)
        if not parsed.items:
            parsed.items = self._extract_items(body)

    def _parse_delivered(self, parsed: ParsedOrder, body: str, email_date: date):
        parsed.delivered_date = self._extract_delivered_date(body) or email_date
        parsed.order_date = self._extract_order_date(body)
        parsed.total_amount = self._extract_total(body)
        parsed.items = self._extract_items(body)

    # --- Extraction helpers ---

    def _extract_total(self, body: str) -> float:
        soup = BeautifulSoup(body, HTML_PARSER)
        el = soup.find(class_=self._TOTAL_CLASS)
        if el:
            m = self._AMOUNT.search(el.get_text())
            if m:
                return float(m.group(1))

        text = soup.get_text(separator=' ', strip=True)
        m = self._TOTAL_FALLBACK.search(text)
        if m:
            return float(m.group(1))

        return self._extract_payment_amount(body)

    def _extract_payment_amount(self, body: str) -> float:
        m = self._PAYMENT_PATTERN.search(body)
        if m:
            return float(m.group(1))
        return 0.0

    def _extract_order_date(self, body: str) -> Optional[date]:
        m = self._ORDER_DATE.search(body)
        if m:
            return self._parse_date_string(m.group(1))
        return None

    def _extract_arrives_date(self, body: str) -> Optional[date]:
        m = self._ARRIVES.search(body)
        if m:
            return self._parse_date_string(m.group(1))
        return None

    def _extract_delivered_date(self, body: str) -> Optional[date]:
        m = self._DELIVERED_DATE.search(body)
        if m:
            return self._parse_date_string(m.group(1))
        return None

    def _extract_items(self, body: str) -> List[ParsedItem]:
        soup = BeautifulSoup(body, HTML_PARSER)
        items = []
        seen = set()

        # Find product images: GUEST_ pattern first, then fallback to scene7 images
        # that sit near a "Qty" label (some delivered/preorder emails use placeholders)
        guest_imgs = soup.find_all('img', src=self._GUEST_IMG)
        if not guest_imgs:
            for img in soup.find_all('img', src=self._SCENE7_IMG):
                alt = img.get('alt', '')
                if len(alt) < 15:
                    continue
                alt_lower = alt.lower()
                if alt_lower.startswith(('bullseye', 'target ', 'down arrow')):
                    continue
                # Walk up to see if this image is near a "Qty" label (= real product)
                parent = img
                for _ in range(10):
                    parent = parent.parent
                    if parent is None:
                        break
                    if 'Qty' in parent.get_text(separator=' ', strip=True):
                        guest_imgs.append(img)
                        break

        for img in guest_imgs:
            alt = img.get('alt', '').strip()
            if not alt or len(alt) < 5:
                continue

            name_key = alt.lower()
            if name_key in seen:
                continue
            seen.add(name_key)

            image_url = img.get('src', '')

            # Walk up to find the enclosing table cell / row with Qty and price
            qty = 1
            price = 0.0
            parent = img
            for _ in range(10):
                parent = parent.parent
                if parent is None:
                    break
                parent_text = parent.get_text(separator=' ', strip=True)
                if 'Qty' in parent_text:
                    qm = self._QTY.search(parent_text)
                    if qm:
                        qty = int(qm.group(1))
                    pm = self._PRICE_EA.search(parent_text)
                    if pm:
                        price = float(pm.group(1))
                    break

            items.append(ParsedItem(
                name=self._WHITESPACE.sub(' ', alt)[:150],
                quantity=qty,
                unit_price=price,
                item_type=self._categorize_item(alt),
                image_url=image_url,
            ))

            if len(items) >= 10:
                break

        return items

    def _categorize_item(self, name: str) -> str:
        name_lower = name.lower()
        if 'pokemon' in name_lower or 'pokémon' in name_lower:
            if any(kw in name_lower for kw in ['card', 'tcg', 'booster', 'tin', 'box', 'collection', 'bundle']):
                return 'Pokemon TCG'
            return 'Pokemon'
        if 'trading card' in name_lower:
            return 'Trading Cards'
        return 'Other'

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        date_str = date_str.strip().rstrip('.')

        formats = [
            "%B %d, %Y",    # March 23, 2026
            "%B %d %Y",     # March 23 2026
            "%b %d, %Y",    # Mar 23, 2026
            "%b %d %Y",     # Mar 23 2026
            "%b. %d, %Y",   # Mar. 23, 2026
            "%B %d",         # March 23
            "%b %d",         # Mar 23
            "%b. %d",        # Mar. 23
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                if parsed.year == 1900:
                    now = datetime.now()
                    parsed = parsed.replace(year=now.year)
                    if (now - parsed).days > 180:
                        parsed = parsed.replace(year=now.year + 1)
                    elif (parsed - now).days > 180:
                        parsed = parsed.replace(year=now.year - 1)
                return parsed.date()
            except ValueError:
                continue

        return None
