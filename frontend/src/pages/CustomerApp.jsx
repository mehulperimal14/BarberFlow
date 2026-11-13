import React, { useEffect, useMemo, useState } from 'react';
import {
  fetchShops, fetchRecommendations, fetchShopDetail, joinQueue, bookAppointment,
  fetchWaitingTimeCharts, fetchDemandCharts,
} from '../services/api';
import { Search, Star, Clock, MapPin, Compass, CheckCircle2, ChevronRight, Calendar, X, UserRound } from 'lucide-react';
import { ResponsiveContainer, ComposedChart, Bar, Area, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import { AREAS, Loading, Notice, buttonGold, hourLabel, selectClass, tooltipStyle } from '../components/ui';

const CUSTOMER_KEY = 'barberflow.demoCustomer';
const readCustomer = () => {
  try { return parseInt(localStorage.getItem(CUSTOMER_KEY), 10) || 125; } catch { return 125; }
};

function waitOf(shop) {
  return shop.live_queue_enabled ? shop.estimated_wait_minutes : shop.typical_wait_minutes;
}

function StatusBadge({ shop }) {
  const wait = waitOf(shop) ?? 0;
  const label = shop.live_queue_enabled ? 'now' : 'typical';
  const cls = wait <= 5 ? 'bg-emerald-900/40 text-emerald-400 border-emerald-800'
    : wait <= 15 ? 'bg-yellow-950/40 text-yellow-500 border-yellow-800'
    : wait <= 30 ? 'bg-orange-950/40 text-orange-400 border-orange-800'
    : 'bg-red-950/40 text-red-400 border-red-800';
  const text = wait <= 5 ? 'Short wait' : wait <= 15 ? 'Some wait' : wait <= 30 ? 'Busy' : 'Long wait';
  return (
    <span className={`border text-[11px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${cls}`}
          title={`${Math.round(wait)} min (${label})`}>
      {text} · {Math.round(wait)}m
    </span>
  );
}

function timeSlots(shop, service) {
  if (!shop) return [];
  const open = parseInt(shop.opening_time, 10) * 60;
  const close = parseInt(shop.closing_time, 10) * 60;
  const duration = service?.average_duration_minutes || 30;
  const slots = [];
  for (let m = open; m + duration <= close; m += 30) {
    slots.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`);
  }
  return slots;
}

const isoDate = (d) => d.toISOString().slice(0, 10);

export default function CustomerApp() {
  const [tab, setTab] = useState('search');
  const [filters, setFilters] = useState({ search: '', area: '', shop_type: '', min_rating: '' });
  const [shops, setShops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [weights, setWeights] = useState({ weight_rating: 30, weight_wait: 30, weight_distance: 20, weight_price: 20 });
  const [recs, setRecs] = useState([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [customerId, setCustomerId] = useState(readCustomer);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await fetchShops({ ...filters, min_rating: filters.min_rating || undefined });
        setShops(data);
        setError('');
      } catch (err) {
        if (err.name !== 'AbortError') setError(err.message);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [filters]);

  useEffect(() => {
    if (tab !== 'recommend') return;
    const t = setTimeout(async () => {
      setRecsLoading(true);
      try {
        const w = Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / 100]));
        setRecs(await fetchRecommendations(w));
        setError('');
      } catch (err) {
        setError(err.message);
      } finally {
        setRecsLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [tab, weights]);

  const saveCustomer = (v) => {
    const n = Math.max(1, Math.min(5000, parseInt(v, 10) || 1));
    setCustomerId(n);
    try { localStorage.setItem(CUSTOMER_KEY, String(n)); } catch { /* storage unavailable */ }
  };

  return (
    <div className="space-y-6">
      <div className="text-center py-4 sm:py-6 border-b border-brand-800">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-2">
          Find a barber. <span className="text-accent-gold">Skip the wait.</span>
        </h1>
        <p className="text-gray-400 text-sm sm:text-lg max-w-xl mx-auto">
          Compare shops by rating, distance, price and waiting time, then join the virtual queue or book a slot.
        </p>
        <div className="mt-4 inline-flex items-center gap-2 text-xs text-gray-400 bg-brand-850/60 border border-brand-800 rounded-lg px-3 py-1.5">
          <UserRound size={14} className="text-accent-gold" />
          <label htmlFor="demo-customer">Acting as demo customer #</label>
          <input id="demo-customer" type="number" min={1} max={5000} value={customerId}
                 onChange={(e) => saveCustomer(e.target.value)}
                 className="w-20 bg-brand-900 border border-brand-700 rounded px-2 py-0.5 text-white" />
          <span className="hidden sm:inline text-gray-500">(simulated customers 1–5000)</span>
        </div>
      </div>

      <div className="flex border-b border-brand-850" role="tablist">
        {[['search', 'Search & Filter', Search], ['recommend', 'Explainable Matches', Compass]].map(([id, label, Icon]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 sm:px-5 py-3 border-b-2 font-medium text-sm transition-all ${tab === id ? 'border-accent-gold text-accent-gold' : 'border-transparent text-gray-400 hover:text-gray-200'}`}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      {tab === 'search' && (
        <div className="space-y-6">
          <div className="glass-card p-4 rounded-xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
              <input type="text" placeholder="Search by shop name…" value={filters.search} aria-label="Search shops"
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="w-full pl-9 pr-3 py-2 bg-brand-800/80 border border-brand-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-accent-gold" />
            </div>
            <select aria-label="Area" value={filters.area} onChange={(e) => setFilters({ ...filters, area: e.target.value })} className={selectClass}>
              <option value="">All neighborhoods</option>
              {AREAS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <select aria-label="Shop type" value={filters.shop_type} onChange={(e) => setFilters({ ...filters, shop_type: e.target.value })} className={selectClass}>
              <option value="">All classes</option>
              <option value="Premium">Premium</option>
              <option value="Standard">Standard</option>
              <option value="Budget">Budget friendly</option>
              <option value="Bottleneck">Bottleneck (small capacity)</option>
            </select>
            <select aria-label="Minimum rating" value={filters.min_rating} onChange={(e) => setFilters({ ...filters, min_rating: e.target.value })} className={selectClass}>
              <option value="">Any rating</option>
              <option value="4">4.0★ and up</option>
              <option value="4.5">4.5★ and up</option>
            </select>
          </div>

          {loading ? <Loading label="Loading shops…" /> : shops.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No shops match these filters.</div>
          ) : (
            <>
              <p className="text-xs text-gray-500">
                {shops.length} shops · distance measured from the city centre ·{' '}
                {shops[0]?.live_queue_enabled ? 'wait = live ML estimate from the current queue' : 'wait = typical wait at this hour (history)'}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                {shops.map(shop => (
                  <button key={shop.shop_id} onClick={() => setSelected(shop.shop_id)}
                    className="text-left glass-card rounded-xl p-5 hover:border-accent-gold/40 hover:-translate-y-0.5 transition-all flex flex-col justify-between gap-4">
                    <div>
                      <div className="flex justify-between items-start gap-2 mb-2">
                        <h3 className="text-lg font-bold text-white leading-tight">{shop.shop_name}</h3>
                        <StatusBadge shop={shop} />
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 text-xs text-gray-400 mb-3">
                        <span className="flex items-center gap-0.5 text-accent-gold font-medium"><Star size={13} className="fill-accent-gold" /> {shop.rating}</span>
                        <span>•</span><span>{shop.review_count} reviews</span><span>•</span><span>{shop.shop_type}</span>
                      </div>
                      <div className="space-y-1.5 text-sm text-gray-400">
                        <div className="flex items-center gap-1.5"><MapPin size={15} className="text-accent-gold shrink-0" />{shop.area} · {shop.distance_km} km</div>
                        <div className="flex items-center gap-1.5"><Clock size={15} className="text-accent-gold shrink-0" />{shop.opening_time}–{shop.closing_time} · from ${shop.min_price?.toFixed(0)}</div>
                      </div>
                    </div>
                    <div className="pt-3 border-t border-brand-850 flex items-center justify-between text-xs">
                      <span className="text-gray-400">
                        {shop.live_queue_enabled
                          ? <><b className="text-white">{shop.waiting}</b> waiting · <b className="text-white">{shop.in_service}</b> in chair</>
                          : <>Typical wait now: <b className="text-white">{Math.round(shop.typical_wait_minutes ?? 0)} min</b></>}
                      </span>
                      <span className="text-accent-gold font-semibold flex items-center">Join / Book <ChevronRight size={15} /></span>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'recommend' && (
        <div className="space-y-6">
          <div className="glass-card rounded-xl p-5 space-y-4">
            <div>
              <h3 className="text-lg font-bold text-accent-gold mb-1">Explainable recommendation score</h3>
              <p className="text-sm text-gray-400">
                No black box: each shop gets a 0–100 score from four normalised factors. Move the sliders to change what matters to you.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[['weight_rating', 'Rating'], ['weight_wait', 'Short wait'], ['weight_distance', 'Proximity'], ['weight_price', 'Low price']].map(([k, label]) => (
                <label key={k} className="text-xs text-gray-400 space-y-1">
                  <span className="flex justify-between"><span>{label}</span><b className="text-white">{weights[k]}</b></span>
                  <input type="range" min={0} max={100} step={5} value={weights[k]}
                    onChange={(e) => setWeights({ ...weights, [k]: +e.target.value })} className="w-full accent-[#C5A880]" />
                </label>
              ))}
            </div>
          </div>
          {recsLoading && recs.length === 0 ? <Loading label="Scoring shops…" /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              {recs.slice(0, 6).map((shop, idx) => (
                <button key={shop.shop_id} onClick={() => setSelected(shop.shop_id)}
                  className="text-left glass-card rounded-xl p-5 relative hover:border-accent-gold/45 transition-all">
                  <div className="absolute top-0 right-0 bg-accent-gold text-brand-900 text-xs font-bold px-3 py-1 rounded-tr-xl rounded-bl-xl">
                    #{idx + 1} · {shop.recommendation_score}
                  </div>
                  <h3 className="text-xl font-extrabold text-white mb-1.5 pr-20">{shop.shop_name}</h3>
                  <div className="flex flex-wrap items-center gap-2 text-xs mb-3 text-gray-400">
                    <span className="flex items-center text-accent-gold font-bold"><Star size={13} className="fill-accent-gold mr-0.5" /> {shop.rating}</span>
                    <span>•</span><span>{shop.distance_km} km</span><span>•</span><span>avg ${shop.average_price}</span>
                    <span>•</span><span>wait {Math.round(shop.wait_used_minutes)} min</span>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {shop.reasons.map(r => (
                      <span key={r} className="bg-brand-800/80 text-accent-gold text-xs px-2.5 py-1 rounded-md border border-brand-700 font-semibold">{r}</span>
                    ))}
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-[10px] text-gray-500">
                    {Object.entries(shop.score_breakdown).map(([k, v]) => (
                      <div key={k}>
                        <div className="h-1.5 bg-brand-800 rounded"><div className="h-1.5 bg-accent-gold rounded" style={{ width: `${v}%` }} /></div>
                        <span className="capitalize">{k} {Math.round(v)}</span>
                      </div>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {selected && <ShopModal shopId={selected} customerId={customerId} onClose={() => setSelected(null)} />}
    </div>
  );
}

function ShopModal({ shopId, customerId, onClose }) {
  const [shop, setShop] = useState(null);
  const [chart, setChart] = useState([]);
  const [service, setService] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState(null);
  const tomorrow = useMemo(() => { const d = new Date(); d.setDate(d.getDate() + 1); return isoDate(d); }, []);
  const maxDate = useMemo(() => { const d = new Date(); d.setDate(d.getDate() + 60); return isoDate(d); }, []);
  const [date, setDate] = useState(tomorrow);
  const [time, setTime] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [detail, wait, demand] = await Promise.all([
          fetchShopDetail(shopId), fetchWaitingTimeCharts(shopId), fetchDemandCharts(shopId),
        ]);
        if (!alive) return;
        setShop(detail);
        const byHourWait = Object.fromEntries(wait.wait_by_hour.map(w => [parseInt(w.hour, 10), w.avg_wait]));
        const byHourDemand = Object.fromEntries(demand.demand_by_hour.map(d => [parseInt(d.hour, 10), d.visits]));
        const days = 91;
        setChart(Array.from({ length: 13 }, (_, i) => i + 8).map(h => ({
          time: hourLabel(h),
          wait: byHourWait[h] ?? 0,
          visits: byHourDemand[h] ? +(byHourDemand[h] / days).toFixed(2) : 0,
        })));
      } catch (err) {
        if (alive) setError(err.message);
      }
    })();
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => { alive = false; window.removeEventListener('keydown', onKey); };
  }, [shopId, onClose]);

  const slots = timeSlots(shop, service);
  useEffect(() => { if (slots.length && !slots.includes(time)) setTime(slots[Math.min(4, slots.length - 1)]); }, [slots, time]);

  const run = async (fn) => {
    setBusy(true); setError('');
    try { setConfirmation(await fn()); } catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  const handleJoin = () => run(async () => ({ type: 'queue', ...(await joinQueue(shop.shop_id, customerId, service.service_id)) }));
  const handleBook = () => run(async () => ({ type: 'booking', ...(await bookAppointment(customerId, shop.shop_id, service.service_id, date, time)) }));
  const liveEnabled = shop?.live_queue_enabled;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-start sm:items-center justify-center p-2 sm:p-4 overflow-y-auto"
         role="dialog" aria-modal="true" aria-label={shop?.shop_name || 'Shop details'} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="glass-card bg-brand-900 w-full max-w-4xl rounded-2xl p-4 sm:p-8 space-y-6 relative my-4">
        <button onClick={onClose} aria-label="Close" className="absolute top-3 right-3 text-gray-400 hover:text-white p-2"><X size={20} /></button>
        {!shop ? (error ? <Notice tone="error">{error}</Notice> : <Loading label="Loading shop…" />) : confirmation ? (
          <div className="text-center py-6 space-y-4 max-w-md mx-auto">
            <CheckCircle2 size={56} className="text-emerald-400 mx-auto" />
            <h3 className="text-2xl font-bold text-white">{confirmation.type === 'queue' ? "You're in the queue!" : 'Appointment booked!'}</h3>
            <div className="bg-brand-800/80 border border-brand-700 p-5 rounded-xl text-left space-y-2 text-sm">
              <Row k="Shop" v={confirmation.shop_name} />
              <Row k="Service" v={`${confirmation.service_name} ($${confirmation.price})`} />
              {confirmation.type === 'queue' ? (
                <>
                  <Row k="Ticket" v={`#${confirmation.entry_id}`} gold />
                  <Row k="Position" v={`${confirmation.position} (${confirmation.people_ahead} ahead)`} />
                  <Row k="Estimated wait" v={`${confirmation.estimated_wait_minutes} min (ML estimate)`} />
                </>
              ) : (
                <>
                  <Row k="Booking" v={`#${confirmation.booking_id}`} gold />
                  <Row k="Slot" v={`${confirmation.appointment_date} at ${confirmation.appointment_time}`} />
                  <Row k="Barbers booked in slot" v={`${confirmation.barbers_booked_in_slot} of ${confirmation.slot_capacity}`} />
                </>
              )}
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <a href={`#/barber/${shop.shop_id}`} onClick={onClose} className="flex-1 border border-brand-700 text-white font-bold py-2 rounded-lg hover:bg-brand-800 text-sm">
                See it in the Barber Panel
              </a>
              <button onClick={onClose} className={`flex-1 py-2 text-sm ${buttonGold}`}>Done</button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
            <div className="space-y-5 min-w-0">
              <div>
                <h2 className="text-2xl font-extrabold text-white mb-1 pr-8">{shop.shop_name}</h2>
                <p className="text-sm text-gray-400">{shop.area}, {shop.city} · {shop.opening_time}–{shop.closing_time} · {shop.number_of_barbers} barber(s), {shop.number_of_seats} seats</p>
                <div className="flex flex-wrap items-center gap-1.5 text-xs text-gray-400 mt-2">
                  <span className="flex items-center text-accent-gold font-bold"><Star size={13} className="fill-accent-gold mr-0.5" />{shop.rating}</span>
                  <span>listed · reviews average {shop.review_average?.avg_rating} ({shop.review_average?.n})</span>
                </div>
              </div>
              <div className="bg-brand-800/40 p-4 rounded-xl border border-brand-800">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Typical day at this shop</h4>
                <p className="text-[11px] text-gray-500 mb-2">Average wait (min) and arrivals per hour over the 91 simulated days</p>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chart}>
                      <XAxis dataKey="time" stroke="#757c85" fontSize={10} tickLine={false} interval={1} />
                      <YAxis yAxisId="w" stroke="#757c85" fontSize={10} width={28} />
                      <YAxis yAxisId="v" orientation="right" stroke="#757c85" fontSize={10} width={28} />
                      <Tooltip {...tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar yAxisId="v" dataKey="visits" name="Arrivals / hour" fill="#3c434c" radius={[3, 3, 0, 0]} />
                      <Area yAxisId="w" type="monotone" dataKey="wait" name="Avg wait (min)" stroke="#C5A880" fill="rgba(197,168,128,0.25)" strokeWidth={2} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">1. Select a service</h3>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {shop.services.map(srv => (
                    <button key={srv.service_id} onClick={() => setService(srv)} aria-pressed={service?.service_id === srv.service_id}
                      className={`w-full p-3 rounded-lg border flex justify-between items-center text-left transition-all ${service?.service_id === srv.service_id ? 'border-accent-gold bg-brand-800/80' : 'border-brand-800 bg-brand-800/20 hover:border-brand-700'}`}>
                      <span><span className="block text-white text-sm font-semibold">{srv.service_name}</span>
                        <span className="text-xs text-gray-500">{srv.average_duration_minutes} minutes</span></span>
                      <span className="text-accent-gold font-bold">${srv.price}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="border-t lg:border-t-0 lg:border-l border-brand-800 lg:pl-8 pt-6 lg:pt-0 space-y-5 min-w-0">
              {error && <Notice tone="error">{error}</Notice>}
              {!liveEnabled && <Notice tone="warn">Joining the queue and booking are disabled on this read-only deployment.</Notice>}
              <div className="bg-brand-800/40 p-5 rounded-xl border border-brand-800 space-y-3">
                <h4 className="font-bold text-white flex items-center gap-2"><Clock className="text-accent-gold" size={18} /> 2a. Join the virtual queue</h4>
                <div className="bg-brand-900/50 p-3 rounded-lg border border-brand-800 grid grid-cols-2 gap-2 text-xs">
                  <div><span className="block text-gray-500">Waiting now</span><b className="text-white text-base">{liveEnabled ? shop.waiting : '—'}</b></div>
                  <div><span className="block text-gray-500">Estimated wait</span>
                    <b className="text-accent-gold text-base">{liveEnabled ? `${shop.estimated_wait_minutes} min` : '—'}</b></div>
                  <div className="col-span-2 text-gray-500">Typical at this hour: {Math.round(shop.typical_wait_minutes ?? 0)} min (history)</div>
                </div>
                <button onClick={handleJoin} disabled={!service || !liveEnabled || busy} className={`w-full py-2.5 ${buttonGold}`}>
                  {service ? 'Join queue now' : 'Select a service first'}
                </button>
              </div>
              <div className="bg-brand-800/40 p-5 rounded-xl border border-brand-800 space-y-3">
                <h4 className="font-bold text-white flex items-center gap-2"><Calendar className="text-accent-gold" size={18} /> 2b. Book an appointment</h4>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-xs text-gray-500 space-y-1">Date
                    <input type="date" value={date} min={isoDate(new Date())} max={maxDate} onChange={(e) => setDate(e.target.value)}
                      className="w-full bg-brand-900 border border-brand-700 text-xs rounded-lg p-2 text-white" />
                  </label>
                  <label className="text-xs text-gray-500 space-y-1">Time
                    <select value={time} onChange={(e) => setTime(e.target.value)} className={`w-full ${selectClass}`}>
                      {slots.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                </div>
                <button onClick={handleBook} disabled={!service || !liveEnabled || busy || !time}
                  className="w-full bg-brand-700 text-white font-bold py-2.5 rounded-lg hover:bg-brand-650 transition-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm">
                  {service ? 'Book appointment' : 'Select a service first'}
                </button>
                <p className="text-[11px] text-gray-500">Slots respect opening hours and the service length; each slot holds as many bookings as the shop has barbers.</p>
              </div>
              {shop.reviews?.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Latest reviews</h4>
                  {shop.reviews.slice(0, 3).map(r => (
                    <div key={r.review_id} className="text-xs text-gray-400 flex justify-between border-b border-brand-850 pb-1">
                      <span>{r.review_date} · {r.gender}, {r.age_group}</span>
                      <span className="text-accent-gold font-bold">{r.rating}★ <span className="text-gray-500 font-normal">(wait {r.waiting_time_rating})</span></span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, v, gold }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-gray-500">{k}</span>
      <span className={`font-semibold text-right ${gold ? 'text-accent-gold' : 'text-white'}`}>{v}</span>
    </div>
  );
}
