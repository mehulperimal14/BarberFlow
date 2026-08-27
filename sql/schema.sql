-- BarberFlow Relational Database Schema (SQLite)

-- 1. Shops Table
CREATE TABLE IF NOT EXISTS shops (
    shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    area TEXT NOT NULL,
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    rating REAL NOT NULL,
    review_count INTEGER NOT NULL,
    opening_time TEXT NOT NULL,
    closing_time TEXT NOT NULL,
    number_of_seats INTEGER NOT NULL,
    number_of_barbers INTEGER NOT NULL,
    shop_status TEXT NOT NULL,
    shop_type TEXT NOT NULL
);

-- 2. Services Table
CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    price REAL NOT NULL,
    average_duration_minutes INTEGER NOT NULL,
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE
);

-- 3. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    age_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    area TEXT NOT NULL,
    preferred_service TEXT NOT NULL,
    average_spending REAL NOT NULL,
    customer_rating REAL NOT NULL
);

-- 4. Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL, -- YYYY-MM-DD
    appointment_time TEXT NOT NULL, -- HH:MM
    booking_time TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS
    status TEXT NOT NULL, -- Completed, Cancelled, No-Show, Scheduled
    cancellation_flag INTEGER NOT NULL DEFAULT 0, -- 0 or 1
    no_show_flag INTEGER NOT NULL DEFAULT 0, -- 0 or 1
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE
);

-- 5. Visits Table (Queue / Completed service)
CREATE TABLE IF NOT EXISTS visits (
    visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD
    arrival_time TEXT NOT NULL, -- HH:MM
    service_start_time TEXT NOT NULL, -- HH:MM
    service_end_time TEXT NOT NULL, -- HH:MM
    waiting_time_minutes INTEGER NOT NULL,
    service_duration_minutes INTEGER NOT NULL,
    seat_id INTEGER NOT NULL, -- seat/barber index used
    visit_type TEXT NOT NULL, -- Walk-in, Appointment
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE
);

-- 6. Availability Snapshot Logs
CREATE TABLE IF NOT EXISTS availability (
    timestamp TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS
    shop_id INTEGER NOT NULL,
    total_seats INTEGER NOT NULL,
    occupied_seats INTEGER NOT NULL,
    available_seats INTEGER NOT NULL,
    queue_length INTEGER NOT NULL,
    estimated_wait_minutes INTEGER NOT NULL,
    PRIMARY KEY (timestamp, shop_id),
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE
);

-- 7. Reviews Table
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    rating REAL NOT NULL,
    service_rating REAL NOT NULL,
    cleanliness_rating REAL NOT NULL,
    value_rating REAL NOT NULL,
    waiting_time_rating REAL NOT NULL,
    review_date TEXT NOT NULL, -- YYYY-MM-DD
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE
);

-- 8. Create Indexes to optimize analytical and prediction queries
CREATE INDEX IF NOT EXISTS idx_services_shop ON services(shop_id);
CREATE INDEX IF NOT EXISTS idx_appointments_shop_date ON appointments(shop_id, appointment_date);
CREATE INDEX IF NOT EXISTS idx_visits_shop_date ON visits(shop_id, date);
CREATE INDEX IF NOT EXISTS idx_availability_shop_timestamp ON availability(shop_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_reviews_shop ON reviews(shop_id);
