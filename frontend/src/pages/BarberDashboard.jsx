import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchShops, fetchShopDetail, fetchQueue, fetchShopAnalytics, fetchLiveBookings, fetchSimulatedDay,
  joinQueue, updateQueueEntry,
} from '../services/api';
import { UserPlus, Check, Play, Lightbulb, SkipForward, RefreshCw, CalendarDays, History } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { Card, Kpi, Loading, Notice, buttonGold, fmt, money, selectClass, tooltipStyle } from '../components/ui';

const POLL_MS = 10000;

const shopFromHash = () => {
  const parts = window.location.hash.replace(/^#\/?/, '').split('/');
  return parts[0] === 'barber' && parts[1] ? parseInt(parts[1], 10) : null;
};

const sinceLabel = (iso) => {
  if (!iso) return '';
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return mins < 1 ? 'just now' : mins < 60 ? `${mins} min ago` : `${Math.floor(mins / 60)} h ${mins % 60} m ago`;
};

export default function BarberDashboard() {
  const [shops, setShops] = useState([]);
  const [shopId, setShopId] = useState(shopFromHash() || 1);
  const [detail, setDetail] = useState(null);
  const [queue, setQueue] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [bookings, setBookings] = useState(null);
  const [history, setHistory] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [walkin, setWalkin] = useState({ open: false, customer: '', service: '' });

  useEffect(() => { fetchShops().then(setShops).catch(err => setError(err.message)); }, []);

  const refreshLive = useCallback(async () => {
    try {
      const [q, b] = await Promise.all([fetchQueue(shopId), fetchLiveBookings(shopId)]);
      setQueue(q); setBookings(b); setError('');
    } catch (err) { setError(err.message); }
  }, [shopId]);

  useEffect(() => {
    let alive = true;
    setLoading(true); setHistory(null); setShowHistory(false);
    window.history.replaceState(null, '', `#/barber/${shopId}`);
    Promise.all([fetchShopDetail(shopId), fetchShopAnalytics(shopId), fetchQueue(shopId), fetchLiveBookings(shopId)])
      .then(([d, a, q, b]) => { if (alive) { setDetail(d); setAnalytics(a); setQueue(q); setBookings(b); setError(''); } })
      .catch(err => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [shopId]);

  // Near-real-time: poll the live queue (WebSockets are not available on serverless functions).
  useEffect(() => {
    if (!queue?.live_queue_enabled) return undefined;
    const t = setInterval(refreshLive, POLL_MS);
    return () => clearInterval(t);
  }, [queue?.live_queue_enabled, refreshLive]);

  const act = async (entryId, action) => {
    setBusyId(entryId); setActionError('');
    try { await updateQueueEntry(entryId, action); await refreshLive(); }
    catch (err) { setActionError(err.message); }
    finally { setBusyId(null); }
  };

  const addWalkin = async (e) => {
    e.preventDefault();
    setActionError('');
    try {
      await joinQueue(shopId, parseInt(walkin.customer, 10), parseInt(walkin.service, 10), 'barber_walkin');
      setWalkin({ open: false, customer: '', service: '' });
      await refreshLive();
    } catch (err) { setActionError(err.message); }
  };

  const toggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && !history) {
      try { setHistory(await fetchSimulatedDay(shopId)); } catch (err) { setActionError(err.message); }
    }
  };

  const live = queue?.live_queue_enabled;
  const kpis = analytics?.kpis || {};
  const serviceChart = (analytics?.services_revenue || []).map(s => ({ name: s.service_name, visits: s.count }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 py-2 border-b border-brand-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Barber Dashboard</h1>
          <p className="text-gray-400 text-sm">Run today's live queue, check in walk-ins, and review the shop's history.</p>
        </div>
        <select aria-label="Shop" value={shopId} onChange={(e) => setShopId(parseInt(e.target.value, 10))} className={`${selectClass} text-sm p-2.5 max-w-full`}>
          {shops.map(s => <option key={s.shop_id} value={s.shop_id}>{s.shop_name} ({s.shop_type})</option>)}
        </select>
      </div>

      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <Loading label="Loading shop…" /> : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <Kpi label="Live queue" value={live ? `${queue.waiting.length} waiting` : '—'}
                 hint={live ? `${queue.in_service.length} of ${queue.number_of_barbers} barber(s) busy · new arrival waits ~${queue.estimated_wait_for_new_customer} min` : 'Live queue disabled'} />
            <Kpi label="Avg wait (history)" value={`${fmt(kpis.avg_wait, 1)} min`} hint={`${fmt(kpis.total_visits)} simulated visits`} />
            <Kpi label="Revenue (history)" value={money(kpis.total_revenue)} hint={`Avg ticket ${money(kpis.avg_ticket)} · list prices`} />
            <Kpi label="Repeat clients" value={`${fmt(analytics?.repeat_customer_rate_pct, 1)}%`}
                 hint={`No-show ${fmt(analytics?.appointment_noshow_rate_pct, 1)}% · cancel ${fmt(analytics?.appointment_cancellation_rate_pct, 1)}%`} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2" title="Live queue"
              subtitle={live ? `Stored in ${queue.storage === 'postgres' ? 'PostgreSQL' : 'SQLite'} · refreshes every ${POLL_MS / 1000}s` : queue?.message}
              right={live && (
                <div className="flex gap-2">
                  <button onClick={refreshLive} aria-label="Refresh queue" className="p-1.5 rounded-lg border border-brand-700 text-gray-400 hover:text-white"><RefreshCw size={14} /></button>
                  <button onClick={() => setWalkin({ ...walkin, open: !walkin.open })} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs ${buttonGold}`}>
                    <UserPlus size={14} /> Add walk-in
                  </button>
                </div>
              )}>
              {actionError && <Notice tone="error">{actionError}</Notice>}
              {walkin.open && (
                <form onSubmit={addWalkin} className="bg-brand-800/60 p-4 border border-brand-700 rounded-xl grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                  <label className="text-xs text-gray-400 space-y-1">Customer ID (1–5000)
                    <input type="number" min={1} max={5000} required value={walkin.customer} onChange={(e) => setWalkin({ ...walkin, customer: e.target.value })}
                      className="w-full bg-brand-950 border border-brand-700 rounded-lg text-xs p-2 text-white" placeholder="e.g. 12" />
                  </label>
                  <label className="text-xs text-gray-400 space-y-1">Service
                    <select required value={walkin.service} onChange={(e) => setWalkin({ ...walkin, service: e.target.value })} className={`w-full ${selectClass}`}>
                      <option value="">Choose service</option>
                      {detail?.services.map(s => <option key={s.service_id} value={s.service_id}>{s.service_name} (${s.price})</option>)}
                    </select>
                  </label>
                  <div className="flex gap-2">
                    <button type="submit" className={`flex-1 text-xs py-2 ${buttonGold}`}>Check in</button>
                    <button type="button" onClick={() => setWalkin({ open: false, customer: '', service: '' })} className="bg-brand-700 text-white text-xs font-bold py-2 px-3 rounded-lg">Cancel</button>
                  </div>
                </form>
              )}
              {live && (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse min-w-[560px]">
                    <thead>
                      <tr className="border-b border-brand-800 text-[11px] text-gray-500 font-bold uppercase">
                        <th className="py-2">Ticket</th><th>Customer</th><th>Service</th><th>Status</th><th>Joined</th><th className="text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {queue.in_service.length + queue.waiting.length === 0 && (
                        <tr><td colSpan={6} className="text-center py-6 text-gray-500 text-sm">
                          Nobody is waiting. Join from the Customer App or add a walk-in.
                        </td></tr>
                      )}
                      {[...queue.in_service, ...queue.waiting].map(item => (
                        <tr key={item.entry_id} className="border-b border-brand-850">
                          <td className="py-2.5 font-bold text-accent-gold">#{item.entry_id}</td>
                          <td><span className="block text-white font-semibold">Customer {item.customer_id}</span>
                            <span className="text-xs text-gray-500">{item.gender}, {item.age_group} · {item.source === 'barber_walkin' ? 'walk-in' : 'app'}</span></td>
                          <td><span className="block text-white">{item.service_name}</span><span className="text-xs text-gray-500">{item.service_duration_minutes} min</span></td>
                          <td>
                            {item.status === 'In Service'
                              ? <span className="text-xs font-semibold text-emerald-400">In service</span>
                              : <span className="text-xs font-semibold text-yellow-500">Waiting #{item.position} · ~{item.estimated_wait_minutes_now} min</span>}
                          </td>
                          <td className="text-xs text-gray-500">{sinceLabel(item.joined_at)}</td>
                          <td className="text-right py-2 space-x-1.5 whitespace-nowrap">
                            {item.status === 'Waiting' && (
                              <>
                                <button disabled={busyId === item.entry_id} onClick={() => act(item.entry_id, 'start')} className="bg-brand-700 hover:bg-brand-650 text-white px-2 py-1 rounded-md text-xs font-bold inline-flex items-center gap-1 disabled:opacity-50"><Play size={12} /> Start</button>
                                <button disabled={busyId === item.entry_id} onClick={() => act(item.entry_id, 'skip')} aria-label="Skip customer" title="Skip (no-show)" className="border border-brand-700 text-gray-400 hover:text-red-400 px-2 py-1 rounded-md text-xs disabled:opacity-50"><SkipForward size={12} /></button>
                              </>
                            )}
                            {item.status === 'In Service' && (
                              <button disabled={busyId === item.entry_id} onClick={() => act(item.entry_id, 'complete')} className="bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded-md text-xs font-bold inline-flex items-center gap-1 disabled:opacity-50"><Check size={12} /> Finish</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {queue.recent.length > 0 && (
                    <p className="text-xs text-gray-500 mt-3">
                      Recently: {queue.recent.slice(0, 6).map(r => `#${r.entry_id} ${r.status.toLowerCase()}`).join(' · ')}
                    </p>
                  )}
                </div>
              )}
            </Card>

            <div className="space-y-6 min-w-0">
              <Card title={<span className="flex items-center gap-2"><Lightbulb size={16} className="text-accent-gold" /> Recommendations</span>} subtitle="Rules computed from this shop's history">
                <div className="space-y-3">
                  {analytics?.business_recommendations?.map(rec => (
                    <div key={rec.type} className="bg-brand-850/40 border border-brand-800 p-3 rounded-lg space-y-1">
                      <span className="block text-xs font-bold text-accent-gold">{rec.type}</span>
                      <p className="text-xs text-gray-400 leading-relaxed">{rec.message}</p>
                    </div>
                  ))}
                </div>
              </Card>
              <Card title={<span className="flex items-center gap-2"><CalendarDays size={16} className="text-accent-gold" /> Upcoming bookings</span>}>
                {!bookings?.live_bookings_enabled ? <p className="text-xs text-gray-500">Bookings are disabled on this deployment.</p>
                  : bookings.bookings.length === 0 ? <p className="text-xs text-gray-500">No upcoming bookings yet.</p> : (
                    <ul className="space-y-1.5 text-xs">
                      {bookings.bookings.map(b => (
                        <li key={b.booking_id} className="flex justify-between gap-2 border-b border-brand-850 pb-1">
                          <span className="text-gray-300">{b.appointment_date} {b.appointment_time}</span>
                          <span className="text-gray-500 truncate">#{b.customer_id} · {b.service_name}</span>
                        </li>
                      ))}
                    </ul>
                  )}
              </Card>
              <Card title="Visits by service (history)">
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={serviceChart} layout="vertical" margin={{ left: 10 }}>
                      <XAxis type="number" stroke="#757c85" fontSize={10} />
                      <YAxis type="category" dataKey="name" stroke="#757c85" fontSize={10} width={95} />
                      <Tooltip {...tooltipStyle} />
                      <Bar dataKey="visits" name="Visits" fill="#C5A880" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          </div>

          <Card title={<span className="flex items-center gap-2"><History size={16} className="text-accent-gold" /> Last simulated day</span>}
                subtitle="The shop's final day in the generated dataset, exactly as simulated (arrival, start, end, wait)."
                right={<button onClick={toggleHistory} className="text-xs text-accent-gold hover:underline">{showHistory ? 'Hide' : 'Show'}</button>}>
            {showHistory && (!history ? <Loading /> : (
              <div className="overflow-x-auto">
                <p className="text-xs text-gray-500 mb-2">{history.date} · {history.visits.length} visits</p>
                <table className="w-full text-left text-xs min-w-[560px]">
                  <thead><tr className="text-gray-500 uppercase border-b border-brand-800"><th className="py-1.5">Arrived</th><th>Start</th><th>End</th><th>Wait</th><th>Service</th><th>Type</th></tr></thead>
                  <tbody>
                    {history.visits.map(v => (
                      <tr key={v.visit_id} className="border-b border-brand-850 text-gray-300">
                        <td className="py-1.5">{v.arrival_time}</td><td>{v.service_start_time}</td><td>{v.service_end_time}</td>
                        <td className={v.waiting_time_minutes > 30 ? 'text-red-400' : ''}>{v.waiting_time_minutes} min</td>
                        <td>{v.service_name}</td><td>{v.visit_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </Card>
        </>
      )}
    </div>
  );
}
