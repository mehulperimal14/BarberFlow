"""Train, evaluate and export the three BarberFlow models.

Run from anywhere:  python scripts/train_models.py

Outputs (committed, ~MBs, no pickle):
    backend/app/ml_models/demand_model.json
    backend/app/ml_models/waiting_time_model.json
    backend/app/ml_models/no_show_model.json
    backend/app/ml_models/model_card.json     <- the ONLY source of metrics shown in the API/UI

Fixes compared with the original notebooks:
  * Demand: `historical_average_demand` is computed from TRAINING dates only (the old version
    averaged over all dates, leaking test targets). `month` is dropped (the test window is a
    single month and production dates fall outside the training range). `is_open` is added
    (hours outside opening times are structural zeros). The model is chosen on a validation
    window, not assumed.
  * Waiting time: evaluated with a time-based split (last 20% of dates) instead of a random one.
  * No-show: demographic features removed; unweighted logistic regression so probabilities are
    on the real base-rate scale; risk tiers defined relative to the base rate. The label in the
    simulator is random, so the card marks this model as experimental.
  * Metrics are measured here and written to model_card.json -- nothing is hard-coded.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (balanced_accuracy_score, mean_absolute_error, mean_squared_error,
                             r2_score, roc_auc_score)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "backend" / "app" / "ml_models"
SEED = 42

DEMAND_FEATURES = ["hour", "day_of_week", "weekend_flag", "is_open", "rating",
                   "number_of_seats", "number_of_barbers", "historical_average_demand"]
WAIT_FEATURES = ["queue_length", "occupied_seats", "available_seats", "number_of_barbers",
                 "number_of_seats", "hour", "day_of_week"]
NOSHOW_FEATURES = ["hour", "booking_lag_days", "customer_rating"]


# ----------------------------------------------------------------------------- export helpers
def export_forest(model: RandomForestRegressor, features: list[str]) -> dict:
    trees = []
    for est in model.estimators_:
        t = est.tree_
        trees.append({
            "left": t.children_left.tolist(),
            "right": t.children_right.tolist(),
            "feature": t.feature.tolist(),
            "threshold": [float(x) for x in t.threshold],          # full precision
            "value": [round(float(v), 6) for v in t.value[:, 0, 0]],
        })
    return {"type": "random_forest_regressor", "features": features, "trees": trees}


def export_linear(model: LinearRegression, features: list[str]) -> dict:
    return {"type": "linear_regression", "features": features,
            "coef": [float(c) for c in model.coef_], "intercept": float(model.intercept_)}


def export_logistic(model: LogisticRegression, mean, scale, features: list[str]) -> dict:
    return {"type": "logistic_regression", "features": features,
            "mean": [float(m) for m in mean], "scale": [float(s) for s in scale],
            "coef": [float(c) for c in model.coef_[0]], "intercept": float(model.intercept_[0])}


def reg_metrics(y, p) -> dict:
    return {"mae": round(float(mean_absolute_error(y, p)), 3),
            "rmse": round(float(math.sqrt(mean_squared_error(y, p))), 3),
            "r2": round(float(r2_score(y, p)), 3)}


def date_split(dates: pd.Series, frac: float):
    unique = sorted(dates.unique())
    cut = unique[int(len(unique) * frac)]
    return dates < cut, dates >= cut, pd.Timestamp(cut).date().isoformat(), len(unique)


# ----------------------------------------------------------------------------- data
def load():
    shops = pd.read_csv(DATA / "shops.csv")
    visits = pd.read_csv(DATA / "visits.csv")
    availability = pd.read_csv(DATA / "availability.csv")
    appointments = pd.read_csv(DATA / "appointments.csv")
    customers = pd.read_csv(DATA / "customers.csv")
    shops["open_hour"] = shops["opening_time"].str[:2].astype(int)
    shops["close_hour"] = shops["closing_time"].str[:2].astype(int)
    return shops, visits, availability, appointments, customers


def hist_average(frame: pd.DataFrame) -> pd.DataFrame:
    return (frame.groupby(["shop_id", "hour", "day_of_week"])["customer_count"]
            .mean().reset_index(name="historical_average_demand"))


# ----------------------------------------------------------------------------- demand
def train_demand(shops, visits):
    visits = visits.copy()
    visits["hour"] = visits["arrival_time"].str[:2].astype(int)
    counts = visits.groupby(["shop_id", "date", "hour"]).size().reset_index(name="customer_count")
    grid = pd.MultiIndex.from_product(
        [shops["shop_id"], sorted(visits["date"].unique()), np.arange(8, 21)],
        names=["shop_id", "date", "hour"]).to_frame(index=False)
    d = grid.merge(counts, on=["shop_id", "date", "hour"], how="left").fillna({"customer_count": 0})
    d = d.merge(shops[["shop_id", "rating", "number_of_seats", "number_of_barbers",
                       "open_hour", "close_hour"]], on="shop_id")
    d["date"] = pd.to_datetime(d["date"])
    d["day_of_week"] = d["date"].dt.dayofweek                       # 0 = Monday
    d["weekend_flag"] = (d["day_of_week"] >= 4).astype(int)        # Fri, Sat, Sun (as simulated)
    d["is_open"] = ((d["hour"] >= d["open_hour"]) & (d["hour"] < d["close_hour"])).astype(int)

    train_mask, test_mask, split_date, n_dates = date_split(d["date"], 0.8)
    train, test = d[train_mask].copy(), d[test_mask].copy()
    # validation window = last 20% of the training dates (for model selection only)
    sub_mask, val_mask, val_date, _ = date_split(train["date"], 0.8)
    sub, val = train[sub_mask].copy(), train[val_mask].copy()

    def with_hist(target, source):
        return target.merge(hist_average(source), on=["shop_id", "hour", "day_of_week"], how="left") \
                     .fillna({"historical_average_demand": 0.0})

    sub_f, val_f = with_hist(sub, sub), with_hist(val, sub)
    candidates = {
        "linear_regression": lambda: LinearRegression(),
        "random_forest": lambda: RandomForestRegressor(n_estimators=100, max_depth=10,
                                                       random_state=SEED, n_jobs=-1),
    }
    selection = {"baseline_historical_average": reg_metrics(val_f["customer_count"],
                                                            val_f["historical_average_demand"])}
    for name, make in candidates.items():
        m = make().fit(sub_f[DEMAND_FEATURES], sub_f["customer_count"])
        selection[name] = reg_metrics(val_f["customer_count"], m.predict(val_f[DEMAND_FEATURES]))
    # Selection rule: lowest validation MAE, but keep the simpler linear model unless the forest
    # improves validation MAE by more than 1% (Occam's razor; smaller, explainable artefact).
    best = min(candidates, key=lambda k: selection[k]["mae"])
    if best == "random_forest" and \
            selection["random_forest"]["mae"] > 0.99 * selection["linear_regression"]["mae"]:
        best = "linear_regression"
    selection["selection_rule"] = "lowest validation MAE; prefer linear unless forest is >1% better"

    train_f, test_f = with_hist(train, train), with_hist(test, train)   # leak-free
    model = candidates[best]().fit(train_f[DEMAND_FEATURES], train_f["customer_count"])
    pred = model.predict(test_f[DEMAND_FEATURES])
    test_metrics = reg_metrics(test_f["customer_count"], pred)
    baseline = reg_metrics(test_f["customer_count"], test_f["historical_average_demand"])
    other = {}
    for name, make in candidates.items():
        if name != best:
            m = make().fit(train_f[DEMAND_FEATURES], train_f["customer_count"])
            other[name] = reg_metrics(test_f["customer_count"], m.predict(test_f[DEMAND_FEATURES]))

    exported = export_forest(model, DEMAND_FEATURES) if best == "random_forest" \
        else export_linear(model, DEMAND_FEATURES)
    # Serving-time lookup: average over ALL history (all of it is in the past at serving time),
    # including zero-demand dates -- identical definition to training, so no train/serve skew.
    full_hist = hist_average(d)
    exported["historical_average_demand"] = {
        f"{int(r.shop_id)}|{int(r.hour)}|{int(r.day_of_week)}": round(float(r.historical_average_demand), 4)
        for r in full_hist.itertuples()}
    if best == "random_forest":
        importances = dict(zip(DEMAND_FEATURES, model.feature_importances_.round(3).tolist()))
    else:
        importances = None

    card = {
        "name": "Hourly customer demand",
        "status": "baseline",
        "algorithm": "Linear Regression" if best == "linear_regression" else "Random Forest Regressor",
        "target": "customers arriving per shop per hour (08:00-20:59)",
        "features": DEMAND_FEATURES,
        "rows": int(len(d)), "train_rows": int(len(train_f)), "test_rows": int(len(test_f)),
        "split": f"time-based: first 80% of {n_dates} dates train, last 20% test (from {split_date}); "
                 f"model chosen on a validation window starting {val_date}",
        "model_selection_validation_mae": selection,
        "test_metrics": test_metrics,
        "test_metrics_other_candidates": other,
        "test_baseline_historical_average": baseline,
        "feature_importances": importances,
        "limitations": [
            "Trained on simulated data (Poisson arrivals); it learns the simulator's weekday and hour multipliers.",
            "Most of the signal is the historical shop/hour/weekday average; the model adds little beyond it.",
            "No seasonality or holidays: the data covers 91 summer days only.",
        ],
    }
    return model, exported, card, test_f, pred


# ----------------------------------------------------------------------------- waiting time
def train_wait(shops, visits, availability):
    v = visits.copy()
    v["hour"] = v["arrival_time"].str[:2].astype(int)
    v["day_of_week"] = pd.to_datetime(v["date"]).dt.dayofweek
    a = availability.copy()
    a["date"] = a["timestamp"].str[:10]
    a["hour"] = a["timestamp"].str[11:13].astype(int)
    a = a.drop_duplicates(subset=["shop_id", "date", "hour"])
    # Queue state at the top of the arrival hour = information available before the visit.
    w = v.merge(a[["shop_id", "date", "hour", "queue_length", "occupied_seats", "available_seats"]],
                on=["shop_id", "date", "hour"], how="left")
    unmatched = int(w["queue_length"].isna().sum())
    w = w.merge(shops[["shop_id", "number_of_barbers", "number_of_seats"]], on="shop_id")
    w["queue_length"] = w["queue_length"].fillna(0)
    w["occupied_seats"] = w["occupied_seats"].fillna(0)
    w["available_seats"] = w["available_seats"].fillna(w["number_of_seats"])

    tr, te, split_date, n_dates = date_split(pd.to_datetime(w["date"]), 0.8)
    X, y = w[WAIT_FEATURES], w["waiting_time_minutes"]
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=SEED, n_jobs=-1)
    model.fit(X[tr], y[tr])
    pred = model.predict(X[te])
    err = np.abs(y[te].to_numpy() - pred)
    card = {
        "name": "Walk-in waiting time",
        "status": "good on simulated data",
        "algorithm": "Random Forest Regressor (100 trees, max_depth 10)",
        "target": "waiting_time_minutes of a visit",
        "features": WAIT_FEATURES,
        "rows": int(len(w)), "train_rows": int(tr.sum()), "test_rows": int(te.sum()),
        "unmatched_snapshot_rows": unmatched,
        "split": f"time-based: first 80% of {n_dates} dates train, last 20% test (from {split_date})",
        "test_metrics": reg_metrics(y[te], pred),
        "test_baseline_train_mean": reg_metrics(y[te], np.full(int(te.sum()), y[tr].mean())),
        "test_error_profile": {
            "median_absolute_error": round(float(np.median(err)), 2),
            "share_within_5_minutes": round(float((err <= 5).mean()), 3),
            "mae_when_actual_wait_over_30": round(float(err[y[te].to_numpy() > 30].mean()), 2),
        },
        "feature_importances": dict(zip(WAIT_FEATURES, model.feature_importances_.round(3).tolist())),
        "limitations": [
            "Features describe the queue at the top of the hour, so they can be up to 59 minutes stale.",
            "Errors are large for very long waits (heavy-tailed target); treat long estimates as ranges.",
            "In the live demo the queue counts come from the live store, not from a sensor.",
        ],
    }
    return model, export_forest(model, WAIT_FEATURES), card, X[te], pred


# ----------------------------------------------------------------------------- no-show
def train_noshow(appointments, customers):
    a = appointments.merge(customers[["customer_id", "customer_rating"]], on="customer_id")
    a["hour"] = a["appointment_time"].str[:2].astype(int)
    a["booking_lag_days"] = (pd.to_datetime(a["appointment_date"] + " " + a["appointment_time"])
                             - pd.to_datetime(a["booking_time"])).dt.total_seconds() / 86400
    X, y = a[NOSHOW_FEATURES], a["no_show_flag"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    mean, scale = Xtr.mean().to_numpy(), Xtr.std(ddof=0).to_numpy()
    model = LogisticRegression(max_iter=1000).fit((Xtr - mean) / scale, ytr)
    p = model.predict_proba((Xte - mean) / scale)[:, 1]
    base = float(ytr.mean())
    low, high = round(base * 0.75, 4), round(base * 1.5, 4)
    # Decision threshold for the balanced-accuracy figure: the training base rate.
    pred = (p >= base).astype(int)
    tiers = pd.Series(pd.cut(p, [-1, low, high, 2], labels=["Low", "Medium", "High"])).value_counts(normalize=True)
    without_hour = LogisticRegression(max_iter=1000).fit(
        ((Xtr - mean) / scale).drop(columns=["hour"]), ytr)
    auc_without_hour = roc_auc_score(yte, without_hour.predict_proba(
        ((Xte - mean) / scale).drop(columns=["hour"]))[:, 1])
    card = {
        "name": "Appointment no-show risk",
        "status": "experimental - not for business decisions",
        "algorithm": "Logistic Regression (standardised features, unweighted)",
        "target": "no_show_flag",
        "features": NOSHOW_FEATURES,
        "rows": int(len(a)), "train_rows": int(len(Xtr)), "test_rows": int(len(Xte)),
        "split": "stratified random 80/20",
        "base_rate": round(base, 4),
        "risk_tier_thresholds": {"low_below": low, "high_at_or_above": high},
        "test_metrics": {
            "roc_auc": round(float(roc_auc_score(yte, p)), 3),
            "balanced_accuracy_at_base_rate_threshold": round(float(balanced_accuracy_score(yte, pred)), 3),
            "roc_auc_without_hour_feature": round(float(auc_without_hour), 3),
        },
        "test_tier_distribution": {k: round(float(v), 3) for k, v in tiers.items()},
        "limitations": [
            "In the simulator the no-show label is assigned at random; the only learnable signal is that "
            "missed bookings were given uniformly random hours while completed ones follow peak hours.",
            "Without the hour feature the model is no better than chance (see roc_auc_without_hour_feature).",
            "Do not use it to charge deposits or penalise customers.",
        ],
    }
    return model, export_logistic(model, mean, scale, NOSHOW_FEATURES), card, Xte, p


def main():
    shops, visits, availability, appointments, customers = load()
    OUT.mkdir(parents=True, exist_ok=True)

    print("Training demand model ...")
    dm, d_exp, d_card, d_test, d_pred = train_demand(shops, visits)
    print("Training waiting-time model ...")
    wm, w_exp, w_card, w_test, w_pred = train_wait(shops, visits, availability)
    print("Training no-show model ...")
    nm, n_exp, n_card, n_test, n_prob = train_noshow(appointments, customers)

    # Verify that the exported JSON reproduces scikit-learn exactly before writing anything.
    sys.path.insert(0, str(ROOT))
    from backend.app.ml import load_model_from_dict
    checks = {}
    for name, exp, X, ref in [("demand", d_exp, d_test[DEMAND_FEATURES], d_pred),
                              ("waiting_time", w_exp, w_test, w_pred)]:
        m = load_model_from_dict(exp)
        sample = X.to_numpy()[:3000]
        diff = max(abs(m.predict(list(row)) - r) for row, r in zip(sample, ref[:3000]))
        checks[name] = diff
    ns = load_model_from_dict(n_exp)
    checks["no_show"] = max(abs(ns.predict_proba(list(row)) - r)
                            for row, r in zip(n_test.to_numpy()[:3000], n_prob[:3000]))
    print("Max |exported - sklearn| on 3,000 test rows:", checks)
    assert all(v < 1e-4 for v in checks.values()), "Exported model does not match scikit-learn"

    trained_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for fname, exp in [("demand_model.json", d_exp), ("waiting_time_model.json", w_exp),
                       ("no_show_model.json", n_exp)]:
        (OUT / fname).write_text(json.dumps(exp, separators=(",", ":")), encoding="utf-8")
    card = {
        "trained_at": trained_at,
        "data": "simulated dataset: 50 shops, 5,000 customers, 91 days (2026-06-01 to 2026-08-30)",
        "training_script": "scripts/train_models.py",
        "export_check_max_abs_diff": {k: float(f"{v:.2e}") for k, v in checks.items()},
        "models": {"demand": d_card, "waiting_time": w_card, "no_show": n_card},
    }
    (OUT / "model_card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps({k: v["test_metrics"] for k, v in card["models"].items()}, indent=2))
    print(f"Demand algorithm selected on validation: {d_card['algorithm']}")
    for f in sorted(OUT.glob("*.json")):
        print(f"  {f.name}: {f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
