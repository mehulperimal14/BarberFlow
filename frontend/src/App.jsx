import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Compass, Users, BarChart3, BrainCircuit, Database } from 'lucide-react';
import { fetchMeta } from './services/api';
import { Loading, Notice } from './components/ui';

const CustomerApp = lazy(() => import('./pages/CustomerApp'));
const BarberDashboard = lazy(() => import('./pages/BarberDashboard'));
const AnalystDashboard = lazy(() => import('./pages/AnalystDashboard'));
const PredictionsView = lazy(() => import('./pages/PredictionsView'));
const DataExplorer = lazy(() => import('./pages/DataExplorer'));

const MODES = [
  { id: 'customer', name: 'Customer App', short: 'Customer', icon: Compass, Page: CustomerApp },
  { id: 'barber', name: 'Barber Panel', short: 'Barber', icon: Users, Page: BarberDashboard },
  { id: 'analyst', name: 'Analyst Dashboard', short: 'Analytics', icon: BarChart3, Page: AnalystDashboard },
  { id: 'ml', name: 'ML Predictions', short: 'ML', icon: BrainCircuit, Page: PredictionsView },
  { id: 'explorer', name: 'Data Explorer', short: 'Data', icon: Database, Page: DataExplorer },
];

const modeFromHash = () => {
  const [id] = window.location.hash.replace(/^#\/?/, '').split('/');
  return MODES.some(m => m.id === id) ? id : 'customer';
};

export default function App() {
  const [activeMode, setActiveMode] = useState(modeFromHash);
  const [meta, setMeta] = useState(null);
  const [metaError, setMetaError] = useState('');

  useEffect(() => {
    const onHash = () => setActiveMode(modeFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(err => setMetaError(err.message));
  }, []);

  const go = (id) => {
    window.location.hash = `/${id}`;
    setActiveMode(id);
    window.scrollTo({ top: 0 });
  };
  const { Page } = MODES.find(m => m.id === activeMode);

  return (
    <div className="min-h-screen bg-brand-900 bg-grid-pattern text-gray-100 flex flex-col">
      <header className="sticky top-0 z-40 bg-brand-900/90 backdrop-blur-md border-b border-brand-800">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-2 sm:h-16 flex flex-col sm:flex-row items-center justify-between gap-2">
          <a href="#/customer" onClick={(e) => { e.preventDefault(); go('customer'); }}
             className="text-xl font-black text-white tracking-wider flex items-center gap-1.5">
            <span>Barber</span><span className="text-accent-gold">Flow</span> <span aria-hidden>💈</span>
          </a>
          <nav aria-label="Main" className="w-full sm:w-auto overflow-x-auto">
            <div className="flex space-x-1 bg-brand-850 p-1 rounded-lg border border-brand-800 w-max mx-auto">
              {MODES.map(({ id, name, short, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => go(id)}
                  aria-current={activeMode === id ? 'page' : undefined}
                  className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md text-xs font-bold transition-accent whitespace-nowrap ${activeMode === id ? 'bg-accent-gold text-brand-900' : 'text-gray-400 hover:text-gray-200 hover:bg-brand-800/40'}`}
                >
                  <Icon size={14} />
                  <span className="lg:hidden">{short}</span>
                  <span className="hidden lg:inline">{name}</span>
                </button>
              ))}
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-grow max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-4">
        {metaError && <Notice tone="error">{metaError}</Notice>}
        {meta && !meta.live_queue_enabled && (
          <Notice tone="warn">
            Read-only demo: the live queue and new bookings need a persistent database, which isn't
            configured on this deployment. Analytics, predictions and the data explorer work normally.
          </Notice>
        )}
        <Suspense fallback={<Loading />}>
          <Page meta={meta} />
        </Suspense>
      </main>

      <footer className="border-t border-brand-800 bg-brand-900/40 py-6 px-4 text-center text-xs text-gray-500 space-y-1">
        <p>
          BarberFlow — portfolio project. Historical data is <strong className="text-gray-400">simulated</strong>
          {meta?.dataset ? ` (${meta.dataset.start_date} to ${meta.dataset.end_date})` : ''}; live queue and
          bookings {meta?.live_queue_enabled ? 'are stored in a real database' : 'are disabled here'}.
        </p>
        <p>
          <a className="text-accent-gold hover:underline" href="/api/docs" target="_blank" rel="noreferrer">API docs</a>
          {' · '}
          <a className="text-accent-gold hover:underline" href="https://github.com/mehulperimal14/BarberFlow" target="_blank" rel="noreferrer">Source on GitHub</a>
        </p>
      </footer>
    </div>
  );
}
