const API_BASE = "http://127.0.0.1:8000/api";

export async function fetchShops(filters = {}) {
  const params = new URLSearchParams();
  if (filters.search) params.append("search", filters.search);
  if (filters.area) params.append("area", filters.area);
  if (filters.min_rating) params.append("min_rating", filters.min_rating);
  if (filters.shop_type) params.append("shop_type", filters.shop_type);
  if (filters.user_lat) params.append("user_lat", filters.user_lat);
  if (filters.user_lon) params.append("user_lon", filters.user_lon);
  
  const res = await fetch(`${API_BASE}/shops?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch shops");
  return res.json();
}

export async function fetchShopDetail(shopId) {
  const res = await fetch(`${API_BASE}/shops/${shopId}`);
  if (!res.ok) throw new Error("Failed to fetch shop details");
  return res.json();
}

export async function fetchRecommendations(weights = {}) {
  const params = new URLSearchParams();
  if (weights.weight_rating !== undefined) params.append("weight_rating", weights.weight_rating);
  if (weights.weight_wait !== undefined) params.append("weight_wait", weights.weight_wait);
  if (weights.weight_distance !== undefined) params.append("weight_distance", weights.weight_distance);
  if (weights.weight_price !== undefined) params.append("weight_price", weights.weight_price);
  
  const res = await fetch(`${API_BASE}/shops/recommendations?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch recommendations");
  return res.json();
}

export async function fetchQueue(shopId) {
  const res = await fetch(`${API_BASE}/queue/${shopId}`);
  if (!res.ok) throw new Error("Failed to fetch queue");
  return res.json();
}

export async function joinQueue(shopId, customerId, serviceId) {
  const res = await fetch(`${API_BASE}/queue/${shopId}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer_id: customerId, service_id: serviceId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to join queue");
  }
  return res.json();
}

export async function skipQueue(visitId) {
  const res = await fetch(`${API_BASE}/queue/${visitId}/skip`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to skip queue record");
  return res.json();
}

export async function fetchAppointments(filters = {}) {
  const params = new URLSearchParams();
  if (filters.shop_id) params.append("shop_id", filters.shop_id);
  if (filters.customer_id) params.append("customer_id", filters.customer_id);
  
  const res = await fetch(`${API_BASE}/appointments?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch appointments");
  return res.json();
}

export async function bookAppointment(customerId, shopId, serviceId, date, time) {
  const res = await fetch(`${API_BASE}/appointments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_id: customerId,
      shop_id: shopId,
      service_id: serviceId,
      appointment_date: date,
      appointment_time: time
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to book appointment");
  }
  return res.json();
}

export async function fetchMarketOverview(area = "", shopId = "") {
  const params = new URLSearchParams();
  if (area) params.append("area", area);
  if (shopId) params.append("shop_id", shopId);
  const res = await fetch(`${API_BASE}/analytics/overview?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch market overview");
  return res.json();
}

export async function fetchDemandCharts(shopId = "") {
  const params = new URLSearchParams();
  if (shopId) params.append("shop_id", shopId);
  const res = await fetch(`${API_BASE}/analytics/demand?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch demand analytics");
  return res.json();
}

export async function fetchWaitingTimeCharts(shopId = "") {
  const params = new URLSearchParams();
  if (shopId) params.append("shop_id", shopId);
  const res = await fetch(`${API_BASE}/analytics/waiting-time?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch wait time analytics");
  return res.json();
}

export async function fetchShopPerformance() {
  const res = await fetch(`${API_BASE}/analytics/shop-performance`);
  if (!res.ok) throw new Error("Failed to fetch shop performance");
  return res.json();
}

export async function fetchLocationOpportunity() {
  const res = await fetch(`${API_BASE}/analytics/location`);
  if (!res.ok) throw new Error("Failed to fetch location analytics");
  return res.json();
}

export async function fetchShopAnalytics(shopId) {
  const res = await fetch(`${API_BASE}/analytics/shop/${shopId}`);
  if (!res.ok) throw new Error("Failed to fetch shop specific analytics");
  return res.json();
}

export async function predictDemand(shopId, hour, dayOfWeek, month) {
  const res = await fetch(`${API_BASE}/predictions/demand`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      shop_id: shopId,
      hour: parseInt(hour),
      day_of_week: parseInt(dayOfWeek),
      month: parseInt(month)
    }),
  });
  if (!res.ok) throw new Error("Failed to predict demand");
  return res.json();
}

export async function predictWaitTime(shopId, queueLen, occupied, avail, hour, day) {
  const res = await fetch(`${API_BASE}/predictions/waiting-time`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      shop_id: shopId,
      queue_length: parseInt(queueLen),
      occupied_seats: parseInt(occupied),
      available_seats: parseInt(avail),
      hour: parseInt(hour),
      day_of_week: parseInt(day)
    }),
  });
  if (!res.ok) throw new Error("Failed to predict waiting time");
  return res.json();
}

export async function predictNoShow(customerId, hour, lagDays) {
  const res = await fetch(`${API_BASE}/predictions/no-show`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_id: customerId,
      hour: parseInt(hour),
      booking_lag_days: parseFloat(lagDays)
    }),
  });
  if (!res.ok) throw new Error("Failed to predict no-show probability");
  return res.json();
}
