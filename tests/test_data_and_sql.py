import csv
import re
import sqlite3

from backend.app import database


def _csv_rows(root, name):
    with open(root / "data" / "processed" / name, newline="", encoding="utf-8") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def test_processed_csvs_exist_and_match_db_counts(root):
    counts = database.table_counts()
    for table, csv_file in database.TABLES:
        assert counts[table] == _csv_rows(root, csv_file) > 0, table


def test_shop_integrity():
    bad = database.scalar("""SELECT COUNT(*) FROM shops WHERE rating < 1 OR rating > 5
                             OR number_of_seats < 2 OR number_of_barbers > number_of_seats""")
    assert bad == 0


def test_no_foreign_key_violations():
    conn = sqlite3.connect(database.ensure_database())
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_all_twenty_analysis_queries_run(root):
    sql = (root / "sql" / "analysis_queries.sql").read_text(encoding="utf-8")
    ran = 0
    for block in re.split(r"\n(?=-- \d+\. )", sql):
        if not re.match(r"-- \d+\. ", block.strip()):
            continue
        lines = [ln for ln in block.splitlines() if not ln.strip().startswith("--")]
        database.query("\n".join(lines).strip().rstrip(";"))  # raises on any SQL error
        ran += 1
    assert ran == 20


def test_review_matching_is_one_to_one(client):
    body = client.get("/api/analytics/satisfaction").json()
    assert 0 < body["matched_reviews"] <= body["total_reviews"]
