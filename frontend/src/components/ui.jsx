import React from 'react';
import { AlertTriangle, Info, Loader2 } from 'lucide-react';

export const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
export const AREAS = ['Downtown', 'Westside', 'Northside', 'Eastside', 'Suburbs'];

export const hourLabel = (h) => `${h % 12 === 0 ? 12 : h % 12} ${h >= 12 ? 'PM' : 'AM'}`;
export const fmt = (n, digits = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? '—' : Number(n).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
export const money = (n) => (n === null || n === undefined ? '—' : `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`);

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-gray-500 text-sm" role="status">
      <Loader2 size={16} className="animate-spin" /> {label}
    </div>
  );
}

export function Notice({ tone = 'info', children, className = '' }) {
  const styles = {
    info: 'bg-brand-850/60 border-brand-700 text-gray-300',
    warn: 'bg-amber-950/40 border-amber-800 text-amber-300',
    error: 'bg-red-950/40 border-red-800 text-red-300',
    success: 'bg-emerald-950/40 border-emerald-800 text-emerald-300',
  };
  const Icon = tone === 'info' || tone === 'success' ? Info : AlertTriangle;
  return (
    <div className={`flex items-start gap-2 border rounded-lg p-3 text-xs leading-relaxed ${styles[tone]} ${className}`} role={tone === 'error' ? 'alert' : undefined}>
      <Icon size={15} className="shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  );
}

export function Kpi({ label, value, hint }) {
  return (
    <div className="glass-card p-4 rounded-xl space-y-1 min-w-0">
      <span className="block text-[10px] text-gray-500 font-bold uppercase tracking-wider truncate">{label}</span>
      <span className="block text-xl font-black text-white truncate">{value}</span>
      {hint && <span className="block text-[10px] text-gray-500 leading-snug">{hint}</span>}
    </div>
  );
}

export function Card({ title, subtitle, children, className = '', right }) {
  return (
    <section className={`glass-card rounded-xl p-4 sm:p-5 space-y-4 min-w-0 ${className}`}>
      {(title || right) && (
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider">{title}</h3>}
            {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export const tooltipStyle = {
  contentStyle: { backgroundColor: '#121418', borderColor: '#2c3139', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#fff' },
  itemStyle: { color: '#e1e3e5' },
};

export const selectClass =
  'bg-brand-800 border border-brand-700 text-white rounded-lg p-2 text-xs focus:outline-none focus:border-accent-gold';
export const buttonGold =
  'bg-accent-gold text-brand-900 font-bold rounded-lg hover:bg-accent-goldHover transition-accent disabled:opacity-50 disabled:cursor-not-allowed';
