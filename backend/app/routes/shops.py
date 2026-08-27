from fastapi import APIRouter, HTTPException, Query
from app.database import execute_query
import math

router = APIRouter(prefix="/api/shops", tags=["Shops"])

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    R = 6371.0  # Earth radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.get("")
def get_shops(
    search: str = None,
    area: str = None,
    min_rating: float = None,
    shop_type: str = None,
    user_lat: float = None,
    user_lon: float = None
):
    query = "SELECT * FROM shops WHERE shop_status = 'Active'"
    params = []
    
    if area:
        query += " AND area = ?"
        params.append(area)
    if shop_type:
        query += " AND shop_type = ?"
        params.append(shop_type)
    if min_rating:
        query += " AND rating >= ?"
        params.append(min_rating)
    if search:
        query += " AND (shop_name LIKE ? OR owner_name LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
        
    shops = execute_query(query, tuple(params))
    
    # Calculate distance if user lat/lon is provided
    for shop in shops:
        if user_lat is not None and user_lon is not None:
            dist = haversine_distance(user_lat, user_lon, shop["latitude"], shop["longitude"])
            shop["distance_km"] = round(dist, 2)
        else:
            shop["distance_km"] = round(haversine_distance(40.7128, -74.0060, shop["latitude"], shop["longitude"]), 2)
            
        # Get current availability snapshot for this shop
        # We find the latest snapshot (e.g. from availability)
        avail = execute_query(
            "SELECT * FROM availability WHERE shop_id = ? ORDER BY timestamp DESC LIMIT 1",
            (shop["shop_id"],),
            fetch_all=False
        )
        if avail:
            shop["occupied_seats"] = avail["occupied_seats"]
            shop["available_seats"] = avail["available_seats"]
            shop["queue_length"] = avail["queue_length"]
            shop["estimated_wait_minutes"] = avail["estimated_wait_minutes"]
        else:
            # Fallbacks
            shop["occupied_seats"] = 0
            shop["available_seats"] = shop["number_of_seats"]
            shop["queue_length"] = 0
            shop["estimated_wait_minutes"] = 0
            
    return shops

@router.get("/recommendations")
def get_recommendations(
    user_lat: float = 40.7128,
    user_lon: float = -74.0060,
    weight_rating: float = 0.3,
    weight_wait: float = 0.3,
    weight_distance: float = 0.2,
    weight_price: float = 0.2
):
    """
    Transparent weighted recommendation system.
    Ranks shops based on a configurable mix of Rating, Wait Time, Distance, and Price.
    """
    shops = get_shops(user_lat=user_lat, user_lon=user_lon)
    if not shops:
        return []
        
    # Find min/max values to normalize features between 0 and 1
    max_rating = max(s["rating"] for s in shops)
    min_rating = min(s["rating"] for s in shops)
    max_wait = max(s["estimated_wait_minutes"] for s in shops)
    min_wait = min(s["estimated_wait_minutes"] for s in shops)
    max_dist = max(s["distance_km"] for s in shops)
    min_dist = min(s["distance_km"] for s in shops)
    
    # Prices
    shop_avg_prices = {}
    for s in shops:
        srvs = execute_query("SELECT AVG(price) as avg_p FROM services WHERE shop_id = ?", (s["shop_id"],), fetch_all=False)
        shop_avg_prices[s["shop_id"]] = srvs["avg_p"] if srvs and srvs["avg_p"] else 20.0
        
    max_price = max(shop_avg_prices.values())
    min_price = min(shop_avg_prices.values())
    
    scored_shops = []
    for s in shops:
        s_id = s["shop_id"]
        price = shop_avg_prices[s_id]
        
        # Normalize: higher is better
        norm_rating = (s["rating"] - min_rating) / (max_rating - min_rating + 1e-5)
        norm_wait = 1 - ((s["estimated_wait_minutes"] - min_wait) / (max_wait - min_wait + 1e-5))
        norm_dist = 1 - ((s["distance_km"] - min_dist) / (max_dist - min_dist + 1e-5))
        norm_price = 1 - ((price - min_price) / (max_price - min_price + 1e-5))
        
        score = (
            weight_rating * norm_rating +
            weight_wait * norm_wait +
            weight_distance * norm_dist +
            weight_price * norm_price
        )
        
        # Reasons list
        reasons = []
        if s["rating"] >= 4.5:
            reasons.append("⭐ Highly Rated")
        if s["estimated_wait_minutes"] <= 10:
            reasons.append("🟢 Short Wait")
        if s["distance_km"] <= 1.5:
            reasons.append("📍 Very Close")
        if price <= min_price * 1.3:
            reasons.append("💰 Budget Friendly")
        if not reasons:
            reasons.append("👍 Good overall balance")
            
        scored_shops.append({
            **s,
            "recommendation_score": round(score * 100, 1),
            "average_price": round(price, 2),
            "reasons": reasons[:2] # return top 2 reasons
        })
        
    # Sort by score descending
    scored_shops = sorted(scored_shops, key=lambda x: x["recommendation_score"], reverse=True)
    return scored_shops

@router.get("/{shop_id}")
def get_shop_detail(shop_id: int):
    shop = execute_query("SELECT * FROM shops WHERE shop_id = ?", (shop_id,), fetch_all=False)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
        
    services = execute_query("SELECT * FROM services WHERE shop_id = ?", (shop_id,))
    reviews = execute_query(
        "SELECT r.*, c.gender, c.age_group FROM reviews r JOIN customers c ON r.customer_id = c.customer_id WHERE r.shop_id = ? ORDER BY r.review_date DESC LIMIT 5",
        (shop_id,)
    )
    
    # Current availability
    avail = execute_query(
        "SELECT * FROM availability WHERE shop_id = ? ORDER BY timestamp DESC LIMIT 1",
        (shop_id,),
        fetch_all=False
    )
    
    result = dict(shop)
    result["services"] = services
    result["reviews"] = reviews
    if avail:
        result["occupied_seats"] = avail["occupied_seats"]
        result["available_seats"] = avail["available_seats"]
        result["queue_length"] = avail["queue_length"]
        result["estimated_wait_minutes"] = avail["estimated_wait_minutes"]
    else:
        result["occupied_seats"] = 0
        result["available_seats"] = shop["number_of_seats"]
        result["queue_length"] = 0
        result["estimated_wait_minutes"] = 0
        
    return result
