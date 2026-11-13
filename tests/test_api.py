from datetime import timedelta

from backend.app import config, ml
from backend.app.database import scalar
from backend.app.domain import now_local


def test_health_and_meta(client):
    for path in ("/health", "/api/health"):
        r = client.get(path)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "healthy"
        assert body["database"]["tables"]["visits"] == 64991
        assert all(body["models"].values())
        from tests.conftest import EXPECTED_LIVE_MODE
        assert body["live_store"] == {"mode": EXPECTED_LIVE_MODE, "ok": True}
    meta = client.get("/api/meta").json()
    assert meta["dataset"]["type"] == "simulated" and meta["live_queue_enabled"] is True


def test_shops_list_and_detail_include_services(client):
    shops = client.get("/api/shops").json()
    assert len(shops) == 50
    assert {"distance_km", "average_price", "typical_wait_minutes", "estimated_wait_minutes"} <= shops[0].keys()
    detail = client.get("/api/shops/1").json()
    assert len(detail["services"]) == 7      # the old UI never loaded these, so booking was impossible
    assert client.get("/api/shops/9999").status_code == 404
    assert client.get("/api/shops?min_rating=9").status_code == 422


def test_recommendations_ranked(client):
    recs = client.get("/api/shops/recommendations?weight_rating=1&weight_wait=0"
                      "&weight_distance=0&weight_price=0").json()
    scores = [r["recommendation_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert recs[0]["rating"] == max(r["rating"] for r in recs)


def test_overview_filters(client):
    all_ = client.get("/api/analytics/overview").json()
    assert all_["total_shops"] == 50 and all_["total_visits"] == 64991
    assert all_["average_wait_minutes"] == 19.0 and all_["median_wait_minutes"] == 0
    assert round(all_["appointment_noshow_rate_pct"], 2) == 7.11
    shop = client.get("/api/analytics/overview?shop_id=1")          # used to return HTTP 500
    assert shop.status_code == 200 and shop.json()["total_visits"] == 1365
    area = client.get("/api/analytics/overview?area=Downtown").json()
    assert area["total_shops"] == 9 and area["total_visits"] == 11497


def test_shop_performance_has_no_fan_out(client):
    body = client.get("/api/analytics/shop-performance").json()
    perf = {s["shop_id"]: s for s in body["shops_data"]}
    assert perf[1]["total_visits"] == 1365                           # was 1,739,010
    assert sum(s["total_visits"] for s in perf.values()) == 64991
    assert body["quadrant_counts"] == {"Bottleneck": 22, "Underutilized": 14, "Low Scale": 9, "Leader": 5}
    visits = [s["total_visits"] for s in body["shops_data"]]
    assert visits == sorted(visits, reverse=True)


def test_location_has_no_fan_out(client):
    body = client.get("/api/analytics/location").json()
    areas = {a["area"]: a for a in body["areas"]}
    assert sum(a["total_seats"] for a in areas.values()) == scalar("SELECT SUM(number_of_seats) FROM shops")
    assert sum(a["total_visits"] for a in areas.values()) == 64991
    assert areas["Eastside"]["visits_per_seat"] == 357.7
    assert areas["Eastside"]["status"].startswith("High Opportunity")
    assert areas["Northside"]["status"] == "Over-saturated"


def test_charts_and_shop_analytics(client):
    demand = client.get("/api/analytics/demand?area=Eastside").json()
    assert len(demand["demand_by_day"]) == 7
    wait = client.get("/api/analytics/waiting-time?shop_id=1").json()
    assert sum(t["count"] for t in wait["wait_distribution"]) == 1365
    shop = client.get("/api/analytics/shop/1").json()
    assert shop["kpis"]["total_visits"] == 1365 and len(shop["business_recommendations"]) == 3
    assert client.get("/api/analytics/shop/999").status_code == 404


def test_queue_lifecycle(client):
    shop = 1  # 1 barber
    assert client.post(f"/api/queue/{shop}/join", json={"customer_id": 10, "service_id": 999}).status_code == 404
    assert client.post(f"/api/queue/{shop}/join", json={"customer_id": 999999, "service_id": 1}).status_code == 404
    a = client.post(f"/api/queue/{shop}/join", json={"customer_id": 10, "service_id": 1})
    assert a.status_code == 201, a.text
    assert client.post(f"/api/queue/{shop}/join", json={"customer_id": 10, "service_id": 2}).status_code == 409
    b = client.post(f"/api/queue/{shop}/join",
                    json={"customer_id": 11, "service_id": 2, "source": "barber_walkin"})
    assert b.status_code == 201 and b.json()["position"] == 2
    q = client.get(f"/api/queue/{shop}").json()
    assert [e["customer_id"] for e in q["waiting"]] == [10, 11]
    assert q["waiting"][0]["service_name"] is not None
    ea, eb = a.json()["entry_id"], b.json()["entry_id"]
    assert client.patch(f"/api/queue/entries/{ea}", json={"action": "complete"}).status_code == 409
    assert client.patch(f"/api/queue/entries/{ea}", json={"action": "start"}).json()["new_status"] == "In Service"
    assert client.patch(f"/api/queue/entries/{eb}", json={"action": "start"}).status_code == 409  # barber busy
    assert client.patch(f"/api/queue/entries/{ea}", json={"action": "complete"}).json()["new_status"] == "Completed"
    assert client.patch(f"/api/queue/entries/{eb}", json={"action": "skip"}).json()["new_status"] == "Skipped"
    assert client.patch(f"/api/queue/entries/{eb}", json={"action": "fly"}).status_code == 422
    assert client.patch("/api/queue/entries/987654", json={"action": "start"}).status_code == 404
    q = client.get(f"/api/queue/{shop}").json()
    assert q["waiting"] == [] and q["in_service"] == [] and len(q["recent"]) == 2
    hist = client.get(f"/api/queue/{shop}/history").json()
    assert hist["date"] == "2026-08-30" and "status" not in hist["visits"][0]


def test_booking_validation(client):
    tomorrow = (now_local().date() + timedelta(days=1)).isoformat()
    base = {"customer_id": 20, "shop_id": 1, "service_id": 1, "appointment_date": tomorrow,
            "appointment_time": "14:00"}
    assert client.post("/api/appointments", json={**base, "appointment_date": "2020-01-01"}).status_code == 422
    assert client.post("/api/appointments", json={**base, "appointment_date": "not-a-date"}).status_code == 422
    assert client.post("/api/appointments", json={**base, "appointment_time": "25:00"}).status_code == 422
    assert client.post("/api/appointments", json={**base, "appointment_time": "06:00"}).status_code == 422
    ok = client.post("/api/appointments", json=base)
    assert ok.status_code == 201, ok.text
    assert client.post("/api/appointments", json=base).status_code == 409                   # same customer
    assert client.post("/api/appointments", json={**base, "customer_id": 21}).status_code == 409  # 1 barber
    listed = client.get("/api/bookings?shop_id=1").json()
    assert listed["bookings"][0]["booking_id"] == ok.json()["booking_id"]
    assert len(client.get("/api/appointments?shop_id=1&limit=5").json()) == 5


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(config, "WRITE_RATE_LIMIT", 0)
    r = client.post("/api/queue/2/join", json={"customer_id": 30, "service_id": 8})
    assert r.status_code == 429


def test_live_store_disabled_mode(client, monkeypatch):
    monkeypatch.setattr(config, "LIVE_STORE_DISABLED", True)
    assert client.post("/api/queue/2/join", json={"customer_id": 30, "service_id": 8}).status_code == 503
    assert client.get("/api/queue/2").json()["live_queue_enabled"] is False
    assert client.get("/api/shops").json()[0]["estimated_wait_minutes"] is None
    assert client.get("/api/analytics/overview").status_code == 200


def test_predictions_and_metrics_come_from_model_card(client):
    card = ml.model_card()["models"]
    d = client.post("/api/predictions/demand", json={"shop_id": 1, "hour": 17, "day_of_week": 5})
    assert d.status_code == 200 and d.json()["model"]["test_metrics"] == card["demand"]["test_metrics"]
    assert client.post("/api/predictions/demand",
                       json={"shop_id": 1, "hour": 3, "day_of_week": 5}).status_code == 422
    w = client.post("/api/predictions/waiting-time",
                    json={"shop_id": 1, "queue_length": 5, "occupied_seats": 1, "hour": 17, "day_of_week": 5})
    assert w.status_code == 200 and w.json()["predicted_waiting_time_minutes"] > 0
    assert w.json()["model"]["test_metrics"] == card["waiting_time"]["test_metrics"]
    assert client.post("/api/predictions/waiting-time",
                       json={"shop_id": 1, "queue_length": 5, "occupied_seats": 9, "hour": 17,
                             "day_of_week": 5}).status_code == 422
    assert client.post("/api/predictions/waiting-time",
                       json={"shop_id": 1, "queue_length": 5, "occupied_seats": 1, "available_seats": 5,
                             "hour": 17, "day_of_week": 5}).status_code == 422
    n = client.post("/api/predictions/no-show", json={"customer_id": 120, "hour": 9, "booking_lag_days": 3})
    assert n.status_code == 200 and n.json()["risk_tier"] in {"Low", "Medium", "High"}
    assert "experimental" in n.json()["model"]["status"]
    assert client.post("/api/predictions/no-show",
                       json={"customer_id": 0, "hour": 9, "booking_lag_days": 3}).status_code == 422


def test_explorer_whitelist(client):
    body = client.get("/api/explorer/visits?limit=5").json()
    assert body["total_rows"] == 64991 and len(body["rows"]) == 5
    assert {"column": "shop_id", "references": "shops.shop_id", "on_delete": "CASCADE"} in body["foreign_keys"]
    assert client.get("/api/explorer/sqlite_master").status_code == 400
