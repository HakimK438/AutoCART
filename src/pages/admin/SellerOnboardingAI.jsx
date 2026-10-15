import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, XCircle, MessageSquareWarning, PauseCircle, FileText, X, RefreshCw } from 'lucide-react';
import api from '../../services/api';
import LocationPinMap from '../../storefront/LocationPinMap';
import '../../storefront/forms.css';

const TABS = [
  ['PENDING_ADMIN_APPROVAL', 'Ready to review'],
  ['NEEDS_MANUAL_REVIEW', 'Needs a closer look'],
  ['NEEDS_MORE_INFORMATION', 'Waiting for seller'],
  ['APPROVED', 'Approved'],
  ['REJECTED', 'Rejected'],
  ['', 'All'],
];
const TONE = {
  PENDING_ADMIN_APPROVAL: 'bg-blue-100 text-blue-800', NEEDS_MANUAL_REVIEW: 'bg-amber-100 text-amber-800', NEEDS_MORE_INFORMATION: 'bg-orange-100 text-orange-800',
  APPROVED: 'bg-green-100 text-green-800', REJECTED: 'bg-red-100 text-red-800', SUSPENDED: 'bg-gray-200 text-gray-800', DRAFT: 'bg-gray-100 text-gray-700',
};
const label = (s) => String(s || '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
const DOC_LABEL = { AADHAAR: 'Aadhaar (masked)', PAN: 'PAN card', GST_CERTIFICATE: 'GST certificate', ADDRESS_PROOF: 'Address proof', BANK_PROOF: 'Bank proof', STORE_PHOTO: 'Store photo' };

const Card = ({ title, children, className = '' }) => (
  <section className={`bg-white rounded-2xl border border-gray-200 p-5 ${className}`}><h3 className="font-bold text-gray-900 mb-3">{title}</h3>{children}</section>
);
const Row = ({ k, v }) => (v ? <div className="flex gap-3 py-1.5 text-sm"><dt className="w-36 shrink-0 text-gray-500">{k}</dt><dd className="font-medium text-gray-900 break-words min-w-0">{v}</dd></div> : null);

export default function SellerOnboardingAI() {
  const [tab, setTab] = useState('PENDING_ADMIN_APPROVAL');
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [reason, setReason] = useState('');
  const [mode, setMode] = useState(null); // REJECT | REQUEST_INFO | SUSPEND
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loadError, setLoadError] = useState('');

  const loadList = useCallback(async () => {
    try {
      const { data } = await api.get('/seller/applications', { params: tab ? { status: tab } : {} });
      setRows(data); setLoadError('');
    } catch (e) { setLoadError(e?.response?.status === 403 ? 'Only administrators can see applications.' : 'Could not load applications.'); }
  }, [tab]);
  useEffect(() => { loadList(); }, [loadList]);

  const open = async (id) => {
    setSelected(id); setMode(null); setReason(''); setProfile(null);
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

  const view = async (doc) => {
    try {
      const { data } = await api.get(doc.fileUrl.replace(/^\/api/, ''), { responseType: 'blob' });
      setPreview({ url: URL.createObjectURL(data), type: doc.mimeType, name: DOC_LABEL[doc.docType] });
    } catch { setToast({ bad: true, text: 'This file is not available (an unmasked Aadhaar is never kept).' }); }
  };

  const p = profile;
  const canDecide = p && ['PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW'].includes(p.status);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Seller applications</h1>
          <p className="text-gray-600 text-sm mt-1">Review the details and documents, then approve or reject. The automatic checks only suggest a risk score. You make the decision.</p>
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

      <div className="grid lg:grid-cols-[320px_1fr] gap-5 items-start">
        <div className="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100 overflow-hidden">
          {rows.length === 0 && <p className="p-5 text-sm text-gray-500">No applications here yet.</p>}
          {rows.map((a) => (
            <button key={a.id} onClick={() => open(a.id)} className={`w-full text-left p-4 hover:bg-gray-50 ${selected === a.id ? 'bg-indigo-50' : ''}`}>
              <div className="flex items-center justify-between gap-2"><b className="text-gray-900 truncate">{a.companyName}</b>
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap ${TONE[a.status] || TONE.DRAFT}`}>{label(a.status)}</span></div>
              <div className="text-sm text-gray-500 mt-1 truncate">{a.applicantName} · {a.city}</div>
              <div className="text-xs text-gray-400 mt-1">{a.documentCount} documents · risk {a.riskScore}/100</div>
            </button>
          ))}
        </div>

        <div className="space-y-4 min-w-0">
          {!selected && <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-10 text-center text-gray-500">Choose an application to see the full seller profile.</div>}
          {selected && !p && <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-gray-500">Loading…</div>}
          {p && (
            <>
              <Card title={p.companyName}>
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${TONE[p.status] || TONE.DRAFT}`}>{label(p.status)}</span>
                  <span className="text-sm text-gray-600">Automatic risk score <b>{p.riskScore}/100</b> ({p.riskCategory})</span>
                </div>
                {p.aiAssessment && <p className="text-sm text-gray-600 mt-3">{p.aiAssessment}</p>}
                {p.rejectionReason && <p className="text-sm text-red-700 mt-2"><b>Reason given:</b> {p.rejectionReason}</p>}
                {canDecide && !mode && (
                  <div className="flex flex-wrap gap-2 mt-4">
                    <button disabled={busy} onClick={() => decide('APPROVE')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white font-semibold text-sm"><CheckCircle2 className="w-4 h-4" /> Approve and go live</button>
                    <button onClick={() => setMode('REQUEST_INFO')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-sm"><MessageSquareWarning className="w-4 h-4" /> Ask for more</button>
                    <button onClick={() => setMode('REJECT')} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm"><XCircle className="w-4 h-4" /> Reject</button>
                  </div>
                )}
                {p.status === 'APPROVED' && !mode && <button onClick={() => setMode('SUSPEND')} className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold"><PauseCircle className="w-4 h-4" /> Suspend store</button>}
                {mode && (
                  <div className="mt-4 space-y-2">
                    <label htmlFor="reason" className="block text-sm font-semibold text-gray-800">{mode === 'REQUEST_INFO' ? 'What do you need from the seller?' : mode === 'SUSPEND' ? 'Why is the store being suspended?' : 'Why is it being rejected?'} The seller will see this.</label>
                    <textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="w-full rounded-xl border border-gray-300 p-3 text-sm" />
                    <div className="flex gap-2">
                      <button disabled={busy || !reason.trim()} onClick={() => decide(mode)} className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-sm disabled:opacity-50">Confirm</button>
                      <button onClick={() => { setMode(null); setReason(''); }} className="px-4 py-2 rounded-xl border border-gray-300 text-sm font-semibold">Cancel</button>
                    </div>
                  </div>
                )}
              </Card>

              <div className="grid md:grid-cols-2 gap-4">
                <Card title="Identity (from Aadhaar and PAN)">
                  <dl>
                    <Row k="Name" v={p.identity?.name} /><Row k="Date of birth" v={p.identity?.dob} /><Row k="Gender" v={p.identity?.gender} />
                    <Row k="Aadhaar" v={p.identity?.aadhaarMasked} /><Row k="PAN" v={p.identity?.pan} /><Row k="PAN name" v={p.identity?.panName} />
                    <Row k="Father's name" v={p.identity?.fatherName} /><Row k="Address on Aadhaar" v={p.identity?.address} />
                  </dl>
                  {!Object.keys(p.identity || {}).length && <p className="text-sm text-gray-500">Nothing could be read from the identity documents. Open them below.</p>}
                  <p className="text-xs text-gray-400 mt-3">Only the last 4 digits of the Aadhaar are stored.</p>
                </Card>
                <Card title="Business">
                  <dl>
                    <Row k="Applicant" v={p.applicantName} /><Row k="Phone" v={p.phone} /><Row k="Email" v={p.email} /><Row k="Type" v={p.businessType} />
                    <Row k="GSTIN" v={p.gstin} /><Row k="PAN (form)" v={p.pan} /><Row k="Categories" v={(p.productCategories || []).join(', ')} />
                  </dl>
                </Card>
              </div>

              <Card title="Store location">
                <p className="text-sm text-gray-700 mb-3">{p.store?.name}, {p.store?.address}, {p.store?.city}, {p.store?.state} {p.store?.pincode}</p>
                {p.store?.latitude != null && <LocationPinMap lat={p.store.latitude} lng={p.store.longitude} height={280} />}
              </Card>

              <Card title={`Products they plan to sell (${(p.plannedProducts || []).length})`}>
                {(p.plannedProducts || []).length ? (
                  <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-gray-500"><th className="py-1 pr-4">Product</th><th className="pr-4">Category</th><th>Price</th></tr></thead>
                    <tbody>{p.plannedProducts.map((x, i) => <tr key={i} className="border-t border-gray-100"><td className="py-2 pr-4 font-medium">{x.name}</td><td className="pr-4">{x.category || '-'}</td><td>{x.approxPrice ? `₹${x.approxPrice}` : '-'}</td></tr>)}</tbody></table></div>
                ) : <p className="text-sm text-gray-500">No products listed.</p>}
                {p.liveProducts?.length > 0 && <p className="text-sm text-gray-600 mt-3">{p.liveProducts.length} products live in the catalogue under this seller.</p>}
              </Card>

              <Card title="Do the form and the documents agree?">
                {(p.comparison?.checks || []).map((c) => (
                  <div key={c.label} className="flex items-start gap-3 py-2 border-t first:border-t-0 border-gray-100 text-sm">
                    <span className={`mt-0.5 px-2 py-0.5 rounded-full text-xs font-bold ${c.status === 'match' ? 'bg-green-100 text-green-800' : c.status === 'mismatch' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{c.status === 'match' ? 'Matches' : c.status === 'mismatch' ? 'Does not match' : 'Not read'}</span>
                    <div><div className="font-medium text-gray-900">{c.label}</div><div className="text-gray-500">{c.detail}</div></div>
                  </div>
                ))}
              </Card>

              <Card title={`Documents (${p.documents?.length || 0} of ${p.requiredDocuments?.length || 6})`}>
                {(p.missingDocuments || []).length > 0 && <p className="text-sm text-amber-700 mb-3">Missing: {p.missingDocuments.map((d) => DOC_LABEL[d] || d).join(', ')}</p>}
                {(p.documents || []).map((d) => (
                  <div key={d.id} className="flex items-center justify-between gap-3 py-3 border-t first:border-t-0 border-gray-100">
                    <div className="min-w-0"><b className="text-sm">{DOC_LABEL[d.docType] || d.docType}</b> <span className="text-xs text-gray-500">{d.fileName}</span>
                      {d.warnings?.map((w) => <div key={w} className="text-xs text-red-600">{w}</div>)}
                      <div className="text-xs text-gray-500">Reading: {label(d.ocrStatus)}{d.confidence ? ` · ${d.confidence}% of fields found` : ''}</div></div>
                    <button onClick={() => view(d)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 text-sm font-semibold whitespace-nowrap"><FileText className="w-4 h-4" /> Open</button>
                  </div>
                ))}
              </Card>

              <Card title="History">
                <ol className="space-y-2 text-sm">{(p.auditTrail || []).map((a) => (
                  <li key={a.id} className="flex gap-3"><span className="text-gray-400 w-40 shrink-0">{new Date(a.timestamp).toLocaleString()}</span>
                    <span><b>{label(a.action)}</b> by {a.performedBy}{a.fromStatus ? `, ${label(a.fromStatus)} to ${label(a.toStatus)}` : ''}{a.reason ? `. ${a.reason}` : ''}</span></li>))}</ol>
              </Card>
            </>
          )}
        </div>
      </div>

      {preview && (
        <div className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={preview.name}>
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b"><b>{preview.name}</b><button onClick={() => { URL.revokeObjectURL(preview.url); setPreview(null); }} aria-label="Close preview"><X className="w-5 h-5" /></button></div>
            <div className="overflow-auto p-4 flex-1">{(preview.type || '').includes('pdf') ? <iframe src={preview.url} title={preview.name} className="w-full h-[70vh]" /> : <img src={preview.url} alt={preview.name} className="max-w-full mx-auto" />}</div>
          </div>
        </div>
      )}
    </div>
  );
}
