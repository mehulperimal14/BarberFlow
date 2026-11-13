"""Analytics over the historical (simulated) dataset.

Every multi-table metric pre-aggregates each fact table per shop in a CTE *before* joining,
so one row per shop is joined to one row per shop. (The previous version joined visits x
availability directly, multiplying counts by ~1,000 -- the "join fan-out" bug.)
"""
import math

from fastapi import APIRouter, Query

from ..database import query, query_one, scalar
from ..domain import get_shop_or_404

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULL_DAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WAIT_TIERS = ["0 min", "1-10 min", "11-20 min", "21-30 min", "30+ min"]


def _filter(area: str | None, shop_id: int | None, col: str = "shop_id") -> tuple[str, list]:
    """WHERE fragment restricting `col` to shops matching the filters. Params built per fragment."""
    if not area and not shop_id:
        return "1 = 1", []
    sub, params = "SELECT shop_id FROM shops WHERE 1 = 1", []
    if area:
        sub += " AND area = ?"
        params.append(area)
    if shop_id:
        sub += " AND shop_id = ?"
        params.append(shop_id)
    return f"{col} IN ({sub})", params


def _wait_percentile(where: str, params: list, p: float):
    n = scalar(f"SELECT COUNT(*) FROM visits WHERE {where}", params)
    if not n:
        return None
    offset = int(math.floor(p * (n - 1)))
    return scalar(f"SELECT waiting_time_minutes FROM visits WHERE {where} "
                  f"ORDER BY waiting_time_minutes LIMIT 1 OFFSET ?", params + [offset])


def _round(v, nd=1):
    return round(v, nd) if v is not None else None


@router.get("/overview")
def get_market_overview(area: str | None = Query(None, max_length=40),
                        shop_id: int | None = Query(None, ge=1)):
    f, p = _filter(area, shop_id)
    fs, ps = _filter(area, shop_id, "s.shop_id")
    fv, pv = _filter(area, shop_id, "v.shop_id")
    filtered = bool(area or shop_id)

    visits = query_one(f"""
        SELECT COUNT(*) AS total_visits, AVG(waiting_time_minutes) AS avg_wait,
               AVG(CASE WHEN waiting_time_minutes = 0 THEN 1.0 ELSE 0 END) AS zero_share,
               AVG(CASE WHEN waiting_time_minutes > 30 THEN 1.0 ELSE 0 END) AS over30_share,
               COUNT(DISTINCT customer_id) AS customers_served
        FROM visits WHERE {f}""", p)
    appts = query_one(f"""
        SELECT COUNT(*) AS total,
               SUM(status = 'Completed') AS completed, SUM(status = 'Cancelled') AS cancelled,
               SUM(status = 'No-Show') AS no_show
        FROM appointments WHERE {f}""", p)
    revenue = query_one(f"""
        SELECT SUM(srv.price) AS revenue, AVG(srv.price) AS avg_ticket
        FROM visits v JOIN services srv ON srv.service_id = v.service_id WHERE {fv}""", pv)
    util = query_one(f"""SELECT AVG(occupied_seats * 100.0 / total_seats) AS util,
                                AVG(queue_length) AS avg_queue, MAX(queue_length) AS max_queue
                         FROM availability WHERE {f}""", p)
    shops = query_one(f"SELECT COUNT(*) AS n, AVG(rating) AS listed FROM shops s WHERE {fs}", ps)
    reviews = query_one(f"SELECT COUNT(*) AS n, AVG(rating) AS avg FROM reviews WHERE {f}", p)
    total_appts = appts["total"] or 0

    def rate(x):
        return round((x or 0) * 100.0 / total_appts, 2) if total_appts else 0.0

    return {
        "filters": {"area": area, "shop_id": shop_id},
        "total_shops": shops["n"],
        "total_customers": visits["customers_served"] if filtered else scalar("SELECT COUNT(*) FROM customers"),
        "customers_label": "customers served by the selected shops" if filtered else "registered customers",
        "total_visits": visits["total_visits"],
        "average_wait_minutes": _round(visits["avg_wait"]),
        "median_wait_minutes": _wait_percentile(f, p, 0.5),
        "p90_wait_minutes": _wait_percentile(f, p, 0.9),
        "zero_wait_share_pct": _round((visits["zero_share"] or 0) * 100),
        "over_30_min_share_pct": _round((visits["over30_share"] or 0) * 100),
        "average_rating": _round(shops["listed"], 2),            # listed shop rating (generator attribute)
        "average_review_rating": _round(reviews["avg"], 2),      # mean of individual reviews
        "total_reviews": reviews["n"],
        "average_utilization_pct": _round(util["util"]),
        "average_queue_length": _round(util["avg_queue"], 2),
        "max_queue_length": util["max_queue"],
        "total_appointments": total_appts,
        "appointment_completion_rate_pct": rate(appts["completed"]),
        "appointment_cancellation_rate_pct": rate(appts["cancelled"]),
        "appointment_noshow_rate_pct": rate(appts["no_show"]),
        "total_revenue": _round(revenue["revenue"], 2),
        "average_ticket": _round(revenue["avg_ticket"], 2),
        "revenue_note": "list price x completed visits (simulated; no payment data)",
    }


@router.get("/demand")
def get_demand_charts(shop_id: int | None = Query(None, ge=1),
                      area: str | None = Query(None, max_length=40)):
    f, p = _filter(area, shop_id)
    by_hour = query(f"""
        SELECT SUBSTR(arrival_time, 1, 2) AS hour, COUNT(*) AS visits
        FROM visits WHERE {f} GROUP BY hour ORDER BY hour""", p)
    total = sum(r["visits"] for r in by_hour) or 1
    for r in by_hour:
        r["share_pct"] = round(r["visits"] * 100.0 / total, 2)
    by_day_rows = query(f"""
        SELECT (CAST(STRFTIME('%w', date) AS INTEGER) + 6) % 7 AS dow,
               COUNT(*) AS visits, COUNT(DISTINCT date) AS days
        FROM visits WHERE {f} GROUP BY dow""", p)
    by_day = {r["dow"]: r for r in by_day_rows}
    return {
        "demand_by_hour": by_hour,
        "demand_by_day": [{"day_name": DAY_NAMES[d], "visits": by_day.get(d, {}).get("visits", 0),
                           "avg_visits_per_day": round(by_day[d]["visits"] / by_day[d]["days"], 1)
                           if d in by_day else 0}
                          for d in range(7)],
    }


@router.get("/waiting-time")
def get_waiting_time_charts(shop_id: int | None = Query(None, ge=1),
                            area: str | None = Query(None, max_length=40)):
    f, p = _filter(area, shop_id)
    by_hour = query(f"""
        SELECT SUBSTR(arrival_time, 1, 2) AS hour, AVG(waiting_time_minutes) AS avg_wait, COUNT(*) AS visits
        FROM visits WHERE {f} GROUP BY hour ORDER BY hour""", p)
    dist = query(f"""
        SELECT CASE WHEN waiting_time_minutes = 0 THEN '0 min'
                    WHEN waiting_time_minutes <= 10 THEN '1-10 min'
                    WHEN waiting_time_minutes <= 20 THEN '11-20 min'
                    WHEN waiting_time_minutes <= 30 THEN '21-30 min'
                    ELSE '30+ min' END AS wait_tier,
               COUNT(*) AS count
        FROM visits WHERE {f} GROUP BY wait_tier""", p)
    by_day = query(f"""
        SELECT (CAST(STRFTIME('%w', date) AS INTEGER) + 6) % 7 AS dow, AVG(waiting_time_minutes) AS avg_wait
        FROM visits WHERE {f} GROUP BY dow ORDER BY dow""", p)
    counts = {d["wait_tier"]: d["count"] for d in dist}
    return {
        "wait_by_hour": [{"hour": h["hour"], "avg_wait": round(h["avg_wait"], 1), "visits": h["visits"]}
                         for h in by_hour],
        "wait_by_day": [{"day_name": DAY_NAMES[d["dow"]], "avg_wait": round(d["avg_wait"], 1)} for d in by_day],
        "wait_distribution": [{"wait_tier": t, "count": counts.get(t, 0)} for t in WAIT_TIERS],
    }


@router.get("/satisfaction")
def get_satisfaction(shop_id: int | None = Query(None, ge=1),
                     area: str | None = Query(None, max_length=40)):
    """Average review rating by the wait the reviewer actually experienced.

    Reviews have no visit_id, so each review is matched to that customer's visit at the same
    shop on the review date or the day before (reviews are written 0-1 days after a visit);
    ROW_NUMBER keeps exactly one visit per review to avoid double counting.
    """
    f, p = _filter(area, shop_id, "r.shop_id")
    rows = query(f"""
        WITH matched AS (
            SELECT r.review_id, r.rating, r.waiting_time_rating, v.waiting_time_minutes,
                   ROW_NUMBER() OVER (PARTITION BY r.review_id ORDER BY v.date DESC, v.visit_id DESC) AS rn
            FROM reviews r
            JOIN visits v ON v.customer_id = r.customer_id AND v.shop_id = r.shop_id
                         AND v.date BETWEEN DATE(r.review_date, '-1 day') AND r.review_date
            WHERE {f})
        SELECT CASE WHEN waiting_time_minutes = 0 THEN '0 min'
                    WHEN waiting_time_minutes <= 10 THEN '1-10 min'
                    WHEN waiting_time_minutes <= 25 THEN '11-25 min'
                    ELSE '25+ min' END AS wait_tier,
               MIN(waiting_time_minutes) AS sort_key,
               COUNT(*) AS reviews,
               ROUND(AVG(rating), 2) AS avg_rating,
               ROUND(AVG(waiting_time_rating), 2) AS avg_wait_experience_rating
        FROM matched WHERE rn = 1
        GROUP BY wait_tier ORDER BY sort_key""", p)
    total_reviews = scalar(f"SELECT COUNT(*) FROM reviews r WHERE {f}", p)
    insight = None
    by_tier = {r["wait_tier"]: r for r in rows}
    if "0 min" in by_tier and "25+ min" in by_tier:
        a, b = by_tier["0 min"]["avg_rating"], by_tier["25+ min"]["avg_rating"]
        insight = (f"Reviews after no wait average {a} stars versus {b} stars after waits over "
                   f"25 minutes, a {round((a - b) / a * 100)}% drop. In the simulation, wait experience "
                   f"is one of the inputs to the rating, so this confirms the pipeline recovers it.")
    for r in rows:
        r.pop("sort_key", None)
    return {"tiers": rows, "matched_reviews": sum(r["reviews"] for r in rows),
            "total_reviews": total_reviews, "insight": insight}


@router.get("/shop-performance")
def get_shop_performance():
    """Demand vs capacity per shop, with quadrants split at the market averages."""
    perf = query("""
        WITH v AS (SELECT shop_id, COUNT(*) AS total_visits, AVG(waiting_time_minutes) AS avg_wait
                   FROM visits GROUP BY shop_id),
             a AS (SELECT shop_id, AVG(occupied_seats * 100.0 / total_seats) AS avg_util
                   FROM availability GROUP BY shop_id),
             r AS (SELECT shop_id, AVG(rating) AS review_rating FROM reviews GROUP BY shop_id),
             rev AS (SELECT v.shop_id, SUM(srv.price) AS revenue
                     FROM visits v JOIN services srv ON srv.service_id = v.service_id GROUP BY v.shop_id)
        SELECT s.shop_id, s.shop_name, s.shop_type, s.area, s.number_of_seats, s.number_of_barbers,
               s.rating, COALESCE(v.total_visits, 0) AS total_visits,
               ROUND(v.avg_wait, 1) AS avg_wait, ROUND(a.avg_util, 1) AS avg_utilization,
               ROUND(r.review_rating, 2) AS review_rating, ROUND(rev.revenue, 2) AS revenue
        FROM shops s
        LEFT JOIN v ON v.shop_id = s.shop_id
        LEFT JOIN a ON a.shop_id = s.shop_id
        LEFT JOIN r ON r.shop_id = s.shop_id
        LEFT JOIN rev ON rev.shop_id = s.shop_id
        ORDER BY total_visits DESC, s.shop_id""")
    if not perf:
        return {"shops_data": [], "threshold_visits": 0, "threshold_seats": 0, "quadrant_counts": {}}
    avg_visits = sum(x["total_visits"] for x in perf) / len(perf)
    avg_seats = sum(x["number_of_seats"] for x in perf) / len(perf)
    counts = {}
    for x in perf:
        high_demand, high_capacity = x["total_visits"] >= avg_visits, x["number_of_seats"] >= avg_seats
        x["quadrant"] = {(True, True): "Leader", (True, False): "Bottleneck",
                         (False, True): "Underutilized", (False, False): "Low Scale"}[(high_demand, high_capacity)]
        counts[x["quadrant"]] = counts.get(x["quadrant"], 0) + 1
    return {"shops_data": perf, "threshold_visits": round(avg_visits, 0),
            "threshold_seats": round(avg_seats, 2), "quadrant_counts": counts}


@router.get("/location")
def get_location_opportunity():
    """Visits per seat by area, compared with the market-wide ratio."""
    areas = query("""
        WITH sv AS (SELECT shop_id, COUNT(*) AS visits, SUM(waiting_time_minutes) AS wait_sum
                    FROM visits GROUP BY shop_id)
        SELECT s.area, COUNT(*) AS shop_count, SUM(s.number_of_seats) AS total_seats,
               SUM(s.number_of_barbers) AS total_barbers, COALESCE(SUM(sv.visits), 0) AS total_visits,
               ROUND(SUM(sv.wait_sum) * 1.0 / NULLIF(SUM(sv.visits), 0), 1) AS avg_wait_minutes,
               ROUND(AVG(s.rating), 2) AS avg_rating
        FROM shops s LEFT JOIN sv ON sv.shop_id = s.shop_id
        GROUP BY s.area""")
    seats = sum(a["total_seats"] for a in areas) or 1
    market = sum(a["total_visits"] for a in areas) / seats
    high, low = market * 1.15, market * 0.85
    for a in areas:
        a["visits_per_seat"] = round(a["total_visits"] / a["total_seats"], 1) if a["total_seats"] else 0
        a["visits_per_barber"] = round(a["total_visits"] / a["total_barbers"], 1) if a["total_barbers"] else 0
        a["index_vs_market"] = round(a["visits_per_seat"] / market, 2)
        if a["visits_per_seat"] >= high:
            a["status"] = "High Opportunity (Under-served)"
        elif a["visits_per_seat"] <= low:
            a["status"] = "Over-saturated"
        else:
            a["status"] = "Balanced Market"
    areas.sort(key=lambda a: a["visits_per_seat"], reverse=True)
    return {"areas": areas, "market_visits_per_seat": round(market, 1),
            "thresholds": {"high_opportunity_at_or_above": round(high, 1),
                           "over_saturated_at_or_below": round(low, 1)}}


@router.get("/shop/{shop_id}")
def get_shop_analytics(shop_id: int):
    shop = get_shop_or_404(shop_id)
    kpis = query_one("""
        SELECT COUNT(v.visit_id) AS total_visits, ROUND(AVG(v.waiting_time_minutes), 1) AS avg_wait,
               ROUND(SUM(srv.price), 2) AS total_revenue, ROUND(AVG(srv.price), 2) AS avg_ticket
        FROM visits v JOIN services srv ON v.service_id = srv.service_id
        WHERE v.shop_id = ?""", (shop_id,))
    util = scalar("SELECT ROUND(AVG(occupied_seats * 100.0 / total_seats), 1) FROM availability WHERE shop_id = ?",
                  (shop_id,))
    services = query("""
        SELECT srv.service_id, srv.service_name, COUNT(v.visit_id) AS count, ROUND(SUM(srv.price), 2) AS revenue
        FROM visits v JOIN services srv ON v.service_id = srv.service_id
        WHERE v.shop_id = ? GROUP BY srv.service_id, srv.service_name ORDER BY count DESC""", (shop_id,))
    repeat = query_one("""
        WITH client_visits AS (SELECT customer_id, COUNT(*) AS visit_count FROM visits
                               WHERE shop_id = ? GROUP BY customer_id)
        SELECT COUNT(*) AS total_clients, SUM(CASE WHEN visit_count >= 3 THEN 1 ELSE 0 END) AS repeat_clients
        FROM client_visits""", (shop_id,))
    appts = query_one("""SELECT COUNT(*) AS total, SUM(cancellation_flag) AS cancelled, SUM(no_show_flag) AS no_shows
                         FROM appointments WHERE shop_id = ?""", (shop_id,))
    by_day = query("""
        SELECT (CAST(STRFTIME('%w', date) AS INTEGER) + 6) % 7 AS dow,
               COUNT(*) * 1.0 / COUNT(DISTINCT date) AS avg_visits
        FROM visits WHERE shop_id = ? GROUP BY dow ORDER BY avg_visits ASC""", (shop_id,))

    def pct(a, b):
        return round((a or 0) * 100.0 / b, 1) if b else 0.0

    avg_wait = (kpis or {}).get("avg_wait") or 0
    recs = []
    if avg_wait >= 20:
        recs.append({"type": "Capacity bottleneck",
                     "message": f"Average wait is {avg_wait} minutes with {shop['number_of_barbers']} barber(s). "
                                f"Add a barber at peak hours before adding chairs: barbers, not seats, serve the queue."})
    else:
        recs.append({"type": "Healthy flow",
                     "message": f"Average wait is {avg_wait} minutes, so the queue clears efficiently."})
    if by_day:
        slow, busy = by_day[0], by_day[-1]
        recs.append({"type": "Slow-day promotion",
                     "message": f"{FULL_DAY[slow['dow']]}s average {slow['avg_visits']:.1f} visits vs "
                                f"{busy['avg_visits']:.1f} on {FULL_DAY[busy['dow']]}s. "
                                f"Consider an off-peak offer on {FULL_DAY[slow['dow']]} mornings."})
    if services:
        top = max(services, key=lambda s: s["revenue"] or 0)
        recs.append({"type": "Revenue focus",
                     "message": f"'{top['service_name']}' earns the most revenue (${top['revenue']:,.0f}). "
                                f"Feature it in bundles to lift the average ticket."})
    return {
        "shop": {k: shop[k] for k in ("shop_id", "shop_name", "shop_type", "area", "number_of_seats",
                                      "number_of_barbers", "opening_time", "closing_time", "rating")},
        "kpis": {**(kpis or {}), "avg_utilization_pct": util},
        "services_revenue": services,
        "repeat_customer_rate_pct": pct(repeat["repeat_clients"], repeat["total_clients"]),
        "appointment_cancellation_rate_pct": pct(appts["cancelled"], appts["total"]),
        "appointment_noshow_rate_pct": pct(appts["no_shows"], appts["total"]),
        "business_recommendations": recs,
        "data_note": "All-time figures from the simulated 91-day history.",
    }
