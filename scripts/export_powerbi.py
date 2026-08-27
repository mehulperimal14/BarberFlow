import os
import shutil
import pandas as pd
import sqlite3

def export_powerbi():
    print("Preparing Power BI exports...")
    source_dir = 'data/processed'
    dest_dir = 'powerbi'
    os.makedirs(dest_dir, exist_ok=True)

    # 1. Copy dimension and fact tables
    mapping = {
        "shops.csv": "dim_shops.csv",
        "services.csv": "dim_services.csv",
        "customers.csv": "dim_customers.csv",
        "appointments.csv": "fact_appointments.csv",
        "visits.csv": "fact_visits.csv",
        "reviews.csv": "fact_reviews.csv"
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
    db_path = 'backend/app/barberflow.db'
    if os.path.exists(db_path):
        print("Calculating analytics summary from SQLite...")
        conn = sqlite3.connect(db_path)
        
        query = """
            SELECT 
                s.shop_id,
                s.shop_name,
                s.area,
                s.shop_type,
                s.number_of_seats,
                s.number_of_barbers,
                COUNT(v.visit_id) as total_visits,
                ROUND(SUM(srv.price), 2) as total_revenue,
                ROUND(AVG(v.waiting_time_minutes), 1) as avg_wait_minutes,
                ROUND(AVG(a.occupied_seats * 100.0 / a.total_seats), 1) as avg_utilization_pct,
                s.rating as average_rating
            FROM shops s
            LEFT JOIN visits v ON s.shop_id = v.shop_id
            LEFT JOIN services srv ON v.service_id = srv.service_id
            LEFT JOIN availability a ON s.shop_id = a.shop_id
            GROUP BY s.shop_id
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
