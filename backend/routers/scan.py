"""Scan router with WebSocket progress streaming."""
import asyncio
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from routers.email import get_email_client, get_connected_email
from services.parsers.walmart_parser import WalmartParser
from services.database.models import Order, Item, Scan, get_order_statistics
from services.database.db import clear_orders
from utils.config import EXTENDED_SEARCH_DAYS, STORE_CONFIGS

router = APIRouter(tags=["scan"])

# Track active scans
_active_scans = {}


class ScanRequest(BaseModel):
    startDate: str  # YYYY-MM-DD
    endDate: str    # YYYY-MM-DD
    store: str = "Walmart"


class ScanResponse(BaseModel):
    scanId: str


@router.post("/api/scan/start", response_model=ScanResponse)
async def start_scan(req: ScanRequest):
    """Start a new email scan."""
    client = get_email_client()
    if not client or not client.connected:
        raise HTTPException(status_code=400, detail="Not connected to email")

    store_config = STORE_CONFIGS.get(req.store)
    if not store_config or not store_config.get("enabled"):
        raise HTTPException(status_code=400, detail="Store not supported")

    scan_id = str(uuid.uuid4())
    _active_scans[scan_id] = {
        "status": "pending",
        "progress": [],
        "start_date": req.startDate,
        "end_date": req.endDate,
        "store": req.store,
        "sender_filter": store_config["sender_filter"],
    }

    # Start scan in background
    asyncio.get_event_loop().run_in_executor(
        None, _run_scan, scan_id
    )

    return ScanResponse(scanId=scan_id)


@router.websocket("/ws/scan/{scan_id}")
async def scan_websocket(websocket: WebSocket, scan_id: str):
    """WebSocket endpoint for scan progress updates."""
    await websocket.accept()

    if scan_id not in _active_scans:
        await websocket.send_json({"error": "Scan not found"})
        await websocket.close()
        return

    scan_data = _active_scans[scan_id]
    last_index = 0

    try:
        while True:
            # Send any new progress messages
            progress = scan_data["progress"]
            while last_index < len(progress):
                await websocket.send_json(progress[last_index])
                last_index += 1

            # Check if scan is complete
            if scan_data["status"] in ("complete", "error"):
                # Send remaining messages
                while last_index < len(progress):
                    await websocket.send_json(progress[last_index])
                    last_index += 1
                break

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up after client disconnects
        if scan_id in _active_scans and _active_scans[scan_id]["status"] in ("complete", "error"):
            del _active_scans[scan_id]


def _run_scan(scan_id: str):
    """Run the email scan (runs in thread pool)."""
    scan_data = _active_scans[scan_id]
    scan_data["status"] = "running"

    parser = WalmartParser()
    client = get_email_client()
    email_cache = {}

    try:
        start = datetime.strptime(scan_data["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(scan_data["end_date"], "%Y-%m-%d").date()
        sender_filter = scan_data["sender_filter"]
        store = scan_data["store"]

        # Add one day to end date to make it inclusive
        end_inclusive = end + timedelta(days=1)

        # Clear previous results
        clear_orders()

        # Phase 1: Search for emails
        _emit(scan_id, "searching", 0, 0, f"Searching {store} emails...")

        emails = client.search_and_fetch(
            start, end_inclusive,
            sender_filter=sender_filter,
            progress_callback=lambda c, t: _emit(scan_id, "fetching", c, t, f"Fetching email {c}/{t}")
        )

        # Cache emails
        for em in emails:
            email_cache[em.uid] = em

        # Parse and save orders
        orders_found = 0
        for i, raw_email in enumerate(emails):
            parsed = parser.parse(raw_email)
            if parsed:
                _save_parsed_order(parsed)
                orders_found += 1
            _emit(scan_id, "parsing", i + 1, len(emails), f"Parsing email {i+1}/{len(emails)}")

        _emit(scan_id, "extended", 0, 0, f"Found {orders_found} orders. Checking statuses...")

        # Phase 2: Extended search
        _extended_status_search(scan_id, client, parser, email_cache, sender_filter)

        # Save scan history
        stats = get_order_statistics()
        scan = Scan(
            email_used=get_connected_email(),
            start_date=start,
            end_date=end,
            total_orders=stats['total_orders'],
            total_confirmed=stats['confirmed'],
            total_cancelled=stats['cancelled'],
            total_shipped=stats['shipped'],
            total_delivered=stats['delivered'],
            total_spent=stats['total_spent']
        )
        scan.save()

        # Save scan items for history detail
        _save_scan_items(scan.id)

        _emit(scan_id, "complete", 1, 1, f"Scan complete! Found {orders_found} orders")
        scan_data["status"] = "complete"

    except Exception as e:
        _emit(scan_id, "error", 0, 0, f"Error: {str(e)}")
        scan_data["status"] = "error"


def _extended_status_search(scan_id, client, parser, email_cache, sender_filter):
    """Search for shipped/delivered emails for active orders."""
    active_orders = Order.get_active_orders()
    if not active_orders:
        return

    earliest_date = None
    latest_date = date.today() + timedelta(days=1)

    for order in active_orders:
        order_start = order.order_date or date.today() - timedelta(days=60)
        if earliest_date is None or order_start < earliest_date:
            earliest_date = order_start
        if order.expected_delivery_date:
            extended_end = order.expected_delivery_date + timedelta(days=EXTENDED_SEARCH_DAYS)
            if extended_end > latest_date:
                latest_date = min(extended_end, date.today() + timedelta(days=1))

    if earliest_date is None:
        return

    _emit(scan_id, "extended", 0, 0, "Searching extended date range...")

    try:
        cached_uids = set(email_cache.keys())
        all_uids = client.search_emails(earliest_date, latest_date, sender_filter=sender_filter)
        new_uids = [uid for uid in all_uids if uid not in cached_uids]

        total_new = len(new_uids)
        for i, uid in enumerate(new_uids):
            em = client.fetch_email(uid)
            if em:
                email_cache[uid] = em
            _emit(scan_id, "extended_fetch", i + 1, total_new, f"Fetching extended {i+1}/{total_new}")

        order_numbers = {order.order_number: order for order in active_orders}
        total_emails = len(email_cache)

        for i, em in enumerate(email_cache.values()):
            parsed = parser.parse(em)
            if parsed and parsed.order_number in order_numbers:
                order = order_numbers[parsed.order_number]
                if parsed.email_type == 'shipped' and not order.shipped_date:
                    order.shipped_date = parsed.shipped_date
                    order.status = 'shipped'
                    if parsed.expected_delivery_date:
                        order.expected_delivery_date = parsed.expected_delivery_date
                    order.save()
                elif parsed.email_type == 'delivered' and not order.delivered_date:
                    order.delivered_date = parsed.delivered_date
                    order.status = 'delivered'
                    order.save()
                elif parsed.email_type == 'cancelled' and order.status != 'cancelled':
                    order.status = 'cancelled'
                    order.save()
            _emit(scan_id, "updating", i + 1, total_emails, f"Updating statuses {i+1}/{total_emails}")

    except Exception as e:
        print(f"Error in extended search: {e}")


def _save_parsed_order(parsed):
    """Save parsed order to database."""
    existing = Order.get_by_order_number(parsed.order_number)

    if existing:
        if parsed.email_type == 'confirmation':
            if not existing.order_date and parsed.order_date:
                existing.order_date = parsed.order_date
            if not existing.expected_delivery_date and parsed.expected_delivery_date:
                existing.expected_delivery_date = parsed.expected_delivery_date
            if existing.total_amount == 0 and parsed.total_amount:
                existing.total_amount = parsed.total_amount
            if not existing.items and parsed.items:
                existing.items = [
                    Item(name=item.name, quantity=item.quantity, unit_price=item.unit_price,
                         item_type=item.item_type, image_url=item.image_url)
                    for item in parsed.items
                ]
        elif parsed.email_type == 'shipped':
            existing.shipped_date = parsed.shipped_date
            if existing.status in ('confirmed', ''):
                existing.status = 'shipped'
            if parsed.expected_delivery_date:
                existing.expected_delivery_date = parsed.expected_delivery_date
            if parsed.order_date and not existing.order_date:
                existing.order_date = parsed.order_date
        elif parsed.email_type == 'delivered':
            existing.delivered_date = parsed.delivered_date
            existing.status = 'delivered'
            if parsed.order_date and not existing.order_date:
                existing.order_date = parsed.order_date
            if parsed.total_amount and existing.total_amount == 0:
                existing.total_amount = parsed.total_amount
        elif parsed.email_type == 'cancelled':
            existing.status = 'cancelled'
            if parsed.total_amount and existing.total_amount == 0:
                existing.total_amount = parsed.total_amount
        existing.save()
    else:
        if parsed.email_type != 'confirmation':
            return

        order = Order(
            order_number=parsed.order_number,
            order_date=parsed.order_date,
            expected_delivery_date=parsed.expected_delivery_date,
            shipped_date=parsed.shipped_date,
            delivered_date=parsed.delivered_date,
            total_amount=parsed.total_amount,
            status='confirmed',
            items=[
                Item(name=item.name, quantity=item.quantity, unit_price=item.unit_price,
                     item_type=item.item_type, image_url=item.image_url)
                for item in parsed.items
            ] if parsed.items else []
        )
        order.save()


def _save_scan_items(scan_id: int):
    """Save item breakdown for the scan."""
    from services.database.models import get_spending_by_item_name
    from services.database.db import get_db

    items = get_spending_by_item_name()
    with get_db() as conn:
        cursor = conn.cursor()
        for item in items:
            cursor.execute("""
                INSERT INTO scan_items (scan_id, item_name, total_quantity, cancelled_quantity, total_spent, image_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                item['name'],
                item['active_quantity'] + item['cancelled_quantity'],
                item['cancelled_quantity'],
                item['total_spent'],
                item.get('image_url', '')
            ))


def _emit(scan_id: str, phase: str, current: int, total: int, status: str):
    """Emit a progress message for a scan."""
    if scan_id in _active_scans:
        _active_scans[scan_id]["progress"].append({
            "phase": phase,
            "current": current,
            "total": total,
            "status": status,
        })
