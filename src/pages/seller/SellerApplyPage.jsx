import HowItWorks from './HowItWorks';
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Upload, FileCheck2, LocateFixed, ScanText, Loader2 } from 'lucide-react';
import ApplicationPrintForm from './ApplicationPrintForm';
import { reverseGeocode } from '../../utils/geocode';
import api from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import LocationPinMap, { findOnMap } from '../../storefront/LocationPinMap';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';

const DOCS = [
  { type: 'AADHAAR', key: 'aadhaar', label: 'Aadhaar card', hint: 'A clear photo or PDF of your Aadhaar (front side with the number). The number is stored encrypted and shown to our team only as XXXX XXXX 1234.' },
  { type: 'PAN', key: 'pan', label: 'PAN card', hint: 'A clear photo or PDF of your PAN card.' },
  { type: 'BANK_PROOF', key: 'bank', label: 'Bank proof', hint: 'A cancelled cheque or the first page of your passbook.' },
];
// Only what is actually printed on each document is shown for it (the Aadhaar never shows a PAN number).
const SHOW = {
  AADHAAR: [['name', 'Name'], ['dob', 'Date of birth'], ['aadhaarMasked', 'Aadhaar number'], ['address', 'Address']],
  PAN: [['name', 'Name'], ['pan', 'PAN']],
  BANK_PROOF: [['accountHolder', 'Account holder'], ['bankName', 'Bank'], ['ifsc', 'IFSC'], ['accountLast4', 'Account ending']],
};
const DEFAULT_PIN = { lat: 19.076, lng: 72.8777 };
const FINAL = ['PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED'];

const STATUS_COPY = {
  PENDING_ADMIN_APPROVAL: ['info', 'Waiting for review', 'All your documents are in and the details match. A person on our team will review your application next.'],
  NEEDS_MANUAL_REVIEW: ['warn', 'A person will check your details', 'Some details did not match your documents, or a document could not be read automatically. Our team will look at it by hand.'],
  NEEDS_MORE_INFORMATION: ['warn', 'We need a little more from you', 'Please add what is missing below and submit again.'],
  APPROVED: ['ok', 'You are approved', 'Your store is live and shows up on the nearby-store map.'],
  REJECTED: ['bad', 'Application not approved', 'See the reason below. You can contact support if you think this is a mistake.'],
  SUSPENDED: ['bad', 'Store suspended', 'Your store is paused. See the reason below.'],
  DRAFT: ['info', 'Draft', 'Finish the steps below and submit.'],
};

const Field = ({ id, label, hint, error, children }) => (
  <div className="ac-field">
    <label htmlFor={id}>{label}</label>
    {children}
    {hint && !error && <small>{hint}</small>}
    {error && <span className="ac-err" role="alert">{error}</span>}
  </div>
);

export default function SellerApplyPage() {
  const { user } = useAuth();
  const [justSubmitted, setJustSubmitted] = useState(false);
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [agree, setAgree] = useState(false);
  const [pin, setPin] = useState(null);
  const [files, setFiles] = useState({});
  const [previews, setPreviews] = useState({});
  const [progress, setProgress] = useState(0);
  const [located, setLocated] = useState(false);
  const [problems, setProblems] = useState({});
  const [form, setForm] = useState({
    companyName: '', storeName: '', contactName: user?.name || '', email: user?.email || '', phone: user?.phone || '', businessType: 'Retailer',
    pan: '', address: '', city: '', state: '', pincode: '',
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const unnamed = (v) => /store not named yet/.test(v || '');

  /** Copy what the server knows (read from the documents) into the editable form. */
  const fillFrom = (a) => {
    setForm((f) => ({
      ...f, companyName: unnamed(a.companyName) ? f.companyName : a.companyName || f.companyName, storeName: unnamed(a.storeName) ? f.storeName : a.storeName || f.storeName,
      contactName: a.applicantName || f.contactName, email: a.email || f.email, phone: a.phone || f.phone, businessType: a.businessType || f.businessType,
      pan: a.pan || f.pan, address: a.address || f.address, city: a.city || f.city, state: a.addressState || f.state, pincode: a.pincode || f.pincode,
    }));
    if (a.storeLatitude) setPin({ lat: a.storeLatitude, lng: a.storeLongitude });
  };

  useEffect(() => { document.title = 'Sell on AutoCart'; }, []);

  // Pick up where the seller left off.
  useEffect(() => {
    if (!user) { setLoading(false); return; }
    api.get('/seller/applications').then((r) => {
      const mine = (r.data || []).find((a) => a.ownerUserId === user.id && !['REJECTED'].includes(a.status)) || (r.data || [])[0];
      if (!mine) {  // first visit: open a draft now so the admin can see this applicant
        if (user.role === 'CUSTOMER') return api.post('/seller/applications/start').then((d) => setApp(d.data)).catch(() => {});
        return null;
      }
      return api.get(`/seller/applications/${mine.id}`).then((d) => { setApp(d.data); fillFrom(d.data); });
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  const docByType = useMemo(() => Object.fromEntries((app?.documents || []).map((d) => [d.docType, d])), [app]);
  const have = DOCS.filter((d) => docByType[d.type] && docByType[d.type].ocrStatus !== 'REJECTED').length;
  const ready = have > 0 || !!form.address;   // the details section opens as soon as anything was read
  const submitted = app && (FINAL.includes(app.status) || (justSubmitted && app.status === 'NEEDS_MORE_INFORMATION'));

  /** Choosing a file only remembers it. Nothing is sent until all three are chosen and the seller presses "Read my documents". */
  const pick = (key, file) => {
    if (!file) return;
    setFiles((f) => ({ ...f, [key]: file }));
    setPreviews((p) => { if (p[key]) URL.revokeObjectURL(p[key]); return { ...p, [key]: file.type.startsWith('image/') ? URL.createObjectURL(file) : '' }; });
    setMessage('');
  };

  // A gentle progress bar while the server reads all three files together.
  useEffect(() => {
    if (busy !== 'read') return undefined;
    setProgress(6);
    const t = window.setInterval(() => setProgress((v) => Math.min(94, v + (v < 40 ? 5 : v < 80 ? 2.5 : 0.6))), 400);
    return () => window.clearInterval(t);
  }, [busy]);

  /** Where the seller is standing right now becomes the store address (used when the Aadhaar has no address, or when they prefer it). */
  const useHere = async (quiet = false) => {
    if (!navigator.geolocation) { if (!quiet) setMessage('Your browser cannot share your location. Type the address instead.'); return; }
    setBusy('here');
    await new Promise((resolve) => navigator.geolocation.getCurrentPosition(async (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      const a = await reverseGeocode(lat, lng);
      if (a) setForm((f) => ({ ...f, address: a.line || a.area || f.address, city: a.city || f.city, state: a.state || f.state, pincode: a.pincode || f.pincode }));
      setPin({ lat, lng }); setLocated(true); resolve();
    }, () => { if (!quiet) setMessage('We could not get your location. Allow location access, or type the address.'); resolve(); }, { enableHighAccuracy: true, timeout: 10000 }));
    setBusy('');
  };

  /** One request: all three files are sent together, read in parallel, and every field is filled. */
  const readAll = async () => {
    if (DOCS.some((d) => !files[d.key])) { setMessage('Choose all three documents first.'); return; }
    setBusy('read'); setMessage(''); setLocated(false);
    const body = new FormData();
    DOCS.forEach((d) => body.append(d.key, files[d.key]));
    try {
      const { data } = await api.post('/seller/applications/autofill', body, { headers: { 'Content-Type': 'multipart/form-data' } });
      setProgress(100); setApp(data); fillFrom(data);
      setProblems(data.autofill?.problems || {});
      if (!data.autofill?.filled?.length && !Object.keys(data.autofill?.problems || {}).length) setMessage('We could not read those files. Try clearer, well-lit photos or the original PDFs.');
      else if (!data.address) { setBusy(''); await useHere(true); return; }  // no address on the Aadhaar: use where the seller is now
    } catch (e) { setMessage(e?.response?.data?.detail || 'That upload did not work. Try smaller images or PDFs.'); }
    setBusy('');
  };

  const locate = async () => {
    setBusy('locate'); setMessage('');
    try {
      const hit = await findOnMap([form.address, form.city, form.pincode].filter(Boolean).join(', '));
      if (hit) setPin(hit); else setMessage('We could not find that address. Drag the pin to your shop instead.');
    } catch { setMessage('The map search is not available right now. Drag the pin to your shop instead.'); }
    setBusy('');
  };

  const submit = async () => {
    if (!agree) { setMessage('Please tick the confirmation box, then press Submit again.'); document.getElementById('agree-box')?.scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
    setBusy('submit'); setMessage(''); setErrors({});
    try {
      const at = pin || DEFAULT_PIN;
      await api.post('/seller/applications', { ...form, storeLatitude: at.lat, storeLongitude: at.lng, plannedProducts: [] });
      const { data } = await api.post(`/seller/applications/${app.id}/submit`);
      setApp(data); setJustSubmitted(true); window.scrollTo({ top: 0 });
    } catch (e) {
      setErrors(e?.response?.data?.errors || {});
      setMessage(e?.response?.data?.detail || 'We could not submit your application.');
    }
    setBusy('');
  };

  if (loading) return <div className="ac ac-page"><div className="ac-wrap"><div className="ac-skel" style={{ height: 320 }} /></div></div>;

  if (!user) {
    return (
      <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 720 }}>
        <h1 className="ac-display">Sell on AutoCart</h1>
        <details className="ac-howfold"><summary>How selling works and what it costs (tap to open)</summary><HowItWorks compact /></details>
        <p className="ac-sub">Reach shoppers near your store. Create an account, upload three documents, and we fill in the rest.</p>
        <div className="ac-row" style={{ marginTop: 24 }}>
          <Link to="/seller/login?mode=create" className="ac-btn ac-btn-blue">Create a seller account</Link>
          <Link to="/seller/login" className="ac-btn ac-btn-outline">Sign in</Link>
        </div>
      </div></div>
    );
  }

  // ---- already submitted: show where it stands ----
  if (submitted) {
    const [tone, title, text] = STATUS_COPY[app.status] || STATUS_COPY.DRAFT;
    return (
      <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 820 }}>
        <h1 className="ac-display">Your seller application</h1>
        <div className="ac-box" style={{ marginTop: 24 }}>
          <span className="ac-chip-status" data-tone={tone}>{title}</span>
          <p style={{ margin: '14px 0 0', fontSize: 18 }}>{text}</p>
          {app.rejectionReason && <p className="ac-warn" style={{ fontSize: 16 }}>Reason: {app.rejectionReason}</p>}
          {app.status === 'NEEDS_MORE_INFORMATION' && app.adminNotes && <p className="ac-warn" style={{ fontSize: 16 }}>Message from our team: {app.adminNotes}</p>}
          {app.status === 'NEEDS_MORE_INFORMATION' && (app.missingDocuments || []).length > 0 && (
            <p className="ac-warn" style={{ fontSize: 16 }}>Still needed: {app.missingDocuments.map((t) => DOCS.find((d) => d.type === t)?.label || t).join(', ')}. Add these and it moves forward.</p>
          )}
          <p className="ac-muted">Store: {app.storeName || app.companyName} · {app.address}, {app.city} {app.pincode}</p>
          <div className="ac-row">
            {app.status === 'NEEDS_MORE_INFORMATION' && <button className="ac-btn ac-btn-blue" onClick={() => { setJustSubmitted(false); window.scrollTo({ top: 0 }); }}>Add the missing documents</button>}
            {app.status === 'APPROVED' && <Link to="/seller/dashboard" className="ac-btn ac-btn-blue">Go to your seller dashboard</Link>}
            {['REJECTED', 'SUSPENDED'].includes(app.status) && <Link to="/support" className="ac-btn ac-btn-blue">Contact support</Link>}
            <Link to="/" className="ac-btn ac-btn-outline">Back to the store</Link>
          </div>
        </div>
        <ApplicationPrintForm app={app} />
        {app.comparison?.checks?.length > 0 && (
          <div className="ac-box ac-noprint">
            <h2>What we checked</h2>
            <div className="ac-scroll-x"><table className="ac-table"><tbody>{app.comparison.checks.map((c) => (
              <tr key={c.label}><td>{c.label}</td><td><span className="ac-chip-status" data-tone={c.status === 'match' ? 'ok' : c.status === 'mismatch' ? 'bad' : 'warn'}>{c.status === 'match' ? 'Matches' : c.status === 'mismatch' ? 'Does not match' : 'Could not read'}</span></td></tr>))}</tbody></table></div>
          </div>
        )}
      </div></div>
    );
  }


  return (
    <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 900 }}>
      <h1 className="ac-display">Sell on AutoCart</h1>
      <details className="ac-howfold"><summary>How selling works and what it costs (tap to open)</summary><HowItWorks compact /></details>
      <p className="ac-sub" style={{ marginTop: 18 }}>Add three documents and press one button. We read them, fill in your name, store, address and map pin, and prepare a printable form. You only check it and submit.</p>

      {message && <div className="ac-box" role="alert" style={{ marginBottom: 20, borderColor: 'var(--coral)' }}>{message}</div>}
      {app?.status === 'NEEDS_MORE_INFORMATION' && (app.adminNotes || app.aiAssessment) && <div className="ac-box" style={{ marginBottom: 20, borderColor: 'var(--gold)' }}><b>We need a little more</b><p style={{ margin: '6px 0 0' }}>{app.adminNotes || app.aiAssessment}</p></div>}

      <div className="ac-box"><h2>1. Add your three documents</h2>
        <p className="ac-muted">{DOCS.filter((d) => files[d.key]).length} of {DOCS.length} chosen. Add them all, then press <b>Submit documents</b>. They are read together in a few seconds and your form fills itself. Files are private to you and our review team.</p>
        <div className="ac-droptiles">
          {DOCS.map((d) => {
            const f = files[d.key];
            const doc = docByType[d.type];
            const bad = problems[d.type] || (doc?.ocrStatus === 'REJECTED' && doc.warnings?.[0]);
            return (
              <label key={d.type} className="ac-droptile" data-has={!!f} data-bad={!!bad}>
                <input type="file" className="ac-sr" accept="image/*,.pdf" disabled={!!busy} onChange={(e) => { pick(d.key, e.target.files?.[0]); e.target.value = ''; }} />
                <span className="ac-droptile-pic">{previews[d.key] ? <img src={previews[d.key]} alt="" /> : f ? <FileCheck2 size={30} /> : <Upload size={28} />}</span>
                <b>{d.label}</b>
                <small>{f ? f.name : d.hint}</small>
                <span className="ac-droptile-act">{f ? 'Change file' : 'Choose file'}</span>
                {bad && <small className="ac-warn" role="alert">{bad}</small>}
              </label>
            );
          })}
        </div>
        <div className="ac-row" style={{ marginTop: 18 }}>
          <button className="ac-btn ac-btn-blue" disabled={!!busy || DOCS.some((d) => !files[d.key])} onClick={readAll}>
            {busy === 'read' ? <><Loader2 size={18} className="ac-spin" /> Reading…</> : <><ScanText size={18} /> {have ? 'Submit documents again' : 'Submit documents'}</>}
          </button>
          {DOCS.some((d) => !files[d.key]) && <span className="ac-muted">Choose all three, then submit them together.</span>}
        </div>
        {busy === 'read' && (
          <div className="ac-readprog" role="status" aria-live="polite">
            <div className="ac-readbar"><i style={{ width: `${progress}%` }} /></div>
            <ol>
              <li data-on={progress >= 6}>Uploading your documents</li>
              <li data-on={progress >= 25}>Reading the Aadhaar, PAN and bank proof together</li>
              <li data-on={progress >= 80}>Filling in your form</li>
            </ol>
          </div>
        )}
        {have > 0 && !busy && (
          <div className="ac-found">
            <b>What we read</b>
            <div className="ac-found-grid">
              {DOCS.map((d) => {
                const doc = docByType[d.type];
                if (!doc) return null;
                const f = doc.extractedFields || {};
                const rows = SHOW[d.type].filter(([k]) => f[k]);
                return (
                  <div key={d.type} className="ac-found-card">
                    <div className="ac-row-between"><b>{d.label.replace(' (masked copy)', '')}</b>
                      <span className="ac-chip-status" data-tone={doc.ocrStatus === 'DONE' && rows.length ? 'ok' : 'warn'}>{doc.ocrStatus === 'DONE' && rows.length ? 'Read' : 'Check by hand'}</span></div>
                    {rows.length ? <dl>{rows.map(([k, l]) => <React.Fragment key={k}><dt>{l}</dt><dd>{f[k]}</dd></React.Fragment>)}</dl> : <p className="ac-muted" style={{ margin: '6px 0 0', fontSize: 14 }}>{doc.warnings?.[0] || 'Nothing could be read from this file.'}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {ready && (
        <div className="ac-box"><h2>2. Check your details</h2>
          <p className="ac-muted">Filled in automatically from your documents. Change anything that is wrong.</p>
          {located && <p className="ac-muted" style={{ marginTop: 10 }}>Your Aadhaar did not list an address, so we used your current location. Change it if the shop is somewhere else.</p>}
          <div className="ac-grid-2" style={{ marginTop: 16 }}>
            <Field id="companyName" label="Business name" error={errors.companyName}><input id="companyName" className="ac-input" value={form.companyName} onChange={(e) => { set('companyName', e.target.value); set('storeName', e.target.value); }} /></Field>
            <Field id="contactName" label="Your full name" error={errors.contactName}><input id="contactName" className="ac-input" value={form.contactName} onChange={(e) => set('contactName', e.target.value)} /></Field>
            <Field id="phone" label="Phone number" error={errors.phone}><input id="phone" className="ac-input" inputMode="tel" value={form.phone} onChange={(e) => set('phone', e.target.value)} /></Field>
            <Field id="email" label="Email" error={errors.email}><input id="email" type="email" className="ac-input" value={form.email} onChange={(e) => set('email', e.target.value)} /></Field>
            <Field id="pan" label="PAN" error={errors.pan}><input id="pan" className="ac-input" maxLength={10} value={form.pan} onChange={(e) => set('pan', e.target.value.toUpperCase())} /></Field>
            <Field id="pincode" label="PIN code" error={errors.pincode}><input id="pincode" className="ac-input" inputMode="numeric" maxLength={6} value={form.pincode} onChange={(e) => set('pincode', e.target.value.replace(/\D/g, ''))} /></Field>
            <div style={{ gridColumn: '1 / -1' }}><Field id="address" label="Store address" error={errors.address}><input id="address" className="ac-input" value={form.address} onChange={(e) => set('address', e.target.value)} /></Field></div>
            <Field id="city" label="City"><input id="city" className="ac-input" value={form.city} onChange={(e) => set('city', e.target.value)} /></Field>
            <Field id="state" label="State"><input id="state" className="ac-input" value={form.state} onChange={(e) => set('state', e.target.value)} /></Field>
          </div>
          {(app?.identity?.bankName || app?.identity?.accountHolder) && (
            <p className="ac-muted" style={{ marginTop: 12 }}>Bank: {[app.identity.accountHolder, app.identity.bankName, app.identity.branch, app.identity.accountLast4 && `account ending ${app.identity.accountLast4}`].filter(Boolean).join(' · ')}</p>
          )}
          <div style={{ marginTop: 20 }}>
            <div className="ac-row-between" style={{ marginBottom: 10 }}>
              <b>Your store on the map</b>
              <div className="ac-row" style={{ gap: 8 }}>
                <button type="button" className="ac-btn ac-btn-soft ac-btn-small" onClick={() => useHere(false)} disabled={!!busy}><LocateFixed size={15} /> {busy === 'here' ? 'Locating…' : 'Use my current location'}</button>
                <button type="button" className="ac-btn ac-btn-outline ac-btn-small" onClick={locate} disabled={busy === 'locate' || !form.address}>{busy === 'locate' ? 'Searching…' : 'Find my address on the map'}</button>
              </div>
            </div>
            <LocationPinMap lat={(pin || DEFAULT_PIN).lat} lng={(pin || DEFAULT_PIN).lng} onChange={(lat, lng) => setPin({ lat, lng })} />
            <p className="ac-muted" style={{ fontSize: 14, margin: '8px 0 0' }}>{pin ? 'We placed the pin from your address. Drag it to your shop door if it is off.' : 'Press "Find my address on the map" or click the map to place the pin.'}</p>
            {errors.location && <span className="ac-err ac-warn" role="alert">{errors.location}</span>}
          </div>
          <label className="ac-check" id="agree-box" style={{ marginTop: 16 }}><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
            <span>I confirm these details are correct, and I agree that my documents are read automatically and reviewed by AutoCart staff. We keep only the last 4 digits of your Aadhaar. You can add your products from the dashboard after approval.</span></label>
          <div className="ac-row" style={{ marginTop: 20, paddingBottom: 20 }}>
            <button className="ac-btn ac-btn-blue" disabled={!!busy || !app || have < DOCS.length} onClick={submit}>{busy === 'submit' ? 'Submitting…' : <><Check size={18} /> Submit application</>}</button>
            {have < DOCS.length && <span className="ac-muted">Add all three documents to submit.</span>}
          </div>
        </div>
      )}
    </div></div>
  );
}
