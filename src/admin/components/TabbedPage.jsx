import React from 'react';
import { useSearchParams } from 'react-router-dom';

/** One admin area with a few clearly named tabs, so the sidebar can stay short. The chosen tab lives in the address (?tab=...). */
export default function TabbedPage({ title, subtitle, tabs }) {
  const [params, setParams] = useSearchParams();
  const current = tabs.find((t) => t.key === params.get('tab')) || tabs[0];
  const Body = current.Component;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {tabs.length > 1 && (
        <div role="tablist" aria-label={title} className="flex gap-2 flex-wrap border-b border-gray-200 pb-3">
          {tabs.map((t) => (
            <button key={t.key} role="tab" aria-selected={t.key === current.key} onClick={() => setParams({ tab: t.key })}
              className={`px-4 py-2 rounded-full text-sm font-semibold border transition ${t.key === current.key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200 hover:border-indigo-600'}`}>
              {t.label}
            </button>
          ))}
        </div>
      )}
      <Body />
    </div>
  );
}
