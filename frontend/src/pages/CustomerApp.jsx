import React, { useState, useEffect } from 'react';
import { fetchShops, fetchRecommendations, joinQueue, bookAppointment, fetchWaitingTimeCharts, fetchDemandCharts } from '../services/api';
import { Search, SlidersHorizontal, Star, Clock, MapPin, Compass, CheckCircle2, ChevronRight, AlertTriangle, Calendar } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, AreaChart, Area } from 'recharts';

export default function CustomerApp() {
  const [shops, setShops] = useState([]);
  const [recs, setRecs] = useState([]);
  const [filters, setFilters] = useState({ search: '', area: '', min_rating: '', shop_type: '' });
  const [selectedShop, setSelectedShop] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const [bookingDate, setBookingDate] = useState('2026-08-30');
  const [bookingTime, setBookingTime] = useState('14:00');
  const [bookingConfirmed, setBookingConfirmed] = useState(null);
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'recommend' | 'bookings'
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Sample Customer details for demo
  const customerId = 125; 

  useEffect(() => {
    loadShops();
  }, [filters]);

  useEffect(() => {
    if (activeTab === 'recommend') {
      loadRecommendations();
    }
  }, [activeTab]);

  const loadShops = async () => {
    setLoading(true);
    try {
      const data = await fetchShops(filters);
      setShops(data);
    } catch (err) {
      setError('Error loading barber shops');
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async () => {
    try {
      const data = await fetchRecommendations();
      setRecs(data);
    } catch (err) {
      setError('Error loading recommendations');
    }
  };

  const handleShopClick = async (shop) => {
    try {
      const waitCharts = await fetchWaitingTimeCharts(shop.shop_id);
      const demandCharts = await fetchDemandCharts(shop.shop_id);
      
      // Combine chart data
      const hours = Array.from({ length: 13 }, (_, i) => i + 8); // 8 AM to 8 PM
      const formatted = hours.map(h => {
        const hourStr = String(h).padStart(2, '0');
        const waitObj = waitCharts.wait_by_hour.find(w => parseInt(w.hour) === h);
        const demandObj = demandCharts.demand_by_hour.find(d => parseInt(d.hour) === h);
        return {
          time: `${h === 12 ? 12 : h % 12} ${h >= 12 ? 'PM' : 'AM'}`,
          wait: waitObj ? waitObj.avg_wait : 10,
          demand: demandObj ? demandObj.visits : 1
        };
      });
      
      setChartData(formatted);
      setSelectedShop({ ...shop, services: shop.services || [] });
      setSelectedService(null);
      setBookingConfirmed(null);
    } catch (err) {
      console.error(err);
    }
  };

  const handleJoinQueue = async () => {
    if (!selectedService) {
      alert("Please select a service first.");
      return;
    }
    try {
      const res = await joinQueue(selectedShop.shop_id, customerId, selectedService.service_id);
      setBookingConfirmed({
        type: 'Walk-In Queue',
        shopName: selectedShop.shop_name,
        serviceName: selectedService.service_name,
        price: selectedService.price,
        queueNo: res.queue_number,
        estimatedWait: res.estimated_wait_minutes,
        time: res.arrival_time,
        startTime: res.estimated_start_time
      });
    } catch (err) {
      alert(err.message);
    }
  };

  const handleBookAppointment = async () => {
    if (!selectedService) {
      alert("Please select a service first.");
      return;
    }
    try {
      const res = await bookAppointment(customerId, selectedShop.shop_id, selectedService.service_id, bookingDate, bookingTime);
      setBookingConfirmed({
        type: 'Scheduled Appointment',
        shopName: selectedShop.shop_name,
        serviceName: selectedService.service_name,
        price: selectedService.price,
        queueNo: res.queue_number,
        estimatedWait: 0,
        time: `${bookingDate} @ ${bookingTime}`,
        startTime: bookingTime
      });
    } catch (err) {
      alert(err.message);
    }
  };

  const getStatusBadge = (wait) => {
    if (wait === 0) return <span className="bg-emerald-900/40 text-emerald-400 border border-emerald-800 text-xs px-2.5 py-1 rounded-full font-medium">🟢 Available</span>;
    if (wait <= 15) return <span className="bg-yellow-950/40 text-yellow-500 border border-yellow-800 text-xs px-2.5 py-1 rounded-full font-medium">🟡 Limited</span>;
    if (wait <= 30) return <span className="bg-orange-950/40 text-orange-500 border border-orange-800 text-xs px-2.5 py-1 rounded-full font-medium">🟠 Busy</span>;
    return <span className="bg-red-950/40 text-red-400 border border-red-800 text-xs px-2.5 py-1 rounded-full font-medium">🔴 Full ({wait} min wait)</span>;
  };

  return (
    <div className="space-y-6">
      {/* Hero Header */}
      <div className="text-center py-6 border-b border-brand-800">
        <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2">
          Find a barber. <span className="text-accent-gold">Skip the wait.</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto">
          Discover high-performance shops, compare current waiting times, and book or join queue instantly.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-brand-850">
        <button 
          onClick={() => setActiveTab('search')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition-all ${activeTab === 'search' ? 'border-accent-gold text-accent-gold bg-brand-800/10' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          <Search size={16} /> Search & Filter
        </button>
        <button 
          onClick={() => setActiveTab('recommend')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 font-medium text-sm transition-all ${activeTab === 'recommend' ? 'border-accent-gold text-accent-gold bg-brand-800/10' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          <Compass size={16} /> Explainable Matches (AI)
        </button>
      </div>

      {activeTab === 'search' && (
        <div className="space-y-6">
          {/* Filters Panel */}
          <div className="glass-card p-4 rounded-xl flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex flex-1 gap-2 w-full">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                <input 
                  type="text" 
                  placeholder="Search by shop name..." 
                  value={filters.search} 
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="w-full pl-10 pr-4 py-2 bg-brand-800/80 border border-brand-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-accent-gold"
                />
              </div>
              <select
                value={filters.area}
                onChange={(e) => setFilters({ ...filters, area: e.target.value })}
                className="bg-brand-800/80 border border-brand-700 rounded-lg px-3 text-white focus:outline-none focus:border-accent-gold"
              >
                <option value="">All Neighborhoods</option>
                <option value="Downtown">Downtown</option>
                <option value="Westside">Westside</option>
                <option value="Northside">Northside</option>
                <option value="Eastside">Eastside</option>
                <option value="Suburbs">Suburbs</option>
              </select>
            </div>
            
            <div className="flex gap-2 w-full md:w-auto">
              <select
                value={filters.shop_type}
                onChange={(e) => setFilters({ ...filters, shop_type: e.target.value })}
                className="w-full bg-brand-800/80 border border-brand-700 rounded-lg p-2 text-white focus:outline-none focus:border-accent-gold"
              >
                <option value="">All Classes</option>
                <option value="Premium">Premium ⭐⭐⭐⭐⭐</option>
                <option value="Standard">Standard</option>
                <option value="Budget">Budget Friendly</option>
                <option value="Bottleneck">Bottleneck (Limited Capacity)</option>
              </select>
            </div>
          </div>

          {/* Shops Grid */}
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading shops...</div>
          ) : shops.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No shops found matching your filters.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {shops.map(shop => (
                <div 
                  key={shop.shop_id} 
                  onClick={() => handleShopClick(shop)}
                  className="glass-card rounded-xl p-5 cursor-pointer hover:border-accent-gold/40 hover:-translate-y-0.5 transition-all flex flex-col justify-between h-64"
                >
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-lg font-bold text-white leading-tight">{shop.shop_name}</h3>
                      {getStatusBadge(shop.estimated_wait_minutes)}
                    </div>
                    
                    <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-3">
                      <span className="flex items-center gap-0.5 text-accent-gold font-medium">
                        <Star size={14} className="fill-accent-gold" /> {shop.rating}
                      </span>
                      <span>•</span>
                      <span>{shop.review_count} reviews</span>
                      <span>•</span>
                      <span className="capitalize">{shop.shop_type}</span>
                    </div>

                    <div className="space-y-1.5 text-sm text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <MapPin size={15} className="text-accent-gold" />
                        <span>{shop.area}, {shop.city} ({shop.distance_km} km)</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock size={15} className="text-accent-gold" />
                        <span>Open: {shop.opening_time} - {shop.closing_time}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-brand-850 flex items-center justify-between">
                    <div className="text-xs">
                      <span className="block text-gray-500">Live queue</span>
                      <span className="text-white font-bold">{shop.queue_length} waiting / {shop.available_seats} seats open</span>
                    </div>
                    <span className="text-accent-gold text-sm font-semibold flex items-center">
                      Join / Book <ChevronRight size={16} />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'recommend' && (
        <div className="space-y-6">
          <div className="bg-brand-850/30 border border-brand-800 rounded-xl p-5 mb-4">
            <h3 className="text-lg font-bold text-accent-gold mb-1">Explainable Recommendation Engine</h3>
            <p className="text-sm text-gray-400">
              Unlike black-box AI algorithms, BarberFlow matches you using a direct weighted model. These shops are scored based on proximity, ratings, wait times, and price value.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {recs.slice(0, 6).map((shop, idx) => (
              <div 
                key={shop.shop_id}
                onClick={() => handleShopClick(shop)}
                className="glass-card rounded-xl p-5 relative cursor-pointer border-brand-800 hover:border-accent-gold/45 transition-all"
              >
                <div className="absolute top-0 right-0 bg-accent-gold text-brand-900 text-xs font-bold px-3 py-1 rounded-tr-xl rounded-bl-xl">
                  {idx + 1}st Best Match ({shop.recommendation_score}%)
                </div>
                
                <h3 className="text-xl font-extrabold text-white mb-1.5">{shop.shop_name}</h3>
                
                <div className="flex items-center gap-2 text-xs mb-4 text-gray-400">
                  <span className="flex items-center text-accent-gold font-bold">
                    <Star size={13} className="fill-accent-gold mr-0.5" /> {shop.rating}
                  </span>
                  <span>•</span>
                  <span>{shop.distance_km} km away</span>
                  <span>•</span>
                  <span>Avg price: ${shop.average_price}</span>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  {shop.reasons.map((r, i) => (
                    <span key={i} className="bg-brand-800/80 text-accent-gold text-xs px-2.5 py-1 rounded-md border border-brand-700 font-semibold">
                      {r}
                    </span>
                  ))}
                </div>

                <div className="border-t border-brand-850 pt-3 flex justify-between items-center text-sm">
                  <div className="text-gray-400">
                    Live Wait Time: <span className="text-white font-bold">{shop.estimated_wait_minutes} mins</span>
                  </div>
                  <span className="text-accent-gold text-sm font-semibold flex items-center">
                    Select Shop <ChevronRight size={16} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Shop Details & Booking Modal */}
      {selectedShop && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="glass-card w-full max-w-4xl rounded-2xl overflow-hidden p-6 md:p-8 space-y-6 relative max-h-[90vh] overflow-y-auto">
            <button 
              onClick={() => setSelectedShop(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white text-xl font-bold p-2"
            >
              ✕
            </button>
            
            {bookingConfirmed ? (
              <div className="text-center py-8 space-y-4 max-w-md mx-auto">
                <CheckCircle2 size={64} className="text-emerald-400 mx-auto" />
                <h3 className="text-2xl font-bold text-white">Booking Confirmed!</h3>
                <div className="bg-brand-800/80 border border-brand-700 p-5 rounded-xl text-left space-y-2">
                  <div className="flex justify-between"><span className="text-gray-500 text-sm">Shop:</span> <span className="font-semibold text-white">{bookingConfirmed.shopName}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500 text-sm">Service:</span> <span className="font-semibold text-white">{bookingConfirmed.serviceName} (${bookingConfirmed.price})</span></div>
                  <div className="flex justify-between"><span className="text-gray-500 text-sm">Type:</span> <span className="font-semibold text-accent-gold">{bookingConfirmed.type}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500 text-sm">Slot/Arrival:</span> <span className="font-semibold text-white">{bookingConfirmed.time}</span></div>
                  {bookingConfirmed.queueNo && (
                    <div className="flex justify-between border-t border-brand-850 pt-2 mt-2">
                      <span className="text-gray-400 font-bold">Queue Ticket:</span> 
                      <span className="font-extrabold text-accent-gold">#{bookingConfirmed.queueNo}</span>
                    </div>
                  )}
                  {bookingConfirmed.estimatedWait > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-500 text-sm">Estimated Wait:</span> 
                      <span className="font-bold text-yellow-500">{bookingConfirmed.estimatedWait} minutes</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-500 text-sm">Est. Service Start:</span> 
                    <span className="font-bold text-white">{bookingConfirmed.startTime}</span>
                  </div>
                </div>
                <button 
                  onClick={() => setSelectedShop(null)}
                  className="w-full bg-accent-gold text-brand-900 font-bold py-2 rounded-lg hover:bg-accent-goldHover transition-accent"
                >
                  Awesome, got it!
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Left side: Information, charts, services */}
                <div className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-extrabold text-white mb-1">{selectedShop.shop_name}</h2>
                    <p className="text-sm text-gray-400">{selectedShop.area}, {selectedShop.city}</p>
                    <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-2">
                      <span className="flex items-center text-accent-gold font-bold"><Star size={13} className="fill-accent-gold mr-0.5" />{selectedShop.rating}</span>
                      <span>•</span>
                      <span>{selectedShop.review_count} reviews</span>
                      <span>•</span>
                      <span className="text-emerald-400 font-bold">Estimated wait: {selectedShop.estimated_wait_minutes} min</span>
                    </div>
                  </div>

                  {/* Typical Demand Chart */}
                  <div className="bg-brand-800/40 p-4 rounded-xl border border-brand-800">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Typical Wait Time & Demand by Hour</h4>
                    <div className="h-44">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient id="colorWait" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#C5A880" stopOpacity={0.4}/>
                              <stop offset="95%" stopColor="#C5A880" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="time" stroke="#757c85" fontSize={10} tickLine={false} />
                          <Tooltip contentStyle={{ backgroundColor: '#121418', borderColor: '#2c3139' }} labelStyle={{ color: '#fff' }} />
                          <Area type="monotone" dataKey="wait" name="Wait Time (min)" stroke="#C5A880" fillOpacity={1} fill="url(#colorWait)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Services List */}
                  <div>
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Select Service</h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {selectedShop.services && selectedShop.services.length > 0 ? (
                        selectedShop.services.map(srv => (
                          <div 
                            key={srv.service_id} 
                            onClick={() => setSelectedService(srv)}
                            className={`p-3 rounded-lg border cursor-pointer flex justify-between items-center transition-all ${selectedService?.service_id === srv.service_id ? 'border-accent-gold bg-brand-800/80' : 'border-brand-800 bg-brand-800/20 hover:border-brand-700'}`}
                          >
                            <div>
                              <span className="block text-white text-sm font-semibold">{srv.service_name}</span>
                              <span className="text-xs text-gray-500">{srv.average_duration_minutes} minutes</span>
                            </div>
                            <span className="text-accent-gold font-bold">${srv.price}</span>
                          </div>
                        ))
                      ) : (
                        <div className="text-gray-500 text-xs">No services listed for this shop.</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right side: Booking and Live Queue booking forms */}
                <div className="border-t lg:border-t-0 lg:border-l border-brand-800 lg:pl-8 pt-6 lg:pt-0 space-y-6">
                  {/* Join Live Queue Box */}
                  <div className="bg-brand-800/40 p-5 rounded-xl border border-brand-800 space-y-3">
                    <h4 className="font-bold text-white text-md flex items-center gap-2">
                      <Clock className="text-accent-gold" size={18} /> Join Virtual Queue
                    </h4>
                    <p className="text-xs text-gray-400">
                      Skip traveling and waiting. Secure a slot right now and arrive when your barber is ready.
                    </p>
                    <div className="bg-brand-900/50 p-3 rounded-lg border border-brand-800 flex justify-between items-center">
                      <span className="text-xs text-gray-500">Live Estimated Wait</span>
                      <span className="text-lg font-bold text-accent-gold">{selectedShop.estimated_wait_minutes} minutes</span>
                    </div>
                    <button 
                      onClick={handleJoinQueue}
                      disabled={!selectedService}
                      className="w-full bg-accent-gold text-brand-900 font-bold py-2.5 rounded-lg hover:bg-accent-goldHover transition-accent disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Join Queue Now
                    </button>
                  </div>

                  {/* Book Appointment Box */}
                  <div className="bg-brand-800/40 p-5 rounded-xl border border-brand-800 space-y-3">
                    <h4 className="font-bold text-white text-md flex items-center gap-2">
                      <Calendar className="text-accent-gold" size={18} /> Book Scheduled Appointment
                    </h4>
                    <p className="text-xs text-gray-400">
                      Reserve a specific calendar slot. Best for planning ahead.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Select Date</label>
                        <input 
                          type="date" 
                          value={bookingDate}
                          onChange={(e) => setBookingDate(e.target.value)}
                          className="w-full bg-brand-900 border border-brand-700 text-xs rounded-lg p-2 text-white focus:outline-none focus:border-accent-gold"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Select Time</label>
                        <select 
                          value={bookingTime}
                          onChange={(e) => setBookingTime(e.target.value)}
                          className="w-full bg-brand-900 border border-brand-700 text-xs rounded-lg p-2 text-white focus:outline-none focus:border-accent-gold"
                        >
                          <option value="09:00">09:00 AM</option>
                          <option value="10:00">10:00 AM</option>
                          <option value="11:00">11:00 AM</option>
                          <option value="12:00">12:00 PM</option>
                          <option value="13:00">01:00 PM</option>
                          <option value="14:00">02:00 PM</option>
                          <option value="15:00">03:00 PM</option>
                          <option value="16:00">04:00 PM</option>
                          <option value="17:00">05:00 PM</option>
                          <option value="18:00">06:00 PM</option>
                          <option value="19:00">07:00 PM</option>
                        </select>
                      </div>
                    </div>

                    <button 
                      onClick={handleBookAppointment}
                      disabled={!selectedService}
                      className="w-full bg-brand-700 text-white font-bold py-2.5 rounded-lg hover:bg-brand-650 transition-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      Book Appointment Slot
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
