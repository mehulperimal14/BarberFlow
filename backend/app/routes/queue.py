"""Virtual queue: live entries (persisted in the live store) + read-only simulated history."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from fastapi import HTTPException

from .. import config, live_store
from ..database import query, query_one
from ..domain import (client_ip, estimate_wait, get_customer_or_404, get_service_or_404,
                      get_shop_or_404, live_window_start, now_local)

router = APIRouter(prefix="/api/queue", tags=["Queue"])


class JoinQueueBody(BaseModel):
    customer_id: int = Field(..., ge=1, le=10_000_000)
    service_id: int = Field(..., ge=1)
    source: Literal["customer_app", "barber_walkin"] = "customer_app"


class QueueAction(BaseModel):
    action: Literal["start", "complete", "skip"]


def _decorate(entries: list[dict]) -> list[dict]:
    """Attach customer and service details from the historical DB (cross-store 'join')."""
    if not entries:
        return entries
    cust_ids = sorted({e["customer_id"] for e in entries})
    srv_ids = sorted({e["service_id"] for e in entries})
    cust = {r["customer_id"]: r for r in query(
        f"SELECT customer_id, age_group, gender FROM customers WHERE customer_id IN ({','.join('?' * len(cust_ids))})",
        cust_ids)}
    srv = {r["service_id"]: r for r in query(
        f"SELECT service_id, service_name, price FROM services WHERE service_id IN ({','.join('?' * len(srv_ids))})",
        srv_ids)}
    for e in entries:
        e.update({k: cust.get(e["customer_id"], {}).get(k) for k in ("age_group", "gender")})
        e.update({k: srv.get(e["service_id"], {}).get(k) for k in ("service_name", "price")})
    return entries


def _shop_queue(shop: dict, executor=None) -> dict:
    store = live_store.get_store()
    reader = executor.all if executor else store.read
    rows = reader("""
        SELECT * FROM live_queue_entries
        WHERE shop_id = ? AND joined_at >= ?
        ORDER BY joined_at, entry_id""", (shop["shop_id"], live_window_start()))
    in_service = [r for r in rows if r["status"] == "In Service"]
    waiting = [r for r in rows if r["status"] == "Waiting"]
    recent = [r for r in rows if r["status"] in ("Completed", "Skipped")][-15:]
    now = now_local()
    for pos, r in enumerate(waiting):
        r["position"] = pos + 1
        r["estimated_wait_minutes_now"] = estimate_wait(shop, pos, len(in_service), now)
    return {"in_service": in_service, "waiting": waiting, "recent": recent[::-1]}


@router.get("/{shop_id}")
def get_shop_queue(shop_id: int):
    shop = get_shop_or_404(shop_id)
    store = live_store.get_store()
    if store is None:
        return {"shop_id": shop_id, "live_queue_enabled": False, "storage": "disabled",
                "message": "Live queue is disabled on this deployment because no persistent "
                           "database is configured. Analytics and predictions still work.",
                "in_service": [], "waiting": [], "recent": [],
                "number_of_barbers": shop["number_of_barbers"]}
    q = _shop_queue(shop)
    for k in ("in_service", "waiting", "recent"):
        _decorate(q[k])
    return {"shop_id": shop_id, "live_queue_enabled": True, "storage": store.backend,
            "number_of_barbers": shop["number_of_barbers"],
            "estimated_wait_for_new_customer": estimate_wait(shop, len(q["waiting"]), len(q["in_service"])),
            **q}


@router.get("/{shop_id}/history")
def get_simulated_day(shop_id: int):
    """The last simulated day for this shop, exactly as generated (no invented statuses)."""
    get_shop_or_404(shop_id)
    day = query_one("SELECT MAX(date) AS d FROM visits WHERE shop_id = ?", (shop_id,))["d"]
    visits = query("""
        SELECT v.visit_id, v.customer_id, v.arrival_time, v.service_start_time, v.service_end_time,
               v.waiting_time_minutes, v.service_duration_minutes, v.seat_id, v.visit_type,
               c.age_group, c.gender, s.service_name, s.price
        FROM visits v
        JOIN customers c ON v.customer_id = c.customer_id
        JOIN services s ON v.service_id = s.service_id
        WHERE v.shop_id = ? AND v.date = ?
        ORDER BY v.arrival_time, v.visit_id""", (shop_id, day))
    return {"shop_id": shop_id, "date": day, "source": "simulated history", "visits": visits}


@router.post("/{shop_id}/join", status_code=201)
def join_queue(shop_id: int, body: JoinQueueBody, request: Request):
    shop = get_shop_or_404(shop_id)
    if shop["shop_status"] != "Active":
        raise HTTPException(status_code=409, detail="This shop is not accepting customers")
    get_customer_or_404(body.customer_id)
    service = get_service_or_404(body.service_id, shop_id)
    store = live_store.require_store()
    fingerprint = live_store.client_fingerprint(client_ip(request))
    with store.transaction(lock_key=shop_id) as tx:
        tx.check_rate_limit(fingerprint)
        window = live_window_start()
        active = tx.all("""SELECT customer_id, status FROM live_queue_entries
                           WHERE shop_id = ? AND status IN ('Waiting', 'In Service') AND joined_at >= ?""",
                        (shop_id, window))
        if any(int(a["customer_id"]) == body.customer_id for a in active):
            raise HTTPException(status_code=409, detail="This customer is already in this shop's queue")
        waiting = sum(1 for a in active if a["status"] == "Waiting")
        in_service = len(active) - waiting
        if waiting >= config.MAX_ACTIVE_QUEUE_PER_SHOP:
            raise HTTPException(status_code=409, detail="The queue is full right now; please try another shop")
        eta = estimate_wait(shop, waiting, in_service)
        row = tx.one("""
            INSERT INTO live_queue_entries (shop_id, customer_id, service_id, service_duration_minutes,
                status, source, joined_at, estimated_wait_minutes, client_hash)
            VALUES (?, ?, ?, ?, 'Waiting', ?, ?, ?, ?) RETURNING entry_id, joined_at""",
            (shop_id, body.customer_id, body.service_id, service["average_duration_minutes"],
             body.source, live_store.iso(live_store.utcnow()), eta, fingerprint))
    return {"status": "success", "entry_id": row["entry_id"], "shop_id": shop_id,
            "shop_name": shop["shop_name"], "service_name": service["service_name"],
            "price": service["price"], "position": waiting + 1, "people_ahead": waiting,
            "estimated_wait_minutes": eta, "joined_at": row["joined_at"]}


_TRANSITIONS = {
    "start": ({"Waiting"}, "In Service", "started_at"),
    "complete": ({"In Service"}, "Completed", "completed_at"),
    "skip": ({"Waiting"}, "Skipped", "completed_at"),
}


@router.patch("/entries/{entry_id}")
def update_entry(entry_id: int, body: QueueAction, request: Request):
    store = live_store.require_store()
    fingerprint = live_store.client_fingerprint(client_ip(request))
    allowed_from, new_status, ts_col = _TRANSITIONS[body.action]
    entry = store.read("SELECT * FROM live_queue_entries WHERE entry_id = ?", (entry_id,))
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    shop = get_shop_or_404(int(entry[0]["shop_id"]))
    with store.transaction(lock_key=shop["shop_id"]) as tx:
        tx.check_rate_limit(fingerprint)
        current = tx.one("SELECT status FROM live_queue_entries WHERE entry_id = ?", (entry_id,))
        if current["status"] not in allowed_from:
            raise HTTPException(status_code=409,
                                detail=f"Cannot {body.action} an entry that is '{current['status']}'")
        if body.action == "start":
            busy = tx.scalar("""SELECT COUNT(*) AS n FROM live_queue_entries
                                WHERE shop_id = ? AND status = 'In Service' AND joined_at >= ?""",
                             (shop["shop_id"], live_window_start()))
            if busy >= shop["number_of_barbers"]:
                raise HTTPException(status_code=409,
                                    detail=f"All {shop['number_of_barbers']} barber(s) are busy")
        row = tx.one(f"""UPDATE live_queue_entries SET status = ?, {ts_col} = ?
                         WHERE entry_id = ? RETURNING entry_id, status""",
                     (new_status, live_store.iso(live_store.utcnow()), entry_id))
    return {"status": "success", "entry_id": row["entry_id"], "new_status": row["status"]}
