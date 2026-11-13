"""BarberFlow API entry point.

Run locally from the repository root:
    python -m uvicorn backend.app.main:app --reload --port 8000
On Vercel the same `app` is served by api/index.py.
"""
import logging
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, database, live_store, ml
from .routes import analytics, appointments, predictions, queue, shops

logger = logging.getLogger("barberflow")
APP_VERSION = "2.0.0"

app = FastAPI(
    title="BarberFlow API",
    description="Discovery, virtual queue, bookings, analytics and ML predictions for a simulated "
                "barber-shop market.",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

# Production: the React app and the API share one origin on Vercel, so CORS is only needed for
# local development (Vite on :5173). No credentials are used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(live_store.LiveStoreUnavailable)
async def live_store_unavailable(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(live_store.RateLimited)
async def rate_limited(_, exc):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled(_, exc):
    # Log the details server-side; never leak internals (SQL, paths) to clients.
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(shops.router)
app.include_router(queue.router)
app.include_router(appointments.router)
app.include_router(analytics.router)
app.include_router(predictions.router)


@app.get("/api", tags=["Meta"])
@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Welcome to the BarberFlow API", "version": APP_VERSION,
            "docs_url": "/api/docs", "health_check": "/api/health"}


@app.get("/health", tags=["Meta"])
@app.get("/api/health", tags=["Meta"])
def health_check():
    """Liveness + dependency check: historical DB, live store and model files."""
    started = time.perf_counter()
    db = {"ok": False}
    try:
        counts = database.table_counts()
        db = {"ok": all(counts.values()), "tables": counts,
              "cold_build_seconds": database.last_build_seconds}
    except Exception as exc:  # report, don't crash the health endpoint
        logger.exception("DB health failed", exc_info=exc)
        db = {"ok": False, "error": "historical database unavailable"}
    live = {"mode": live_store.mode(), "ok": None}
    store = live_store.get_store()
    if store is not None:
        try:
            live["ok"] = store.ping()
        except Exception as exc:
            logger.exception("Live store health failed", exc_info=exc)
            live["ok"] = False
    models = ml.models_status()
    healthy = db["ok"] and all(models.values()) and live["ok"] is not False
    body = {"status": "healthy" if healthy else "degraded", "version": APP_VERSION,
            "database": db, "live_store": live, "models": models,
            "response_ms": round((time.perf_counter() - started) * 1000, 1)}
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@app.get("/api/meta", tags=["Meta"])
def meta():
    """Facts the UI needs to label data honestly."""
    span = database.query_one("SELECT MIN(date) AS start, MAX(date) AS end FROM visits")
    card = ml.model_card()
    return {
        "version": APP_VERSION,
        "dataset": {"type": "simulated", "start_date": span["start"], "end_date": span["end"],
                    "generator": "scripts/generate_data.py"},
        "live_store": live_store.mode(),
        "live_queue_enabled": live_store.get_store() is not None,
        "models": {k: {"status": v.get("status"), "algorithm": v.get("algorithm")}
                   for k, v in card.get("models", {}).items()},
    }


@app.get("/api/explorer/{table_name}", tags=["Explorer"])
def explore_table(table_name: str, limit: int = Query(25, ge=1, le=100),
                  offset: int = Query(0, ge=0, le=100_000)):
    """Read-only schema + sample rows. The table name is checked against a whitelist before it
    is interpolated, so it cannot be used for SQL injection."""
    if table_name not in database.TABLE_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid table. Choose one of {database.TABLE_NAMES}")
    cols = database.query(f"PRAGMA table_info({table_name})")
    fks = database.query(f"PRAGMA foreign_key_list({table_name})")
    return {
        "table": table_name,
        "columns": [{"name": c["name"], "type": c["type"], "not_null": bool(c["notnull"]),
                     "primary_key": bool(c["pk"])} for c in cols],
        "foreign_keys": [{"column": f["from"], "references": f"{f['table']}.{f['to']}",
                          "on_delete": f["on_delete"]} for f in fks],
        "rows": database.query(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset)),
        "total_rows": database.scalar(f"SELECT COUNT(*) FROM {table_name}"),
        "limit": limit, "offset": offset,
    }
