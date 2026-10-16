import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, XCircle, MessageSquareWarning, PauseCircle, RefreshCw } from 'lucide-react';
import api from '../../services/api';
import SellerProfileView, { RiskBadge, readiness } from './SellerProfileView';
import '../../storefront/forms.css';

const TABS = [
  ['PENDING_ADMIN_APPROVAL', 'Ready to review'],
  ['NEEDS_MANUAL_REVIEW', 'Needs a closer look'],
  ['NEEDS_MORE_INFORMATION', 'Waiting for seller'],
  ['DRAFT', 'Still filling in'],
  ['APPROVED', 'Approved'],
  ['REJECTED', 'Rejected'],
  ['', 'All'],
];
const TONE = {
  PENDING_ADMIN_APPROVAL: 'bg-blue-100 text-blue-800', NEEDS_MANUAL_REVIEW: 'bg-amber-100 text-amber-800', NEEDS_MORE_INFORMATION: 'bg-orange-100 text-orange-800',
  APPROVED: 'bg-green-100 text-green-800', REJECTED: 'bg-red-100 text-red-800', SUSPENDED: 'bg-gray-200 text-gray-800', DRAFT: 'bg-gray-100 text-gray-700',
};
const label = (s) => (s === 'DRAFT' ? 'Not submitted yet' : String(s || '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()));

/** Review one seller application: the facts first (risk, checklist, Aadhaar, PAN, location), then the decision. */
export default function SellerOnboardingAI() {
  const [tab, setTab] = useState('PENDING_ADMIN_APPROVAL');
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [reason, setReason] = useState('');
  const [mode, setMode] = useState(null); // REJECT | REQUEST_INFO | SUSPEND
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [loadError, setLoadError] = useState('');

  const loadList = useCallback(async () => {
    try {
      const { data } = await api.get('/seller/applications', { params: tab ? { status: tab } : {} });
      setRows(data); setLoadError('');
    } catch (e) { setLoadError(e?.response?.status === 403 ? 'Only administrators can see applications.' : 'Could not load applications.'); }
  }, [tab]);
  useEffect(() => { loadList(); }, [loadList]);

  const open = async (id) => {
    setSelected(id); setMode(null); setReason(''); setProfile(null); setToast(null);
    try { const { data } = await api.get(`/seller/applications/${id}`); setProfile(data); } catch { setToast({ bad: true, text: 'Could not open that application.' }); }
  };

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
          <h1 className="text-2xl font-extrabold text-gray-900">Seller applications</h1>
          <p className="text-gray-600 text-sm mt-1">Open an application, check every item, then decide. The risk score is only a guide. You make the decision.</p>
        </div>
        <button onClick={loadList} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm font-semibold hover:bg-gray-50"><RefreshCw className="w-4 h-4" /> Refresh</button>
      </div>

      {toast && <div role="status" className={`px-4 py-3 rounded-xl text-sm font-semibold ${toast.bad ? 'bg-red-50 text-red-800' : 'bg-green-50 text-green-800'}`}>{toast.text}</div>}
      {loadError && <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{loadError}</div>}

      <div className="flex gap-2 flex-wrap">
        {TABS.map(([key, name]) => (
          <button key={key || 'all'} onClick={() => { setTab(key); setSelected(null); setProfile(null); }} aria-pressed={tab === key}
            className={`px-4 py-2 rounded-full text-sm font-semibold border ${tab === key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200 hover:border-indigo-600'}`}>{name}</button>
        ))}
      </div>

      <div className="grid lg:grid-cols-[300px_1fr] gap-5 items-start">
        <div className="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100 overflow-hidden">
          {rows.length === 0 && <p className="p-5 text-sm text-gray-500">No applications here yet.</p>}
          {rows.map((a) => (
            <button key={a.id} onClick={() => open(a.id)} className={`w-full text-left p-4 hover:bg-gray-50 flex items-center gap-3 ${selected === a.id ? 'bg-indigo-50' : ''}`}>
              <div className="min-w-0 flex-1">
                <b className="text-gray-900 block truncate">{a.companyName}</b>
                <div className="text-sm text-gray-500 truncate">{a.applicantName} · {a.city}</div>
                <div className="mt-1 flex items-center gap-2 flex-wrap"><span className={`px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap ${TONE[a.status] || TONE.DRAFT}`}>{label(a.status)}</span>
                  <span className="text-xs text-gray-500">{a.documentCount} of 6 documents</span></div>
              </div>
              <RiskBadge score={a.riskScore} category={a.documentCount < 2 ? 'Incomplete' : a.riskCategory} size="sm" />
            </button>
          ))}
        </div>

        <div className="space-y-4 min-w-0">
          {!selected && <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-10 text-center text-gray-500">Choose an application to see the full seller profile.</div>}
          {selected && !p && <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-gray-500">Loading…</div>}
          {p && (
            <>
              <section className="bg-white rounded-2xl border-2 border-indigo-200 p-4 sticky top-2 z-10 shadow-sm" aria-label="Decision">
                <div className="flex flex-wrap items-center gap-3 justify-between">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${TONE[p.status] || TONE.DRAFT}`}>{label(p.status)}</span>
                  {canDecide && !mode && (
                    <div className="flex flex-wrap gap-2">
                      <button disabled={busy || blockers.length > 0} onClick={() => decide('APPROVE')} title={blockers.length ? `Missing: ${blockers.join(', ')}` : ''}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed"><CheckCircle2 className="w-4 h-4" /> Approve and go live</button>
                      <button onClick={() => setMode('REQUEST_INFO')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-sm"><MessageSquareWarning className="w-4 h-4" /> Ask for more</button>
                      <button onClick={() => setMode('REJECT')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm"><XCircle className="w-4 h-4" /> Reject</button>
                    </div>
                  )}
                  {p.status === 'APPROVED' && !mode && <button onClick={() => setMode('SUSPEND')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold"><PauseCircle className="w-4 h-4" /> Suspend store</button>}
                </div>
                {canDecide && blockers.length > 0 && !mode && <p className="text-sm text-red-700 mt-2"><b>Approve is locked.</b> Missing: {blockers.join(', ')}. Use "Ask for more" to request them.</p>}
                {p.rejectionReason && <p className="text-sm text-red-700 mt-2"><b>Reason given:</b> {p.rejectionReason}</p>}
                {mode && (
                  <div className="mt-3 space-y-2">
                    <label htmlFor="reason" className="block text-sm font-semibold text-gray-800">{mode === 'REQUEST_INFO' ? 'What do you need from the seller?' : mode === 'SUSPEND' ? 'Why is the store being suspended?' : 'Why is it being rejected?'} The seller will see this.</label>
                    <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full rounded-xl border border-gray-300 p-3 text-sm" />
                    <div className="flex gap-2">
                      <button disabled={busy || !reason.trim()} onClick={() => decide(mode)} className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-sm disabled:opacity-50">Confirm</button>
                      <button onClick={() => { setMode(null); setReason(''); }} className="px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold">Cancel</button>
                    </div>
                  </div>
                )}
              </section>
              <SellerProfileView p={p} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
