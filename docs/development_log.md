# BarberFlow Development Log

This log documents key milestones, implementation challenges, solutions, and design choices throughout the development of **BarberFlow**.

---

## Phase 1: Project Setup
- Created the project directory structure.
- Created `requirements.txt` with python packages for data processing (pandas, numpy), model training (scikit-learn), backend (fastapi, sqlalchemy), and notebooks.

## Phase 2: Data Generation
- Coded a discrete-event queue simulation ([generate_data.py](file:///g:/TrimPulse/scripts/generate_data.py)) to model arrival congestion, wait times, and reviews.
- Generated realistic files: 50 shops, 337 services, 5,000 customers, 65,000 visits, 32,522 appointments, 57,000 availability logs, and 26,000 reviews.

## Phase 3: Database Engineering
- Structured `sql/schema.sql` defining relational PKs, FKs, and index strategies.
- Created `scripts/seed_db.py` to seed SQLite database ([barberflow.db](file:///g:/TrimPulse/backend/app/barberflow.db)).

## Phase 4: SQL Business Queries
- Formulated 20+ analytical business queries in `sql/analysis_queries.sql` demonstrating CTEs, windows (ranking), and CASE statements.

## Phase 5: Python EDA & Notebooks
- Coded notebook compiler script to write and execute `01_data_cleaning.ipynb` and `02_eda.ipynb` with full charts.

## Phase 6: Machine Learning
- Trained Random Forest and Logistic Regression models in notebooks. (Superseded in Phase 14: the original notebook metrics were demand R² 0.54, wait MAE 8.1 min, no-show balanced accuracy 0.65, not the figures first written here.)
- Saved model checkpoints under `models/` folder.

## Phase 7: Backend API Development
- Built a FastAPI backend. Implemented endpoints for shop listings, custom recommendation score matching, queues check-in, appointments, analytics aggregates, and model predictions.
- Hosted on port 8000.

## Phase 8-11: Frontend Dashboards
- Initialized React/Vite/Tailwind UI and configured Tailwind CSS v4 support.
- Built a dark-themed UI covering the Customer Portal, Barber Manager Panel, Analyst BI Dashboard (Recharts), ML Forecaster, and Relational Data Explorer.
- Hosted on port 5173.

## Phase 12: Testing
- Programmed a suite of 10 tests in `tests/test_barberflow.py` verifying data schemas, seeding counts, health metrics, and model endpoints.
- (Phase 14 replaced this suite: the original tests needed `PYTHONPATH=backend` to run.)

## Phase 13: Documentation
- Written dictionary, insights report, 30 interview questions, resume bullets, README, and final walkthrough.


## Phase 14: Production repair & deployment
- Fixed join fan-out in shop-performance, location and the Power BI summary (pre-aggregated CTEs); fixed the `/overview?shop_id` 500; fixed SQL #11, #16 and #20.
- Split storage: a read-only historical SQLite DB (built from CSVs at startup) and a writable live store (PostgreSQL via `DATABASE_URL`, SQLite locally) for the queue and bookings.
- Retrained models leak-free (`scripts/train_models.py`), served them from JSON without pickle, and read metrics from `model_card.json`.
- Rewrote the five React pages against the corrected API (services load in the booking modal, persisted barber actions, quadrant chart, relative location thresholds).
- 18 pytest tests pass on SQLite and PostgreSQL. Deployed on Vercel (static frontend plus a Python function).
