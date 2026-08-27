from fastapi import APIRouter, HTTPException, Body
from app.database import execute_query, execute_write
from datetime import datetime

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.get("")
def get_appointments(shop_id: int = None, customer_id: int = None):
    query = """
        SELECT a.*, s.shop_name, srv.service_name, srv.price, c.age_group, c.gender
        FROM appointments a
        JOIN shops s ON a.shop_id = s.shop_id
        JOIN services srv ON a.service_id = srv.service_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE 1=1
    """
    params = []
    if shop_id:
        query += " AND a.shop_id = ?"
        params.append(shop_id)
    if customer_id:
        query += " AND a.customer_id = ?"
        params.append(customer_id)
        
    query += " ORDER BY a.appointment_date DESC, a.appointment_time DESC LIMIT 100"
    return execute_query(query, tuple(params))

@router.post("")
def book_appointment(
    customer_id: int = Body(..., embed=True),
    shop_id: int = Body(..., embed=True),
    service_id: int = Body(..., embed=True),
    appointment_date: str = Body(..., embed=True), # YYYY-MM-DD
    appointment_time: str = Body(..., embed=True)  # HH:MM
):
    """
    Books an appointment. 
    Inserts a new record in appointments and returns estimated details.
    """
    # Verify customer, shop, and service
    customer = execute_query("SELECT * FROM customers WHERE customer_id = ?", (customer_id,), fetch_all=False)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    shop = execute_query("SELECT * FROM shops WHERE shop_id = ?", (shop_id,), fetch_all=False)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    service = execute_query("SELECT * FROM services WHERE service_id = ? AND shop_id = ?", (service_id, shop_id), fetch_all=False)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found for this shop")

    # Check if shop is open at that time
    open_h = int(shop["opening_time"].split(":")[0])
    close_h = int(shop["closing_time"].split(":")[0])
    app_h = int(appointment_time.split(":")[0])
    
    if app_h < open_h or app_h >= close_h:
        raise HTTPException(status_code=400, detail=f"Shop is closed. Operating hours are {shop['opening_time']} to {shop['closing_time']}")

    # Insert into appointments
    booking_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
        INSERT INTO appointments (customer_id, shop_id, service_id, appointment_date, appointment_time, booking_time, status, cancellation_flag, no_show_flag)
        VALUES (?, ?, ?, ?, ?, ?, 'Scheduled', 0, 0)
    """
    appointment_id = execute_write(query, (
        customer_id, shop_id, service_id, appointment_date, appointment_time, booking_time_str
    ))
    
    # Calculate queue number (number of existing bookings for that shop-date-time range)
    existing_bookings = execute_query(
        "SELECT COUNT(*) as count FROM appointments WHERE shop_id = ? AND appointment_date = ? AND appointment_time <= ?",
        (shop_id, appointment_date, appointment_time),
        fetch_all=False
    )
    queue_no = existing_bookings["count"] if existing_bookings else 1
    
    return {
        "status": "success",
        "appointment_id": appointment_id,
        "queue_number": queue_no,
        "estimated_wait_minutes": 0, # Scheduled slots have no initial wait time
        "appointment_date": appointment_date,
        "appointment_time": appointment_time
    }
