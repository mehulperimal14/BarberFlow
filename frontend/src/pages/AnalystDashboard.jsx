import React, { useEffect, useState } from 'react';
import {
  fetchMarketOverview, fetchDemandCharts, fetchWaitingTimeCharts, fetchSatisfaction,
  fetchShopPerformance, fetchLocationOpportunity,
} from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, ScatterChart, Scatter,
  ZAxis, ReferenceLine, Legend, CartesianGrid,
} from 'recharts';
import { TrendingUp, Smile, Map, BarChart3 } from 'lucide-react';
import { AREAS, Card, Kpi, Loading, Notice, fmt, money, selectClass, tooltipStyle } from '../components/ui';

const QUADRANTS = [
  { key: 'Leader', color: '#34d399', text: 'High demand, high capacity: well scaled.' },
  { key: 'Bottleneck', color: '#f59e0b', text: 'High demand, low capacity: long waits. Add a barber at peak hours.' },
  { key: 'Underutilized', color: '#60a5fa', text: 'Low demand, high capacity: idle chairs. Promote off-peak.' },
  { key: 'Low Scale', color: '#9fa4ab', text: 'Low demand, low capacity: small local operations.' },
];
const STATUS_COLOR = { 'High Opportunity (Under-served)': 'text-red-400', 'Balanced Market': 'text-yellow-500', 'Over-saturated': 'text-emerald-400' };

export default function AnalystDashboard() {
  const [tab, setTab] = useState('overview');
  const [area, setArea] = useState('');
  const [state, setState] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const loaders = {
      overview: () => Promise.all([fetchMarketOverview(area), fetchDemandCharts('', area)])
        .then(([kpis, demand]) => ({ kpis, demand })),
      experience: () => Promise.all([fetchWaitingTimeCharts('', area), fetchSatisfaction(area)])
        .then(([wait, satisfaction]) => ({ wait, satisfaction })),
      performance: () => fetchShopPerformance().then(performance => ({ performance })),
      location: () => fetchLocationOpportunity().then(location => ({ location })),
    };
    loaders[tab]()
      .then(data => { if (alive) { setState(s => ({ ...s, ...data })); setError(''); } })
      .catch(err => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [tab, area]);

  const areaAware = tab === 'overview' || tab === 'experience';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-brand-800 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Business Analytics</h1>
          <p className="text-gray-400 text-sm">Market KPIs, demand, waiting-time drivers, shop performance and location opportunity (91 simulated days).</p>
        </div>
        <select aria-label="Neighborhood filter" value={area} onChange={(e) => setArea(e.target.value)} disabled={!areaAware}
                className={`${selectClass} disabled:opacity-40`} title={areaAware ? '' : 'This view always covers the whole market'}>
          <option value="">All neighborhoods</option>
          {AREAS.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-brand-850 pb-2" role="tablist">
        {[['overview', 'Market Overview', TrendingUp], ['experience', 'Customer Experience', Smile],
          ['performance', 'Shop Performance', BarChart3], ['location', 'Location Opportunity', Map]].map(([id, name, Icon]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-lg text-xs font-bold transition-accent ${tab === id ? 'bg-accent-gold text-brand-900' : 'text-gray-400 hover:text-gray-200 hover:bg-brand-800/40'}`}>
            <Icon size={15} /> {name}
          </button>
        ))}
      </div>

      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <Loading label="Running analytics queries…" /> : (
        <>
          {tab === 'overview' && state.kpis && <Overview kpis={state.kpis} demand={state.demand} />}
          {tab === 'experience' && state.wait && <Experience wait={state.wait} satisfaction={state.satisfaction} />}
          {tab === 'performance' && state.performance && <Performance data={state.performance} />}
          {tab === 'location' && state.location && <Location data={state.location} />}
        </>
      )}
    </div>
  );
}

function Overview({ kpis, demand }) {
  const byHour = demand.demand_by_hour.map(d => ({ hour: `${d.hour}:00`, visits: d.visits, share: d.share_pct }));
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        <Kpi label="Shops" value={kpis.total_shops} />
        <Kpi label="Customers" value={fmt(kpis.total_customers)} hint={kpis.customers_label} />
        <Kpi label="Visits" value={fmt(kpis.total_visits)} />
        <Kpi label="Wait (mean / median)" value={`${kpis.average_wait_minutes} / ${kpis.median_wait_minutes} min`} hint={`p90 ${kpis.p90_wait_minutes} min · ${kpis.zero_wait_share_pct}% wait 0`} />
        <Kpi label="Seat utilization" value={`${kpis.average_utilization_pct}%`} hint={`avg queue ${kpis.average_queue_length} (hourly snapshots)`} />
        <Kpi label="Review rating" value={`${kpis.average_review_rating} ★`} hint={`${fmt(kpis.total_reviews)} reviews · listed ${kpis.average_rating}`} />
        <Kpi label="Appointments" value={fmt(kpis.total_appointments)} hint={`${kpis.appointment_completion_rate_pct}% completed`} />
        <Kpi label="No-show rate" value={`${kpis.appointment_noshow_rate_pct}%`} />
        <Kpi label="Cancellation rate" value={`${kpis.appointment_cancellation_rate_pct}%`} />
        <Kpi label="Revenue" value={money(kpis.total_revenue)} hint={kpis.revenue_note} />
        <Kpi label="Avg ticket" value={`$${fmt(kpis.average_ticket, 2)}`} />
        <Kpi label="Long waits" value={`${kpis.over_30_min_share_pct}%`} hint="share of visits waiting > 30 min" />
      </div>
      {kpis.median_wait_minutes === 0 && kpis.average_wait_minutes > 5 && (
        <Notice>
          The mean wait ({kpis.average_wait_minutes} min) is far above the median (0 min): most customers never wait,
          while a minority waits a long time. Report the median and p90 alongside the mean.
        </Notice>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Arrivals by hour" subtitle="Total visits per arrival hour">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={byHour}>
                <CartesianGrid stroke="#1d2127" vertical={false} />
                <XAxis dataKey="hour" stroke="#757c85" fontSize={10} tickLine={false} />
                <YAxis stroke="#757c85" fontSize={10} tickLine={false} width={40} />
                <Tooltip {...tooltipStyle} formatter={(v, n, p) => [`${fmt(v)} (${p.payload.share}%)`, 'Visits']} />
                <Area type="monotone" dataKey="visits" stroke="#C5A880" fill="rgba(197,168,128,0.25)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Average visits per day, by weekday" subtitle="Each weekday occurs 13 times in the 91 days">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={demand.demand_by_day}>
                <CartesianGrid stroke="#1d2127" vertical={false} />
                <XAxis dataKey="day_name" stroke="#757c85" fontSize={10} tickLine={false} />
                <YAxis stroke="#757c85" fontSize={10} tickLine={false} width={40} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="avg_visits_per_day" name="Visits per day" fill="#C5A880" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Experience({ wait, satisfaction }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Waiting-time distribution" subtitle="Number of visits per wait band">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wait.wait_distribution}>
                <CartesianGrid stroke="#1d2127" vertical={false} />
                <XAxis dataKey="wait_tier" stroke="#757c85" fontSize={10} tickLine={false} />
                <YAxis stroke="#757c85" fontSize={10} tickLine={false} width={45} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="count" name="Visits" fill="#C5A880" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Average wait by arrival hour" subtitle="Minutes">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={wait.wait_by_hour.map(w => ({ hour: `${w.hour}:00`, wait: w.avg_wait }))}>
                <CartesianGrid stroke="#1d2127" vertical={false} />
                <XAxis dataKey="hour" stroke="#757c85" fontSize={10} tickLine={false} />
                <YAxis stroke="#757c85" fontSize={10} tickLine={false} width={35} />
                <Tooltip {...tooltipStyle} />
                <Area type="monotone" dataKey="wait" name="Avg wait (min)" stroke="#d97706" fill="rgba(217,119,6,0.15)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      {satisfaction && (
        <Card title="Review rating vs. the wait the reviewer experienced"
              subtitle={`${fmt(satisfaction.matched_reviews)} of ${fmt(satisfaction.total_reviews)} reviews matched to exactly one visit`}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={satisfaction.tiers}>
                  <CartesianGrid stroke="#1d2127" vertical={false} />
                  <XAxis dataKey="wait_tier" stroke="#757c85" fontSize={10} tickLine={false} />
                  <YAxis domain={[0, 5]} stroke="#757c85" fontSize={10} width={25} />
                  <Tooltip {...tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="avg_rating" name="Overall rating" fill="#C5A880" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="avg_wait_experience_rating" name="Wait rating" fill="#3c434c" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {satisfaction.insight && <Notice>{satisfaction.insight}</Notice>}
              <table className="w-full text-xs text-left">
                <thead><tr className="text-gray-500 uppercase border-b border-brand-800"><th className="py-1.5">Wait</th><th>Reviews</th><th>Rating</th><th>Wait rating</th></tr></thead>
                <tbody>{satisfaction.tiers.map(t => (
                  <tr key={t.wait_tier} className="border-b border-brand-850 text-gray-300">
                    <td className="py-1.5">{t.wait_tier}</td><td>{fmt(t.reviews)}</td><td>{t.avg_rating}</td><td>{t.avg_wait_experience_rating}</td>
                  </tr>))}</tbody>
              </table>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

function Performance({ data }) {
  return (
    <div className="space-y-6">
      <Card title="Shop performance matrix" subtitle={`Demand (total visits) vs capacity (seats). Lines mark the market averages: ${fmt(data.threshold_visits)} visits, ${data.threshold_seats} seats.`}>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
              <CartesianGrid stroke="#1d2127" />
              <XAxis type="number" dataKey="number_of_seats" name="Seats" stroke="#757c85" fontSize={10} domain={[1, 11]} allowDecimals={false} />
              <YAxis type="number" dataKey="total_visits" name="Visits" stroke="#757c85" fontSize={10} width={45} domain={['auto', 'auto']} />
              <ZAxis range={[60, 60]} />
              <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: '3 3' }}
                       content={({ payload }) => payload?.[0] ? (
                         <div className="bg-brand-800 border border-brand-700 rounded-lg p-2 text-xs text-gray-200">
                           <b>{payload[0].payload.shop_name}</b><br />{payload[0].payload.quadrant} · {payload[0].payload.shop_type}<br />
                           {payload[0].payload.number_of_seats} seats · {fmt(payload[0].payload.total_visits)} visits · wait {payload[0].payload.avg_wait} min
                         </div>) : null} />
              <ReferenceLine x={data.threshold_seats} stroke="#757c85" strokeDasharray="4 4" />
              <ReferenceLine y={data.threshold_visits} stroke="#757c85" strokeDasharray="4 4" />
              {QUADRANTS.map(q => (
                <Scatter key={q.key} name={q.key} data={data.shops_data.filter(s => s.quadrant === q.key)} fill={q.color} />
              ))}
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {QUADRANTS.map(q => (
            <div key={q.key} className="bg-brand-850/30 p-3 rounded-lg border border-brand-800">
              <span className="font-bold block mb-1" style={{ color: q.color }}>{q.key} · {data.quadrant_counts[q.key] || 0} shops</span>
              <p className="text-gray-500">{q.text}</p>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Shop rankings by demand" subtitle="All 50 shops, sorted by total visits">
        <div className="overflow-x-auto max-h-[480px]">
          <table className="w-full text-left border-collapse min-w-[720px] text-sm">
            <thead className="sticky top-0 bg-brand-900">
              <tr className="border-b border-brand-800 text-[11px] text-gray-500 font-bold uppercase">
                <th className="py-2">#</th><th>Shop</th><th>Class</th><th>Quadrant</th><th>Seats</th><th>Visits</th><th>Avg wait</th><th>Util.</th><th>Reviews ★</th><th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {data.shops_data.map((s, i) => (
                <tr key={s.shop_id} className="border-b border-brand-850">
                  <td className="py-2 text-gray-500">{i + 1}</td>
                  <td className="font-semibold text-white">{s.shop_name}</td>
                  <td className="text-gray-400">{s.shop_type}</td>
                  <td style={{ color: QUADRANTS.find(q => q.key === s.quadrant)?.color }}>{s.quadrant}</td>
                  <td className="text-gray-400">{s.number_of_seats}</td>
                  <td className="font-bold text-white">{fmt(s.total_visits)}</td>
                  <td className={s.avg_wait > 20 ? 'text-red-400' : 'text-gray-400'}>{s.avg_wait} min</td>
                  <td className="text-gray-400">{s.avg_utilization}%</td>
                  <td className="text-accent-gold">{s.review_rating}</td>
                  <td className="text-gray-400">{money(s.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Location({ data }) {
  return (
    <Card title="Location opportunity by neighborhood"
          subtitle={`Visits per seat compared with the market average of ${data.market_visits_per_seat}. ≥ ${data.thresholds.high_opportunity_at_or_above} = under-served, ≤ ${data.thresholds.over_saturated_at_or_below} = over-saturated.`}>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.areas}>
            <CartesianGrid stroke="#1d2127" vertical={false} />
            <XAxis dataKey="area" stroke="#757c85" fontSize={10} tickLine={false} />
            <YAxis stroke="#757c85" fontSize={10} width={40} />
            <Tooltip {...tooltipStyle} />
            <ReferenceLine y={data.market_visits_per_seat} stroke="#C5A880" strokeDasharray="4 4" label={{ value: 'market', fill: '#C5A880', fontSize: 10, position: 'right' }} />
            <Bar dataKey="visits_per_seat" name="Visits per seat" fill="#3c434c" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.areas.map(a => (
          <div key={a.area} className="bg-brand-800/40 p-4 rounded-xl border border-brand-800 space-y-2">
            <div className="flex justify-between items-start">
              <h4 className="font-extrabold text-white text-lg">{a.area}</h4>
              <span className="text-[10px] bg-brand-900 px-2 py-0.5 rounded-full border border-brand-700 text-gray-400 font-bold uppercase">{a.shop_count} shops</span>
            </div>
            <div className="space-y-1 text-xs text-gray-400">
              <Line k="Seats / barbers" v={`${a.total_seats} / ${a.total_barbers}`} />
              <Line k="Visits" v={fmt(a.total_visits)} />
              <Line k="Average wait" v={`${a.avg_wait_minutes} min`} />
              <Line k="Visits per seat" v={<span className="text-accent-gold font-black">{a.visits_per_seat} ({a.index_vs_market}× market)</span>} />
            </div>
            <div className={`border-t border-brand-850 pt-2 text-xs font-bold ${STATUS_COLOR[a.status]}`}>{a.status}</div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-gray-500">Area-level only: there is no map layer, population or competitor data in this simulated dataset.</p>
    </Card>
  );
}

function Line({ k, v }) {
  return <div className="flex justify-between gap-2"><span>{k}</span><span className="text-white font-bold text-right">{v}</span></div>;
}
