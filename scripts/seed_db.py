"""Build the historical SQLite database (backend/app/barberflow.db) from data/processed/*.csv.

Usage (from any directory):  python scripts/seed_db.py [--force]
Uses only the Python standard library. The API also builds the database automatically on first
use if it is missing, so running this script is optional.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import config  # noqa: E402
from backend.app.database import build_database  # noqa: E402


def main():
    target = config.DEFAULT_DB_PATH
    if target.exists() and "--force" not in sys.argv:
        print(f"{target} already exists (use --force to rebuild).")
        return
    started = time.perf_counter()
    counts = build_database(target)
    print(f"Built {target} in {time.perf_counter() - started:.2f}s")
    for table, n in counts.items():
        print(f" - {table}: {n:,} rows")


if __name__ == "__main__":
    main()
