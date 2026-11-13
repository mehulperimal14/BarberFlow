import React, { useEffect, useState } from 'react';
import { Database, KeyRound, Link2, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchTable } from '../services/api';
import { Loading, Notice, fmt, selectClass } from '../components/ui';

const TABLES = [
  ['shops', 'Dimension', 'Shop attributes: location, type, rating, seats, barbers and opening hours.'],
  ['services', 'Dimension', 'Each shop\'s service menu with price and duration.'],
  ['customers', 'Dimension', 'Simulated customers: age group, gender, area, preferred service.'],
  ['appointments', 'Fact', 'Bookings with status (Completed / Cancelled / No-Show) and flags.'],
  ['visits', 'Fact', 'Every served customer: arrival, start, end, wait and seat (queue simulation).'],
  ['availability', 'Snapshot', 'Hourly snapshots of occupied seats, queue length and estimated wait.'],
  ['reviews', 'Fact', 'Review scores for overall, service, cleanliness, value and waiting time.'],
];
const PAGE = 25;

export default function DataExplorer() {
  const [table, setTable] = useState('shops');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchTable(table, PAGE, offset)
      .then(d => { if (alive) { setData(d); setError(''); } })
      .catch(err => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [table, offset]);

  const info = TABLES.find(t => t[0] === table);
  const pk = data?.columns.filter(c => c.primary_key).map(c => c.name) || [];

  return (
    <div className="space-y-6">
      <div className="border-b border-brand-850 pb-4">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-2"><Database className="text-accent-gold" /> Relational Data Explorer</h1>
        <p className="text-gray-400 text-sm">Inspect the SQLite schema, keys, relationships and raw rows of the simulated dataset (read-only).</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 glass-card p-5 rounded-xl space-y-4 h-fit">
          <label className="block text-xs text-gray-500 font-bold uppercase space-y-2">
            <span>Table</span>
            <select value={table} onChange={(e) => { setTable(e.target.value); setOffset(0); }} className={`w-full ${selectClass} text-sm`}>
              {TABLES.map(([t, kind]) => <option key={t} value={t}>{t} ({kind})</option>)}
            </select>
          </label>
          <div className="border-t border-brand-850 pt-3 space-y-3 text-xs">
            <div><span className="text-gray-500 block">Rows</span><span className="text-white font-bold">{fmt(data?.total_rows)}</span></div>
            <div><span className="text-gray-500 block">Description</span><p className="text-gray-400">{info?.[2]}</p></div>
            {data && (
              <>
                <div>
                  <span className="text-gray-500 flex items-center gap-1"><KeyRound size={12} /> Primary key</span>
                  <span className="text-white font-mono">{pk.length ? pk.join(', ') : '—'}</span>
                </div>
                <div>
                  <span className="text-gray-500 flex items-center gap-1"><Link2 size={12} /> Foreign keys</span>
                  {data.foreign_keys.length === 0 ? <span className="text-gray-400">none</span> : (
                    <ul className="font-mono text-gray-300 space-y-0.5">
                      {data.foreign_keys.map(f => <li key={f.column}>{f.column} → {f.references}</li>)}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
        <div className="lg:col-span-3 min-w-0">
          {error ? <Notice tone="error">{error}</Notice> : loading && !data ? <Loading label="Querying database…" /> : data && (
            <div className="glass-card rounded-xl p-4 sm:p-5 space-y-3">
              <div className="flex flex-wrap justify-between items-center gap-2 border-b border-brand-850 pb-3">
                <h3 className="font-bold text-white text-sm uppercase">
                  Rows {fmt(offset + 1)}–{fmt(Math.min(offset + PAGE, data.total_rows))} of {fmt(data.total_rows)}
                </h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">{data.columns.length} columns</span>
                  <button aria-label="Previous page" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="p-1 rounded border border-brand-700 disabled:opacity-30"><ChevronLeft size={14} /></button>
                  <button aria-label="Next page" disabled={offset + PAGE >= data.total_rows || loading} onClick={() => setOffset(offset + PAGE)} className="p-1 rounded border border-brand-700 disabled:opacity-30"><ChevronRight size={14} /></button>
                </div>
              </div>
              <div className="overflow-auto max-h-[520px]">
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 bg-brand-900">
                    <tr className="border-b border-brand-800 text-[11px] text-gray-500 font-bold">
                      {data.columns.map(col => (
                        <th key={col.name} className="py-2 pr-4 whitespace-nowrap">
                          {col.primary_key && <KeyRound size={10} className="inline mr-1 text-accent-gold" />}{col.name}{' '}
                          <span className="text-[9px] text-accent-gold/60 font-normal">{col.type}{col.not_null ? ' NOT NULL' : ''}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="text-xs font-mono">
                    {data.rows.map((row, i) => (
                      <tr key={i} className="border-b border-brand-850 text-gray-300">
                        {data.columns.map(col => (
                          <td key={col.name} className="py-2 pr-4 max-w-[200px] truncate" title={String(row[col.name] ?? 'NULL')}>
                            {row[col.name] !== null ? String(row[col.name]) : <span className="text-red-400/40">NULL</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
