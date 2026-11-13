# Resume Bullet Points: BarberFlow

Every number below is verified by the code. Model metrics come from `backend/app/ml_models/model_card.json`, analytics numbers from the SQL queries, and test counts from `pytest`. Say "simulated data" once in the project line.

---

### Option 1 (Data Analyst / Business Analyst)
* **Designed** a 7-table SQLite schema (PKs, FKs, composite key, indexes) and **wrote** 20 analytical SQL queries (CTEs, `RANK()`/`ROW_NUMBER()` window functions, `HAVING`, subqueries) over a simulated 65K-visit, 50-shop barber market.
* **Found** that the 19-minute mean wait masked a **median of 0**: 76% of customers never waited, while 16 low-capacity shops averaged **52.7-minute** waits. Also found that 58.7% of arrivals fell between 4 and 7 PM, and turned these findings into staffing and off-peak recommendations.
* **Fixed** a join fan-out bug that inflated dashboard visit counts about 1,000×, by pre-aggregating fact tables in CTEs. Added regression tests that reconcile dashboard totals with raw row counts.

### Option 2 (Data Scientist / ML)
* **Trained** a Random Forest waiting-time model reaching **R² 0.84 and MAE 8.5 minutes** on a time-based hold-out, against a 30-minute mean baseline. Queue length carries 91% of the feature importance.
* **Removed** target leakage from a historical-demand feature and **selected** models on a validation window. Showed that a linear model matched the forest (R² 0.50), and **flagged** a no-show classifier as experimental after ablation showed its signal was a simulation artefact (AUC 0.68 → 0.51 without the hour feature).
* **Served** the models without pickle by exporting scikit-learn trees and coefficients to JSON (matching to within 1e-7), with metrics loaded from a model card instead of being hard-coded.

### Option 3 (Software / Full-stack)
* **Built and deployed** a React 19 + Vite + Tailwind frontend and FastAPI backend on Vercel serverless functions, with a read-only SQLite analytics store and a PostgreSQL live store for queue and booking writes.
* **Implemented** a virtual queue with persisted status transitions, transactional slot-capacity checks, database-backed rate limiting and Pydantic validation, plus 18 pytest tests that run against both SQLite and PostgreSQL.
