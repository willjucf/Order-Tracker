"""Data retrieval router for stats, spending, orders, and history."""
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from services.database.models import (
    get_order_statistics,
    get_spending_by_item_name,
    get_spending_by_item_type,
    Order,
    Scan,
)
from services.database.db import get_db

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/stats")
def get_stats():
    """Get order statistics summary."""
    return get_order_statistics()


@router.get("/spending")
def get_spending():
    """Get spending breakdown by item name with stick rates."""
    return get_spending_by_item_name()


@router.get("/spending/by-type")
def get_spending_by_type():
    """Get spending breakdown by item type."""
    return get_spending_by_item_type()


@router.get("/orders")
def get_orders():
    """Get all orders."""
    orders = Order.get_all()
    return [
        {
            "id": o.id,
            "orderNumber": o.order_number,
            "orderDate": str(o.order_date) if o.order_date else None,
            "expectedDeliveryDate": str(o.expected_delivery_date) if o.expected_delivery_date else None,
            "shippedDate": str(o.shipped_date) if o.shipped_date else None,
            "deliveredDate": str(o.delivered_date) if o.delivered_date else None,
            "totalAmount": o.total_amount,
            "status": o.status,
        }
        for o in orders
    ]


@router.get("/orders/{order_number}")
def get_order(order_number: str):
    """Get a specific order with items."""
    order = Order.get_by_order_number(order_number)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.id,
        "orderNumber": order.order_number,
        "orderDate": str(order.order_date) if order.order_date else None,
        "expectedDeliveryDate": str(order.expected_delivery_date) if order.expected_delivery_date else None,
        "shippedDate": str(order.shipped_date) if order.shipped_date else None,
        "deliveredDate": str(order.delivered_date) if order.delivered_date else None,
        "totalAmount": order.total_amount,
        "status": order.status,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unitPrice": item.unit_price,
                "itemType": item.item_type,
                "imageUrl": item.image_url,
            }
            for item in order.items
        ]
    }


@router.get("/history")
def get_history():
    """Get all scan history."""
    scans = Scan.get_all()
    return [
        {
            "id": s.id,
            "emailUsed": s.email_used,
            "startDate": str(s.start_date) if s.start_date else None,
            "endDate": str(s.end_date) if s.end_date else None,
            "totalOrders": s.total_orders,
            "totalConfirmed": s.total_confirmed,
            "totalShipped": s.total_shipped,
            "totalDelivered": s.total_delivered,
            "totalCancelled": s.total_cancelled,
            "totalSpent": s.total_spent,
            "scannedAt": str(s.scanned_at) if s.scanned_at else None,
        }
        for s in scans
    ]


@router.get("/history/{scan_id}")
def get_scan_detail(scan_id: int):
    """Get detailed scan information including item breakdown."""
    scans = Scan.get_all()
    scan = next((s for s in scans if s.id == scan_id), None)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get scan items from the database
    scan_items = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scan_items WHERE scan_id = ?", (scan_id,))
        for row in cursor.fetchall():
            scan_items.append({
                "itemName": row['item_name'],
                "totalQuantity": row['total_quantity'],
                "cancelledQuantity": row['cancelled_quantity'],
                "totalSpent": row['total_spent'],
                "imageUrl": row['image_url'] or "",
            })

    # Get all orders for context
    all_orders = Order.get_all()
    orders_data = []
    for o in all_orders:
        orders_data.append({
            "id": o.id,
            "orderNumber": o.order_number,
            "orderDate": str(o.order_date) if o.order_date else None,
            "expectedDeliveryDate": str(o.expected_delivery_date) if o.expected_delivery_date else None,
            "shippedDate": str(o.shipped_date) if o.shipped_date else None,
            "deliveredDate": str(o.delivered_date) if o.delivered_date else None,
            "totalAmount": o.total_amount,
            "status": o.status,
        })

    return {
        "id": scan.id,
        "emailUsed": scan.email_used,
        "startDate": str(scan.start_date) if scan.start_date else None,
        "endDate": str(scan.end_date) if scan.end_date else None,
        "totalOrders": scan.total_orders,
        "totalConfirmed": scan.total_confirmed,
        "totalShipped": scan.total_shipped,
        "totalDelivered": scan.total_delivered,
        "totalCancelled": scan.total_cancelled,
        "totalSpent": scan.total_spent,
        "scannedAt": str(scan.scanned_at) if scan.scanned_at else None,
        "items": scan_items,
        "orders": orders_data,
    }
