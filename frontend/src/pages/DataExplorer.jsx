import React, { useState, useEffect } from 'react';

export default function DataExplorer() {
  const [selectedTable, setSelectedTable] = useState('shops');
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTableData();
  }, [selectedTable]);

  const loadTableData = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch metadata from explorer API
      const res = await fetch(`http://127.0.0.1:8000/api/explorer/${selectedTable}`);
      if (!res.ok) throw new Error("Failed to fetch table details");
      const data = await res.json();
      
      setColumns(data.columns);
      setRows(data.rows);
      setTotalRows(data.total_rows);
    } catch (err) {
      setError(`Error connecting to explorer API: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getTableStats = () => {
    if (selectedTable === 'shops') return "Contains geo-coordinates, shop types, ratings, and seat capacity capacity.";
    if (selectedTable === 'services') return "Tracks service names, prices, and average durations mapped to shops.";
    if (selectedTable === 'customers') return "Tracks demographic groups (age, gender), preferred service, and spending habits.";
    if (selectedTable === 'appointments') return "Contains appointment scheduling times, cancellation logs, and no-show flags.";
    if (selectedTable === 'visits') return "Live-simulated arrival queue times, actual wait times, and seat IDs.";
    if (selectedTable === 'availability') return "Hourly snapshots logging seat congestion and estimated wait minutes.";
    return "Feedback scores, service ratings, and cleanliness marks.";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="py-4 border-b border-brand-850">
        <h1 className="text-3xl font-extrabold text-white flex items-center gap-2">
          <Database className="text-accent-gold" /> Relational Data Explorer
        </h1>
        <p className="text-gray-400 text-sm">
          Audit the underlying SQLite relational tables. Inspect data schemas, counts, and raw rows.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left selector */}
        <div className="lg:col-span-1 glass-card p-5 rounded-xl space-y-4 h-fit">
          <div>
            <label className="block text-xs text-gray-500 font-bold uppercase mb-2">Select Database Table</label>
            <select
              value={selectedTable}
              onChange={(e) => setSelectedTable(e.target.value)}
              className="w-full bg-brand-900 border border-brand-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-accent-gold font-semibold"
            >
              <option value="shops">shops (Dimension)</option>
              <option value="services">services (Dimension)</option>
              <option value="customers">customers (Dimension)</option>
              <option value="appointments">appointments (Fact)</option>
              <option value="visits">visits (Fact)</option>
              <option value="availability">availability (Log Snapshot)</option>
              <option value="reviews">reviews (Fact)</option>
            </select>
          </div>

          <div className="border-t border-brand-850 pt-3 space-y-2 text-xs">
            <div>
              <span className="text-gray-500 block">Row Count</span>
              <span className="text-white font-bold">{totalRows.toLocaleString()} rows</span>
            </div>
            <div>
              <span className="text-gray-500 block">Description</span>
              <p className="text-gray-400 leading-relaxed font-medium">{getTableStats()}</p>
            </div>
          </div>
        </div>

        {/* Right table view */}
        <div className="lg:col-span-3 space-y-4">
          {error ? (
            <div className="bg-red-950/40 border border-red-800 text-red-400 p-4 rounded-xl text-xs">
              {error}
            </div>
          ) : loading ? (
            <div className="text-center py-12 text-gray-500">Querying database metadata...</div>
          ) : (
            <div className="glass-card rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-center border-b border-brand-850 pb-3">
                <h3 className="font-bold text-white text-md uppercase">Raw Table Rows (Limit 25)</h3>
                <span className="text-xs text-gray-500">{columns.length} columns found</span>
              </div>
              
              <div className="overflow-x-auto max-h-[500px]">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-brand-800 text-xs text-gray-500 font-bold uppercase">
                      {columns.map(col => (
                        <th key={col.name} className="py-2 pr-4">{col.name} <span className="text-[9px] text-accent-gold/60 font-normal">({col.type})</span></th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="text-xs font-mono">
                    {rows.map((row, rIdx) => (
                      <tr key={rIdx} className="border-b border-brand-850 hover:bg-brand-800/10 text-gray-300">
                        {columns.map(col => (
                          <td key={col.name} className="py-2.5 pr-4 max-w-[200px] truncate" title={String(row[col.name] ?? 'NULL')}>
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

// Simple local imports helper for layout
import { Database } from 'lucide-react';
