import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardCheck, LifeBuoy, HelpCircle, CreditCard, PackageX, ArrowRight, CheckCircle2 } from 'lucide-react';
import api from '../../services/api';
import { RiskGauge } from './SellerProfileView';

// One calm colour per kind of work. Full class names, so Tailwind can see them.
const TONES = {
  indigo: { chip: 'bg-indigo-100 text-indigo-700', bar: 'bg-indigo-500', card: 'from-indigo-50 border-indigo-200', pill: 'bg-indigo-100 text-indigo-800' },
  sky: { chip: 'bg-sky-100 text-sky-700', bar: 'bg-sky-500', card: 'from-sky-50 border-sky-200', pill: 'bg-sky-100 text-sky-800' },
  violet: { chip: 'bg-violet-100 text-violet-700', bar: 'bg-violet-500', card: 'from-violet-50 border-violet-200', pill: 'bg-violet-100 text-violet-800' },
  amber: { chip: 'bg-amber-100 text-amber-700', bar: 'bg-amber-500', card: 'from-amber-50 border-amber-200', pill: 'bg-amber-100 text-amber-900' },
  rose: { chip: 'bg-rose-100 text-rose-700', bar: 'bg-rose-500', card: 'from-rose-50 border-rose-200', pill: 'bg-rose-100 text-rose-800' },
};

const LEVEL = { bad: 'bg-red-50 text-red-800 border-red-200', warn: 'bg-amber-50 text-amber-900 border-amber-200', info: 'bg-blue-50 text-blue-900 border-blue-200', good: 'bg-green-50 text-green-900 border-green-200' };


/** The first thing an admin sees: what needs a decision right now, as big cards and a plain-language briefing. */
export default function AdminAttention() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/overview').then((r) => setD(r.data)).catch(() => setD(null)); }, []);
  if (!d) return null;
  const c = d.cards;
  const tiles = [
    { to: '/admin/sellers?tab=applications', icon: ClipboardCheck, n: c.applications, tone: 'indigo', label: 'Seller applications to review', hot: c.applications > 0 },
    { to: '/admin/support', icon: LifeBuoy, n: c.openTickets, tone: 'sky', label: c.overdueTickets ? `Support tickets (${c.overdueTickets} overdue)` : 'Open support tickets', hot: c.overdueTickets > 0 },
    { to: '/admin/enquiries', icon: HelpCircle, n: c.openEnquiries, tone: 'violet', label: 'Customer questions unanswered', hot: c.openEnquiries > 0 },
    { to: '/admin/payments', icon: CreditCard, n: c.awaitingPayment, tone: 'amber', label: 'Orders waiting for payment', hot: c.awaitingPayment > 0 },
    { to: '/admin/inventory', icon: PackageX, n: c.outOfStock + c.lowStock, tone: 'rose', label: 'Products low or out of stock', hot: c.outOfStock > 0 },
  ];
  return (
    <section aria-label="Needs your attention" className="space-y-4">
      <h2 className="text-lg font-extrabold text-gray-900">Needs your attention</h2>
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {tiles.map((t) => {
          const tone = TONES[t.tone];
          const todo = t.n > 0;
          return (
            <Link key={t.label} to={t.to} className={`group relative overflow-hidden rounded-2xl border p-5 pt-6 transition duration-200 hover:-translate-y-1 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 ${t.hot ? `bg-gradient-to-b ${tone.card} to-white` : 'bg-white border-gray-200'}`}>
              <span className={`absolute inset-x-0 top-0 h-1 ${todo ? tone.bar : 'bg-emerald-400'}`} aria-hidden="true" />
              <div className="flex items-center justify-between gap-2">
                <span className={`w-11 h-11 rounded-xl grid place-items-center ${todo ? tone.chip : 'bg-emerald-50 text-emerald-600'}`}><t.icon className="w-5 h-5" aria-hidden="true" /></span>
                {todo
                  ? <span className={`text-[11px] font-bold rounded-full px-2.5 py-1 ${tone.pill}`}>{t.hot ? 'Needs action' : 'To review'}</span>
                  : <span className="text-[11px] font-bold rounded-full px-2.5 py-1 bg-emerald-50 text-emerald-700 inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" aria-hidden="true" /> All clear</span>}
              </div>
              <div className="mt-4 text-4xl font-extrabold text-gray-900 tabular-nums leading-none">{t.n}</div>
              <div className="text-sm text-gray-600 mt-1.5 min-h-[40px]">{t.label}</div>
              <div className="mt-2 text-xs font-semibold text-gray-400 group-hover:text-indigo-600 inline-flex items-center gap-1 transition">Open <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" /></div>
            </Link>
          );
        })}
      </div>
      {d.applications?.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <h3 className="font-bold text-gray-900 mb-1">New sellers waiting for you</h3>
          <p className="text-sm text-gray-600 mb-3">Risk is worked out from how well their documents match what they typed. Lower is safer. You always make the final decision.</p>
          <ul className="divide-y divide-gray-100">
            {d.applications.map((a) => (
              <li key={a.id}>
                <Link to="/admin/sellers?tab=applications" className="flex flex-wrap items-center gap-3 py-3 hover:bg-gray-50 rounded-xl px-2">
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-gray-900">{a.company}</div>
                    <div className="text-sm text-gray-600">{a.applicant} · {a.city} · {a.documents} document{a.documents === 1 ? '' : 's'} · sent {a.submitted}</div>
                    {a.reasons.length > 0 && <div className="text-xs text-amber-800 mt-0.5">Check: {a.reasons.join(' · ')}</div>}
                  </div>
                  <RiskGauge score={a.riskScore} category={a.documents < 2 ? 'Incomplete' : a.riskCategory} size="sm" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="rounded-2xl border border-gray-200 bg-white p-5">
        <h3 className="font-bold text-gray-900 mb-3">Today's briefing</h3>
        <ul className="space-y-2">
          {d.briefing.map((b) => (
            <li key={b.text} className={`rounded-xl border px-4 py-2.5 text-sm ${LEVEL[b.level]}`}>
              {b.text} {b.link && <Link to={b.link} className="font-bold underline ml-1">Open</Link>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
