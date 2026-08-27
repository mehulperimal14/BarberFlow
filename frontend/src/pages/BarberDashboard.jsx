import React, { useState, useEffect } from 'react';
import { fetchShops, fetchQueue, skipQueue, joinQueue, fetchShopAnalytics } from '../services/api';
import { Users, Clock, Flame, CreditCard, ChevronRight, UserPlus, Trash, Check, Play, Lightbulb } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, BarChart, Bar } from 'recharts';

export default function BarberDashboard() {
  const [shops, setShops] = useState([]);
  const [selectedShopId, setSelectedShopId] = useState(1);
  const [queue, setQueue] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [showAddWalkin, setShowAddWalkin] = useState(false);
  const [walkinCustId, setWalkinCustId] = useState('');
  const [walkinSrvId, setWalkinSrvId] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadShops();
  }, []);

  useEffect(() => {
    if (selectedShopId) {
      loadQueueAndAnalytics();
    }
  }, [selectedShopId]);

  const loadShops = async () => {
    try {
      const data = await fetchShops();
      setShops(data);
      if (data.length > 0) {
        setSelectedShopId(data[0].shop_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadQueueAndAnalytics = async () => {
    setLoading(true);
    try {
      const qData = await fetchQueue(selectedShopId);
      setQueue(qData);
      
      const aData = await fetchShopAnalytics(selectedShopId);
      setAnalytics(aData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartService = (visitId) => {
    // Modify status locally for demo simulation
    setQueue(prev => prev.map(q => q.visit_id === visitId ? { ...q, status: "In Service" } : q));
  };

  const handleCompleteService = (visitId) => {
    setQueue(prev => prev.map(q => q.visit_id === visitId ? { ...q, status: "Completed" } : q));
  };

  const handleSkip = async (visitId) => {
    if (!confirm("Are you sure you want to skip/cancel this customer?")) return;
    try {
      await skipQueue(visitId);
      loadQueueAndAnalytics();
    } catch (err) {
      alert("Error removing customer");
    }
  };

  const handleAddWalkinSubmit = async (e) => {
    e.preventDefault();
    if (!walkinCustId || !walkinSrvId) {
      alert("Please enter customer ID and select a service");
      return;
    }
    try {
      await joinQueue(selectedShopId, parseInt(walkinCustId), parseInt(walkinSrvId));
      setShowAddWalkin(false);
      setWalkinCustId('');
      loadQueueAndAnalytics();
    } catch (err) {
      alert(err.message);
    }
  };

  // Safe fallback KPI values
  const totalVisits = queue.length;
  const inService = queue.filter(q => q.status === "In Service").length;
  const waiting = queue.filter(q => q.status === "Waiting").length;
  
  const totalRevenue = analytics?.kpis?.total_revenue || 0.0;
  const avgWait = analytics?.kpis?.avg_wait || 0;
  const repeatRate = analytics?.repeat_customer_rate_pct || 0;

  // Format charts
  const revByServiceData = analytics?.services_revenue?.map(s => ({
    name: s.service_name,
    visits: s.count,
    revenue: s.revenue
  })) || [];

  return (
    <div className="space-y-6">
      {/* Top Selector */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-4 border-b border-brand-800">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Barber Dashboard</h1>
          <p className="text-gray-400 text-sm">Manage queue flow, add walk-ins, and view daily analytics.</p>
        </div>
        <div>
          <select 
            value={selectedShopId}
            onChange={(e) => setSelectedShopId(parseInt(e.target.value))}
            className="bg-brand-800 border border-brand-700 text-white rounded-lg p-2.5 text-sm focus:outline-none focus:border-accent-gold"
          >
            {shops.map(shop => (
              <option key={shop.shop_id} value={shop.shop_id}>{shop.shop_name}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading shop data...</div>
      ) : (
        <div className="space-y-6">
          {/* Today's KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card p-5 rounded-xl flex items-center gap-4">
              <div className="p-3 bg-brand-800 rounded-lg text-accent-gold"><Users size={24} /></div>
              <div>
                <span className="block text-xs text-gray-500 font-bold uppercase">Queue length</span>
                <span className="text-2xl font-black text-white">{waiting} waiting <span className="text-xs font-normal text-gray-400">({inService} busy)</span></span>
              </div>
            </div>
            
            <div className="glass-card p-5 rounded-xl flex items-center gap-4">
              <div className="p-3 bg-brand-800 rounded-lg text-accent-gold"><Clock size={24} /></div>
              <div>
                <span className="block text-xs text-gray-500 font-bold uppercase">Avg wait time</span>
                <span className="text-2xl font-black text-white">{avgWait} mins</span>
              </div>
            </div>

            <div className="glass-card p-5 rounded-xl flex items-center gap-4">
              <div className="p-3 bg-brand-800 rounded-lg text-accent-gold"><CreditCard size={24} /></div>
              <div>
                <span className="block text-xs text-gray-500 font-bold uppercase">Total revenue</span>
                <span className="text-2xl font-black text-white">${totalRevenue.toLocaleString()}</span>
              </div>
            </div>

            <div className="glass-card p-5 rounded-xl flex items-center gap-4">
              <div className="p-3 bg-brand-800 rounded-lg text-accent-gold"><Flame size={24} /></div>
              <div>
                <span className="block text-xs text-gray-500 font-bold uppercase">Repeat clients</span>
                <span className="text-2xl font-black text-white">{repeatRate}%</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Live Queue Table (2/3 width) */}
            <div className="lg:col-span-2 glass-card rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-bold text-white">Live Queue Management</h3>
                <button 
                  onClick={() => setShowAddWalkin(true)}
                  className="flex items-center gap-1.5 bg-accent-gold hover:bg-accent-goldHover text-brand-900 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-accent"
                >
                  <UserPlus size={15} /> Add Walk-in
                </button>
              </div>

              {/* Add Walkin Dialog */}
              {showAddWalkin && (
                <form onSubmit={handleAddWalkinSubmit} className="bg-brand-800/60 p-4 border border-brand-700 rounded-xl grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Customer ID (1-5000)</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 12"
                      value={walkinCustId}
                      onChange={(e) => setWalkinCustId(e.target.value)}
                      className="w-full bg-brand-950 border border-brand-700 rounded-lg text-xs p-2 text-white focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Select Service</label>
                    <select
                      value={walkinSrvId}
                      onChange={(e) => setWalkinSrvId(e.target.value)}
                      className="w-full bg-brand-950 border border-brand-700 rounded-lg text-xs p-2 text-white focus:outline-none"
                    >
                      <option value="">Choose Service</option>
                      {analytics?.services_revenue?.map((s, idx) => (
                        <option key={idx} value={idx + 1}>{s.service_name}</option> // Mock match service_id
                      ))}
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button type="submit" className="flex-1 bg-accent-gold text-brand-900 text-xs font-bold py-2 rounded-lg">Check-in</button>
                    <button type="button" onClick={() => setShowAddWalkin(false)} className="bg-brand-700 text-white text-xs font-bold py-2 px-3 rounded-lg">Cancel</button>
                  </div>
                </form>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-brand-800 text-xs text-gray-500 font-bold uppercase">
                      <th className="py-2.5">Ticket</th>
                      <th>Customer Info</th>
                      <th>Service</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="text-center py-6 text-gray-500 text-sm">Queue is empty.</td>
                      </tr>
                    ) : (
                      queue.map((item, idx) => (
                        <tr key={item.visit_id} className="border-b border-brand-850 hover:bg-brand-800/10 text-sm transition-all">
                          <td className="py-3 font-bold text-accent-gold">#{idx + 1}</td>
                          <td>
                            <span className="block text-white font-semibold">User {item.customer_id}</span>
                            <span className="text-xs text-gray-500">{item.gender}, {item.age_group}</span>
                          </td>
                          <td>
                            <span className="block text-white font-medium">{item.service_name}</span>
                            <span className="text-xs text-gray-500">{item.service_duration_minutes} min</span>
                          </td>
                          <td>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${item.visit_type === 'Appointment' ? 'bg-indigo-900/30 text-indigo-400 border border-indigo-900' : 'bg-amber-900/30 text-amber-400 border border-amber-900'}`}>
                              {item.visit_type}
                            </span>
                          </td>
                          <td>
                            <span className={`text-xs font-semibold ${item.status === 'Completed' ? 'text-gray-500' : item.status === 'In Service' ? 'text-emerald-400' : 'text-yellow-500'}`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="text-right py-3 space-x-1.5">
                            {item.status === "Waiting" && (
                              <button 
                                onClick={() => handleStartService(item.visit_id)}
                                className="bg-brand-700 hover:bg-brand-650 text-white p-1.5 rounded-md text-xs font-bold inline-flex items-center gap-1 transition-all"
                                title="Start Service"
                              >
                                <Play size={12} /> Start
                              </button>
                            )}
                            {item.status === "In Service" && (
                              <button 
                                onClick={() => handleCompleteService(item.visit_id)}
                                className="bg-emerald-600 hover:bg-emerald-555 text-white p-1.5 rounded-md text-xs font-bold inline-flex items-center gap-1 transition-all"
                                title="Complete"
                              >
                                <Check size={12} /> Finish
                              </button>
                            )}
                            {item.status !== "Completed" && (
                              <button 
                                onClick={() => handleSkip(item.visit_id)}
                                className="bg-brand-850 hover:bg-red-950/40 text-gray-400 hover:text-red-400 border border-brand-800 p-1.5 rounded-md text-xs transition-all"
                                title="Skip customer"
                              >
                                <Trash size={12} />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Sidebar Suggestions & Charts (1/3 width) */}
            <div className="space-y-6">
              {/* Automated Insights */}
              <div className="glass-card rounded-xl p-5 space-y-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Lightbulb size={20} className="text-accent-gold" /> Business Optimization
                </h3>
                <div className="space-y-3">
                  {analytics?.business_recommendations?.map((rec, i) => (
                    <div key={i} className="bg-brand-850/40 border border-brand-800 p-3 rounded-lg space-y-1">
                      <span className="block text-xs font-bold text-accent-gold">{rec.type}</span>
                      <p className="text-xs text-gray-400 leading-relaxed">{rec.message}</p>
                    </div>
                  ))}
                  {!analytics?.business_recommendations?.length && (
                    <p className="text-gray-500 text-xs text-center py-4">No recommendations at this time.</p>
                  )}
                </div>
              </div>

              {/* Service Sales Performance Chart */}
              <div className="glass-card rounded-xl p-5">
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Volume by Service Category</h3>
                <div className="h-44">
                  {revByServiceData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={revByServiceData.slice(0, 4)}>
                        <XAxis dataKey="name" stroke="#757c85" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                        <Bar dataKey="visits" name="Visits" fill="#C5A880" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-gray-500 text-xs text-center py-12">No sales logs found.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
