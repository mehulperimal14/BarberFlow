import os
import sqlite3
import pandas as pd

def seed_database():
    db_path = 'backend/app/barberflow.db'
    schema_path = 'sql/schema.sql'
    data_dir = 'data/processed'

    # Create backend app directory if not exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read and execute schema
    print(f"Initializing schema from {schema_path}...")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()

    # List of tables and corresponding CSVs
    tables = [
        ("shops", "shops.csv"),
        ("services", "services.csv"),
        ("customers", "customers.csv"),
        ("appointments", "appointments.csv"),
        ("visits", "visits.csv"),
        ("availability", "availability.csv"),
        ("reviews", "reviews.csv")
    ]

    for table_name, csv_file in tables:
        csv_path = os.path.join(data_dir, csv_file)
        if not os.path.exists(csv_path):
            print(f"Warning: CSV file {csv_path} not found. Skipping table {table_name}.")
            continue

        print(f"Seeding table '{table_name}' from {csv_path}...")
        df = pd.read_csv(csv_path)

        # Append to SQL table
        # If SQLite tables already exist, we want to overwrite/reseed, so we clear them first.
        cursor.execute(f"DELETE FROM {table_name}")
        df.to_sql(table_name, conn, if_exists='append', index=False)
        print(f"Successfully seeded {len(df)} records into '{table_name}'.")

    # Verify counts
    print("\nVerification - Table Counts:")
    for table_name, _ in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f" - {table_name}: {count} records")

    conn.commit()
    conn.close()
    print("\nDatabase seeding completed successfully.")

if __name__ == '__main__':
    seed_database()
