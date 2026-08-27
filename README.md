# BarberFlow 💈
### Barber Shop Demand, Availability & Customer Analytics Platform

BarberFlow is a complete data-driven discovery, queue management, and demand analytics platform. It helps customers compare nearby shops by ratings, prices, and live waiting times, while providing shop owners and business analysts with historical KPIs and machine learning predictions to optimize seat capacity.

Designed primarily for a **Junior Data Analyst / Business Analyst portfolio**, this project showcases data engineering, SQL analysis, exploratory data analysis (EDA), predictive machine learning modeling, and responsive dashboard development.

---

## 🚀 Key Features

* **Customer Search & Booking**: Compare shops by distance, ratings, wait times, and price. Join virtual queues (walk-in) or book scheduled slots.
* **Barber Queue Manager**: A live-updating terminal for shop owners to start, complete, or skip customers, and check-in walk-ins.
* **Analyst Dashboard**:
  * **Market Overview**: Market-wide KPIs (shops, clients, wait averages, utilization).
  * **Customer Experience**: Wait times vs ratings analysis.
  * **Shop Performance**: Quadrant matrix categorizing shops into Leaders, Bottlenecks, Underutilized, or Low Scale.
  * **Location Opportunity**: Aggregated Visits-per-Seat neighborhood ratios to spot commercial expansion opportunities.
* **ML Predictions**: Form interfaces query Random Forest Regressors to forecast demand and wait times, and Logistic Regression to evaluate appointment no-show risk.
* **Relational Data Explorer**: A tool to audit the relational SQLite tables, schema types, and counts directly.

---

## 🛠️ Technology Stack

* **Frontend**: React.js, Vite, Tailwind CSS (v4), Recharts (data visualizations), Lucide Icons
* **Backend**: FastAPI (Python), Uvicorn, SQLite (relational database)
* **Data Engineering**: Pandas, NumPy, Scikit-learn, Jupyter Notebooks

---

## 📈 Data & Machine Learning Pipeline

```
Raw Synthetic Data (Queue Simulation)
        ↓
Data Cleaning & Validation (01_data_cleaning.ipynb)
        ↓
Relational Database Seeding (SQLite)
        ↓
SQL Business Analytics (20+ Advanced Queries)
        ↓
Exploratory Data Analysis (02_eda.ipynb)
        ↓
ML Models Training & Evaluation (Random Forest & Logistic Regression)
        ↓
FastAPI Backend Services
        ↓
Interactive React Dashboards
```

### Model Performance Metrics:
* **Customer Demand Prediction** (Random Forest): MAE = 0.45 customers/hr, $R^2$ = 0.81.
* **Waiting Time Prediction** (Random Forest): MAE = 2.1 minutes.
* **No-Show Classifier** (Logistic Regression): Balanced accuracy = 72%.

---

## 📂 Project Structure

```text
TrimPulse/
│
├── backend/
│   ├── app/
│   │   ├── routes/          # FastAPI routers (shops, queue, analytics, predictions)
│   │   ├── database.py      # SQLite connection helpers
│   │   ├── main.py          # FastAPI application entrypoint
│   │   └── barberflow.db    # Relational SQLite database file
│
├── frontend/
│   ├── src/
│   │   ├── pages/           # Customer, Barber, Analyst, Predictions, and Explorer views
│   │   ├── services/        # API client requests
│   │   ├── App.jsx          # Main orchestrator dashboard shell
│   │   └── index.css        # CSS styles and Tailwind v4 theme variables
│   ├── tailwind.config.js   # Tailwind configuration
│   └── postcss.config.js    # PostCSS configuration
│
├── data/
│   ├── raw/                 # Generated raw CSV datasets
│   └── processed/           # Validated clean CSV datasets
│
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_demand_prediction.ipynb
│   └── 04_waiting_time_prediction.ipynb
│
├── sql/
│   ├── schema.sql           # Database schema definition (DDL)
│   └── analysis_queries.sql # 20+ advanced analytical SQL queries
│
├── powerbi/
│   ├── dim_shops.csv        # Dimension table for Power BI import
│   ├── dim_customers.csv
│   ├── dim_services.csv
│   ├── fact_visits.csv      # Fact table for Power BI import
│   ├── fact_appointments.csv
│   ├── fact_reviews.csv
│   └── analytics_summary.csv # Consolidate shop performance aggregates
│
├── models/
│   ├── demand_model.pkl     # Trained scikit-learn model checkpoints
│   ├── waiting_time_model.pkl
│   └── noshow_model.pkl
│
├── docs/                    # Extensive documentation (dictionary, insights, questions)
├── scripts/                 # Python automation scripts (data generation, seeding, Power BI export)
├── requirements.txt         # Python package dependencies
└── README.md
```

---

## 🏃 How to Run the Project Locally

### Prerequisites
* Python 3.12+
* Node.js (v18+)

### 1. Set Up and Start Backend
Open a terminal in the root directory:
```bash
# Install dependencies
python -m pip install -r requirements.txt

# Run the backend FastAPI server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
The server will start at `http://127.0.0.1:8000`. You can inspect the interactive swagger documentation at `http://127.0.0.1:8000/docs`.

### 2. Start Frontend
Open a second terminal in the `frontend` directory:
```bash
# Install dependencies
npm install

# Start Vite dev server
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser and navigate to `http://127.0.0.1:5173/` to view the dashboards!

---

## 🔒 Limitations & Future Work

* **Simulated Real-Time**: Availability updates are simulated on database state transitions. A production build would connect directly to Point of Sale (POS) terminal triggers.
* **Map Mocking**: Location analysis uses neighborhood grid aggregates instead of active map layers (like Google Maps or Mapbox) to avoid requiring API key credentials.
* **Advanced Churn Modeling**: Future increments include training classification algorithms to identify customers with declining visit frequencies for automated promotional targeting.
