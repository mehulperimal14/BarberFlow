"""Writable store for live operations: virtual-queue entries and new appointment bookings.

Why separate from the historical DB?
  * The 91-day simulated dataset is the analytical source of truth and must stay immutable.
  * Serverless hosts (Vercel) have a read-only deployment filesystem, so live writes need a
    real database. In production that is PostgreSQL (``DATABASE_URL``, e.g. Neon); in local
    development a SQLite file is used. Without either, live features are disabled (HTTP 503)
    rather than silently writing to a temporary filesystem.

The SQL below is deliberately portable between SQLite and PostgreSQL.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import config

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS live_queue_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    {common_queue}
);
CREATE TABLE IF NOT EXISTS live_bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    {common_booking}
);
CREATE TABLE IF NOT EXISTS live_write_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
_POSTGRES_DDL = """
CREATE TABLE IF NOT EXISTS live_queue_entries (
    entry_id BIGSERIAL PRIMARY KEY,
    {common_queue}
);
CREATE TABLE IF NOT EXISTS live_bookings (
    booking_id BIGSERIAL PRIMARY KEY,
    {common_booking}
);
CREATE TABLE IF NOT EXISTS live_write_events (
    event_id BIGSERIAL PRIMARY KEY,
    client_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
_COMMON_QUEUE = """
    shop_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    service_duration_minutes INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Waiting', 'In Service', 'Completed', 'Skipped')),
    source TEXT NOT NULL CHECK (source IN ('customer_app', 'barber_walkin')),
    joined_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    estimated_wait_minutes INTEGER,
    client_hash TEXT NOT NULL"""
_COMMON_BOOKING = """
    shop_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Scheduled', 'Cancelled')),
    created_at TEXT NOT NULL,
    client_hash TEXT NOT NULL"""
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_lq_shop_status ON live_queue_entries (shop_id, status, joined_at)",
    "CREATE INDEX IF NOT EXISTS idx_lb_shop_slot ON live_bookings (shop_id, appointment_date, appointment_time)",
    # A customer cannot hold two scheduled bookings for the same shop and slot.
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_lb_customer_slot ON live_bookings "
    "(shop_id, customer_id, appointment_date, appointment_time) WHERE status = 'Scheduled'",
    "CREATE INDEX IF NOT EXISTS idx_lwe_client ON live_write_events (client_hash, created_at)",
]


class LiveStoreUnavailable(RuntimeError):
    pass


class RateLimited(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def client_fingerprint(ip: str | None) -> str:
    """Salted hash of the caller's IP -- used only for rate limiting, never stored raw."""
    return hashlib.sha256(f"{config.RATE_LIMIT_SALT}:{ip or 'unknown'}".encode()).hexdigest()[:32]


class LiveStore:
    def __init__(self, backend: str, target: str):
        self.backend = backend          # "sqlite" | "postgres"
        self._target = target
        self._lock = threading.Lock()   # serialises SQLite writers inside one process
        self._schema_ready = False

    # ---------------------------------------------------------------- connections
    def _connect(self):
        if self.backend == "sqlite":
            conn = sqlite3.connect(self._target, timeout=10)
            conn.row_factory = sqlite3.Row
            return conn
        import psycopg  # imported lazily so local SQLite mode does not need the driver
        from psycopg.rows import dict_row
        # prepare_threshold=None keeps it compatible with PgBouncer/Neon pooled endpoints.
        return psycopg.connect(self._target, row_factory=dict_row, prepare_threshold=None,
                               connect_timeout=10)

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.backend == "postgres" else sql

    def ensure_schema(self):
        if self._schema_ready:
            return
        ddl = (_SQLITE_DDL if self.backend == "sqlite" else _POSTGRES_DDL).format(
            common_queue=_COMMON_QUEUE, common_booking=_COMMON_BOOKING)
        statements = [s.strip() for s in ddl.split(";") if s.strip()] + _INDEXES
        conn = self._connect()
        try:
            cur = conn.cursor()
            for stmt in statements:
                cur.execute(stmt)
            conn.commit()
        finally:
            conn.close()
        self._schema_ready = True

    @contextmanager
    def transaction(self, lock_key: int | None = None):
        """Yield a cursor-like executor inside one transaction.

        ``lock_key`` serialises concurrent writers for the same shop: a PostgreSQL advisory
        transaction lock, or BEGIN IMMEDIATE + a process lock for SQLite.
        """
        self.ensure_schema()
        conn = self._connect()
        held = False
        try:
            if self.backend == "sqlite":
                self._lock.acquire()
                held = True
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE")
            elif lock_key is not None:
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (int(lock_key),))
            yield _Executor(self, conn)
            conn.commit() if self.backend == "postgres" else conn.execute("COMMIT")
        except Exception:
            try:
                conn.rollback() if self.backend == "postgres" else conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()
            if held:
                self._lock.release()

    def read(self, sql: str, params=()) -> list[dict]:
        self.ensure_schema()
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(self._sql(sql), tuple(params))
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def ping(self) -> bool:
        self.read("SELECT 1 AS ok")
        return True


class _Executor:
    def __init__(self, store: LiveStore, conn):
        self._store, self._conn = store, conn

    def all(self, sql, params=()) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(self._store._sql(sql), tuple(params))
        return [dict(r) for r in cur.fetchall()]

    def one(self, sql, params=()) -> dict | None:
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def check_rate_limit(self, client_hash: str):
        """Shared, database-backed limit (works across serverless instances)."""
        window_start = iso(utcnow() - timedelta(minutes=config.WRITE_RATE_WINDOW_MINUTES))
        recent = self.scalar(
            "SELECT COUNT(*) AS n FROM live_write_events WHERE client_hash = ? AND created_at >= ?",
            (client_hash, window_start))
        if recent >= config.WRITE_RATE_LIMIT:
            raise RateLimited(
                f"Too many changes from this device. Limit is {config.WRITE_RATE_LIMIT} "
                f"per {config.WRITE_RATE_WINDOW_MINUTES} minutes.")
        self.all("INSERT INTO live_write_events (client_hash, created_at) VALUES (?, ?) RETURNING event_id",
                 (client_hash, iso(utcnow())))
        self.all("DELETE FROM live_write_events WHERE created_at < ? RETURNING event_id",
                 (iso(utcnow() - timedelta(days=1)),))


_store: LiveStore | None = None
_store_init_lock = threading.Lock()


def get_store() -> LiveStore | None:
    """Return the configured live store, or None when running as a read-only demo."""
    global _store
    if config.LIVE_STORE_DISABLED:
        return None
    if _store is not None:
        return _store
    with _store_init_lock:
        if _store is None:
            if config.DATABASE_URL:
                _store = LiveStore("postgres", config.DATABASE_URL)
            elif not config.IS_SERVERLESS:
                config.LIVE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                _store = LiveStore("sqlite", str(config.LIVE_DB_PATH))
    return _store


def require_store() -> LiveStore:
    store = get_store()
    if store is None:
        raise LiveStoreUnavailable(
            "Live queue and booking are disabled on this deployment because no persistent "
            "database is configured (set DATABASE_URL). Analytics and predictions still work.")
    return store


def mode() -> str:
    store = get_store()
    return store.backend if store else "disabled"
