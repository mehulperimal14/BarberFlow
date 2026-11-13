import os
import shutil
import sys
from pathlib import Path
import pandas as pd
import sqlite3

def export_powerbi():
    print("Preparing Power BI exports...")
    root = Path(__file__).resolve().parents[1]
    source_dir = root / 'data' / 'processed'
    dest_dir = root / 'powerbi'
    os.makedirs(dest_dir, exist_ok=True)

    # 1. Copy dimension and fact tables
    mapping = {
        "shops.csv": "dim_shops.csv",
        "services.csv": "dim_services.csv",
        "customers.csv": "dim_customers.csv",
        "appointments.csv": "fact_appointments.csv",
        "visits.csv": "fact_visits.csv",
        "reviews.csv": "fact_reviews.csv",
        "availability.csv": "fact_availability.csv",
    }

    for src_file, dest_file in mapping.items():
        src_path = os.path.join(source_dir, src_file)
        dest_path = os.path.join(dest_dir, dest_file)
        if os.path.exists(src_path):
            shutil.copy(src_path, dest_path)
            print(f"Copied {src_file} -> {dest_path}")
        else:
            print(f"Warning: Source {src_path} not found.")

    # 2. Generate analytics_summary.csv
    # Calculate shop-level aggregates directly from the SQLite database
    sys.path.insert(0, str(root))
    from backend.app.database import ensure_database
    db_path = str(ensure_database())
    if os.path.exists(db_path):
        print("Calculating analytics summary from SQLite...")
        conn = sqlite3.connect(db_path)
        
        # Pre-aggregate each fact table per shop BEFORE joining (the old version joined visits x
        # availability directly, inflating visits and revenue ~1,000x).
        query = """
            WITH v AS (SELECT v.shop_id, COUNT(*) AS total_visits, SUM(srv.price) AS total_revenue,
                              AVG(v.waiting_time_minutes) AS avg_wait_minutes
                       FROM visits v JOIN services srv ON srv.service_id = v.service_id
                       GROUP BY v.shop_id),
                 a AS (SELECT shop_id, AVG(occupied_seats * 100.0 / total_seats) AS avg_utilization_pct
                       FROM availability GROUP BY shop_id),
                 r AS (SELECT shop_id, AVG(rating) AS average_review_rating, COUNT(*) AS review_count
                       FROM reviews GROUP BY shop_id)
            SELECT s.shop_id, s.shop_name, s.area, s.shop_type, s.number_of_seats, s.number_of_barbers,
                   COALESCE(v.total_visits, 0) AS total_visits, ROUND(v.total_revenue, 2) AS total_revenue,
                   ROUND(v.avg_wait_minutes, 1) AS avg_wait_minutes,
                   ROUND(a.avg_utilization_pct, 1) AS avg_utilization_pct,
                   s.rating AS listed_rating, ROUND(r.average_review_rating, 2) AS average_review_rating,
                   r.review_count
            FROM shops s
            LEFT JOIN v ON v.shop_id = s.shop_id
            LEFT JOIN a ON a.shop_id = s.shop_id
            LEFT JOIN r ON r.shop_id = s.shop_id
            ORDER BY s.shop_id
        """
        df_summary = pd.read_sql_query(query, conn)
        df_summary.to_csv(os.path.join(dest_dir, 'analytics_summary.csv'), index=False)
        print(f"Created {os.path.join(dest_dir, 'analytics_summary.csv')} with {len(df_summary)} rows.")
        conn.close()
    else:
        print(f"Warning: Database {db_path} not found. Cannot generate summary.")
        
    print("Power BI export directory populated successfully.")

if __name__ == '__main__':
    export_powerbi()
