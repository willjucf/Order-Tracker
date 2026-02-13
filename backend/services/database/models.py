"""Data models and database operations."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Union
from services.database.db import get_db


def parse_db_date(value: Union[str, date, None]) -> Optional[date]:
    """Parse a date from database (could be string or date)."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


@dataclass
class Item:
    """Represents an item in an order."""
    name: str
    quantity: int = 1
    unit_price: float = 0.0
    item_type: str = ""
    image_url: str = ""
    id: Optional[int] = None
    order_id: Optional[int] = None

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price

    @staticmethod
    def clean_name(name: str) -> str:
        """Clean item name by removing 'Pokemon' and extra whitespace."""
        import re
        # Remove "Pokemon" (case insensitive) and common prefixes
        cleaned = re.sub(r'\bPokemon\b\s*', '', name, flags=re.IGNORECASE)
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else name


@dataclass
class Order:
    """Represents a Walmart order."""
    order_number: str
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    shipped_date: Optional[date] = None
    delivered_date: Optional[date] = None
    total_amount: float = 0.0
    status: str = "confirmed"  # confirmed, shipped, delivered, cancelled
    email_source: str = ""
    items: List[Item] = field(default_factory=list)
    id: Optional[int] = None

    def save(self) -> int:
        """Save order to database. Returns order ID."""
        with get_db() as conn:
            cursor = conn.cursor()

            if self.id:
                # Update existing order
                cursor.execute("""
                    UPDATE orders SET
                        order_date = ?,
                        expected_delivery_date = ?,
                        shipped_date = ?,
                        delivered_date = ?,
                        total_amount = ?,
                        status = ?,
                        email_source = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    self.order_date, self.expected_delivery_date,
                    self.shipped_date, self.delivered_date,
                    self.total_amount, self.status, self.email_source, self.id
                ))
            else:
                # Insert new order
                cursor.execute("""
                    INSERT OR REPLACE INTO orders
                    (order_number, order_date, expected_delivery_date, shipped_date,
                     delivered_date, total_amount, status, email_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.order_number, self.order_date, self.expected_delivery_date,
                    self.shipped_date, self.delivered_date, self.total_amount,
                    self.status, self.email_source
                ))
                self.id = cursor.lastrowid

            # Save items
            if self.items and self.id:
                # Delete existing items first
                cursor.execute("DELETE FROM items WHERE order_id = ?", (self.id,))
                for item in self.items:
                    cursor.execute("""
                        INSERT INTO items (order_id, name, quantity, unit_price, item_type, image_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (self.id, item.name, item.quantity, item.unit_price, item.item_type, item.image_url))

            return self.id

    @classmethod
    def get_by_order_number(cls, order_number: str) -> Optional['Order']:
        """Find order by order number."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
            row = cursor.fetchone()
            if row:
                order = cls(
                    id=row['id'],
                    order_number=row['order_number'],
                    order_date=parse_db_date(row['order_date']),
                    expected_delivery_date=parse_db_date(row['expected_delivery_date']),
                    shipped_date=parse_db_date(row['shipped_date']),
                    delivered_date=parse_db_date(row['delivered_date']),
                    total_amount=row['total_amount'] or 0.0,
                    status=row['status'] or 'confirmed',
                    email_source=row['email_source'] or ''
                )
                # Load items
                cursor.execute("SELECT * FROM items WHERE order_id = ?", (order.id,))
                for item_row in cursor.fetchall():
                    order.items.append(Item(
                        id=item_row['id'],
                        order_id=item_row['order_id'],
                        name=item_row['name'],
                        quantity=item_row['quantity'],
                        unit_price=item_row['unit_price'] or 0.0,
                        item_type=item_row['item_type'] or "",
                        image_url=item_row['image_url'] if 'image_url' in item_row.keys() else ""
                    ))
                return order
        return None

    @classmethod
    def get_all(cls) -> List['Order']:
        """Get all orders."""
        orders = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders ORDER BY order_date DESC")
            for row in cursor.fetchall():
                order = cls(
                    id=row['id'],
                    order_number=row['order_number'],
                    order_date=parse_db_date(row['order_date']),
                    expected_delivery_date=parse_db_date(row['expected_delivery_date']),
                    shipped_date=parse_db_date(row['shipped_date']),
                    delivered_date=parse_db_date(row['delivered_date']),
                    total_amount=row['total_amount'] or 0.0,
                    status=row['status'] or 'confirmed',
                    email_source=row['email_source'] or ''
                )
                orders.append(order)
        return orders

    @classmethod
    def get_active_orders(cls) -> List['Order']:
        """Get orders that are not cancelled or delivered."""
        orders = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders
                WHERE status NOT IN ('cancelled', 'delivered')
                ORDER BY order_date DESC
            """)
            for row in cursor.fetchall():
                order = cls(
                    id=row['id'],
                    order_number=row['order_number'],
                    order_date=parse_db_date(row['order_date']),
                    expected_delivery_date=parse_db_date(row['expected_delivery_date']),
                    shipped_date=parse_db_date(row['shipped_date']),
                    delivered_date=parse_db_date(row['delivered_date']),
                    total_amount=row['total_amount'] or 0.0,
                    status=row['status'] or 'confirmed',
                    email_source=row['email_source'] or ''
                )
                orders.append(order)
        return orders


@dataclass
class Credential:
    """Represents stored email credentials."""
    email: str
    provider: str
    app_password_encrypted: bytes = b""
    id: Optional[int] = None

    def save(self):
        """Save credential to database."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO credentials (email, provider, app_password_encrypted)
                VALUES (?, ?, ?)
            """, (self.email, self.provider, self.app_password_encrypted))
            self.id = cursor.lastrowid

    @classmethod
    def get_by_email(cls, email: str) -> Optional['Credential']:
        """Get credential by email."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credentials WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    email=row['email'],
                    provider=row['provider'],
                    app_password_encrypted=row['app_password_encrypted']
                )
        return None

    @classmethod
    def get_all(cls) -> List['Credential']:
        """Get all saved credentials."""
        credentials = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credentials")
            for row in cursor.fetchall():
                credentials.append(cls(
                    id=row['id'],
                    email=row['email'],
                    provider=row['provider'],
                    app_password_encrypted=row['app_password_encrypted']
                ))
        return credentials

    @classmethod
    def delete_all(cls):
        """Delete all saved credentials."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credentials")


def get_order_statistics() -> dict:
    """Get summary statistics of all orders."""
    with get_db() as conn:
        cursor = conn.cursor()

        stats = {
            'total_orders': 0,
            'confirmed': 0,
            'shipped': 0,
            'delivered': 0,
            'cancelled': 0,
            'total_spent': 0.0
        }

        cursor.execute("SELECT COUNT(*) as count FROM orders")
        stats['total_orders'] = cursor.fetchone()['count']

        cursor.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
        for row in cursor.fetchall():
            if row['status'] in stats:
                stats[row['status']] = row['count']

        cursor.execute("SELECT SUM(total_amount) as total FROM orders WHERE status != 'cancelled'")
        result = cursor.fetchone()
        stats['total_spent'] = result['total'] or 0.0

        return stats


def get_spending_by_item_type() -> List[dict]:
    """Get spending grouped by item type."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE(i.item_type, 'Unknown') as item_type,
                SUM(i.quantity) as total_quantity,
                SUM(i.quantity * i.unit_price) as total_spent
            FROM items i
            JOIN orders o ON i.order_id = o.id
            WHERE o.status != 'cancelled'
            GROUP BY i.item_type
            ORDER BY total_spent DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_spending_by_item_name() -> List[dict]:
    """Get spending grouped by item name with stick rate."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                i.name,
                i.image_url,
                i.quantity,
                i.unit_price,
                o.status,
                o.total_amount,
                (SELECT SUM(quantity) FROM items WHERE order_id = o.id) as order_total_qty
            FROM items i
            JOIN orders o ON i.order_id = o.id
        """)

        # Aggregate by item name
        item_data = {}
        for row in cursor.fetchall():
            name = Item.clean_name(row['name'])
            if name not in item_data:
                item_data[name] = {
                    'image_url': row['image_url'] or '',
                    'active_quantity': 0,
                    'cancelled_quantity': 0,
                    'total_spent': 0.0
                }

            qty = row['quantity'] or 1
            is_cancelled = row['status'] == 'cancelled'

            # Calculate item value
            if row['unit_price'] and row['unit_price'] > 0:
                item_value = row['unit_price'] * qty
            elif row['total_amount'] and row['order_total_qty'] and row['order_total_qty'] > 0:
                item_value = (row['total_amount'] / row['order_total_qty']) * qty
            else:
                item_value = 0.0

            if is_cancelled:
                item_data[name]['cancelled_quantity'] += qty
            else:
                item_data[name]['active_quantity'] += qty
                item_data[name]['total_spent'] += item_value

        # Build results with stick rate
        results = []
        for name, data in item_data.items():
            active_qty = data['active_quantity']
            cancelled_qty = data['cancelled_quantity']
            total_qty = active_qty + cancelled_qty
            stick_rate = (active_qty / total_qty * 100) if total_qty > 0 else 0
            results.append({
                'name': name,
                'image_url': data['image_url'],
                'active_quantity': active_qty,
                'cancelled_quantity': cancelled_qty,
                'total_spent': data['total_spent'],
                'stick_rate': stick_rate
            })

        # Sort by total_spent descending
        results.sort(key=lambda x: x['total_spent'], reverse=True)
        return results


@dataclass
class Scan:
    """Represents a completed scan."""
    email_used: str
    start_date: date
    end_date: date
    total_orders: int = 0
    total_confirmed: int = 0
    total_cancelled: int = 0
    total_shipped: int = 0
    total_delivered: int = 0
    total_spent: float = 0.0
    scanned_at: Optional[datetime] = None
    id: Optional[int] = None

    def save(self) -> int:
        """Save scan to database."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scans
                (email_used, start_date, end_date, total_orders, total_confirmed,
                 total_cancelled, total_shipped, total_delivered, total_spent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.email_used, self.start_date, self.end_date,
                self.total_orders, self.total_confirmed, self.total_cancelled,
                self.total_shipped, self.total_delivered, self.total_spent
            ))
            self.id = cursor.lastrowid
            return self.id

    @classmethod
    def get_all(cls) -> List['Scan']:
        """Get all scans ordered by most recent first."""
        scans = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM scans ORDER BY scanned_at DESC
            """)
            for row in cursor.fetchall():
                scanned_at = None
                if row['scanned_at']:
                    try:
                        scanned_at = datetime.strptime(row['scanned_at'], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                scans.append(cls(
                    id=row['id'],
                    email_used=row['email_used'] or '',
                    start_date=parse_db_date(row['start_date']),
                    end_date=parse_db_date(row['end_date']),
                    total_orders=row['total_orders'] or 0,
                    total_confirmed=row['total_confirmed'] if 'total_confirmed' in row.keys() else 0,
                    total_cancelled=row['total_cancelled'] or 0,
                    total_shipped=row['total_shipped'] or 0,
                    total_delivered=row['total_delivered'] or 0,
                    total_spent=row['total_spent'] if 'total_spent' in row.keys() else 0.0,
                    scanned_at=scanned_at
                ))
        return scans
