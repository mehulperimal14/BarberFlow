import React, { useEffect, useState } from 'react';
import { fetchShops, fetchModelCard, predictDemand, predictWaitTime, predictNoShow } from '../services/api';
import { BrainCircuit, FlaskConical } from 'lucide-react';
import { Card, DAY_NAMES, Loading, Notice, buttonGold, hourLabel, selectClass } from '../components/ui';

const HOURS = Array.from({ length: 13 }, (_, i) => i + 8);
const STATUS_STYLE = {
  baseline: 'bg-yellow-950/40 text-yellow-400 border-yellow-800',
  'good on simulated data': 'bg-emerald-950/40 text-emerald-400 border-emerald-800',
};

function Metrics({ card }) {
  if (!card) return null;
  const m = card.test_metrics || {};
  const entries = Object.entries(m).map(([k, v]) => [k.replace(/_/g, ' ').replace('roc auc', 'ROC-AUC').replace(/\br2\b/, 'R²').replace(/\bmae\b/, 'MAE').replace(/\brmse\b/, 'RMSE'), v]);
  return (
    <div className="text-[11px] text-gray-500 space-y-1 border-t border-brand-850 pt-3">
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {entries.map(([k, v]) => <span key={k}>{k}: <b className="text-gray-300">{v}</b></span>)}
      </div>
      <p>{card.split}</p>
    </div>
  );
}

function ModelHeader({ title, card }) {
  const style = STATUS_STYLE[card?.status] || 'bg-red-950/40 text-red-400 border-red-800';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-start gap-2">
        <h3 className="font-extrabold text-white">{title}</h3>
        {card && <span className={`text-[10px] border px-2 py-0.5 rounded-full font-bold whitespace-nowrap ${style}`}>{card.status}</span>}
      </div>
      {card && <p className="text-[11px] text-accent-gold">{card.algorithm}</p>}
    </div>
  );
}

const Field = ({ label, children }) => (
  <label className="block text-[10px] text-gray-500 font-bold uppercase space-y-1"><span>{label}</span>{children}</label>
);

export default function PredictionsView() {
  const [shops, setShops] = useState([]);
  const [card, setCard] = useState(null);
  const [error, setError] = useState('');
  const [demand, setDemand] = useState({ shop: 1, hour: 17, day: 5 });
  const [wait, setWait] = useState({ shop: 1, queue: 3, occupied: 1, hour: 17, day: 5 });
  const [ns, setNs] = useState({ customer: 120, hour: 10, lag: 3.5 });
  const [results, setResults] = useState({});
  const [busy, setBusy] = useState('');

  useEffect(() => {
    Promise.all([fetchShops(), fetchModelCard()])
      .then(([s, c]) => { setShops(s); setCard(c); })
      .catch(err => setError(err.message));
  }, []);

  const run = (key, fn) => async (e) => {
    e.preventDefault();
    setBusy(key);
    setResults(r => ({ ...r, [key]: null }));
    try { const ok = await fn(); setResults(r => ({ ...r, [key]: { ok } })); }
    catch (err) { setResults(r => ({ ...r, [key]: { error: err.message } })); }
    finally { setBusy(''); }
  };

  const shopSelect = (value, onChange) => (
    <select value={value} onChange={(e) => onChange(+e.target.value)} className={`w-full ${selectClass}`}>
      {shops.map(s => <option key={s.shop_id} value={s.shop_id}>{s.shop_name} ({s.number_of_seats} seats, {s.number_of_barbers} barbers)</option>)}
    </select>
  );
  const hourSelect = (value, onChange) => (
    <select value={value} onChange={(e) => onChange(+e.target.value)} className={`w-full ${selectClass}`}>
      {HOURS.map(h => <option key={h} value={h}>{hourLabel(h)}</option>)}
    </select>
  );
  const daySelect = (value, onChange) => (
    <select value={value} onChange={(e) => onChange(+e.target.value)} className={`w-full ${selectClass}`}>
      {DAY_NAMES.map((d, i) => <option key={d} value={i}>{d}</option>)}
    </select>
  );
  const models = card?.models || {};
  const selectedWaitShop = shops.find(s => s.shop_id === wait.shop);

  return (
    <div className="space-y-6">
      <div className="border-b border-brand-850 pb-4">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-2"><BrainCircuit className="text-accent-gold" /> ML Predictions</h1>
        <p className="text-gray-400 text-sm">Live inference from the three trained models. Every metric shown is measured on held-out data and read from the model card.</p>
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {!card && !error ? <Loading label="Loading models…" /> : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="flex flex-col justify-between">
            <ModelHeader title="Hourly demand" card={models.demand} />
            <p className="text-xs text-gray-400">Expected arrivals at a shop for a given hour and weekday.</p>
            <form onSubmit={run('demand', () => predictDemand(demand.shop, demand.hour, demand.day))} className="space-y-3">
              <Field label="Shop">{shopSelect(demand.shop, v => setDemand({ ...demand, shop: v }))}</Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Hour">{hourSelect(demand.hour, v => setDemand({ ...demand, hour: v }))}</Field>
                <Field label="Day">{daySelect(demand.day, v => setDemand({ ...demand, day: v }))}</Field>
              </div>
              <button disabled={busy === 'demand'} className={`w-full py-2 text-xs ${buttonGold}`}>Predict demand</button>
            </form>
            <Result r={results.demand} render={(d) => (
              <>
                <Big label="Predicted arrivals" value={`${d.predicted_customers} / hour`} />
                <p className="text-[11px] text-gray-500">Historical average for this slot: {d.features.historical_average_demand}{!d.shop_open_at_this_hour && ' · shop closed at this hour'}</p>
              </>)} />
            <Metrics card={models.demand} />
          </Card>

          <Card className="flex flex-col justify-between">
            <ModelHeader title="Walk-in waiting time" card={models.waiting_time} />
            <p className="text-xs text-gray-400">Minutes a new walk-in would wait, given the queue and busy chairs.</p>
            <form onSubmit={run('wait', () => predictWaitTime(wait.shop, wait.queue, wait.occupied, wait.hour, wait.day))} className="space-y-3">
              <Field label="Shop">{shopSelect(wait.shop, v => setWait({ ...wait, shop: v, occupied: 0 }))}</Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="People waiting">
                  <input type="number" min={0} max={100} value={wait.queue} onChange={(e) => setWait({ ...wait, queue: e.target.value })} className={`w-full ${selectClass}`} />
                </Field>
                <Field label={`Busy chairs (of ${selectedWaitShop?.number_of_seats ?? '?'})`}>
                  <input type="number" min={0} max={selectedWaitShop?.number_of_seats ?? 10} value={wait.occupied} onChange={(e) => setWait({ ...wait, occupied: e.target.value })} className={`w-full ${selectClass}`} />
                </Field>
                <Field label="Hour">{hourSelect(wait.hour, v => setWait({ ...wait, hour: v }))}</Field>
                <Field label="Day">{daySelect(wait.day, v => setWait({ ...wait, day: v }))}</Field>
              </div>
              <button disabled={busy === 'wait'} className={`w-full py-2 text-xs ${buttonGold}`}>Predict wait</button>
            </form>
            <Result r={results.wait} render={(d) => (
              <>
                <Big label="Predicted wait" value={`${d.predicted_waiting_time_minutes} min`} />
                <p className="text-[11px] text-gray-500">Typical historical wait at this hour and day: {d.historical_typical_wait_minutes ?? '—'} min</p>
              </>)} />
            <Metrics card={models.waiting_time} />
          </Card>

          <Card className="flex flex-col justify-between">
            <ModelHeader title="Appointment no-show risk" card={models.no_show} />
            <Notice tone="warn">
              <span className="inline-flex items-center gap-1 font-bold"><FlaskConical size={13} /> Experimental.</span>{' '}
              In the simulated data no-shows are random; the model only picks up that missed bookings were
              given random hours. Without the hour feature it is no better than chance.
            </Notice>
            <form onSubmit={run('ns', () => predictNoShow(ns.customer, ns.hour, ns.lag))} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <Field label="Customer ID">
                  <input type="number" min={1} max={5000} value={ns.customer} onChange={(e) => setNs({ ...ns, customer: e.target.value })} className={`w-full ${selectClass}`} />
                </Field>
                <Field label="Booked days ahead">
                  <input type="number" min={0} max={60} step={0.5} value={ns.lag} onChange={(e) => setNs({ ...ns, lag: e.target.value })} className={`w-full ${selectClass}`} />
                </Field>
                <Field label="Appointment hour">{hourSelect(ns.hour, v => setNs({ ...ns, hour: v }))}</Field>
              </div>
              <button disabled={busy === 'ns'} className={`w-full py-2 text-xs ${buttonGold}`}>Assess risk</button>
            </form>
            <Result r={results.ns} render={(d) => (
              <>
                <Big label="No-show probability" value={`${(d.no_show_probability * 100).toFixed(1)}% · ${d.risk_tier}`} />
                <p className="text-[11px] text-gray-500">Base rate {(d.base_rate * 100).toFixed(1)}%. Low &lt; {(d.risk_tier_thresholds.low_below * 100).toFixed(1)}%, High ≥ {(d.risk_tier_thresholds.high_at_or_above * 100).toFixed(1)}%.</p>
              </>)} />
            <Metrics card={models.no_show} />
          </Card>
        </div>
      )}
      {card && (
        <Card title="Methodology" subtitle={`Trained ${card.trained_at} by ${card.training_script}`}>
          <ul className="text-xs text-gray-400 space-y-1.5 list-disc pl-4">
            <li>Demand and waiting time use a <b className="text-gray-200">time-based split</b>: the last 20% of dates are held out, so the models never train on the future.</li>
            <li>Demand's historical-average feature is computed from <b className="text-gray-200">training dates only</b>. The model is chosen on a validation window; a linear model matched the forest, so the simpler one is served.</li>
            <li>Models are exported from scikit-learn to JSON and served without pickle; exported predictions match scikit-learn to within {Math.max(...Object.values(card.export_check_max_abs_diff || { a: 0 })).toExponential(0)}.</li>
            <li>All data is simulated (see the data explorer), so these results show method, not real-world accuracy.</li>
          </ul>
        </Card>
      )}
    </div>
  );
}

function Result({ r, render }) {
  if (!r) return null;
  if (r.error) return <Notice tone="error">{r.error}</Notice>;
  return <div className="bg-brand-900/60 p-3 border border-brand-850 rounded-xl space-y-1">{render(r.ok)}</div>;
}

function Big({ label, value }) {
  return (
    <div className="flex justify-between items-center gap-2">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-lg font-black text-white text-right">{value}</span>
    </div>
  );
}
