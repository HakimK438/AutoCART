import React, { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, XCircle, MessageSquareWarning, PauseCircle, RefreshCw, Search, Inbox, Mail, Phone, MapPin, ChevronRight, ArrowLeft, X, Sparkles, BadgeCheck, Eye, ShieldCheck } from 'lucide-react';
import api from '../../services/api';
import SellerProfileView, { RiskGauge, readiness } from './SellerProfileView';
import SellerDP from './SellerDP';
import '../../storefront/forms.css';

// Only the views an admin actually needs; every other status is still visible under All (each row shows its own status).
const TABS = [
  ['DECIDE', 'Needs your decision', ['PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW']],
  ['APPROVED', 'Approved', ['APPROVED']],
  ['', 'All', null],
];
const TONE = {
  PENDING_ADMIN_APPROVAL: 'bg-blue-100 text-blue-800', NEEDS_MANUAL_REVIEW: 'bg-amber-100 text-amber-800', NEEDS_MORE_INFORMATION: 'bg-orange-100 text-orange-800',
  APPROVED: 'bg-green-100 text-green-800', REJECTED: 'bg-red-100 text-red-800', SUSPENDED: 'bg-gray-200 text-gray-800', DRAFT: 'bg-gray-100 text-gray-700',
};
const label = (s) => (s === 'DRAFT' ? 'Not submitted yet' : String(s || '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()));

const Fact = ({ label: l, value, bad }) => (
  <div className={`rounded-xl border p-3 ${bad ? 'border-amber-300 bg-amber-50' : 'border-gray-200 bg-white'}`}><div className="text-xs text-gray-500">{l}</div><div className="text-lg font-extrabold text-gray-900 mt-0.5">{value}</div></div>
);

/** Review one seller application: the facts first (risk, checklist, Aadhaar, PAN, location), then the decision. */
export default function SellerOnboardingAI() {
  const [tab, setTab] = useState('');   // "All" first, so a brand-new sign-up is never hidden behind another tab
  const [allRows, setAllRows] = useState([]);
  const [find, setFind] = useState('');
  const needle = find.trim().toLowerCase();
  const inTab = (key) => { const t = TABS.find((x) => x[0] === key); return t && t[2] ? allRows.filter((a) => t[2].includes(a.status)) : allRows; };
  const rows = inTab(tab)
    .filter((a) => !needle || `${a.companyName} ${a.applicantName} ${a.city}`.toLowerCase().includes(needle));
  const count = (key) => inTab(key).length;
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [reason, setReason] = useState('');
  const [mode, setMode] = useState(null); // REJECT | REQUEST_INFO | SUSPEND
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [loadError, setLoadError] = useState('');

  const [triage, setTriage] = useState(null);  // autopilot's recommendation for every waiting application
  const [autoBusy, setAutoBusy] = useState(false);
  // The admin sets the highest risk score they accept; everything complete and matching at or under it can be approved in one click.
  const [limit, setLimit] = useState(() => { try { return Number(localStorage.getItem('autopilot_risk_limit')) || 25; } catch { return 25; } });
  const changeLimit = (v) => { const n = Math.max(0, Math.min(100, Number(v) || 0)); setLimit(n); try { localStorage.setItem('autopilot_risk_limit', String(n)); } catch { /* storage blocked */ } };
  const advice = Object.fromEntries((triage?.rows || []).map((r) => [r.id, r]));
  const readyRows = (triage?.rows || []).filter((r) => r.action === 'READY' && r.riskScore <= limit);
  const overLimit = (triage?.rows || []).filter((r) => r.action === 'READY' && r.riskScore > limit).length;
  const askRows = (triage?.rows || []).filter((r) => r.action === 'ASK');
  const eyeRows = (triage?.rows || []).filter((r) => r.action === 'REVIEW').length + overLimit;

  const loadList = useCallback(async () => {
    try {
      const { data } = await api.get('/seller/applications');
      setAllRows(data); setLoadError('');
      api.get('/admin/triage').then((r) => setTriage(r.data)).catch(() => setTriage(null));
    } catch (e) { setLoadError(e?.response?.status === 403 ? 'Only administrators can see applications.' : 'Could not load applications.'); }
  }, []);
  useEffect(() => { loadList(); }, [loadList]);

  // Autopilot does the routine part. It only recommends: these buttons run the same admin actions, after the admin confirms.
  const runAutopilot = async (kind) => {
    const todo = kind === 'READY' ? readyRows : askRows;
    const ask = kind === 'READY'
      ? `Approve ${todo.length} seller${todo.length === 1 ? '' : 's'} with risk ${limit} or lower? Their stores go live straight away.`
      : `Ask ${todo.length} seller${todo.length === 1 ? '' : 's'} to add their missing documents? They will get a message.`;
    if (!todo.length || !window.confirm(ask)) return;
    setAutoBusy(true);
    let done = 0;
    for (const r of todo) {
      try {
        await api.post(`/admin/seller-applications/${r.id}/action`, kind === 'READY' ? { action: 'APPROVE', auto: true } : { action: 'REQUEST_INFO', reason: r.message, auto: true });
        done += 1;
      } catch { /* the server re-checks everything; a failed one simply stays in the list */ }
    }
    setToast({ text: kind === 'READY' ? `${done} of ${todo.length} approved and live.` : `${done} of ${todo.length} reminders sent.` });
    setAutoBusy(false);
    loadList();
  };

  const open = async (id) => {
    setSelected(id); setMode(null); setReason(''); setProfile(null); setToast(null);
    try { const { data } = await api.get(`/seller/applications/${id}`); setProfile(data); } catch { setToast({ bad: true, text: 'Could not open that application.' }); }
  };

  const close = () => { setSelected(null); setProfile(null); setMode(null); setReason(''); };
  // The full-screen view: Escape closes it and the page behind does not scroll.
  useEffect(() => {
    if (!selected) return undefined;
    const esc = (e) => { if (e.key === 'Escape') close(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', esc);
    return () => { window.removeEventListener('keydown', esc); document.body.style.overflow = prev; };
  }, [selected]);

  const decide = async (action) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/admin/seller-applications/${selected}/action`, { action, reason });
      setProfile(data.profile); setMode(null); setReason('');
      setToast({ text: { APPROVE: 'Approved. The seller and store are live.', REJECT: 'Rejected. The seller can see your reason.', REQUEST_INFO: 'Sent back to the seller.', SUSPEND: 'Store suspended.' }[action] });
      loadList();
    } catch (e) { setToast({ bad: true, text: e?.response?.data?.detail || 'That did not work.' }); }
    setBusy(false);
  };

  const p = profile;
  const canDecide = p && ['PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW'].includes(p.status);
  const blockers = p ? readiness(p).blockers : [];

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-xl font-extrabold text-gray-900 tracking-tight">Seller onboarding</h2>
          <p className="text-sm text-gray-500 mt-0.5 max-w-xl">New sellers apply here. We check their documents for you, so you only decide the ones that need a person.</p>
        </div>
        <button onClick={loadList} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm font-semibold hover:bg-gray-50"><RefreshCw className="w-4 h-4" /> Refresh</button>
      </div>

      {toast && !selected && <div role="status" className={`px-4 py-3 rounded-xl text-sm font-semibold ${toast.bad ? 'bg-red-50 text-red-800' : 'bg-green-50 text-green-800'}`}>{toast.text}</div>}

      {triage && triage.rows.length > 0 && (
        <section aria-label="What to do with the new sellers" className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="px-5 sm:px-6 pt-5 pb-4">
            <h3 className="text-lg font-bold text-gray-900">{triage.rows.length} new seller{triage.rows.length === 1 ? ' is' : 's are'} waiting</h3>
            <p className="text-sm text-gray-600 mt-0.5">We already checked their documents. Here is what to do with each group. Nothing happens until you press a button.</p>
          </div>

          <ul className="divide-y divide-gray-100 border-t border-gray-100">
            <li className="flex flex-wrap items-center gap-4 px-5 sm:px-6 py-4">
              <span className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-700 grid place-items-center text-2xl font-extrabold tabular-nums shrink-0">{readyRows.length}</span>
              <div className="min-w-0 flex-1 basis-60">
                <div className="font-bold text-gray-900 flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" /> Ready to approve</div>
                <p className="text-sm text-gray-600">Everything matches and the risk score is {limit} or lower. Safe to say yes.</p>
              </div>
              <button disabled={!readyRows.length || autoBusy} onClick={() => runAutopilot('READY')} className="w-full sm:w-52 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed">{readyRows.length ? `Approve ${readyRows.length === 1 ? 'this seller' : `all ${readyRows.length}`}` : 'Nobody to approve'}</button>
            </li>
            <li className="flex flex-wrap items-center gap-4 px-5 sm:px-6 py-4">
              <span className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-700 grid place-items-center text-2xl font-extrabold tabular-nums shrink-0">{askRows.length}</span>
              <div className="min-w-0 flex-1 basis-60">
                <div className="font-bold text-gray-900 flex items-center gap-1.5"><Mail className="w-4 h-4 text-amber-600" aria-hidden="true" /> Documents missing</div>
                <p className="text-sm text-gray-600">We send the seller a message that lists exactly what to upload.</p>
              </div>
              <button disabled={!askRows.length || autoBusy} onClick={() => runAutopilot('ASK')} className="w-full sm:w-52 px-4 py-2.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed">{askRows.length ? `Send message to ${askRows.length === 1 ? 'this seller' : `all ${askRows.length}`}` : 'Nobody to message'}</button>
            </li>
            <li className="flex flex-wrap items-center gap-4 px-5 sm:px-6 py-4">
              <span className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-700 grid place-items-center text-2xl font-extrabold tabular-nums shrink-0">{eyeRows}</span>
              <div className="min-w-0 flex-1 basis-60">
                <div className="font-bold text-gray-900 flex items-center gap-1.5"><Eye className="w-4 h-4 text-rose-600" aria-hidden="true" /> Needs a look from you</div>
                <p className="text-sm text-gray-600">Something does not match, or the risk score is higher than you allow. Open these in the list below.</p>
              </div>
              <span className="w-full sm:w-52 text-center text-sm font-semibold text-gray-500">{eyeRows ? 'Review them below' : 'All clear'}</span>
            </li>
          </ul>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-5 sm:px-6 py-3.5 bg-gray-50 border-t border-gray-100">
            <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0" aria-hidden="true" />
            <label htmlFor="risk-limit" className="text-sm font-semibold text-gray-800">How careful should we be?</label>
            <select id="risk-limit" value={limit} onChange={(e) => changeLimit(e.target.value)} className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-900">
              {[[10, 'Very careful (score 10 or lower)'], [25, 'Careful (score 25 or lower, low risk)'], [55, 'Relaxed (score 55 or lower, medium risk)']].map(([v, name]) => <option key={v} value={v}>{name}</option>)}
              {![10, 25, 55].includes(limit) && <option value={limit}>Custom (score {limit} or lower)</option>}
            </select>
            <span className="text-xs text-gray-500">Only affects who counts as "ready to approve".</span>
          </div>

          <details className="group border-t border-gray-100">
            <summary className="cursor-pointer select-none list-none flex items-center justify-between gap-3 px-5 sm:px-6 py-3.5 text-sm font-semibold text-indigo-700 hover:bg-indigo-50/50">
              <span>How is the risk score worked out?</span>
              <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" aria-hidden="true" />
            </summary>
            <div className="px-5 sm:px-6 pb-5 text-sm text-gray-700 space-y-3">
              <p>We compare what the seller typed with what is written on their documents. The score goes from <b>0 (safest)</b> to <b>100 (riskiest)</b>.</p>
              <ol className="grid sm:grid-cols-3 gap-2 list-none p-0 m-0">
                <li className="rounded-xl border border-gray-200 p-3"><div className="text-xs font-bold text-gray-500 uppercase tracking-wide">Start</div><div className="text-2xl font-extrabold text-gray-900">10</div><div className="text-xs text-gray-600">Every seller begins here.</div></li>
                <li className="rounded-xl border border-rose-200 bg-rose-50/50 p-3"><div className="text-xs font-bold text-rose-700 uppercase tracking-wide">Does not match</div><div className="text-2xl font-extrabold text-gray-900">+20 <span className="text-sm font-semibold text-gray-500">each</span></div><div className="text-xs text-gray-600">For example the name on the PAN card is different from the form.</div></li>
                <li className="rounded-xl border border-amber-200 bg-amber-50/50 p-3"><div className="text-xs font-bold text-amber-700 uppercase tracking-wide">Could not read</div><div className="text-2xl font-extrabold text-gray-900">+8 <span className="text-sm font-semibold text-gray-500">each</span></div><div className="text-xs text-gray-600">A missing or blurry document, or a detail we could not find.</div></li>
              </ol>
              <div>
                <div className="flex h-3 rounded-full overflow-hidden" aria-hidden="true"><span className="bg-emerald-500" style={{ width: '25%' }} /><span className="bg-amber-400" style={{ width: '30%' }} /><span className="bg-rose-500 flex-1" /></div>
                <div className="flex justify-between text-xs text-gray-600 mt-1"><span><b className="text-emerald-700">0 to 25</b> low risk</span><span><b className="text-amber-700">26 to 55</b> medium</span><span><b className="text-rose-700">56 to 100</b> high</span></div>
              </div>
              <p className="text-xs text-gray-600"><b>Example:</b> one detail does not match and one could not be read: 10 + 20 + 8 = 38, which is medium risk.</p>
              <p className="text-xs text-gray-600"><b>What we compare:</b> PAN number, GSTIN, the name on Aadhaar, PAN and bank proof, and the PIN code. The score is only a guide. Sellers with missing or mismatched documents are never approved with the button above.</p>
            </div>
          </details>
        </section>
      )}
      {loadError &&<div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{loadError}</div>}

      <div className="flex gap-2 flex-wrap">
        {TABS.map(([key, name]) => (
          <button key={key || 'all'} onClick={() => { setTab(key); setSelected(null); setProfile(null); }} aria-pressed={tab === key}
            className={`px-4 py-2 rounded-full text-sm font-semibold border ${tab === key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200 hover:border-indigo-600'}`}>{name} <span className="opacity-70">({count(key)})</span></button>
        ))}
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" aria-hidden="true" />
        <input value={find} onChange={(e) => setFind(e.target.value)} placeholder="Search name, store or city" aria-label="Search applications" className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-white border border-gray-200 text-sm shadow-sm" />
      </div>

      <div className="space-y-3" role="list" aria-label="Seller applications">
        {rows.length === 0 && <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-12 text-center text-sm text-gray-500"><Inbox className="w-9 h-9 mx-auto mb-2 text-gray-300" />No applications here. Pick another tab above.</div>}
        {rows.map((a) => {
          const incomplete = a.documentCount < 3 || a.status === 'DRAFT';
          return (
            <button key={a.id} role="listitem" onClick={() => open(a.id)} aria-label={`Open application from ${a.companyName}`}
              className="group w-full text-left bg-white rounded-2xl border border-gray-200 px-5 py-4 flex items-center gap-4 shadow-sm hover:shadow-md hover:border-indigo-300 hover:-translate-y-0.5 transition">
              <SellerDP name={a.companyName} size={56} />
              <div className="min-w-0 flex-1 basis-56">
                <b className="text-gray-900 text-lg block truncate">{a.companyName}</b>
                <div className="text-sm text-gray-500 truncate">{a.applicantName} · {a.city || 'No city'}</div>
              </div>
              <div className="hidden md:block min-w-0 w-60 text-sm text-gray-600">
                {a.email && <div className="flex items-center gap-1.5 truncate"><Mail className="w-3.5 h-3.5 text-gray-400 shrink-0" />{a.email}</div>}
                {a.phone && <div className="flex items-center gap-1.5 mt-0.5"><Phone className="w-3.5 h-3.5 text-gray-400 shrink-0" />{a.phone}</div>}
              </div>
              <div className="hidden sm:flex flex-col items-start gap-1.5 w-44">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold whitespace-nowrap ${TONE[a.status] || TONE.DRAFT}`}>{label(a.status)}</span>
                <span className="text-xs text-gray-500">{a.status === 'APPROVED' && a.documentCount === 0 ? 'Added by admin' : `${a.documentCount} of 3 documents`}</span>
                {advice[a.id] && (() => { const k = advice[a.id].action === 'READY' && advice[a.id].riskScore > limit ? 'REVIEW' : advice[a.id].action; return <span className={`text-[11px] font-bold ${{ READY: 'text-emerald-700', ASK: 'text-amber-700', REVIEW: 'text-rose-700' }[k]}`} title={advice[a.id].reason}>{{ READY: 'Ready to approve', ASK: 'Documents missing', REVIEW: 'Needs a person' }[k]}</span>; })()}
              </div>
              {a.status === 'APPROVED'
                ? <div className="w-[92px] shrink-0 text-center" aria-label={`Approved and live, risk ${a.riskScore} out of 100`}>
                    <span className="inline-flex p-2 rounded-full bg-emerald-50 text-emerald-600"><BadgeCheck className="w-6 h-6" aria-hidden="true" /></span>
                    <div className="text-xs font-bold text-emerald-700 leading-tight mt-1">Live seller</div>
                    <div className="text-[11px] text-gray-500">Risk {a.riskScore}/100</div>
                  </div>
                : <RiskGauge score={a.riskScore} category={incomplete ? 'Incomplete' : a.riskCategory} size="sm" />}
              <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-indigo-600 shrink-0" aria-hidden="true" />
            </button>
          );
        })}
      </div>

      {selected && createPortal(
        <div className="fixed inset-0 z-[90] bg-slate-50 overflow-y-auto" role="dialog" aria-modal="true" aria-label="Application details">
          <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-gray-200">
            <div className="max-w-5xl mx-auto px-5 py-3 flex items-center justify-between gap-3">
              <button onClick={close} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm font-semibold hover:bg-gray-50"><ArrowLeft className="w-4 h-4" /> All applications</button>
              <b className="text-gray-900 truncate hidden sm:block">{p?.companyName || 'Loading…'}</b>
              <button onClick={close} aria-label="Close" className="p-2 rounded-xl hover:bg-gray-100"><X className="w-5 h-5" /></button>
            </div>
          </div>
          <div className="max-w-5xl mx-auto p-5 space-y-4">
            {toast && <div role="status" className={`px-4 py-3 rounded-xl text-sm font-semibold ${toast.bad ? 'bg-red-50 text-red-800' : 'bg-green-50 text-green-800'}`}>{toast.text}</div>}
            {!p && !toast?.bad && <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center text-gray-500">Loading…</div>}
            {p && (
              <>
              <section className="bg-white rounded-2xl border border-gray-200 p-5" aria-label="Applicant and decision">
                    <div className="flex flex-wrap items-center gap-5">
                      <SellerDP name={p.companyName} size={88} ring />
                      <div className="min-w-0 flex-1 basis-64">
                        <div className="text-xs uppercase tracking-wide text-gray-400">Application {p.id}{p.createdAt ? ` · sent ${new Date(p.createdAt).toLocaleDateString()}` : ''}</div>
                        <h2 className="text-2xl font-extrabold text-gray-900 truncate">{p.companyName}</h2>
                        <p className="text-sm text-gray-600">{p.applicantName}{p.businessType ? ` · ${p.businessType}` : ''}</p>
                        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-700">
                          {p.email && <span className="inline-flex items-center gap-1.5"><Mail className="w-4 h-4 text-gray-400" />{p.email}</span>}
                          {p.phone && <span className="inline-flex items-center gap-1.5"><Phone className="w-4 h-4 text-gray-400" />{p.phone}</span>}
                          {p.city && <span className="inline-flex items-center gap-1.5"><MapPin className="w-4 h-4 text-gray-400" />{p.city}</span>}
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-sm font-bold self-start ${TONE[p.status] || TONE.DRAFT}`}>{label(p.status)}</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
                      <Fact label="Documents" value={`${(p.documents || []).length} of 3`} bad={(p.documents || []).length < 3} />
                      <Fact label="Checks passed" value={`${readiness(p).passed} of ${readiness(p).total}`} />
                      <Fact label="Store pinned" value={p.store?.latitude != null ? 'Yes' : 'No'} bad={p.store?.latitude == null} />
                      <Fact label="GSTIN" value={p.gstin ? 'Given' : 'None'} />
                    </div>
                    {(canDecide || p.status === 'APPROVED') && (
                      <div className="mt-5 pt-4 border-t border-gray-100">
                        {canDecide && !mode && (
                          <div className="flex flex-wrap gap-2 items-center">
                            <button disabled={busy || blockers.length > 0} onClick={() => decide('APPROVE')} title={blockers.length ? `Missing: ${blockers.join(', ')}` : ''}
                              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed"><CheckCircle2 className="w-4 h-4" /> Approve and go live</button>
                            <button onClick={() => { setMode('REQUEST_INFO'); if (advice[p.id]?.message && !reason) setReason(advice[p.id].message); }} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-sm"><MessageSquareWarning className="w-4 h-4" /> Ask for more</button>
                            <button onClick={() => setMode('REJECT')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm"><XCircle className="w-4 h-4" /> Reject</button>
                            {blockers.length > 0 && <span className="text-sm text-red-700"><b>Approve is locked.</b> Missing: {blockers.join(', ')}.</span>}
                          </div>
                        )}
                        {p.status === 'APPROVED' && !mode && <button onClick={() => setMode('SUSPEND')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold"><PauseCircle className="w-4 h-4" /> Suspend store</button>}
                        {mode && (
                          <div className="space-y-2">
                            <label htmlFor="reason" className="block text-sm font-semibold text-gray-800">{mode === 'REQUEST_INFO' ? 'What do you need from the seller?' : mode === 'SUSPEND' ? 'Why is the store being suspended?' : 'Why is it being rejected?'} The seller will see this.</label>
                            <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full rounded-xl border border-gray-300 p-3 text-sm" />
                            <div className="flex gap-2">
                              <button disabled={busy || !reason.trim()} onClick={() => decide(mode)} className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-sm disabled:opacity-50">Confirm</button>
                              <button onClick={() => { setMode(null); setReason(''); }} className="px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold">Cancel</button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {p.rejectionReason && <p className="text-sm text-red-700 mt-3"><b>Reason given:</b> {p.rejectionReason}</p>}
                  </section>
                  <SellerProfileView p={p} showIdentity={false} />
              </>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
