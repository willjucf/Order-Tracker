"""Walmart email parser implementation - optimized for speed."""
import re
from datetime import date, datetime
from typing import Optional, List
from bs4 import BeautifulSoup

from services.parsers.base_parser import BaseParser, ParsedOrder, ParsedItem
from services.email_client.base_client import RawEmail

# Try to use lxml for faster parsing, fallback to html.parser
try:
    import lxml
    HTML_PARSER = 'lxml'
except ImportError:
    HTML_PARSER = 'html.parser'


class WalmartParser(BaseParser):
    """Parser for Walmart order emails - optimized with pre-compiled regex."""

    # Pre-compiled regex patterns for speed
    _ORDER_PATTERNS = [
        re.compile(r'order\s*#\s*(\d{7}-\d{8})', re.IGNORECASE),
        re.compile(r'order\s*#(\d{15,16})', re.IGNORECASE),
        re.compile(r'order\s+number[:\s]+#?(\d{7}-\d{8})', re.IGNORECASE),
        re.compile(r'order\s+number[:\s]+(\d{15,16})', re.IGNORECASE),
        re.compile(r'#(\d{7}-\d{8})'),
        re.compile(r'(\d{7}-\d{8})'),
    ]

    _ORDER_DATE_PATTERNS = [
        re.compile(r'Order\s+date:\s*(\w+,\s+\w+\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
        re.compile(r'Order\s+date:\s*(\w+,\s+\w+\s+\d{1,2})', re.IGNORECASE),
    ]

    _DELIVERY_PATTERNS = [
        re.compile(r'Arrives\s+(?:by\s+)?(?:release\s+date\s+)?(\w+,\s+\w+\s+\d{1,2})', re.IGNORECASE),
    ]

    _TOTAL_PATTERNS = [
        re.compile(r'Order\s+total.*?\$(\d+\.?\d*)', re.IGNORECASE | re.DOTALL),
        re.compile(r'Includes\s+all\s+fees.*?\$(\d+\.?\d*)', re.IGNORECASE | re.DOTALL),
        re.compile(r'total["\s:]+\$(\d+\.?\d*)', re.IGNORECASE),
    ]

    _AMOUNT_PATTERN = re.compile(r'\$(\d+\.\d{2})')
    _QTY_PATTERN = re.compile(r'Qty:\s*(\d+)', re.IGNORECASE)
    _PRICE_EA_PATTERN = re.compile(r'\$(\d+\.?\d*)/EA', re.IGNORECASE)
    _PRODUCT_IMG_PATTERN = re.compile(r'quantity\s+\d+\s+item', re.IGNORECASE)
    _PRODUCT_ALT_PATTERN = re.compile(r'quantity\s+(\d+)\s+item\s+(.+)', re.IGNORECASE)
    _WALMART_IMG_PATTERN = re.compile(r'(https://i\d\.walmartimages\.com/[^\s"\'<>]+)')
    _ALT_TEXT_PATTERN = re.compile(r'alt=["\']([^"\']{10,100})["\']', re.IGNORECASE)
    _WHITESPACE_PATTERN = re.compile(r'\s+')

    def get_store_name(self) -> str:
        return "Walmart"

    def can_parse(self, email: RawEmail) -> bool:
        """Check if this is a Walmart email."""
        return 'walmart' in email.sender.lower()

    def detect_email_type(self, subject: str) -> str:
        """Detect the type of Walmart email from subject."""
        subject_lower = subject.lower()

        # Cancelled - check first (most specific)
        if subject_lower.startswith('canceled:') or 'was canceled' in subject_lower:
            return 'cancelled'

        # Shipped
        if subject_lower.startswith('shipped:'):
            return 'shipped'

        # Arrived/Delivered
        if subject_lower.startswith('arrived:'):
            return 'delivered'

        # Confirmation - various patterns
        if 'thanks for your' in subject_lower:
            return 'confirmation'

        # Preorder preparing to ship is also a confirmation
        if 'preorder is preparing' in subject_lower:
            return 'confirmation'
        if 'double-check your address' in subject_lower:
            return 'confirmation'

        return 'unknown'

    def extract_order_number(self, subject: str, body: str) -> Optional[str]:
        """Extract order number from subject or body."""
        # Try subject first
        for pattern in self._ORDER_PATTERNS:
            match = pattern.search(subject)
            if match:
                return match.group(1).replace('-', '')

        # Try body
        for pattern in self._ORDER_PATTERNS:
            match = pattern.search(body)
            if match:
                return match.group(1).replace('-', '')

        return None

    def parse(self, email: RawEmail) -> Optional[ParsedOrder]:
        """Parse a Walmart email."""
        if not self.can_parse(email):
            return None

        email_type = self.detect_email_type(email.subject)
        if email_type == 'unknown':
            return None

        # Use HTML body, fallback to text
        body = email.body_html if email.body_html else email.body_text

        order_number = self.extract_order_number(email.subject, body)
        if not order_number:
            return None

        # Create parsed order
        parsed = ParsedOrder(
            order_number=order_number,
            email_type=email_type
        )

        # Parse based on email type
        if email_type == 'confirmation':
            self._parse_confirmation(parsed, body, email.date)
        elif email_type == 'shipped':
            parsed.shipped_date = email.date
            self._parse_shipped(parsed, body)
        elif email_type == 'delivered':
            parsed.delivered_date = email.date
            self._parse_delivered(parsed, body, email.date)
        elif email_type == 'cancelled':
            parsed.total_amount = self._extract_total(body)

        return parsed

    def _parse_confirmation(self, parsed: ParsedOrder, body: str, email_date: date):
        """Parse order confirmation email."""
        parsed.order_date = self._extract_order_date(body) or email_date
        parsed.expected_delivery_date = self._extract_expected_delivery(body)
        parsed.total_amount = self._extract_total(body)
        parsed.items = self._extract_items(body)

    def _parse_shipped(self, parsed: ParsedOrder, body: str):
        """Parse shipped email."""
        parsed.expected_delivery_date = self._extract_expected_delivery(body)
        parsed.order_date = self._extract_order_date(body)

    def _parse_delivered(self, parsed: ParsedOrder, body: str, email_date: date):
        """Parse delivered/arrived email."""
        parsed.order_date = self._extract_order_date(body)
        parsed.total_amount = self._extract_total(body)
        parsed.items = self._extract_items(body)

    def _extract_order_date(self, body: str) -> Optional[date]:
        """Extract order date from body."""
        for pattern in self._ORDER_DATE_PATTERNS:
            match = pattern.search(body)
            if match:
                parsed_date = self._parse_date_string(match.group(1))
                if parsed_date:
                    return parsed_date
        return None

    def _extract_expected_delivery(self, body: str) -> Optional[date]:
        """Extract expected delivery date from body."""
        for pattern in self._DELIVERY_PATTERNS:
            match = pattern.search(body)
            if match:
                parsed_date = self._parse_date_string(match.group(1))
                if parsed_date:
                    return parsed_date
        return None

    def _extract_total(self, body: str) -> float:
        """Extract order total from body."""
        for pattern in self._TOTAL_PATTERNS:
            match = pattern.search(body)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        # Fallback: find all dollar amounts and pick the largest reasonable one
        all_amounts = self._AMOUNT_PATTERN.findall(body)
        if all_amounts:
            amounts = [float(a) for a in all_amounts]
            reasonable = [a for a in amounts if 10 <= a <= 10000]
            if reasonable:
                return max(reasonable)

        return 0.0

    def _extract_image_url(self, img_tag) -> str:
        """Extract the actual image URL from an img tag."""
        src = img_tag.get('src', '')
        if not src:
            return ''

        # Google-proxied URLs have the real URL after the # symbol
        if '#' in src:
            real_url = src.split('#')[-1]
            if 'walmartimages.com' in real_url:
                return real_url

        if 'walmartimages.com' in src:
            return src

        return src

    def _extract_items(self, body: str) -> List[ParsedItem]:
        """Extract items from order with images and prices."""
        items = []
        soup = BeautifulSoup(body, HTML_PARSER)

        found_items = []  # List of (name, qty, price, image_url)

        # Strategy 1: Find product images with alt text containing "quantity X item"
        product_images = soup.find_all('img', alt=self._PRODUCT_IMG_PATTERN)

        for img in product_images:
            alt_text = img.get('alt', '')
            match = self._PRODUCT_ALT_PATTERN.search(alt_text)
            if match:
                qty = int(match.group(1))
                name = match.group(2).strip()
                image_url = self._extract_image_url(img)
                found_items.append((name, qty, 0.0, image_url))

        # Strategy 2: Look for items in table rows with product names and prices
        if not found_items:
            for td in soup.find_all(['td', 'div']):
                text = td.get_text(separator=' ', strip=True)
                if 'Qty:' in text or '/EA' in text:
                    qty_match = self._QTY_PATTERN.search(text)
                    price_match = self._PRICE_EA_PATTERN.search(text)

                    item_img = td.find('img', alt=True)
                    if item_img:
                        name = item_img.get('alt', '').strip()
                        if name and len(name) > 5:
                            qty = int(qty_match.group(1)) if qty_match else 1
                            price = float(price_match.group(1)) if price_match else 0.0
                            image_url = self._extract_image_url(item_img)
                            found_items.append((name, qty, price, image_url))

        # Strategy 3: Regex fallback on raw HTML/text
        if not found_items:
            qty_matches = self._QTY_PATTERN.findall(body)
            price_matches = self._PRICE_EA_PATTERN.findall(body)
            walmart_image_urls = self._WALMART_IMG_PATTERN.findall(body)
            alt_matches = self._ALT_TEXT_PATTERN.findall(body)

            for i, alt in enumerate(alt_matches):
                if any(kw in alt.lower() for kw in ['pokemon', 'trading', 'card', 'booster', 'tin', 'box', 'pack']):
                    default_qty = int(qty_matches[0]) if qty_matches else 1
                    default_price = float(price_matches[0]) if price_matches else 0.0
                    image_url = walmart_image_urls[i] if i < len(walmart_image_urls) else ''
                    found_items.append((alt.strip(), default_qty, default_price, image_url))

        # Extract per-item prices from body for items that don't have prices
        all_prices = self._PRICE_EA_PATTERN.findall(body)
        default_price = float(all_prices[0]) if all_prices else 0.0

        # Remove duplicates and create ParsedItems
        seen = set()
        for name, qty, price, image_url in found_items:
            name = self._WHITESPACE_PATTERN.sub(' ', name).strip()[:150]

            name_key = name.lower()
            if name_key in seen or len(name) < 5:
                continue
            seen.add(name_key)

            item_price = price if price > 0 else default_price

            items.append(ParsedItem(
                name=name,
                quantity=qty,
                unit_price=item_price,
                item_type=self._categorize_item(name),
                image_url=image_url
            ))

            if len(items) >= 10:
                break

        # If still no items found but we have qty/price, create a generic item
        if not items:
            qty_matches = self._QTY_PATTERN.findall(body)
            price_matches = self._PRICE_EA_PATTERN.findall(body)
            if qty_matches or price_matches:
                items.append(ParsedItem(
                    name="Walmart Item",
                    quantity=int(qty_matches[0]) if qty_matches else 1,
                    unit_price=float(price_matches[0]) if price_matches else 0.0,
                    item_type="Other",
                    image_url=""
                ))

        return items

    def _categorize_item(self, name: str) -> str:
        """Categorize item by name."""
        name_lower = name.lower()

        if 'pokemon' in name_lower:
            if any(kw in name_lower for kw in ['card', 'tcg', 'booster', 'tin', 'box']):
                return 'Pokemon TCG'
            return 'Pokemon'

        if 'trading card' in name_lower:
            return 'Trading Cards'

        return 'Other'

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            "%a, %b %d, %Y",
            "%a, %b %d %Y",
            "%a, %B %d, %Y",
            "%a, %b %d",
            "%b %d, %Y",
            "%b %d %Y",
            "%b %d",
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
