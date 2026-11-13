"""Read-only access to the historical (simulated) BarberFlow dataset stored in SQLite.

The database is built from the committed CSVs in ``data/processed`` using only the standard
library, so it can be (re)created anywhere -- including at cold start on a serverless host,
where it is written to the temp directory and then opened strictly read-only. The historical
dataset is never modified by the API; live writes go to ``live_store.py``.
"""
import csv
import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from . import config

# Insert order respects foreign keys.
TABLES = [
    ("shops", "shops.csv"),
    ("services", "services.csv"),
    ("customers", "customers.csv"),
    ("appointments", "appointments.csv"),
    ("visits", "visits.csv"),
    ("availability", "availability.csv"),
    ("reviews", "reviews.csv"),
]
TABLE_NAMES = [t for t, _ in TABLES]

_build_lock = threading.Lock()
_local = threading.local()
_db_path: Path | None = None
last_build_seconds: float | None = None


def resolve_db_path() -> Path:
    """Where the historical DB lives: env override > repo file > temp dir on read-only hosts."""
    env = os.getenv("BARBERFLOW_DB_PATH")
    if env:
        return Path(env)
    if config.DEFAULT_DB_PATH.exists():
        return config.DEFAULT_DB_PATH
    if not config.IS_SERVERLESS and os.access(config.DEFAULT_DB_PATH.parent, os.W_OK):
        return config.DEFAULT_DB_PATH
    return Path(tempfile.gettempdir()) / "barberflow.db"


def build_database(db_path: Path, data_dir: Path = config.DATA_DIR,
                   schema_path: Path = config.SCHEMA_PATH) -> dict:
    """Create the SQLite database from schema.sql + CSVs. Atomic: written to a temp file first."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(f"{db_path.name}.{os.getpid()}.building")
    if tmp_path.exists():
        tmp_path.unlink()
    counts = {}
    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        for table, csv_file in TABLES:
            with open(data_dir / csv_file, newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                header = next(reader)
                cols = ", ".join(header)
                marks = ", ".join("?" for _ in header)
                # Column type affinity (INTEGER/REAL) converts numeric strings on insert.
                conn.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})", reader)
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.commit()
        conn.execute("ANALYZE")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Foreign key violations while building DB: {violations[:5]}")
    finally:
        conn.close()
    os.replace(tmp_path, db_path)
    return counts


def ensure_database() -> Path:
    """Return the DB path, building it once (thread-safe) if it does not exist yet."""
    global _db_path, last_build_seconds
    if _db_path is not None and _db_path.exists():
        return _db_path
    with _build_lock:
        path = resolve_db_path()
        if not path.exists():
            started = time.perf_counter()
            build_database(path)
            last_build_seconds = round(time.perf_counter() - started, 2)
        _db_path = path
    return path


def get_connection() -> sqlite3.Connection:
    """One read-only connection per thread (sqlite3 connections are not shared across threads)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        path = ensure_database()
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def query(sql: str, params: tuple | list = ()) -> list[dict]:
    """Run a parameterised read-only query and return rows as dicts."""
    return [dict(r) for r in get_connection().execute(sql, tuple(params)).fetchall()]


def query_one(sql: str, params: tuple | list = ()) -> dict | None:
    row = get_connection().execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def scalar(sql: str, params: tuple | list = ()):
    row = get_connection().execute(sql, tuple(params)).fetchone()
    return row[0] if row else None


def table_counts() -> dict:
    return {t: scalar(f"SELECT COUNT(*) FROM {t}") for t in TABLE_NAMES}
