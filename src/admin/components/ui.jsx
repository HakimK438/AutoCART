import React from 'react';
import { Download } from 'lucide-react';

// Shared look for the admin pages, matching the existing admin cards: white, thin border, soft shadow, brand colour for the main accent.
const TINT = {
  indigo: 'bg-indigo-50 text-indigo-600',
  emerald: 'bg-emerald-50 text-emerald-600',
  amber: 'bg-amber-50 text-amber-600',
  rose: 'bg-rose-50 text-rose-600',
  sky: 'bg-sky-50 text-sky-600',
  slate: 'bg-gray-100 text-gray-600',
};

export const StatCard = ({ icon: Icon, label, value, hint, tone = 'indigo' }) => (
  <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between gap-3">
    <div className="min-w-0 space-y-1">
      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">{label}</p>
      <h3 className="text-2xl font-extrabold text-gray-900 tracking-tight tabular-nums truncate">{value}</h3>
      {hint && <p className="text-[11px] text-gray-400">{hint}</p>}
    </div>
    {Icon && <div className={`p-3.5 rounded-2xl shrink-0 ${TINT[tone] || TINT.indigo}`}><Icon className="w-6 h-6" aria-hidden="true" /></div>}
  </div>
);

export const Panel = ({ title, subtitle, action, children, className = '' }) => (
  <section className={`bg-white rounded-2xl border border-gray-100 shadow-sm ${className}`}>
    {(title || action) && (
      <div className="flex items-start justify-between gap-3 flex-wrap px-5 pt-5">
        <div>
          <h2 className="font-bold text-gray-900">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
    )}
    <div className="p-5">{children}</div>
  </section>
);

export const ExportButton = ({ onClick, disabled, label = 'Download CSV' }) => (
  <button onClick={onClick} disabled={disabled}
    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition disabled:opacity-40 whitespace-nowrap">
    <Download className="w-4 h-4" aria-hidden="true" /> {label}
  </button>
);

export const Pill = ({ active, onClick, children }) => (
  <button onClick={onClick} aria-pressed={active}
    className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${active ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200 hover:border-indigo-600'}`}>{children}</button>
);
