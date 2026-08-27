from fastapi import APIRouter, HTTPException, Body
from app.database import execute_query, execute_write
from datetime import datetime

router = APIRouter(prefix="/api/queue", tags=["Queue"])

@router.get("/{shop_id}")
def get_shop_queue(shop_id: int):
    """
    Returns the queue for a shop on the most recent day in the database (simulating 'Today').
    """
    # Find latest date in visits
    latest_date_row = execute_query("SELECT MAX(date) as max_date FROM visits", fetch_all=False)
    latest_date = latest_date_row["max_date"] if latest_date_row and latest_date_row["max_date"] else "2026-08-30"
    
    # Fetch visits for this shop-date
    query = """
        SELECT v.*, c.age_group, c.gender, s.service_name, s.price
        FROM visits v
        JOIN customers c ON v.customer_id = c.customer_id
        JOIN services s ON v.service_id = s.service_id
        WHERE v.shop_id = ? AND v.date = ?
        ORDER BY v.arrival_time ASC
    """
    visits = execute_query(query, (shop_id, latest_date))
    
    # Categorize status based on wait time and order
    # To simulate real-time, we can determine active customers.
    # In a real app we'd compare to current time. In our portfolio dashboard, we'll return the list of visits
    # and mark them:
    # - Completed: if wait time is set and duration is completed
    # - In Service: first few visits that are not marked completed, or we can use a status flag.
    # Let's add a dynamic status field for display based on their order in queue:
    # E.g. the first 2-3 visits are "In Service" (based on shop seat capacity), subsequent ones are "Waiting", and past ones are "Completed".
    shop_info = execute_query("SELECT number_of_seats, number_of_barbers FROM shops WHERE shop_id = ?", (shop_id,), fetch_all=False)
    barbers = shop_info["number_of_barbers"] if shop_info else 3
    
    # We can assign status dynamically:
    # Let's say if arrival time is early, it is "Completed".
    # Let's sort visits by arrival_time
    for i, v in enumerate(visits):
        # Let's simulate status for display purposes:
        if i < 4:
            v["status"] = "Completed"
        elif i < 4 + barbers:
            v["status"] = "In Service"
        else:
            v["status"] = "Waiting"
            
    return visits

@router.post("/{shop_id}/join")
def join_queue(
    shop_id: int,
    customer_id: int = Body(..., embed=True),
    service_id: int = Body(..., embed=True)
):
    """
    Allows a customer to join the walk-in queue.
    Inserts a new visit record for the latest simulated date.
    """
    # Verify customer and service
    customer = execute_query("SELECT * FROM customers WHERE customer_id = ?", (customer_id,), fetch_all=False)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    service = execute_query("SELECT * FROM services WHERE service_id = ? AND shop_id = ?", (service_id, shop_id), fetch_all=False)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found for this shop")
        
    # Get current wait time estimation
    avail = execute_query(
        "SELECT queue_length, estimated_wait_minutes, occupied_seats, total_seats FROM availability WHERE shop_id = ? ORDER BY timestamp DESC LIMIT 1",
        (shop_id,),
        fetch_all=False
    )
    
    wait_time = avail["estimated_wait_minutes"] if avail else 15
    queue_len = avail["queue_length"] if avail else 0
    occupied = avail["occupied_seats"] if avail else 0
    total_seats = avail["total_seats"] if avail else 3
    
    # Get latest date in database
    latest_date_row = execute_query("SELECT MAX(date) as max_date FROM visits", fetch_all=False)
    latest_date = latest_date_row["max_date"] if latest_date_row and latest_date_row["max_date"] else "2026-08-30"
    
    # Calculate arrival time as latest visit arrival time + 15 minutes, or just 12:00
    last_visit = execute_query(
        "SELECT arrival_time FROM visits WHERE shop_id = ? AND date = ? ORDER BY arrival_time DESC LIMIT 1",
        (shop_id, latest_date),
        fetch_all=False
    )
    if last_visit:
        last_h, last_m = map(int, last_visit["arrival_time"].split(":"))
        new_m = last_m + 15
        new_h = last_h + (new_m // 60)
        new_m = new_m % 60
        arrival_time_str = f"{min(new_h, 21):02d}:{new_m:02d}"
    else:
        arrival_time_str = "10:00"
        
    duration = service["average_duration_minutes"]
    
    # Calculate service start and end
    start_h, start_m = map(int, arrival_time_str.split(":"))
    start_m += wait_time
    start_h += (start_m // 60)
    start_m = start_m % 60
    start_time_str = f"{min(start_h, 21):02d}:{start_m:02d}"
    
    end_m = start_m + duration
    end_h = start_h + (end_m // 60)
    end_m = end_m % 60
    end_time_str = f"{min(end_h, 21):02d}:{end_m:02d}"
    
    # Insert new visit
    query = """
        INSERT INTO visits (customer_id, shop_id, service_id, date, arrival_time, service_start_time, service_end_time, waiting_time_minutes, service_duration_minutes, seat_id, visit_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Walk-in')
    """
    visit_id = execute_write(query, (
        customer_id, shop_id, service_id, latest_date, 
        arrival_time_str, start_time_str, end_time_str, 
        wait_time, duration, (occupied % total_seats) + 1
    ))
    
    # Update availability snapshot log
    timestamp_str = f"{latest_date} {datetime.now().strftime('%H:%M:%S')}"
    new_occupied = min(occupied + 1, total_seats)
    new_queue = queue_len + 1
    new_wait = wait_time + 15 # simple add wait
    
    execute_write("""
        INSERT OR REPLACE INTO availability (timestamp, shop_id, total_seats, occupied_seats, available_seats, queue_length, estimated_wait_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp_str, shop_id, total_seats, new_occupied, total_seats - new_occupied, new_queue, new_wait))
    
    return {
        "status": "success",
        "visit_id": visit_id,
        "queue_number": new_queue + new_occupied,
        "estimated_wait_minutes": wait_time,
        "arrival_time": arrival_time_str,
        "estimated_start_time": start_time_str
    }

@router.delete("/{visit_id}/skip")
def skip_visit(visit_id: int):
    """
    Barber skips or cancels a customer in the queue.
    """
    visit = execute_query("SELECT * FROM visits WHERE visit_id = ?", (visit_id,), fetch_all=False)
    if not visit:
        raise HTTPException(status_code=404, detail="Queue record not found")
        
    execute_write("DELETE FROM visits WHERE visit_id = ?", (visit_id,))
    return {"status": "success", "message": f"Visit {visit_id} removed from queue"}
