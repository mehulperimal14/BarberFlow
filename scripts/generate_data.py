import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_dataset():
    print("Starting synthetic data generation...")
    
    # Create directories if they do not exist
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)

    # 1. GENERATE SHOPS
    print("Generating Shops...")
    shop_names = [
        "The Gentlemen's Club", "Fade & Blade", "Classic Cuts", "Urban Trims", "The Shave Parlor",
        "Barber & Co.", "Razor Sharp", "Prestige Barber", "Dapper & Co.", "The Hair Hub",
        "Modern Man Barbers", "Chop Shop", "Elite Grooming", "Eco Barber Shop", "Vintage Barber",
        "The Grooming Lounge", "Style & Scissors", "Headquarters", "Top Knot", "The Barber Lounge",
        "Bold & Gold", "Trim & Proper", "Executive Barber", "Main Street Barbers", "Cornerstone Cuts",
        "Metro Man", "The Daily Shave", "Slick Backs", "Grizzly Grooming", "Iron & Clay",
        "High-Class Trims", "The Clipper Room", "True & Valiant", "Heritage Barbers", "Fades & Shades",
        "Gold Medal Cuts", "The Hair Loft", "Sharp Styles", "Signature Cuts", "Crown Grooming",
        "Redwood Barbers", "Apex Trims", "Vogue Men", "The Cutting Edge", "Summit Grooming",
        "Atlas Barber", "Lighthouse Cuts", "Blue Collar Barbers", "First Class Barber", "The Hangar Shop"
    ]
    
    areas = ["Downtown", "Westside", "Northside", "Eastside", "Suburbs"]
    cities = ["Metropolis"]
    
    shops = []
    # Create different shop classes to make analytics interesting:
    # 1. Premium: high price, low capacity (exclusive) or high capacity, high rating
    # 2. Budget: low price, high capacity, moderate/low rating
    # 3. High Demand / Bottleneck: high demand, low capacity
    # 4. Standard
    for i, name in enumerate(shop_names):
        shop_id = i + 1
        area = random.choice(areas)
        city = random.choice(cities)
        
        # Latitude: Metropolis center 40.7128, Longitude: -74.0060
        latitude = 40.7128 + np.random.normal(0, 0.04)
        longitude = -74.0060 + np.random.normal(0, 0.04)
        
        # Shop Type assignment
        shop_type = random.choice(["Premium", "Budget", "Bottleneck", "Standard"])
        
        if shop_type == "Premium":
            seats = random.randint(4, 8)
            barbers = random.randint(seats - 1, seats)
            rating = round(random.uniform(4.5, 5.0), 1)
        elif shop_type == "Budget":
            seats = random.randint(5, 10)
            barbers = random.randint(seats - 2, seats - 1)
            rating = round(random.uniform(3.4, 4.2), 1)
        elif shop_type == "Bottleneck":
            seats = random.randint(2, 3)
            barbers = random.randint(1, seats)
            rating = round(random.uniform(4.0, 4.7), 1)
        else: # Standard
            seats = random.randint(3, 5)
            barbers = random.randint(seats - 1, seats)
            rating = round(random.uniform(3.8, 4.5), 1)
            
        review_count = int(random.randint(100, 1000) * (rating - 2.5))
        opening_time = random.choice(["08:00", "09:00"])
        closing_time = random.choice(["19:00", "20:00", "21:00"])
        
        shops.append({
            "shop_id": shop_id,
            "shop_name": name,
            "owner_name": f"Owner {shop_id}",
            "area": area,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "rating": rating,
            "review_count": review_count,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "number_of_seats": seats,
            "number_of_barbers": barbers,
            "shop_status": "Active",
            "shop_type": shop_type
        })
        
    df_shops = pd.DataFrame(shops)
    df_shops.to_csv('data/raw/shops.csv', index=False)

    # 2. GENERATE SERVICES
    print("Generating Services...")
    services_templates = [
        {"name": "Haircut", "base_price": 25.0, "duration": 30},
        {"name": "Haircut + Beard", "base_price": 40.0, "duration": 45},
        {"name": "Beard Trim", "base_price": 15.0, "duration": 20},
        {"name": "Hair Wash", "base_price": 10.0, "duration": 15},
        {"name": "Styling", "base_price": 15.0, "duration": 20},
        {"name": "Kids Haircut", "base_price": 20.0, "duration": 25},
        {"name": "Premium Haircut", "base_price": 50.0, "duration": 50}
    ]
    
    services = []
    service_id = 1
    for _, shop in df_shops.iterrows():
        shop_id = shop["shop_id"]
        shop_type = shop["shop_type"]
        
        # Price multiplier based on shop class
        price_mult = 1.0
        if shop_type == "Premium":
            price_mult = random.uniform(1.4, 1.8)
        elif shop_type == "Budget":
            price_mult = random.uniform(0.7, 0.9)
        elif shop_type == "Bottleneck":
            price_mult = random.uniform(1.0, 1.2)
            
        for s in services_templates:
            # Budget shops might not offer Premium Haircut
            if shop_type == "Budget" and s["name"] == "Premium Haircut":
                continue
                
            services.append({
                "service_id": service_id,
                "shop_id": shop_id,
                "service_name": s["name"],
                "price": round(s["base_price"] * price_mult, 2),
                "average_duration_minutes": s["duration"] + random.choice([-5, 0, 5])
            })
            service_id += 1
            
    df_services = pd.DataFrame(services)
    df_services.to_csv('data/raw/services.csv', index=False)

    # 3. GENERATE CUSTOMERS
    print("Generating Customers...")
    age_groups = ['18-25', '26-35', '36-45', '46-60', '60+']
    genders = ['Male', 'Female', 'Non-binary']
    
    customers = []
    preferred_services_list = [s["name"] for s in services_templates]
    
    for i in range(5000):
        customer_id = i + 1
        age = np.random.choice(age_groups, p=[0.25, 0.35, 0.20, 0.15, 0.05])
        gender = np.random.choice(genders, p=[0.85, 0.12, 0.03]) # Barbershops skew male
        area = random.choice(areas)
        preferred_service = random.choice(preferred_services_list)
        
        # Customer spending habits: higher age groups or premium preference spend more
        avg_spending = random.uniform(15, 60)
        if age in ['26-35', '36-45']:
            avg_spending += random.uniform(10, 20)
            
        customer_rating = round(np.clip(np.random.normal(4.3, 0.5), 1.0, 5.0), 1)
        
        customers.append({
            "customer_id": customer_id,
            "age_group": age,
            "gender": gender,
            "area": area,
            "preferred_service": preferred_service,
            "average_spending": round(avg_spending, 2),
            "customer_rating": customer_rating
        })
        
    df_customers = pd.DataFrame(customers)
    df_customers.to_csv('data/raw/customers.csv', index=False)

    # 4. GENERATE VISITS AND APPOINTMENTS (QUEUE SIMULATION)
    print("Generating Visits and Appointments via queue simulation...")
    # Timeline: 90 days
    start_date = datetime(2026, 6, 1)
    end_date = datetime(2026, 8, 30)
    delta = end_date - start_date
    dates = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
    
    visits = []
    appointments = []
    availability_logs = []
    
    visit_id = 1
    appointment_id = 1
    
    # Store services per shop for lookup
    shop_services = df_services.groupby('shop_id').apply(lambda x: x.to_dict('records')).to_dict()
    
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        weekday = date.weekday() # 0 = Mon, 6 = Sun
        is_weekend = weekday >= 4 # Fri, Sat, Sun
        
        # Day multiplier for demand
        if weekday == 0: # Mon
            day_mult = 0.6
        elif weekday == 1: # Tue
            day_mult = 0.7
        elif weekday == 2: # Wed
            day_mult = 0.8
        elif weekday == 3: # Thu
            day_mult = 0.9
        elif weekday == 4: # Fri
            day_mult = 1.3
        elif weekday == 5: # Sat
            day_mult = 1.6
        else: # Sun
            day_mult = 1.2
            
        for _, shop in df_shops.iterrows():
            shop_id = shop["shop_id"]
            seats = shop["number_of_seats"]
            barbers = shop["number_of_barbers"]
            shop_rating = shop["rating"]
            shop_type = shop["shop_type"]
            
            # Opening and Closing minutes from midnight
            open_hour = int(shop["opening_time"].split(":")[0])
            close_hour = int(shop["closing_time"].split(":")[0])
            open_min = open_hour * 60
            close_min = close_hour * 60
            
            # Shop popularity multiplier
            popularity_mult = 1.0
            if shop_type == "Premium":
                popularity_mult = 1.2
            elif shop_type == "Bottleneck":
                popularity_mult = 1.3
            elif shop_type == "Budget":
                popularity_mult = 1.1
            
            # Base daily arrivals
            base_arrivals = 12
            expected_arrivals = base_arrivals * day_mult * popularity_mult
            
            # Sample number of actual visitors for the day
            num_arrivals = np.random.poisson(expected_arrivals)
            
            # Generate customer arrivals
            arrivals = []
            for _ in range(num_arrivals):
                # Choose customer
                cust = df_customers.sample(1).iloc[0]
                cust_id = int(cust["customer_id"])
                
                # Choose service
                srv = random.choice(shop_services[shop_id])
                srv_id = int(srv["service_id"])
                duration = int(srv["average_duration_minutes"])
                
                # Sample arrival time (minutes from midnight)
                # Distribution peaks: 12-14 (midday) and 16-19 (evening)
                hour = np.random.choice(
                    np.arange(open_hour, close_hour),
                    p=get_hour_probabilities(open_hour, close_hour)
                )
                minute = random.randint(0, 59)
                arr_min = hour * 60 + minute
                
                # Walk-in vs Appointment (40% Appointment, 60% Walk-in)
                visit_type = np.random.choice(['Appointment', 'Walk-in'], p=[0.4, 0.6])
                
                arrivals.append({
                    "customer_id": cust_id,
                    "service_id": srv_id,
                    "duration": duration,
                    "arrival_min": arr_min,
                    "visit_type": visit_type
                })
            
            # Sort arrivals by arrival time
            arrivals = sorted(arrivals, key=lambda x: x["arrival_min"])
            
            # Queue simulation variables
            # Barbers represented by when they will be free (minutes from midnight)
            barber_free_times = [open_min] * barbers
            
            # Store completed visits for this shop-day
            daily_visits = []
            
            # We will also generate cancelled/no-show appointments that did not show up
            # These don't enter the queue, but are booked. Let's do that at the end of the day.
            
            for arr in arrivals:
                arr_min = arr["arrival_min"]
                duration = arr["duration"]
                cust_id = arr["customer_id"]
                srv_id = arr["service_id"]
                visit_type = arr["visit_type"]
                
                # Find the barber who will be free earliest
                earliest_barber_idx = np.argmin(barber_free_times)
                earliest_free_min = barber_free_times[earliest_barber_idx]
                
                if earliest_free_min <= arr_min:
                    # Service starts immediately
                    start_min = arr_min
                    wait_min = 0
                else:
                    # Service starts when barber becomes free
                    start_min = earliest_free_min
                    wait_min = earliest_free_min - arr_min
                
                # Cap service end at close_min + 30 min (barbers finish their last client)
                end_min = start_min + duration
                
                # Update barber free time
                barber_free_times[earliest_barber_idx] = end_min
                
                # Convert minutes back to HH:MM format
                arr_time_str = f"{arr_min // 60:02d}:{arr_min % 60:02d}"
                start_time_str = f"{start_min // 60:02d}:{start_min % 60:02d}"
                end_time_str = f"{end_min // 60:02d}:{end_min % 60:02d}"
                
                # We save this visit
                visit_record = {
                    "visit_id": visit_id,
                    "customer_id": cust_id,
                    "shop_id": shop_id,
                    "service_id": srv_id,
                    "date": date_str,
                    "arrival_time": arr_time_str,
                    "service_start_time": start_time_str,
                    "service_end_time": end_time_str,
                    "waiting_time_minutes": wait_min,
                    "service_duration_minutes": duration,
                    "seat_id": earliest_barber_idx + 1,
                    "visit_type": visit_type,
                    "arrival_min_val": arr_min # temp for availability calculation
                }
                
                visits.append(visit_record)
                daily_visits.append(visit_record)
                
                # If it's an appointment, we also create a completed appointment record
                if visit_type == 'Appointment':
                    booking_days_ahead = random.randint(1, 7)
                    booking_dt = date - timedelta(days=booking_days_ahead)
                    booking_hour = random.randint(9, 18)
                    booking_minute = random.randint(0, 59)
                    booking_time_str = f"{booking_dt.strftime('%Y-%m-%d')} {booking_hour:02d}:{booking_minute:02d}:00"
                    
                    appointments.append({
                        "appointment_id": appointment_id,
                        "customer_id": cust_id,
                        "shop_id": shop_id,
                        "service_id": srv_id,
                        "appointment_date": date_str,
                        "appointment_time": arr_time_str,
                        "booking_time": booking_time_str,
                        "status": "Completed",
                        "cancellation_flag": 0,
                        "no_show_flag": 0
                    })
                    appointment_id += 1
                
                visit_id += 1
                
            # Add some non-completed appointments (Cancellations and No-Shows)
            # Roughly 15% of total bookings are cancelled or no-shows
            num_canceled_no_show = int(np.random.poisson(expected_arrivals * 0.1))
            for _ in range(num_canceled_no_show):
                cust = df_customers.sample(1).iloc[0]
                cust_id = int(cust["customer_id"])
                srv = random.choice(shop_services[shop_id])
                srv_id = int(srv["service_id"])
                
                hour = random.randint(open_hour, close_hour - 1)
                minute = random.randint(0, 59)
                app_time_str = f"{hour:02d}:{minute:02d}"
                
                booking_days_ahead = random.randint(1, 7)
                booking_dt = date - timedelta(days=booking_days_ahead)
                booking_hour = random.randint(9, 18)
                booking_minute = random.randint(0, 59)
                booking_time_str = f"{booking_dt.strftime('%Y-%m-%d')} {booking_hour:02d}:{booking_minute:02d}:00"
                
                status = np.random.choice(["Cancelled", "No-Show"], p=[0.65, 0.35])
                cancellation_flag = 1 if status == "Cancelled" else 0
                no_show_flag = 1 if status == "No-Show" else 0
                
                appointments.append({
                    "appointment_id": appointment_id,
                    "customer_id": cust_id,
                    "shop_id": shop_id,
                    "service_id": srv_id,
                    "appointment_date": date_str,
                    "appointment_time": app_time_str,
                    "booking_time": booking_time_str,
                    "status": status,
                    "cancellation_flag": cancellation_flag,
                    "no_show_flag": no_show_flag
                })
                appointment_id += 1
                
            # Generate Availability snap-shots for this shop-day
            # Sample every 1 hour during working hours (open_hour to close_hour)
            for h in range(open_hour, close_hour + 1):
                timestamp_str = f"{date_str} {h:02d}:00:00"
                current_time_min = h * 60
                
                occupied = 0
                queue_len = 0
                
                # Check occupancy and queue at current_time_min
                for dv in daily_visits:
                    arr_m = dv["arrival_min_val"]
                    start_m = arr_m + dv["waiting_time_minutes"]
                    end_m = start_m + dv["service_duration_minutes"]
                    
                    # Occupied? (Service is happening at this minute)
                    if start_m <= current_time_min < end_m:
                        occupied += 1
                    # In queue? (Arrived but not started yet)
                    elif arr_m <= current_time_min < start_m:
                        queue_len += 1
                
                occupied = min(occupied, seats) # Total active seats cannot exceed total seats
                avail_seats = seats - occupied
                
                # Estimated waiting time for a new walk-in at this exact minute
                if queue_len == 0:
                    est_wait = 0
                else:
                    # roughly 15 minutes per customer in queue, divided by barbers
                    est_wait = int((queue_len * 20) / barbers)
                    
                availability_logs.append({
                    "timestamp": timestamp_str,
                    "shop_id": shop_id,
                    "total_seats": seats,
                    "occupied_seats": occupied,
                    "available_seats": avail_seats,
                    "queue_length": queue_len,
                    "estimated_wait_minutes": est_wait
                })

    df_visits = pd.DataFrame(visits)
    df_appointments = pd.DataFrame(appointments)
    df_availability = pd.DataFrame(availability_logs)
    
    # Save raw files
    df_visits.drop(columns=["arrival_min_val"], errors="ignore").to_csv('data/raw/visits.csv', index=False)
    df_appointments.to_csv('data/raw/appointments.csv', index=False)
    df_availability.to_csv('data/raw/availability.csv', index=False)

    # 5. GENERATE REVIEWS
    print("Generating Reviews...")
    reviews = []
    review_id = 1
    
    # Generate reviews based on completed visits (approx 40% of visits get reviewed)
    df_completed_visits = df_visits # all visits in our df are completed
    
    for _, visit in df_completed_visits.sample(frac=0.4, random_state=42).iterrows():
        cust_id = int(visit["customer_id"])
        shop_id = int(visit["shop_id"])
        wait_time = int(visit["waiting_time_minutes"])
        visit_date = datetime.strptime(visit["date"], '%Y-%m-%d')
        
        # Wait time strongly influences rating
        if wait_time == 0:
            wait_rating = round(random.uniform(4.5, 5.0), 1)
        elif wait_time <= 10:
            wait_rating = round(random.uniform(4.0, 4.8), 1)
        elif wait_time <= 25:
            wait_rating = round(random.uniform(3.0, 4.0), 1)
        else: # wait > 25 mins
            wait_rating = round(random.uniform(1.0, 3.0), 1)
            
        cleanliness_rating = round(np.clip(np.random.normal(4.2, 0.6), 1.0, 5.0), 1)
        service_rating = round(np.clip(np.random.normal(4.4, 0.5), 1.0, 5.0), 1)
        
        # Value rating correlates with price - we find shop type to adjust
        shop_info = df_shops[df_shops["shop_id"] == shop_id].iloc[0]
        shop_type = shop_info["shop_type"]
        if shop_type == "Premium":
            value_rating = round(np.clip(np.random.normal(4.3, 0.6), 1.0, 5.0), 1)
        elif shop_type == "Budget":
            value_rating = round(np.clip(np.random.normal(4.1, 0.7), 1.0, 5.0), 1)
        else:
            value_rating = round(np.clip(np.random.normal(4.2, 0.5), 1.0, 5.0), 1)
            
        # Overall rating is a weighted average with some noise
        overall_rating = round((wait_rating * 0.35 + cleanliness_rating * 0.15 + service_rating * 0.3 + value_rating * 0.2), 1)
        overall_rating = np.clip(overall_rating, 1.0, 5.0)
        
        review_date = (visit_date + timedelta(days=random.choice([0, 1]))).strftime('%Y-%m-%d')
        
        reviews.append({
            "review_id": review_id,
            "customer_id": cust_id,
            "shop_id": shop_id,
            "rating": overall_rating,
            "service_rating": service_rating,
            "cleanliness_rating": cleanliness_rating,
            "value_rating": value_rating,
            "waiting_time_rating": wait_rating,
            "review_date": review_date
        })
        review_id += 1
        
    df_reviews = pd.DataFrame(reviews)
    df_reviews.to_csv('data/raw/reviews.csv', index=False)
    
    print("\nData generation complete! Summary of generated records:")
    print(f"Shops: {len(df_shops)}")
    print(f"Services: {len(df_services)}")
    print(f"Customers: {len(df_customers)}")
    print(f"Visits: {len(df_visits)}")
    print(f"Appointments: {len(df_appointments)}")
    print(f"Availability snapshots: {len(df_availability)}")
    print(f"Reviews: {len(df_reviews)}")

    # Move raw datasets to processed initially
    for file in ["shops.csv", "services.csv", "customers.csv", "visits.csv", "appointments.csv", "availability.csv", "reviews.csv"]:
        pd.read_csv(f"data/raw/{file}").to_csv(f"data/processed/{file}", index=False)
    print("Files copied to data/processed/")

def get_hour_probabilities(open_hour, close_hour):
    # Generates a realistic hourly weight distribution for barber shop arrivals
    hours = np.arange(open_hour, close_hour)
    probs = []
    for h in hours:
        if 9 <= h < 11:
            probs.append(0.04)
        elif 11 <= h < 14: # Midday rush
            probs.append(0.18)
        elif 14 <= h < 16:
            probs.append(0.08)
        elif 16 <= h < 19: # Evening rush
            probs.append(0.48)
        elif 19 <= h < 21: # Late closing
            probs.append(0.22)
        else:
            probs.append(0.05)
            
    # Normalize probabilities
    probs = np.array(probs)
    probs = probs[:len(hours)]
    probs = probs / probs.sum()
    return probs

if __name__ == '__main__':
    generate_dataset()
