"""Test configuration: isolated temp databases so tests never touch local data."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="barberflow-tests-"))
os.environ["BARBERFLOW_DB_PATH"] = str(_TMP / "historical.db")
os.environ["LIVE_DB_PATH"] = str(_TMP / "live.db")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("POSTGRES_URL", None)
os.environ.pop("VERCEL", None)
# Optional: run the same suite against PostgreSQL (e.g. a throwaway local server).
# The live_* tables in that database are dropped first, so never point this at production.
TEST_PG_URL = os.getenv("BARBERFLOW_TEST_DATABASE_URL")
if TEST_PG_URL:
    import psycopg
    with psycopg.connect(TEST_PG_URL, autocommit=True) as _c:
        for _t in ("live_queue_entries", "live_bookings", "live_write_events"):
            _c.execute(f"DROP TABLE IF EXISTS {_t}")
    os.environ["DATABASE_URL"] = TEST_PG_URL
EXPECTED_LIVE_MODE = "postgres" if TEST_PG_URL else "sqlite"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def root():
    return ROOT
