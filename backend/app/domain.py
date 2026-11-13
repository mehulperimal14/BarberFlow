"""Shared lookups and business logic used by several routers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import HTTPException, Request

from . import config, live_store, ml
from .database import query, query_one

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo(config.APP_TIMEZONE)
except Exception:  # tz database missing -> fall back to UTC rather than crash
    _TZ = timezone.utc


def now_local() -> datetime:
    return datetime.now(_TZ)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_shop_or_404(shop_id: int) -> dict:
    shop = query_one("SELECT * FROM shops WHERE shop_id = ?", (shop_id,))
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_id} not found")
    return shop


def get_customer_or_404(customer_id: int) -> dict:
    cust = query_one("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    if not cust:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found (valid IDs: 1-5000)")
    return cust


def get_service_or_404(service_id: int, shop_id: int) -> dict:
    srv = query_one("SELECT * FROM services WHERE service_id = ? AND shop_id = ?", (service_id, shop_id))
    if not srv:
        raise HTTPException(status_code=404, detail=f"Service {service_id} is not offered by shop {shop_id}")
    return srv


def open_hours(shop: dict) -> tuple[int, int]:
    return int(shop["opening_time"][:2]), int(shop["closing_time"][:2])


@lru_cache(maxsize=1)
def _typical_wait_table() -> dict:
    """Average historical wait per (shop, hour, weekday Mon=0). Computed once per process."""
    rows = query("""
        SELECT shop_id,
               CAST(SUBSTR(arrival_time, 1, 2) AS INTEGER) AS hour,
               (CAST(STRFTIME('%w', date) AS INTEGER) + 6) % 7 AS dow,   -- SQLite Sun=0 -> Mon=0
               AVG(waiting_time_minutes) AS avg_wait,
               COUNT(*) AS n
        FROM visits GROUP BY shop_id, hour, dow""")
    return {(r["shop_id"], r["hour"], r["dow"]): (r["avg_wait"], r["n"]) for r in rows}


def typical_wait(shop_id: int, hour: int, dow: int) -> float | None:
    hit = _typical_wait_table().get((shop_id, hour, dow))
    return round(hit[0], 1) if hit else None


def model_hour(shop: dict, when: datetime) -> int:
    """Clamp the clock hour into the shop's trading hours (the model never saw closed hours)."""
    o, c = open_hours(shop)
    return min(max(when.hour, o), c - 1)


def estimate_wait(shop: dict, waiting_ahead: int, in_service: int, when: datetime | None = None) -> int:
    """Live wait estimate (minutes) for someone joining behind `waiting_ahead` people."""
    if waiting_ahead <= 0 and in_service < shop["number_of_barbers"]:
        return 0  # a barber is free right now
    model = ml.get_model("waiting_time")
    when = when or now_local()
    occupied = min(in_service, shop["number_of_seats"])
    if model is None:  # transparent fallback: average service time per barber
        return int(round(waiting_ahead * 30 / max(shop["number_of_barbers"], 1)))
    x = [waiting_ahead, occupied, shop["number_of_seats"] - occupied, shop["number_of_barbers"],
         shop["number_of_seats"], model_hour(shop, when), when.weekday()]
    return max(0, int(round(model.predict(x))))


def live_window_start() -> str:
    return live_store.iso(live_store.utcnow() - timedelta(hours=config.LIVE_QUEUE_WINDOW_HOURS))


def live_counts() -> dict:
    """{shop_id: {"waiting": n, "in_service": m}} for the active live window ({} if disabled)."""
    store = live_store.get_store()
    if store is None:
        return {}
    rows = store.read("""
        SELECT shop_id,
               SUM(CASE WHEN status = 'Waiting' THEN 1 ELSE 0 END) AS waiting,
               SUM(CASE WHEN status = 'In Service' THEN 1 ELSE 0 END) AS in_service
        FROM live_queue_entries
        WHERE status IN ('Waiting', 'In Service') AND joined_at >= ?
        GROUP BY shop_id""", (live_window_start(),))
    return {int(r["shop_id"]): {"waiting": int(r["waiting"] or 0), "in_service": int(r["in_service"] or 0)}
            for r in rows}
