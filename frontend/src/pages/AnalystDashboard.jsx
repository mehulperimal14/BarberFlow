import React, { useState, useEffect } from 'react';
import { fetchMarketOverview, fetchDemandCharts, fetchWaitingTimeCharts, fetchShopPerformance, fetchLocationOpportunity } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, ScatterChart, Scatter, ZAxis, LabelList } from 'recharts';
import { Database, TrendingUp, Smile, Map, BarChart3, SlidersHorizontal, Info, Compass } from 'lucide-react';

export default function AnalystDashboard() {
  const [activeSubTab, setActiveSubTab] = useState('overview'); // 'overview' | 'experience' | 'performance' | 'location'
  const [overviewKpis, setOverviewKpis] = useState(null);
  const [demandData, setDemandData] = useState([]);
  const [waitData, setWaitData] = useState([]);
  const [performanceData, setPerformanceData] = useState(null);
  const [locationData, setLocationData] = useState([]);
  
  const [selectedAreaFilter, setSelectedAreaFilter] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadOverviewAndCharts();
  }, [selectedAreaFilter]);

  useEffect(() => {
    if (activeSubTab === 'performance') {
      loadPerformanceData();
    } else if (activeSubTab === 'location') {
      loadLocationOpportunity();
    } else if (activeSubTab === 'experience') {
      loadExperienceCharts();
    }
  }, [activeSubTab]);

  const loadOverviewAndCharts = async () => {
    setLoading(true);
    try {
      const kpis = await fetchMarketOverview(selectedAreaFilter);
      setOverviewKpis(kpis);
      
      const demand = await fetchDemandCharts();
      setDemandData(demand);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadExperienceCharts = async () => {
    try {
      const wait = await fetchWaitingTimeCharts();
      setWaitData(wait);
    } catch (err) {
      console.error(err);
    }
  };

  const loadPerformanceData = async () => {
    try {
      const perf = await fetchShopPerformance();
      setPerformanceData(perf);
    } catch (err) {
      console.error(err);
    }
  };

  const loadLocationOpportunity = async () => {
    try {
      const loc = await fetchLocationOpportunity();
      setLocationData(loc);
    } catch (err) {
      console.error(err);
    }
  };

  // Convert hour response formatting
  const formattedDemandHour = demandData?.demand_by_hour?.map(d => ({
    hour: `${d.hour}:00`,
    visits: d.visits
  })) || [];

  const formattedDemandDay = demandData?.demand_by_day || [];

  const formattedWaitDist = waitData?.wait_distribution || [];
  const formattedWaitHour = waitData?.wait_by_hour?.map(w => ({
    hour: `${w.hour}:00`,
    wait: w.avg_wait
  })) || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-4 border-b border-brand-800">
        <div>
          <h1 className="text-3xl font-extrabold text-white">Business Analytics</h1>
          <p className="text-gray-400 text-sm">Market KPIs, customer satisfaction drivers, spatial opportunities, and bottleneck metrics.</p>
        </div>
        
        <div className="flex gap-2">
          <select 
            value={selectedAreaFilter}
            onChange={(e) => setSelectedAreaFilter(e.target.value)}
            className="bg-brand-800 border border-brand-700 text-white rounded-lg p-2.5 text-xs focus:outline-none"
          >
            <option value="">All Neighborhoods</option>
            <option value="Downtown">Downtown</option>
            <option value="Westside">Westside</option>
            <option value="Northside">Northside</option>
            <option value="Eastside">Eastside</option>
            <option value="Suburbs">Suburbs</option>
          </select>
        </div>
      </div>

      {/* Sub Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-brand-850 pb-2">
        {[
          { id: 'overview', name: 'Market Overview', icon: <TrendingUp size={15} /> },
          { id: 'experience', name: 'Customer Experience', icon: <Smile size={15} /> },
          { id: 'performance', name: 'Shop Performance', icon: <BarChart3 size={15} /> },
          { id: 'location', name: 'Location Opportunity', icon: <Map size={15} /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-accent ${activeSubTab === tab.id ? 'bg-accent-gold text-brand-900' : 'text-gray-400 hover:text-gray-200 hover:bg-brand-800/40'}`}
          >
            {tab.icon} {tab.name}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading analysis datasets...</div>
      ) : (
        <div className="space-y-6">
          
          {activeSubTab === 'overview' && overviewKpis && (
            <div className="space-y-6">
              {/* KPIs Row */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {[
                  { name: 'Total Shops', value: overviewKpis.total_shops },
                  { name: 'Total Customers', value: overviewKpis.total_customers.toLocaleString() },
                  { name: 'Total Visits', value: overviewKpis.total_visits.toLocaleString() },
                  { name: 'Avg Wait time', value: `${overviewKpis.average_wait_minutes}m` },
                  { name: 'Market Rating', value: `${overviewKpis.average_rating} ⭐` },
                  { name: 'Avg Utilization', value: `${overviewKpis.average_utilization_pct}%` },
                ].map((kpi, idx) => (
                  <div key={idx} className="glass-card p-4 rounded-xl text-center space-y-1">
                    <span className="block text-[10px] text-gray-500 font-bold uppercase tracking-wider">{kpi.name}</span>
                    <span className="text-xl font-black text-white">{kpi.value}</span>
                  </div>
                ))}
              </div>

              {/* Demand Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Demand distribution by hour</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={formattedDemandHour}>
                        <defs>
                          <linearGradient id="colorVisits" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#C5A880" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#C5A880" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="hour" stroke="#757c85" fontSize={10} tickLine={false} />
                        <YAxis stroke="#757c85" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                        <Area type="monotone" dataKey="visits" name="Visits Count" stroke="#C5A880" fillOpacity={1} fill="url(#colorVisits)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="glass-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Visits count by weekday</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={formattedDemandDay}>
                        <XAxis dataKey="day_name" stroke="#757c85" fontSize={10} tickLine={false} />
                        <YAxis stroke="#757c85" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                        <Bar dataKey="visits" name="Visits Count" fill="#3c434c" radius={[4, 4, 0, 0]} activeBar={{ fill: '#C5A880' }} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'experience' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Wait time distribution */}
                <div className="glass-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Waiting Time Frequency Distribution</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={formattedWaitDist}>
                        <XAxis dataKey="wait_tier" stroke="#757c85" fontSize={10} tickLine={false} />
                        <YAxis stroke="#757c85" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                        <Bar dataKey="count" name="Reviews count" fill="#C5A880" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Avg wait times hourly */}
                <div className="glass-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Average Waiting Time (min) by Hour</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={formattedWaitHour}>
                        <XAxis dataKey="hour" stroke="#757c85" fontSize={10} tickLine={false} />
                        <YAxis stroke="#757c85" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                        <Area type="monotone" dataKey="wait" name="Avg Wait Minutes" stroke="#d97706" fill="rgba(217, 119, 6, 0.1)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Business QA Box */}
              <div className="glass-card rounded-xl p-5 space-y-3">
                <h3 className="text-md font-bold text-white flex items-center gap-2">
                  <Info size={18} className="text-accent-gold" /> Key Satisfaction Insight
                </h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                  Analysis reveals a strong non-linear correlation between wait time and rating. If waiting times exceed 20 minutes, average customer review ratings drop from 4.8 stars to under 3.5 stars, directly impacting repeat visit velocity.
                </p>
              </div>
            </div>
          )}

          {activeSubTab === 'performance' && performanceData && (
            <div className="space-y-6">
              {/* Quadrant Scatter plot */}
              <div className="glass-card rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Shop Performance Matrix (Demand vs Capacity)</h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <XAxis type="number" dataKey="number_of_seats" name="Capacity (Seats)" stroke="#757c85" domain={[2, 10]} />
                      <YAxis type="number" dataKey="total_visits" name="Demand (Visits)" stroke="#757c85" />
                      <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} />
                      <Scatter name="Shops" data={performanceData.shops_data} fill="#C5A880">
                        <LabelList dataKey="shop_name" position="top" fill="#9fa4ab" fontSize={9} />
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                
                {/* Quadrant Explanation cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                  <div className="bg-brand-850/30 p-3 rounded-lg border border-brand-800">
                    <span className="font-bold text-emerald-400 block mb-1">Leaders (High Demand / High Capacity)</span>
                    <p className="text-gray-500">Optimally scaled. Keep active, high satisfaction levels.</p>
                  </div>
                  <div className="bg-brand-850/30 p-3 rounded-lg border border-brand-800">
                    <span className="font-bold text-yellow-500 block mb-1">Bottlenecks (High Demand / Low Capacity)</span>
                    <p className="text-gray-500">Wait-time risk. Excellent candidates to add chairs or barbers.</p>
                  </div>
                  <div className="bg-brand-850/30 p-3 rounded-lg border border-brand-800">
                    <span className="font-bold text-blue-400 block mb-1">Underutilized (Low Demand / High Capacity)</span>
                    <p className="text-gray-500">Over-supplied. Recommend price promotions or marketing push.</p>
                  </div>
                  <div className="bg-brand-850/30 p-3 rounded-lg border border-brand-800">
                    <span className="font-bold text-gray-400 block mb-1">Low Scale (Low Demand / Low Capacity)</span>
                    <p className="text-gray-500">Niche or struggling shops with small local operation footprint.</p>
                  </div>
                </div>
              </div>

              {/* Rankings Table */}
              <div className="glass-card rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Shop Performance Rankings</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-brand-800 text-xs text-gray-500 font-bold uppercase">
                        <th className="py-2.5">Shop Name</th>
                        <th>Class</th>
                        <th>Seats</th>
                        <th>Total Visits</th>
                        <th>Avg Wait</th>
                        <th>Avg Util</th>
                        <th>Rating</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {performanceData.shops_data.slice(0, 10).map((shop, idx) => (
                        <tr key={idx} className="border-b border-brand-850 hover:bg-brand-800/10 transition-all">
                          <td className="py-3 font-semibold text-white">{shop.shop_name}</td>
                          <td className="capitalize text-gray-400">{shop.shop_type}</td>
                          <td className="text-gray-400">{shop.number_of_seats}</td>
                          <td className="font-bold text-white">{shop.total_visits}</td>
                          <td className="text-gray-400">{shop.avg_wait}m</td>
                          <td className="text-gray-400">{shop.avg_utilization}%</td>
                          <td className="text-accent-gold font-bold">{shop.rating} ★</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'location' && (
            <div className="space-y-6">
              {/* Neighborhood Map mock-up */}
              <div className="glass-card rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Spatial Demand Opportunity Analysis</h3>
                <p className="text-xs text-gray-400">
                  Calculates capacity utilization index by neighborhood. High Opportunity (Red) indicates regions where client demand is extremely high relative to available barber chairs.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {locationData.map((loc, idx) => (
                    <div key={idx} className="bg-brand-800/40 p-5 rounded-xl border border-brand-800 space-y-3 relative">
                      <div className="flex justify-between items-start">
                        <h4 className="font-extrabold text-white text-lg">{loc.area}</h4>
                        <span className="text-[10px] bg-brand-900 px-2 py-0.5 rounded-full border border-brand-700 text-gray-400 font-bold uppercase">
                          {loc.shop_count} Shops
                        </span>
                      </div>
                      
                      <div className="space-y-1.5 text-xs text-gray-400">
                        <div className="flex justify-between"><span>Total Seats:</span> <span className="text-white font-bold">{loc.total_seats} chairs</span></div>
                        <div className="flex justify-between"><span>Visits Volume:</span> <span className="text-white font-bold">{loc.total_visits}</span></div>
                        <div className="flex justify-between"><span>Average Wait:</span> <span className="text-white font-bold">{loc.avg_wait_minutes}m</span></div>
                        <div className="flex justify-between"><span>Visits / Seat Ratio:</span> <span className="text-accent-gold font-black">{loc.visits_per_seat}</span></div>
                      </div>

                      <div className="border-t border-brand-850 pt-2 flex items-center justify-between">
                        <span className="text-xs text-gray-500 font-medium">Market State</span>
                        <span className={`text-xs font-bold ${loc.visits_per_seat >= 200 ? 'text-red-400' : loc.visits_per_seat >= 130 ? 'text-yellow-500' : 'text-emerald-400'}`}>
                          {loc.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
