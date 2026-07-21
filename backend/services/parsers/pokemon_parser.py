"""Pokemon Center email parser implementation."""
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


class PokemonParser(BaseParser):
    """Parser for Pokemon Center (pokemoncenter.com) order emails.

    Order confirmation / cancellation come from ``info@em.pokemon.com``; shipping and
    delivery notifications come from ``pokemon@pokemoncenter.narvar.com``. iCloud
    forwarding rewrites all of these (e.g. ``info_at_em_pokemon_com_...@icloud.com``),
    so the sender filter (``pokemon``) and ``can_parse`` both key off the broad
    "pokemon" substring rather than a full domain.
    """

    # Subject substrings for server-side IMAP filtering
    SUBJECT_HINTS = [
        "Thank you for shopping",       # confirmation
        "on its way",                   # shipped
        "arrive soon",                  # shipped (narvar out-for-delivery)
        "has been delivered",           # delivered
        "has been canceled",            # cancelled
        "Running a little behind",      # delayed (ETA update, treated as shipped)
    ]

    # Order number: "P" followed by digits (e.g. P0036908291), present in every email type
    _ORDER_NUM = re.compile(r'\b(P\d{8,})\b')

    # Order Summary line item: "<name> SKU # : <sku> Qty : <n> Price : $<unit price>"
    _ITEM = re.compile(
        r'(.+?)\s*SKU\s*#\s*:?\s*([0-9][0-9\-]+)\s*'
        r'Qty\s*:?\s*(\d+)\s*'
        r'Price\s*:?\s*\$([\d,]+\.\d{2})',
        re.IGNORECASE | re.DOTALL,
    )

    # Totals
    _ORDER_TOTAL = re.compile(r'Order\s+Total[:\s]*\$([\d,]+\.\d{2})', re.IGNORECASE)
    _TOTAL_FALLBACK = re.compile(r'(?<!sub)total[:\s]*\$([\d,]+\.\d{2})', re.IGNORECASE)

    # Dates
    _DATE_ORDERED = re.compile(
        r'Date\s+Ordered:?\s*'
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+\d{1,2},?\s+\d{4})',
        re.IGNORECASE,
    )
    # Delay email: "estimated to be delivered on: ... Saturday, July 18"
    _ESTIMATED_DELIVERY = re.compile(
        r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?)',
        re.IGNORECASE,
    )
    _WHITESPACE = re.compile(r'\s+')

    def get_store_name(self) -> str:
        return "Pokemon Center"

    def can_parse(self, email: RawEmail) -> bool:
        return 'pokemon' in email.sender.lower()

    def detect_email_type(self, subject: str) -> str:
        s = subject.lower()
        if 'canceled' in s or 'cancelled' in s:
            return 'cancelled'
        if 'has been delivered' in s or 'package has been delivered' in s:
            return 'delivered'
        if 'on its way' in s or 'arrive soon' in s or 'running a little behind' in s:
            return 'shipped'
        if 'thank you for shopping' in s:
            return 'confirmation'
        return 'unknown'

    def parse(self, email: RawEmail) -> Optional[ParsedOrder]:
        if not self.can_parse(email):
            return None

        email_type = self.detect_email_type(email.subject)
        if email_type == 'unknown':
            return None

        body = email.body_html or email.body_text
        soup = BeautifulSoup(body, HTML_PARSER)
        text = soup.get_text(separator=' ', strip=True)

        order_number = self._extract_order_number(text)
        if not order_number:
            return None

        parsed = ParsedOrder(order_number=order_number, email_type=email_type)

        if email_type == 'confirmation':
            parsed.order_date = self._extract_order_date(text) or email.date
            parsed.total_amount = self._extract_total(text)
            parsed.items = self._extract_items(text)
        elif email_type == 'shipped':
            parsed.shipped_date = email.date
            # "Running a little behind" carries an updated estimated delivery date
            parsed.expected_delivery_date = self._extract_estimated_delivery(text)
        elif email_type == 'delivered':
            parsed.delivered_date = email.date
        elif email_type == 'cancelled':
            pass  # Cancel emails carry no reliable amounts/items

        return parsed

    # --- Extraction helpers ---

    def _extract_order_number(self, text: str) -> Optional[str]:
        m = self._ORDER_NUM.search(text)
        return m.group(1) if m else None

    def _extract_total(self, text: str) -> float:
        m = self._ORDER_TOTAL.search(text)
        if m:
            return self._to_float(m.group(1))
        m = self._TOTAL_FALLBACK.search(text)
        if m:
            return self._to_float(m.group(1))
        return 0.0

    def _extract_items(self, text: str) -> List[ParsedItem]:
        # Narrow to the "Order Summary" ... "Order Subtotal" region so the item
        # regex can't pick up unrelated "$" amounts elsewhere in the email.
        start = re.search(r'Order\s+Summary', text, re.IGNORECASE)
        end = re.search(r'Order\s+Subtotal', text, re.IGNORECASE)
        region = text[start.end():end.start()] if start and end else text

        items: List[ParsedItem] = []
        seen = set()
        for m in self._ITEM.finditer(region):
            name = self._WHITESPACE.sub(' ', m.group(1)).strip()
            if not name or len(name) < 3:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(ParsedItem(
                name=name[:150],
                quantity=int(m.group(3)),
                unit_price=self._to_float(m.group(4)),
                item_type=self._categorize_item(name),
                image_url='',
            ))
            if len(items) >= 20:
                break
        return items

    def _extract_order_date(self, text: str) -> Optional[date]:
        m = self._DATE_ORDERED.search(text)
        if m:
            return self._parse_date_string(m.group(1))
        return None

    def _extract_estimated_delivery(self, text: str) -> Optional[date]:
        m = self._ESTIMATED_DELIVERY.search(text)
        if m:
            return self._parse_date_string(m.group(1))
        return None

    def _categorize_item(self, name: str) -> str:
        name_lower = name.lower()
        if 'pokemon' in name_lower or 'pokémon' in name_lower:
            if any(kw in name_lower for kw in
                   ['card', 'tcg', 'booster', 'tin', 'box', 'collection', 'bundle', 'pack']):
                return 'Pokemon TCG'
            return 'Pokemon'
        if 'trading card' in name_lower:
            return 'Trading Cards'
        return 'Other'

    @staticmethod
    def _to_float(value: str) -> float:
        try:
            return float(value.replace(',', ''))
        except (ValueError, AttributeError):
            return 0.0

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        date_str = date_str.strip().rstrip('.').replace(',', '')

        formats = [
            "%B %d %Y",   # July 20 2026
            "%b %d %Y",   # Jul 20 2026
            "%B %d",      # July 18
            "%b %d",      # Jul 18
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
