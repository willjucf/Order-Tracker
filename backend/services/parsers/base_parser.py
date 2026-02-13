"""Abstract base class for email parsers."""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import date

from services.email_client.base_client import RawEmail


@dataclass
class ParsedItem:
    """Represents a parsed item from an order."""
    name: str
    quantity: int = 1
    unit_price: float = 0.0
    item_type: str = ""
    image_url: str = ""


@dataclass
class ParsedOrder:
    """Represents a parsed order from an email."""
    order_number: str
    email_type: str  # 'confirmation', 'shipped', 'delivered', 'cancelled'
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    shipped_date: Optional[date] = None
    delivered_date: Optional[date] = None
    total_amount: float = 0.0
    items: List[ParsedItem] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []


class BaseParser(ABC):
    """Abstract base class for store-specific email parsers."""

    @abstractmethod
    def can_parse(self, email: RawEmail) -> bool:
        """Check if this parser can handle the given email."""
        pass

    @abstractmethod
    def parse(self, email: RawEmail) -> Optional[ParsedOrder]:
        """Parse the email and extract order information."""
        pass

    @abstractmethod
    def get_store_name(self) -> str:
        """Return the name of the store this parser handles."""
        pass
