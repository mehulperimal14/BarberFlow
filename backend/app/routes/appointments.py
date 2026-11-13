"""Appointments: historical (simulated) records are read-only; new bookings go to the live store."""
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import config, live_store
from ..database import query
from ..domain import (client_ip, get_customer_or_404, get_service_or_404, get_shop_or_404,
                      now_local, open_hours)

router = APIRouter(tags=["Appointments"])


class BookingBody(BaseModel):
    customer_id: int = Field(..., ge=1, le=10_000_000)
    shop_id: int = Field(..., ge=1)
    service_id: int = Field(..., ge=1)
    appointment_date: date
    appointment_time: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$", examples=["14:00"])


@router.get("/api/appointments")
def get_historical_appointments(shop_id: int | None = Query(None, ge=1),
                                customer_id: int | None = Query(None, ge=1),
                                limit: int = Query(100, ge=1, le=500)):
    """Historical (simulated) appointments, newest first."""
    sql = """
        SELECT a.*, s.shop_name, srv.service_name, srv.price, c.age_group, c.gender
        FROM appointments a
        JOIN shops s ON a.shop_id = s.shop_id
        JOIN services srv ON a.service_id = srv.service_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE 1 = 1"""
    params = []
    if shop_id:
        sql += " AND a.shop_id = ?"
        params.append(shop_id)
    if customer_id:
        sql += " AND a.customer_id = ?"
        params.append(customer_id)
    sql += " ORDER BY a.appointment_date DESC, a.appointment_time DESC LIMIT ?"
    params.append(limit)
    return query(sql, params)


@router.post("/api/appointments", status_code=201)
def book_appointment(body: BookingBody, request: Request):
    shop = get_shop_or_404(body.shop_id)
    get_customer_or_404(body.customer_id)
    service = get_service_or_404(body.service_id, body.shop_id)

    today = now_local().date()
    if body.appointment_date < today:
        raise HTTPException(status_code=422, detail="Appointment date is in the past")
    if body.appointment_date > today + timedelta(days=config.BOOKING_HORIZON_DAYS):
        raise HTTPException(status_code=422,
                            detail=f"Bookings open at most {config.BOOKING_HORIZON_DAYS} days ahead")
    o, c = open_hours(shop)
    h, m = map(int, body.appointment_time.split(":"))
    start_min, end_min = h * 60 + m, h * 60 + m + service["average_duration_minutes"]
    if start_min < o * 60 or end_min > c * 60:
        raise HTTPException(status_code=422,
                            detail=f"Outside opening hours ({shop['opening_time']}-{shop['closing_time']}); "
                                   f"a {service['average_duration_minutes']}-minute service must finish by closing")
    if body.appointment_date == today and start_min <= now_local().hour * 60 + now_local().minute:
        raise HTTPException(status_code=422, detail="That time has already passed today")

    store = live_store.require_store()
    fingerprint = live_store.client_fingerprint(client_ip(request))
    day = body.appointment_date.isoformat()
    with store.transaction(lock_key=1_000_000 + body.shop_id) as tx:
        tx.check_rate_limit(fingerprint)
        same_slot = tx.all("""SELECT customer_id FROM live_bookings
                              WHERE shop_id = ? AND appointment_date = ? AND appointment_time = ?
                                AND status = 'Scheduled'""", (body.shop_id, day, body.appointment_time))
        if any(int(r["customer_id"]) == body.customer_id for r in same_slot):
            raise HTTPException(status_code=409, detail="This customer already has this slot booked")
        if len(same_slot) >= shop["number_of_barbers"]:
            raise HTTPException(status_code=409,
                                detail=f"Slot full: all {shop['number_of_barbers']} barber(s) are booked at "
                                       f"{body.appointment_time}")
        row = tx.one("""
            INSERT INTO live_bookings (shop_id, customer_id, service_id, appointment_date,
                appointment_time, status, created_at, client_hash)
            VALUES (?, ?, ?, ?, ?, 'Scheduled', ?, ?) RETURNING booking_id, created_at""",
            (body.shop_id, body.customer_id, body.service_id, day, body.appointment_time,
             live_store.iso(live_store.utcnow()), fingerprint))
    return {"status": "success", "booking_id": row["booking_id"], "shop_id": body.shop_id,
            "shop_name": shop["shop_name"], "service_name": service["service_name"],
            "price": service["price"], "appointment_date": day,
            "appointment_time": body.appointment_time,
            "barbers_booked_in_slot": len(same_slot) + 1, "slot_capacity": shop["number_of_barbers"]}


@router.get("/api/bookings")
def get_live_bookings(shop_id: int = Query(..., ge=1), limit: int = Query(20, ge=1, le=100)):
    """Upcoming bookings made through the live app (empty if the live store is disabled)."""
    get_shop_or_404(shop_id)
    store = live_store.get_store()
    if store is None:
        return {"live_bookings_enabled": False, "bookings": []}
    rows = store.read("""
        SELECT booking_id, customer_id, service_id, appointment_date, appointment_time, status, created_at
        FROM live_bookings
        WHERE shop_id = ? AND status = 'Scheduled' AND appointment_date >= ?
        ORDER BY appointment_date, appointment_time LIMIT ?""",
        (shop_id, now_local().date().isoformat(), limit))
    if rows:
        names = {r["service_id"]: r["service_name"] for r in query(
            "SELECT service_id, service_name FROM services WHERE shop_id = ?", (shop_id,))}
        for r in rows:
            r["service_name"] = names.get(r["service_id"])
    return {"live_bookings_enabled": True, "bookings": rows}
