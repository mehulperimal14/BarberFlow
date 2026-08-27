# Data Dictionary: BarberFlow Database Schema

This schema represents a normalized relational database containing 7 tables stored in SQLite.

---

## 1. Table: `shops` (Dimension Table)
Stores details of individual barber shops.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `shop_id` | INTEGER | PK | `1` | Unique identifier for each barber shop. |
| `shop_name` | TEXT | | `"Fade & Blade"` | Commercial brand name of the shop. |
| `owner_name` | TEXT | | `"Owner 1"` | Name of the franchise owner. |
| `area` | TEXT | | `"Downtown"` | Neighborhood location inside Metropolis. |
| `city` | TEXT | | `"Metropolis"` | Municipality location. |
| `latitude` | REAL | | `40.7128` | Geographical latitude coordinate. |
| `longitude` | REAL | | `-74.0060` | Geographical longitude coordinate. |
| `rating` | REAL | | `4.7` | Overall customer satisfaction score (1.0 to 5.0). |
| `review_count`| INTEGER | | `542` | Total number of reviews received. |
| `opening_time`| TEXT | | `"09:00"` | Shop opening hour (HH:MM). |
| `closing_time`| TEXT | | `"20:00"` | Shop closing hour (HH:MM). |
| `number_of_seats`| INTEGER| | `5` | Total number of barber chairs installed. |
| `number_of_barbers`| INTEGER| | `4` | Number of active barbers scheduled. |
| `shop_status` | TEXT | | `"Active"` | Operation status (`Active`, `Inactive`). |
| `shop_type` | TEXT | | `"Premium"` | Classification segment (`Premium`, `Budget`, `Bottleneck`, `Standard`). |

---

## 2. Table: `services` (Dimension Table)
Stores services provided by each shop.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `service_id` | INTEGER | PK | `1` | Unique identifier for the service. |
| `shop_id` | INTEGER | FK | `1` | References `shops.shop_id`. |
| `service_name`| TEXT | | `"Haircut + Beard"`| Name of the service. |
| `price` | REAL | | `45.00` | Price charged in USD. |
| `average_duration_minutes` | INTEGER | | `45` | Average duration required to perform service. |

---

## 3. Table: `customers` (Dimension Table)
Stores customer demographics and preferences.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `customer_id` | INTEGER | PK | `125` | Unique identifier for each customer. |
| `age_group` | TEXT | | `"26-35"` | Customer age cohort (`18-25`, `26-35`, `36-45`, `46-60`, `60+`). |
| `gender` | TEXT | | `"Male"` | Gender category (`Male`, `Female`, `Non-binary`). |
| `area` | TEXT | | `"Westside"` | Customer residential neighborhood. |
| `preferred_service` | TEXT | | `"Haircut"` | Most frequently requested service. |
| `average_spending` | REAL | | `42.50` | Average ticket amount spent per visit. |
| `customer_rating` | REAL | | `4.6` | Average rating given by customer (1.0 to 5.0). |

---

## 4. Table: `appointments` (Fact Table)
Stores reservations made by customers.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `appointment_id`| INTEGER| PK | `1` | Unique identifier for the booking. |
| `customer_id` | INTEGER | FK | `125` | References `customers.customer_id`. |
| `shop_id` | INTEGER | FK | `1` | References `shops.shop_id`. |
| `service_id` | INTEGER | FK | `2` | References `services.service_id`. |
| `appointment_date`| TEXT | | `"2026-08-30"` | Reservation date (YYYY-MM-DD). |
| `appointment_time`| TEXT | | `"14:00"` | Reservation arrival block (HH:MM). |
| `booking_time` | TEXT | | `"2026-08-25 10:15:00"`| Timestamp when the booking was made (YYYY-MM-DD HH:MM:SS). |
| `status` | TEXT | | `"Completed"` | Final state (`Completed`, `Cancelled`, `No-Show`, `Scheduled`). |
| `cancellation_flag`| INTEGER| | `0` | Binary indicator (1 if cancelled, else 0). |
| `no_show_flag` | INTEGER| | `0` | Binary indicator (1 if no-show, else 0). |

---

## 5. Table: `visits` (Fact Table)
Stores completed service records (walk-ins + completed appointments).

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `visit_id` | INTEGER | PK | `1` | Unique identifier for the visit. |
| `customer_id` | INTEGER | FK | `125` | References `customers.customer_id`. |
| `shop_id` | INTEGER | FK | `1` | References `shops.shop_id`. |
| `service_id` | INTEGER | FK | `2` | References `services.service_id`. |
| `date` | TEXT | | `"2026-08-30"` | Service execution date (YYYY-MM-DD). |
| `arrival_time` | TEXT | | `"13:45"` | Customer arrival timestamp (HH:MM). |
| `service_start_time`| TEXT| | `"14:00"` | Barber service start timestamp (HH:MM). |
| `service_end_time` | TEXT | | `"14:45"` | Barber service end timestamp (HH:MM). |
| `waiting_time_minutes`| INTEGER| | `15` | Minutes spent waiting in queue (`start - arrival`). |
| `service_duration_minutes`| INTEGER| | `45` | Actual service execution minutes (`end - start`). |
| `seat_id` | INTEGER | | `2` | Barber index/chair number assigned. |
| `visit_type` | TEXT | | `"Appointment"` | Channel description (`Walk-in`, `Appointment`). |

---

## 6. Table: `availability` (Log Snapshot Table)
Stores hourly periodic capacity snapshots of shops.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | TEXT | PK | `"2026-08-30 17:00:00"`| Snapshot logging timestamp (YYYY-MM-DD HH:MM:SS). |
| `shop_id` | INTEGER | PK, FK | `1` | References `shops.shop_id`. |
| `total_seats` | INTEGER | | `5` | Total seats installed at snapshot time. |
| `occupied_seats`| INTEGER| | `4` | Number of chairs occupied by customers. |
| `available_seats`| INTEGER| | `1` | Number of open chairs (`total_seats - occupied_seats`). |
| `queue_length` | INTEGER| | `3` | Number of customers waiting in queue. |
| `estimated_wait_minutes`| INTEGER| | `15` | Expected wait time for a new walk-in client. |

---

## 7. Table: `reviews` (Fact Table)
Stores customer review scores.

| Column | Data Type | Key | Example | Description / Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `review_id` | INTEGER | PK | `1` | Unique identifier for the review. |
| `customer_id` | INTEGER | FK | `125` | References `customers.customer_id`. |
| `shop_id` | INTEGER | FK | `1` | References `shops.shop_id`. |
| `rating` | REAL | | `4.5` | Overall review score given (1.0 to 5.0). |
| `service_rating`| REAL | | `4.8` | Quality score given for the service. |
| `cleanliness_rating`| REAL | | `4.2` | Cleanliness score given for the shop. |
| `value_rating` | REAL | | `4.0` | Price value/fairness score. |
| `waiting_time_rating`| REAL| | `4.0` | Rating score given for the queue experience. |
| `review_date` | TEXT | | `"2026-08-30"` | Date review was submitted (YYYY-MM-DD). |
