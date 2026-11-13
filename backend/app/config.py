"""Central configuration. Every path is resolved relative to this file, never the working directory."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent            # backend/app
REPO_ROOT = APP_DIR.parent.parent                      # repository root
DATA_DIR = REPO_ROOT / "data" / "processed"
SCHEMA_PATH = REPO_ROOT / "sql" / "schema.sql"
MODELS_DIR = APP_DIR / "ml_models"

# True on Vercel / other serverless hosts where the deployment directory is read-only.
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

# Historical (simulated, read-only) analytics database.
DEFAULT_DB_PATH = APP_DIR / "barberflow.db"

# Live operations store (queue entries + new bookings).
#   DATABASE_URL / POSTGRES_URL set  -> PostgreSQL (production, e.g. Neon)
#   otherwise, local development      -> SQLite file next to the app (LIVE_DB_PATH overrides)
#   otherwise, serverless with no DB  -> disabled (read-only demo); never a temporary filesystem
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""
LIVE_DB_PATH = Path(os.getenv("LIVE_DB_PATH", str(APP_DIR / "live.db")))
LIVE_STORE_DISABLED = os.getenv("LIVE_STORE", "").lower() == "disabled"

# Comma-separated list of allowed browser origins for CORS. The production frontend is served
# from the same origin as the API on Vercel, so this is only needed for local development.
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

# Demo guard-rails for the publicly writable live store.
MAX_ACTIVE_QUEUE_PER_SHOP = int(os.getenv("MAX_ACTIVE_QUEUE_PER_SHOP", "25"))
WRITE_RATE_LIMIT = int(os.getenv("WRITE_RATE_LIMIT", "30"))           # writes per client ...
WRITE_RATE_WINDOW_MINUTES = int(os.getenv("WRITE_RATE_WINDOW_MINUTES", "10"))  # ... per window
LIVE_QUEUE_WINDOW_HOURS = int(os.getenv("LIVE_QUEUE_WINDOW_HOURS", "12"))
BOOKING_HORIZON_DAYS = int(os.getenv("BOOKING_HORIZON_DAYS", "60"))
RATE_LIMIT_SALT = os.getenv("RATE_LIMIT_SALT", "barberflow-demo")

# The simulated city is centred on New York's coordinates; used only for the model's hour feature.
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/New_York")
