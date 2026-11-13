"""ML prediction endpoints. Metrics come only from model_card.json written at training time."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import ml
from ..domain import get_customer_or_404, get_shop_or_404, open_hours, typical_wait

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


class DemandInput(BaseModel):
    shop_id: int = Field(..., ge=1)
    hour: int = Field(..., ge=8, le=20, description="Hour of day, 8-20 (the hours in the training data)")
    day_of_week: int = Field(..., ge=0, le=6, description="0 = Monday ... 6 = Sunday")


class WaitTimeInput(BaseModel):
    shop_id: int = Field(..., ge=1)
    queue_length: int = Field(..., ge=0, le=100)
    occupied_seats: int = Field(..., ge=0, le=50)
    available_seats: int | None = Field(None, ge=0, le=50,
                                        description="Optional; must equal seats - occupied_seats")
    hour: int = Field(..., ge=8, le=20)
    day_of_week: int = Field(..., ge=0, le=6)


class NoShowInput(BaseModel):
    customer_id: int = Field(..., ge=1)
    hour: int = Field(..., ge=8, le=20)
    booking_lag_days: float = Field(..., ge=0, le=60)


def _card(name: str) -> dict:
    card = ml.model_card().get("models", {}).get(name, {})
    keep = ("name", "status", "algorithm", "split", "test_metrics", "limitations")
    return {k: card[k] for k in keep if k in card} | {"trained_at": ml.model_card().get("trained_at")}


def _model(name: str):
    model = ml.get_model(name)
    if model is None:
        raise HTTPException(status_code=503,
                            detail=f"The {name} model is not available. Run: python scripts/train_models.py")
    return model


@router.get("/model-card")
def get_model_card():
    card = ml.model_card()
    if not card:
        raise HTTPException(status_code=503, detail="model_card.json not found")
    return card


@router.post("/demand")
def predict_demand(data: DemandInput):
    model = _model("demand")
    shop = get_shop_or_404(data.shop_id)
    o, c = open_hours(shop)
    hist = model.extra.get("historical_average_demand", {}).get(
        f"{data.shop_id}|{data.hour}|{data.day_of_week}", 0.0)
    features = {
        "hour": data.hour, "day_of_week": data.day_of_week,
        "weekend_flag": int(data.day_of_week >= 4),          # Fri-Sun, as in the simulation
        "is_open": int(o <= data.hour < c), "rating": shop["rating"],
        "number_of_seats": shop["number_of_seats"], "number_of_barbers": shop["number_of_barbers"],
        "historical_average_demand": hist,
    }
    pred = max(0.0, model.predict([features[f] for f in model.features]))
    return {"predicted_customers": round(pred, 2), "predicted_customers_rounded": int(round(pred)),
            "shop_open_at_this_hour": bool(features["is_open"]), "features": features,
            "model": _card("demand")}


@router.post("/waiting-time")
def predict_waiting_time(data: WaitTimeInput):
    model = _model("waiting_time")
    shop = get_shop_or_404(data.shop_id)
    seats = shop["number_of_seats"]
    if data.occupied_seats > seats:
        raise HTTPException(status_code=422, detail=f"occupied_seats cannot exceed the shop's {seats} seats")
    available = seats - data.occupied_seats
    if data.available_seats is not None and data.available_seats != available:
        raise HTTPException(status_code=422,
                            detail=f"available_seats must equal seats ({seats}) - occupied_seats ({data.occupied_seats})")
    features = {"queue_length": data.queue_length, "occupied_seats": data.occupied_seats,
                "available_seats": available, "number_of_barbers": shop["number_of_barbers"],
                "number_of_seats": seats, "hour": data.hour, "day_of_week": data.day_of_week}
    pred = max(0.0, model.predict([features[f] for f in model.features]))
    return {"predicted_waiting_time_minutes": int(round(pred)), "features": features,
            "historical_typical_wait_minutes": typical_wait(data.shop_id, data.hour, data.day_of_week),
            "model": _card("waiting_time")}


@router.post("/no-show")
def predict_no_show(data: NoShowInput):
    model = _model("no_show")
    cust = get_customer_or_404(data.customer_id)
    features = {"hour": data.hour, "booking_lag_days": data.booking_lag_days,
                "customer_rating": cust["customer_rating"]}
    prob = model.predict_proba([features[f] for f in model.features])
    card = ml.model_card().get("models", {}).get("no_show", {})
    th = card.get("risk_tier_thresholds", {"low_below": 0.05, "high_at_or_above": 0.10})
    tier = "Low" if prob < th["low_below"] else ("High" if prob >= th["high_at_or_above"] else "Medium")
    return {"no_show_probability": round(prob, 4), "risk_tier": tier,
            "base_rate": card.get("base_rate"), "risk_tier_thresholds": th,
            "features": features, "model": _card("no_show")}
