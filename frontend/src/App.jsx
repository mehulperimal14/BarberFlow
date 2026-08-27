import React, { useState } from 'react';
import CustomerApp from './pages/CustomerApp';
import BarberDashboard from './pages/BarberDashboard';
import AnalystDashboard from './pages/AnalystDashboard';
import PredictionsView from './pages/PredictionsView';
import DataExplorer from './pages/DataExplorer';
import { Compass, Users, BarChart3, BrainCircuit, Database } from 'lucide-react';

export default function App() {
  const [activeMode, setActiveMode] = useState('customer'); // 'customer' | 'barber' | 'analyst' | 'ml' | 'explorer'

  const renderActiveMode = () => {
    switch (activeMode) {
      case 'customer':
        return <CustomerApp />;
      case 'barber':
        return <BarberDashboard />;
      case 'analyst':
        return <AnalystDashboard />;
      case 'ml':
        return <PredictionsView />;
      case 'explorer':
        return <DataExplorer />;
      default:
        return <CustomerApp />;
    }
  };

  return (
    <div className="min-h-screen bg-brand-900 bg-grid-pattern text-gray-100 flex flex-col">
      {/* Sticky Premium Top Nav */}
      <header className="sticky top-0 z-40 bg-brand-900/90 backdrop-blur-md border-b border-brand-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-black text-white tracking-wider flex items-center gap-1.5">
              <span>Barber</span><span className="text-accent-gold">Flow</span> 💈
            </span>
          </div>

          {/* Mode Toggles */}
          <nav className="flex space-x-1 bg-brand-850 p-1 rounded-lg border border-brand-800">
            {[
              { id: 'customer', name: 'Customer App', icon: <Compass size={14} /> },
              { id: 'barber', name: 'Barber Panel', icon: <Users size={14} /> },
              { id: 'analyst', name: 'Analyst Dashboard', icon: <BarChart3 size={14} /> },
              { id: 'ml', name: 'ML Predictions', icon: <BrainCircuit size={14} /> },
              { id: 'explorer', name: 'Data Explorer', icon: <Database size={14} /> }
            ].map(mode => (
              <button
                key={mode.id}
                onClick={() => setActiveMode(mode.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-accent ${activeMode === mode.id ? 'bg-accent-gold text-brand-900' : 'text-gray-400 hover:text-gray-200 hover:bg-brand-800/40'}`}
              >
                {mode.icon}
                <span className="hidden md:inline">{mode.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderActiveMode()}
      </main>

      {/* Footer */}
      <footer className="border-t border-brand-800 bg-brand-900/40 py-6 text-center text-xs text-gray-500">
        <p>© 2026 BarberFlow Platform. Built for Data Analytics & ML Portfolio demonstration.</p>
      </footer>
    </div>
  );
}
