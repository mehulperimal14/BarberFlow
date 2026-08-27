from fastapi import APIRouter
from app.database import execute_query

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview")
def get_market_overview(area: str = None, shop_id: int = None):
    # Base WHERE clauses
    where_clause_shops = "1=1"
    where_clause_visits = "1=1"
    params = []
    
    if area:
        where_clause_shops += " AND area = ?"
        where_clause_visits += " AND shop_id IN (SELECT shop_id FROM shops WHERE area = ?)"
        params.append(area)
        params.append(area)
    if shop_id:
        where_clause_shops += " AND shop_id = ?"
        where_clause_visits += " AND shop_id = ?"
        params.append(shop_id)
        params.append(shop_id)

    # 1. Total Shops
    shop_count_res = execute_query(f"SELECT COUNT(*) as count FROM shops WHERE {where_clause_shops}", tuple(params[:1] if shop_id or area else []))
    total_shops = shop_count_res[0]["count"] if shop_count_res else 0
    
    # 2. Total Customers
    cust_count_res = execute_query("SELECT COUNT(*) as count FROM customers")
    total_customers = cust_count_res[0]["count"] if cust_count_res else 0
    
    # 3. Total Visits
    visits_count_res = execute_query(f"SELECT COUNT(*) as count FROM visits WHERE {where_clause_visits}", tuple(params[1:] if area else params))
    total_visits = visits_count_res[0]["count"] if visits_count_res else 0
    
    # 4. Average Wait
    avg_wait_res = execute_query(f"SELECT AVG(waiting_time_minutes) as avg_wait FROM visits WHERE {where_clause_visits}", tuple(params[1:] if area else params))
    avg_wait = round(avg_wait_res[0]["avg_wait"], 1) if avg_wait_res and avg_wait_res[0]["avg_wait"] is not None else 0.0
    
    # 5. Average Rating
    avg_rating_res = execute_query(f"SELECT AVG(rating) as avg_r FROM shops WHERE {where_clause_shops}", tuple(params[:1] if shop_id or area else []))
    avg_rating = round(avg_rating_res[0]["avg_r"], 2) if avg_rating_res and avg_rating_res[0]["avg_r"] is not None else 0.0
    
    # 6. Average Utilization
    # Utilization = occupied_seats / total_seats * 100
    util_res = execute_query(f"SELECT AVG(occupied_seats * 100.0 / total_seats) as avg_util FROM availability WHERE {where_clause_visits}", tuple(params[1:] if area else params))
    avg_util = round(util_res[0]["avg_util"], 1) if util_res and util_res[0]["avg_util"] is not None else 0.0
    
    return {
        "total_shops": total_shops,
        "total_customers": total_customers,
        "total_visits": total_visits,
        "average_wait_minutes": avg_wait,
        "average_rating": avg_rating,
        "average_utilization_pct": avg_util
    }

@router.get("/demand")
def get_demand_charts(shop_id: int = None):
    # Demand by hour
    query_hour = """
        SELECT STRFTIME('%H', arrival_time || ':00') AS hour, COUNT(*) AS visits
        FROM visits
        WHERE 1=1
    """
    # Demand by day of week
    query_day = """
        SELECT 
            CASE CAST(STRFTIME('%w', date) AS INTEGER)
                WHEN 0 THEN 'Sun'
                WHEN 1 THEN 'Mon'
                WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed'
                WHEN 4 THEN 'Thu'
                WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
            END AS day_name,
            CAST(STRFTIME('%w', date) AS INTEGER) as day_num,
            COUNT(*) AS visits
        FROM visits
        WHERE 1=1
    """
    params = []
    if shop_id:
        query_hour += " AND shop_id = ?"
        query_day += " AND shop_id = ?"
        params.append(shop_id)

    query_hour += " GROUP BY hour ORDER BY hour ASC"
    query_day += " GROUP BY day_name, day_num ORDER BY day_num ASC"
    
    hour_res = execute_query(query_hour, tuple(params))
    day_res = execute_query(query_day, tuple(params))
    
    # Clean day order mapping
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_map = {d["day_name"]: d["visits"] for d in day_res}
    formatted_day_res = [{"day_name": d, "visits": day_map.get(d, 0)} for d in day_order]
    
    return {
        "demand_by_hour": hour_res,
        "demand_by_day": formatted_day_res
    }

@router.get("/waiting-time")
def get_waiting_time_charts(shop_id: int = None):
    # Wait time by hour
    query_hour = """
        SELECT STRFTIME('%H', arrival_time || ':00') AS hour, AVG(waiting_time_minutes) AS avg_wait
        FROM visits
        WHERE 1=1
    """
    # Wait time distribution (histogram categories)
    query_dist = """
        SELECT 
            CASE 
                WHEN waiting_time_minutes = 0 THEN '0 min'
                WHEN waiting_time_minutes <= 10 THEN '1-10 min'
                WHEN waiting_time_minutes <= 20 THEN '11-20 min'
                WHEN waiting_time_minutes <= 30 THEN '21-30 min'
                ELSE '30+ min'
            END AS wait_tier,
            COUNT(*) AS count
        FROM visits
        WHERE 1=1
    """
    params = []
    if shop_id:
        query_hour += " AND shop_id = ?"
        query_dist += " AND shop_id = ?"
        params.append(shop_id)
        
    query_hour += " GROUP BY hour ORDER BY hour ASC"
    query_dist += " GROUP BY wait_tier"
    
    hour_res = execute_query(query_hour, tuple(params))
    dist_res = execute_query(query_dist, tuple(params))
    
    # Format wait time hour averages
    formatted_hour = [{"hour": h["hour"], "avg_wait": round(h["avg_wait"], 1)} for h in hour_res]
    
    # Sort distribution logically
    tier_order = ["0 min", "1-10 min", "11-20 min", "21-30 min", "30+ min"]
    dist_map = {d["wait_tier"]: d["count"] for d in dist_res}
    formatted_dist = [{"wait_tier": t, "count": dist_map.get(t, 0)} for t in tier_order]
    
    return {
        "wait_by_hour": formatted_hour,
        "wait_distribution": formatted_dist
    }

@router.get("/shop-performance")
def get_shop_performance():
    """
    Returns data for the scatter plot: Demand vs Capacity.
    """
    query = """
        SELECT 
            s.shop_id,
            s.shop_name,
            s.shop_type,
            s.number_of_seats,
            s.rating,
            COUNT(v.visit_id) as total_visits,
            ROUND(AVG(v.waiting_time_minutes), 1) as avg_wait,
            ROUND(AVG(a.occupied_seats * 100.0 / a.total_seats), 1) as avg_utilization
        FROM shops s
        JOIN visits v ON s.shop_id = v.shop_id
        LEFT JOIN availability a ON s.shop_id = a.shop_id
        GROUP BY s.shop_id, s.shop_name, s.shop_type, s.number_of_seats, s.rating
    """
    perf = execute_query(query)
    
    # Define quadrant boundaries dynamically or standard averages
    avg_visits = sum(p["total_visits"] for p in perf) / len(perf) if perf else 100
    avg_seats = sum(p["number_of_seats"] for p in perf) / len(perf) if perf else 4
    
    for p in perf:
        visits = p["total_visits"]
        seats = p["number_of_seats"]
        
        # Categorize into quadrants
        if visits >= avg_visits and seats >= avg_seats:
            p["quadrant"] = "High Demand / High Capacity (Leader)"
        elif visits >= avg_visits and seats < avg_seats:
            p["quadrant"] = "High Demand / Low Capacity (Bottleneck)"
        elif visits < avg_visits and seats >= avg_seats:
            p["quadrant"] = "Low Demand / High Capacity (Underutilized)"
        else:
            p["quadrant"] = "Low Demand / Low Capacity (Low Scale)"
            
    return {
        "shops_data": perf,
        "threshold_visits": round(avg_visits, 0),
        "threshold_seats": round(avg_seats, 1)
    }

@router.get("/location")
def get_location_opportunity():
    """
    Performs Area Opportunity Analysis: Demand vs. Capacity by neighborhood.
    """
    query = """
        SELECT 
            s.area,
            COUNT(DISTINCT s.shop_id) as shop_count,
            SUM(s.number_of_seats) as total_seats,
            COUNT(v.visit_id) as total_visits,
            ROUND(AVG(v.waiting_time_minutes), 1) as avg_wait_minutes,
            ROUND(AVG(s.rating), 2) as avg_rating
        FROM shops s
        LEFT JOIN visits v ON s.shop_id = v.shop_id
        GROUP BY s.area
    """
    areas_data = execute_query(query)
    
    # Calculate ratio and opportunity score
    # Opportunity score is high where visits-per-seat is high
    for area in areas_data:
        seats = area["total_seats"] if area["total_seats"] else 1
        visits = area["total_visits"]
        ratio = round(visits / seats, 1)
        area["visits_per_seat"] = ratio
        
        # Opportunity assessment
        if ratio >= 200: # high visits per seat
            area["status"] = "High Opportunity (Under-served)"
            area["color"] = "🔴 High Demand/Low Capacity"
        elif ratio >= 130:
            area["status"] = "Balanced Market"
            area["color"] = "🟡 Stable"
        else:
            area["status"] = "Over-saturated"
            area["color"] = "🟢 Over-supplied"
            
    return areas_data

@router.get("/shop/{shop_id}")
def get_shop_analytics(shop_id: int):
    # Total revenue and visits
    query_kpis = """
        SELECT 
            COUNT(v.visit_id) as total_visits,
            ROUND(AVG(v.waiting_time_minutes), 1) as avg_wait,
            ROUND(SUM(srv.price), 2) as total_revenue,
            ROUND(AVG(srv.price), 2) as avg_ticket
        FROM visits v
        JOIN services srv ON v.service_id = srv.service_id
        WHERE v.shop_id = ?
    """
    kpis = execute_query(query_kpis, (shop_id,), fetch_all=False)
    
    # Demand by service
    query_services = """
        SELECT srv.service_name, COUNT(v.visit_id) as count, ROUND(SUM(srv.price), 2) as revenue
        FROM visits v
        JOIN services srv ON v.service_id = srv.service_id
        WHERE v.shop_id = ?
        GROUP BY srv.service_name
        ORDER BY count DESC
    """
    services_res = execute_query(query_services, (shop_id,))
    
    # Customer metrics: Repeat client rate
    # A customer is repeat if they have visited >= 3 times in this shop
    query_repeat = """
        WITH ClientVisits AS (
            SELECT customer_id, COUNT(*) as visit_count
            FROM visits
            WHERE shop_id = ?
            GROUP BY customer_id
        )
        SELECT 
            COUNT(*) as total_clients,
            SUM(CASE WHEN visit_count >= 3 THEN 1 ELSE 0 END) as repeat_clients
        FROM ClientVisits
    """
    repeat_res = execute_query(query_repeat, (shop_id,), fetch_all=False)
    repeat_rate = 0.0
    if repeat_res and repeat_res["total_clients"]:
        repeat_rate = round(repeat_res["repeat_clients"] * 100.0 / repeat_res["total_clients"], 1)
        
    # Cancellation & No-Show Rate
    query_appointments = """
        SELECT 
            COUNT(*) as total_app,
            SUM(cancellation_flag) as cancelled,
            SUM(no_show_flag) as no_shows
        FROM appointments
        WHERE shop_id = ?
    """
    app_res = execute_query(query_appointments, (shop_id,), fetch_all=False)
    cancel_rate = 0.0
    noshow_rate = 0.0
    if app_res and app_res["total_app"]:
        cancel_rate = round(app_res["cancelled"] * 100.0 / app_res["total_app"], 1)
        noshow_rate = round(app_res["no_shows"] * 100.0 / app_res["total_app"], 1)
        
    # Generate business recommendations dynamically based on actual metrics
    recommendations = []
    
    # 1. Staffing/Capacity Recommendation
    avg_wait = kpis["avg_wait"] if kpis and kpis["avg_wait"] else 0
    if avg_wait >= 20:
        recommendations.append({
            "type": "⚠️ Capacity Bottleneck",
            "message": f"Average wait time is {avg_wait} minutes. Consider adding temporary staffing or opening an extra chair during peak hours."
        })
    else:
        recommendations.append({
            "type": "✅ Healthy Flow",
            "message": f"Average wait time is {avg_wait} minutes, indicating efficient queue clearance."
        })
        
    # 2. Promotion Recommendation
    # Find low utilization days
    query_low_day = """
        SELECT STRFTIME('%w', date) as day_num, COUNT(*) as count
        FROM visits
        WHERE shop_id = ?
        GROUP BY day_num
        ORDER BY count ASC
        LIMIT 1
    """
    low_day_res = execute_query(query_low_day, (shop_id,), fetch_all=False)
    days_map = {"0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday", "4": "Thursday", "5": "Friday", "6": "Saturday"}
    if low_day_res:
        slow_day_name = days_map.get(low_day_res["day_num"], "weekday")
        recommendations.append({
            "type": "🎯 Slow Day Promotion",
            "message": f"{slow_day_name}s have the lowest customer throughput. Consider running a 15% discount for bookings on {slow_day_name} mornings."
        })
        
    # 3. Revenue optimization recommendation
    if services_res:
        top_service = services_res[0]["service_name"]
        recommendations.append({
            "type": "💰 Service Bundling",
            "message": f"'{top_service}' is your most popular service. Bundle it with a styling wash to increase average ticket sizes."
        })
        
    return {
        "kpis": kpis,
        "services_revenue": services_res,
        "repeat_customer_rate_pct": repeat_rate,
        "appointment_cancellation_rate_pct": cancel_rate,
        "appointment_noshow_rate_pct": noshow_rate,
        "business_recommendations": recommendations
    }
