# 30 Data Analyst Interview Questions & Answers: BarberFlow

This guide prepares candidates to defend the **BarberFlow** portfolio project in interviews.

---

### 1. Why did you choose this business problem?
* **Answer**: Queuing in barber shops is a tangible, universal problem. It perfectly demonstrates the challenge of matching capacity (supply) with variable customer arrival rates (demand). Analyzing this problem requires demonstrating data engineering, SQL, and predictive analytics skills.

### 2. How did you generate the synthetic dataset?
* **Answer**: Instead of generating random data, I built a custom **discrete-event queue simulation** in Python (`scripts/generate_data.py`). It tracks barber availability and schedules arrivals based on Poisson distributions for weekdays and peak hours. This ensures that wait times and ratings are logically and mathematically consistent with congestion levels.

### 3. What are the key tables and relationships in your database?
* **Answer**: It is a normalized star schema:
  * **Dimension Tables**: `shops`, `services`, `customers`.
  * **Fact Tables**: `appointments`, `visits` (historical queues), `reviews`.
  * **Log Snapshot Table**: `availability` (hourly capacity metrics).

### 4. How did you handle data validation and cleaning?
* **Answer**: I documented this in `01_data_cleaning.ipynb`. I checked for:
  * Missing primary keys or foreign keys.
  * Duplicates in logs.
  * Spatial coordinate anomalies (coordinates outside Metropolis bounds).
  * Outliers in wait times and average spending using the Interquartile Range (IQR) method.

### 5. How is "Seat Utilization" calculated?
* **Answer**: It is calculated hourly in the `availability` log:
  $$\text{Seat Utilization} = \frac{\text{Occupied Seats}}{\text{Total Seats}} \times 100$$
  This represents the percentage of active barber chairs occupied by customers during operating hours.

### 6. What SQL window functions did you use?
* **Answer**: In `sql/analysis_queries.sql`, I used `RANK() OVER (ORDER BY AVG(waiting_time_minutes) DESC)` to rank shops from worst to best in terms of customer queue efficiency, showing analytical SQL fluency.

### 7. How did you calculate repeat customer rate in SQL?
* **Answer**: I used a Common Table Expression (CTE) to count visits per customer-shop pair, then calculated the percentage of customers who visited the same shop 3 or more times.

### 8. Why did you choose a Random Forest Regressor for demand prediction?
* **Answer**: Random Forest handles non-linear relationships (like the evening rush hour or weekend multipliers) and feature interactions (such as the combined impact of shop ratings and capacity) without requiring extensive feature scaling, making it more accurate than simple Linear Regression.

### 9. What evaluation metrics did you use for the demand model, and what do they mean?
* **Answer**: I used Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and $R^2$:
  * **MAE 0.76 customers/hour, $R^2$ 0.50** on the last 20% of dates (see `backend/app/ml_models/model_card.json`).
  * Honest reading: a linear model and the historical shop/hour/weekday average perform the same, so the "model" mostly reproduces that average. The waiting-time model is the strong one (R² 0.84, MAE 8.5 min).

### 10. How did you prevent "data leakage" in your ML pipeline?
* **Answer**: In `scripts/train_models.py` I use a **time-based split**: the first 80% of the 91 dates (72 days) train and the last 19 days test. The historical-average feature is computed **from training dates only**. The original notebook averaged over all dates, which leaked test targets; fixing that lowered R² from 0.54 to about 0.50. I selected the model on a separate validation window, not on the test set.

### 11. What are the most important features in predicting waiting time?
* **Answer**: According to the model card's feature importances, **queue length** dominates (0.91), followed by **number of barbers** and **hour**. This aligns with queuing theory, where queue length represents backlog and barbers represent processing speed.

### 12. Why did you use Logistic Regression for the no-show model?
* **Answer**: No-show prediction is a binary classification problem (will show vs. won't show). Logistic Regression is highly explainable, providing a direct probability score that can be translated into "Low," "Medium," or "High" risk tiers.

### 13. What is the business value of predicting no-show risk?
* **Answer**: By identifying high-risk appointments, shops can send automated SMS reminders, require pre-payment deposits, or double-book slots during peak hours to protect revenue.

### 14. What does "booking lag" mean in your no-show model?
* **Answer**: Booking lag is the time delay (in days) between when the appointment is booked and when it occurs. In this simulated data it has **no** effect: lags are 1–7 days for every status, and no-shows are assigned at random. The model's only signal is the appointment hour (a simulation artefact), so it is labelled experimental.

### 15. How does your weighted recommendation system work?
* **Answer**: It calculates a configurable score based on rating, wait time, distance, and price. Features are normalized to a 0-1 scale so they can be combined. The UI explains the score using badges like "⭐ Highly Rated" or "🟢 Short Wait" to make recommendations transparent.

### 16. What is the difference between the Customer App and the Barber Panel?
* **Answer**: The Customer App is designed for simplicity (search, filter, book, view wait times). The Barber Panel is information-dense, focusing on active queue management, check-in controls, and business KPIs.

### 17. How did you simulate "real-time" availability?
* **Answer**: Since there are no physical sensors, we simulate check-ins and check-outs in the database. When a customer joins via the UI, a row is written to a **live store** (PostgreSQL in production, SQLite locally) with a persisted status (Waiting → In Service → Completed/Skipped). The barber panel polls it every 10 s, and the shop list's wait estimate comes from the ML model applied to the live queue counts.

### 18. What is the "Visits-per-Seat" ratio, and why is it useful?
* **Answer**: It is the total visits in an area divided by the total barber seats in that area. It represents spatial capacity utilization. Areas with high ratios are under-served (high demand, low capacity), presenting business expansion opportunities.

### 19. What factors influence customer rating scores in your reviews data?
* **Answer**: Queue waiting times, shop cleanliness, service quality, and price value. Long wait times have the strongest negative correlation with rating scores.

### 20. Why did you use SQLite instead of PostgreSQL for the initial project?
* **Answer**: SQLite is serverless and self-contained, making it ideal for a portfolio project because it runs out-of-the-box without requiring database server setup. However, the schema and queries use standard SQL, making them easily portable to PostgreSQL.

### 21. How would you connect this project to Power BI?
* **Answer**: I created a Python export script (`scripts/export_powerbi.py`) that exports the SQLite tables as clean CSV files (`dim_shops.csv`, `fact_visits.csv`, etc.). These CSVs can be imported directly into Power BI, maintaining the relational keys.

### 22. What does a "Bottleneck Shop" mean in your analysis?
* **Answer**: A shop with high customer demand (above average visits) but low capacity (3 or fewer seats). These shops have long wait times and represent opportunities to expand capacity by adding chairs or barbers.

### 23. What does "Customer Reneging" mean, and how did you model it?
* **Answer**: Reneging occurs when a customer joins a queue but leaves before receiving service because the wait is too long. In our data generation, we simulated wait times and ratings, showing that customers with wait times over 30 minutes give poor ratings, which correlates with customer churn.

### 24. What is the difference between MAE and RMSE?
* **Answer**: MAE treats all errors equally, while RMSE penalizes larger errors more heavily because it squares the errors before averaging them. A large gap between MAE and RMSE indicates the presence of large prediction errors.

### 25. How would you scale the prediction system for production?
* **Answer**:
  1. Wrap the FastAPI backend in a Docker container.
  2. Deploy it to an AWS ECS or GCP Cloud Run instance.
  3. Set up a database like PostgreSQL on RDS.
  4. Schedule weekly model retraining using a pipeline tool like Apache Airflow.

### 26. Why did you choose React + Vite instead of a standard template?
* **Answer**: Vite provides a modern, fast development server and optimized build bundles. React allows us to build a dynamic, stateful SPA dashboard with tabs and charts.

### 27. How does the model explain its predictions to users?
* **Answer**: The prediction endpoints return the model metadata and feature values. This allows the UI to display exactly why a wait time is estimated at, say, 18 minutes (e.g., "based on 3 people currently in queue with 2 active barbers").

### 28. What is the "average ticket size" and why is it important?
* **Answer**: The average revenue generated per customer visit. Tracking this helps owners evaluate the success of service bundles and upselling strategies.

### 29. How would you capture live wait times in a real-world deployment?
* **Answer**: We would integrate with the shop's Point of Sale (POS) system. When a barber clicks "Start" or "Complete" on their terminal, it would update the queue database in real-time, replacing the simulation.

### 30. If you could improve one thing in this project, what would it be?
* **Answer**: I would implement **classification models for customer churn prediction** to identify which customers are at risk of not returning, using their visit frequency and rating histories.
