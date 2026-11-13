"""Dependency-free inference for the exported BarberFlow models.

Models are trained with scikit-learn in ``scripts/train_models.py`` and exported to JSON
(tree arrays / coefficients). Serving them in pure Python keeps the serverless bundle small,
avoids unpickling untrusted files, and is verified against scikit-learn at export time.
"""
from __future__ import annotations

import json
import math
import struct
import threading
from functools import lru_cache

from . import config

MODEL_FILES = {
    "demand": "demand_model.json",
    "waiting_time": "waiting_time_model.json",
    "no_show": "no_show_model.json",
}


def _f32(x: float) -> float:
    """scikit-learn trees compare float32 inputs against float64 thresholds; mirror that."""
    return struct.unpack("f", struct.pack("f", float(x)))[0]


class ForestRegressor:
    def __init__(self, d: dict):
        self.features = d["features"]
        self.trees = [(t["left"], t["right"], t["feature"], t["threshold"], t["value"])
                      for t in d["trees"]]
        self.extra = d

    def predict(self, x: list[float]) -> float:
        xs = [_f32(v) for v in x]
        total = 0.0
        for left, right, feature, threshold, value in self.trees:
            node = 0
            while left[node] != -1:
                node = left[node] if xs[feature[node]] <= threshold[node] else right[node]
            total += value[node]
        return total / len(self.trees)


class LinearRegressor:
    def __init__(self, d: dict):
        self.features, self.coef, self.intercept, self.extra = d["features"], d["coef"], d["intercept"], d

    def predict(self, x: list[float]) -> float:
        return self.intercept + sum(c * float(v) for c, v in zip(self.coef, x))


class LogisticClassifier:
    def __init__(self, d: dict):
        self.features, self.extra = d["features"], d
        self.mean, self.scale, self.coef, self.intercept = d["mean"], d["scale"], d["coef"], d["intercept"]

    def predict_proba(self, x: list[float]) -> float:
        z = self.intercept + sum(c * (float(v) - m) / s
                                 for c, v, m, s in zip(self.coef, x, self.mean, self.scale))
        return 1.0 / (1.0 + math.exp(-z))


def load_model_from_dict(d: dict):
    kind = d["type"]
    if kind == "random_forest_regressor":
        return ForestRegressor(d)
    if kind == "linear_regression":
        return LinearRegressor(d)
    if kind == "logistic_regression":
        return LogisticClassifier(d)
    raise ValueError(f"Unknown model type {kind}")


_load_lock = threading.Lock()


@lru_cache(maxsize=None)
def get_model(name: str):
    with _load_lock:
        path = config.MODELS_DIR / MODEL_FILES[name]
        if not path.exists():
            return None
        return load_model_from_dict(json.loads(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def model_card() -> dict:
    path = config.MODELS_DIR / "model_card.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def models_status() -> dict:
    return {name: (config.MODELS_DIR / f).exists() for name, f in MODEL_FILES.items()}
