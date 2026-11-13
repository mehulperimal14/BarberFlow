// Same-origin "/api" in production (Vercel serves the SPA and the FastAPI function together).
// In development Vite proxies /api to http://127.0.0.1:8000 (see vite.config.js).
// VITE_API_BASE_URL can point the UI at a separately hosted backend if ever needed.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(body, status) {
  const detail = body && body.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI/Pydantic validation errors (HTTP 422)
    return detail.map(d => `${(d.loc || []).slice(1).join('.') || 'input'}: ${d.msg}`).join('; ');
  }
  return `Request failed (HTTP ${status})`;
}

async function request(path, { method = 'GET', body, params, signal } = {}) {
  const qs = params
    ? '?' + new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
      ).toString()
    : '';
  let res;
  try {
    res = await fetch(`${API_BASE}${path}${qs === '?' ? '' : qs}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the BarberFlow API. Is the backend running?', 0);
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) throw new ApiError(errorMessage(data, res.status), res.status);
  return data;
}

// Meta
export const fetchMeta = () => request('/meta');
export const fetchModelCard = () => request('/predictions/model-card');

// Shops & discovery
export const fetchShops = (filters = {}) => request('/shops', { params: filters });
export const fetchShopDetail = (shopId) => request(`/shops/${shopId}`);
export const fetchRecommendations = (weights = {}) => request('/shops/recommendations', { params: weights });

// Live queue
export const fetchQueue = (shopId) => request(`/queue/${shopId}`);
export const fetchSimulatedDay = (shopId) => request(`/queue/${shopId}/history`);
export const joinQueue = (shopId, customerId, serviceId, source = 'customer_app') =>
  request(`/queue/${shopId}/join`, { method: 'POST', body: { customer_id: customerId, service_id: serviceId, source } });
export const updateQueueEntry = (entryId, action) =>
  request(`/queue/entries/${entryId}`, { method: 'PATCH', body: { action } });

// Appointments
export const bookAppointment = (customerId, shopId, serviceId, date, time) =>
  request('/appointments', {
    method: 'POST',
    body: { customer_id: customerId, shop_id: shopId, service_id: serviceId, appointment_date: date, appointment_time: time },
  });
export const fetchLiveBookings = (shopId) => request('/bookings', { params: { shop_id: shopId } });

// Analytics
export const fetchMarketOverview = (area = '', shopId = '') =>
  request('/analytics/overview', { params: { area, shop_id: shopId } });
export const fetchDemandCharts = (shopId = '', area = '') =>
  request('/analytics/demand', { params: { shop_id: shopId, area } });
export const fetchWaitingTimeCharts = (shopId = '', area = '') =>
  request('/analytics/waiting-time', { params: { shop_id: shopId, area } });
export const fetchSatisfaction = (area = '') => request('/analytics/satisfaction', { params: { area } });
export const fetchShopPerformance = () => request('/analytics/shop-performance');
export const fetchLocationOpportunity = () => request('/analytics/location');
export const fetchShopAnalytics = (shopId) => request(`/analytics/shop/${shopId}`);

// Predictions
export const predictDemand = (shopId, hour, dayOfWeek) =>
  request('/predictions/demand', { method: 'POST', body: { shop_id: +shopId, hour: +hour, day_of_week: +dayOfWeek } });
export const predictWaitTime = (shopId, queueLen, occupied, hour, day) =>
  request('/predictions/waiting-time', {
    method: 'POST',
    body: { shop_id: +shopId, queue_length: +queueLen, occupied_seats: +occupied, hour: +hour, day_of_week: +day },
  });
export const predictNoShow = (customerId, hour, lagDays) =>
  request('/predictions/no-show', {
    method: 'POST',
    body: { customer_id: +customerId, hour: +hour, booking_lag_days: +lagDays },
  });

// Data explorer
export const fetchTable = (table, limit = 25, offset = 0) =>
  request(`/explorer/${table}`, { params: { limit, offset } });
