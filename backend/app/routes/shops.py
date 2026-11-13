import math

from fastapi import APIRouter, Query

from .. import live_store
from ..database import query
from ..domain import (estimate_wait, get_shop_or_404, live_counts, model_hour, now_local,
                      typical_wait)

router = APIRouter(prefix="/api/shops", tags=["Shops"])

CITY_CENTRE = (40.7128, -74.0060)  # simulated "Metropolis" centre


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    d_lat, d_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _list_shops(search=None, area=None, min_rating=None, shop_type=None,
                user_lat=None, user_lon=None) -> list[dict]:
    sql = """
        WITH prices AS (
            SELECT shop_id, AVG(price) AS average_price, MIN(price) AS min_price,
                   COUNT(*) AS service_count
            FROM services GROUP BY shop_id)
        SELECT s.*, p.average_price, p.min_price, p.service_count
        FROM shops s LEFT JOIN prices p ON p.shop_id = s.shop_id
        WHERE s.shop_status = 'Active'"""
    params = []
    if area:
        sql += " AND s.area = ?"
        params.append(area)
    if shop_type:
        sql += " AND s.shop_type = ?"
        params.append(shop_type)
    if min_rating is not None:
        sql += " AND s.rating >= ?"
        params.append(min_rating)
    if search:
        sql += " AND (s.shop_name LIKE ? OR s.owner_name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    sql += " ORDER BY s.shop_id"
    shops = query(sql, params)

    origin = (user_lat, user_lon) if user_lat is not None and user_lon is not None else CITY_CENTRE
    live_enabled = live_store.get_store() is not None
    counts = live_counts() if live_enabled else {}
    now = now_local()
    for s in shops:
        s["distance_km"] = round(haversine_distance(origin[0], origin[1], s["latitude"], s["longitude"]), 2)
        s["distance_from"] = "your location" if origin != CITY_CENTRE else "city centre"
        s["average_price"] = round(s["average_price"] or 0, 2)
        s["typical_wait_minutes"] = typical_wait(s["shop_id"], model_hour(s, now), now.weekday())
        c = counts.get(s["shop_id"], {"waiting": 0, "in_service": 0})
        s["live_queue_enabled"] = live_enabled
        s["waiting"] = c["waiting"] if live_enabled else None
        s["in_service"] = c["in_service"] if live_enabled else None
        s["estimated_wait_minutes"] = (estimate_wait(s, c["waiting"], c["in_service"], now)
                                       if live_enabled else None)
    return shops


@router.get("")
def get_shops(
    search: str | None = Query(None, max_length=60),
    area: str | None = Query(None, max_length=40),
    min_rating: float | None = Query(None, ge=0, le=5),
    shop_type: str | None = Query(None, max_length=20),
    user_lat: float | None = Query(None, ge=-90, le=90),
    user_lon: float | None = Query(None, ge=-180, le=180),
):
    return _list_shops(search, area, min_rating, shop_type, user_lat, user_lon)


@router.get("/recommendations")
def get_recommendations(
    user_lat: float | None = Query(None, ge=-90, le=90),
    user_lon: float | None = Query(None, ge=-180, le=180),
    weight_rating: float = Query(0.3, ge=0, le=1),
    weight_wait: float = Query(0.3, ge=0, le=1),
    weight_distance: float = Query(0.2, ge=0, le=1),
    weight_price: float = Query(0.2, ge=0, le=1),
):
    """Transparent weighted ranking: rating, wait, distance and price, each min-max normalised.
    Wait uses the live ML estimate when the live queue is enabled, otherwise the typical
    historical wait for this hour and weekday."""
    shops = _list_shops(user_lat=user_lat, user_lon=user_lon)
    if not shops:
        return []
    total = weight_rating + weight_wait + weight_distance + weight_price or 1.0
    w = {k: v / total for k, v in dict(rating=weight_rating, wait=weight_wait,
                                         distance=weight_distance, price=weight_price).items()}

    def wait_of(s):
        v = s["estimated_wait_minutes"] if s["live_queue_enabled"] else s["typical_wait_minutes"]
        return v or 0.0

    def norm(values, value, higher_is_better):
        lo, hi = min(values), max(values)
        x = (value - lo) / (hi - lo) if hi > lo else 1.0
        return x if higher_is_better else 1 - x

    ratings = [s["rating"] for s in shops]
    waits = [wait_of(s) for s in shops]
    dists = [s["distance_km"] for s in shops]
    prices = [s["average_price"] for s in shops]
    min_price = min(prices)
    ranked = []
    for s in shops:
        parts = {
            "rating": norm(ratings, s["rating"], True),
            "wait": norm(waits, wait_of(s), False),
            "distance": norm(dists, s["distance_km"], False),
            "price": norm(prices, s["average_price"], False),
        }
        score = sum(w[k] * parts[k] for k in parts)
        reasons = []
        if s["rating"] >= 4.5:
            reasons.append("Highly rated")
        if wait_of(s) <= 10:
            reasons.append("Short wait")
        if s["distance_km"] <= 1.5:
            reasons.append("Very close")
        if s["average_price"] <= min_price * 1.3:
            reasons.append("Budget friendly")
        ranked.append({**s, "recommendation_score": round(score * 100, 1),
                       "score_breakdown": {k: round(v * 100, 1) for k, v in parts.items()},
                       "weights": {k: round(v, 3) for k, v in w.items()},
                       "wait_used_minutes": round(wait_of(s), 1),
                       "reasons": reasons[:2] or ["Good overall balance"]})
    return sorted(ranked, key=lambda x: x["recommendation_score"], reverse=True)


@router.get("/{shop_id}")
def get_shop_detail(shop_id: int):
    base = get_shop_or_404(shop_id)
    listed = [s for s in _list_shops() if s["shop_id"] == shop_id]
    shop = listed[0] if listed else base
    shop["services"] = query(
        "SELECT service_id, service_name, price, average_duration_minutes FROM services "
        "WHERE shop_id = ? ORDER BY price", (shop_id,))
    shop["reviews"] = query("""
        SELECT r.review_id, r.rating, r.service_rating, r.cleanliness_rating, r.value_rating,
               r.waiting_time_rating, r.review_date, c.gender, c.age_group
        FROM reviews r JOIN customers c ON r.customer_id = c.customer_id
        WHERE r.shop_id = ? ORDER BY r.review_date DESC, r.review_id DESC LIMIT 5""", (shop_id,))
    shop["review_average"] = query(
        "SELECT ROUND(AVG(rating), 2) AS avg_rating, COUNT(*) AS n FROM reviews WHERE shop_id = ?",
        (shop_id,))[0]
    return shop
