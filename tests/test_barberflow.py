import os
import sqlite3
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# 1. Test Dataset Generation and Validation
def test_generated_csv_files():
    data_dir = 'data/processed'
    expected_files = ["shops.csv", "services.csv", "customers.csv", "visits.csv", "appointments.csv", "availability.csv", "reviews.csv"]
    
    for f in expected_files:
        path = os.path.join(data_dir, f)
        assert os.path.exists(path), f"Processed CSV file {f} is missing"
        
        df = pd.read_csv(path)
        assert len(df) > 0, f"CSV file {f} is empty"

def test_shops_data_integrity():
    df_shops = pd.read_csv('data/processed/shops.csv')
    assert (df_shops['rating'] >= 1.0).all()
    assert (df_shops['rating'] <= 5.0).all()
    assert (df_shops['number_of_seats'] >= 2).all()
    assert (df_shops['number_of_barbers'] <= df_shops['number_of_seats']).all()

# 2. Test Database Connection and Seeding Counts
def test_database_counts():
    db_path = 'backend/app/barberflow.db'
    assert os.path.exists(db_path), "SQLite database file is missing"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM shops")
    shops_count = cursor.fetchone()[0]
    assert shops_count == 50, f"Expected 50 shops, found {shops_count}"
    
    cursor.execute("SELECT COUNT(*) FROM customers")
    cust_count = cursor.fetchone()[0]
    assert cust_count == 5000, f"Expected 5000 customers, found {cust_count}"
    
    conn.close()

# 3. Test FastAPI Router Endpoints
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["models_status"]["demand_model"] is True

def test_get_shops():
    response = client.get("/api/shops")
    assert response.status_code == 200
    shops_list = response.json()
    assert len(shops_list) > 0
    assert "shop_name" in shops_list[0]
    assert "distance_km" in shops_list[0]

def test_get_analytics_overview():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    kpis = response.json()
    assert kpis["total_shops"] == 50
    assert kpis["total_visits"] > 0
    assert kpis["average_wait_minutes"] >= 0

def test_prediction_demand():
    # Test POST demand prediction
    payload = {
        "shop_id": 1,
        "hour": 17,
        "day_of_week": 5,
        "month": 8
    }
    response = client.post("/api/predictions/demand", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_customers" in data
    assert data["features"]["shop_rating"] > 0

def test_prediction_waiting_time():
    payload = {
        "shop_id": 1,
        "queue_length": 3,
        "occupied_seats": 2,
        "available_seats": 1,
        "hour": 17,
        "day_of_week": 5
    }
    response = client.post("/api/predictions/waiting-time", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_waiting_time_minutes" in data

def test_prediction_no_show():
    payload = {
        "customer_id": 120,
        "hour": 14,
        "booking_lag_days": 3.5
    }
    response = client.post("/api/predictions/no-show", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "no_show_probability" in data
    assert data["risk_tier"] in ["Low", "Medium", "High"]
