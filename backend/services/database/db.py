"""Database connection and schema setup."""
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Credentials table (stores encrypted app passwords)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                provider TEXT NOT NULL,
                app_password_encrypted BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_number TEXT UNIQUE NOT NULL,
                order_date DATE,
                expected_delivery_date DATE,
                shipped_date DATE,
                delivered_date DATE,
                total_amount REAL,
                status TEXT DEFAULT 'confirmed',
                email_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                unit_price REAL,
                item_type TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        """)

        # Scans table (history of scans)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY,
                email_used TEXT,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_orders INTEGER DEFAULT 0,
                total_confirmed INTEGER DEFAULT 0,
                total_cancelled INTEGER DEFAULT 0,
                total_shipped INTEGER DEFAULT 0,
                total_delivered INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Scan items table (track items per scan for stick rate)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_items (
                id INTEGER PRIMARY KEY,
                scan_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                total_quantity INTEGER DEFAULT 0,
                cancelled_quantity INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                image_url TEXT,
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON items(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_items_scan ON scan_items(scan_id)")

        # Add image_url column to items if it doesn't exist
        try:
            cursor.execute("ALTER TABLE items ADD COLUMN image_url TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Migrate scans table - add new columns if they don't exist
        scans_columns_to_add = [
            ("email_used", "TEXT"),
            ("total_confirmed", "INTEGER DEFAULT 0"),
            ("total_spent", "REAL DEFAULT 0.0"),
        ]
        for col_name, col_type in scans_columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE scans ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists


def clear_orders():
    """Clear all orders and items (for fresh scan)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items")
        cursor.execute("DELETE FROM orders")
