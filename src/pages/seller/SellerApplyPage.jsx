import HowItWorks from './HowItWorks';
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Plus, Trash2, Upload } from 'lucide-react';
import api from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import LocationPinMap, { findOnMap } from '../../storefront/LocationPinMap';
import { asList } from '../../storefront/parts';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';

const STEPS = ['Business', 'Store and tax', 'Products', 'Documents', 'Review'];
const DOCS = [
  { type: 'AADHAAR', label: 'Aadhaar (masked copy)', hint: 'Download the masked Aadhaar from myAadhaar. The first 8 digits must be hidden. We only keep the last 4.' },
  { type: 'PAN', label: 'PAN card', hint: 'A clear photo or PDF of the owner’s PAN card.' },
  { type: 'GST_CERTIFICATE', label: 'GST certificate', hint: 'The registration certificate showing your GSTIN.' },
  { type: 'ADDRESS_PROOF', label: 'Store address proof', hint: 'Electricity bill, rent agreement or shop licence showing the store address.' },
  { type: 'BANK_PROOF', label: 'Bank proof', hint: 'A cancelled cheque or the first page of the passbook.' },
  { type: 'STORE_PHOTO', label: 'Store photo', hint: 'A photo of your shopfront.' },
];
const FIELD_STEP = { companyName: 0, contactName: 0, phone: 0, email: 0, gstin: 1, pan: 1, address: 1, pincode: 1, location: 1, plannedProducts: 2 };
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
  const [step, setStep] = useState(0);
  const [justSubmitted, setJustSubmitted] = useState(false);
  const [categories, setCategories] = useState([]);
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const [agree, setAgree] = useState(false);
  const [pin, setPin] = useState(DEFAULT_PIN);
  const [form, setForm] = useState({
    companyName: '', storeName: '', contactName: user?.name || '', email: user?.email || '', phone: user?.phone || '', businessType: 'Retailer',
    gstin: '', pan: '', address: '', city: 'Mumbai', state: 'Maharashtra', pincode: '',
    productCategories: [], plannedProducts: [{ name: '', category: '', approxPrice: '', stock: '', image: '' }],
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => { document.title = 'Sell on AutoCart'; }, []);
  useEffect(() => { api.get('/categories').then((r) => setCategories(asList(r.data))).catch(() => {}); }, []);

  // Pick up where the seller left off.
  useEffect(() => {
    if (!user) { setLoading(false); return; }
    api.get('/seller/applications').then((r) => {
      const mine = (r.data || []).find((a) => a.ownerUserId === user.id && !['REJECTED'].includes(a.status)) || (r.data || [])[0];
      if (!mine) {  // first visit: open a draft now so the admin can see this applicant
        if (user.role === 'CUSTOMER') return api.post('/seller/applications/start').then((d) => setApp(d.data)).catch(() => {});
        return null;
      }
      return api.get(`/seller/applications/${mine.id}`).then((d) => {
        const a = d.data;
        setApp(a);
        setForm((f) => ({
          ...f, companyName: /store not named yet/.test(a.companyName || '') ? '' : a.companyName || '', storeName: /store not named yet/.test(a.storeName || a.companyName || '') ? '' : a.storeName || '', contactName: a.applicantName || f.contactName, email: a.email || f.email,
          phone: a.phone || '', businessType: a.businessType || 'Retailer', gstin: a.gstin || '', pan: a.pan || '', address: a.address || '',
          city: a.city || 'Mumbai', state: a.addressState || 'Maharashtra', pincode: a.pincode || '', productCategories: a.productCategories || [],
          plannedProducts: a.plannedProducts?.length ? a.plannedProducts : f.plannedProducts,
        }));
        if (a.storeLatitude) setPin({ lat: a.storeLatitude, lng: a.storeLongitude });
        if (a.status === 'NEEDS_MORE_INFORMATION') setStep(3);
      });
    }).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  const docByType = useMemo(() => Object.fromEntries((app?.documents || []).map((d) => [d.docType, d])), [app]);
  // After pressing Submit, always show the confirmation, even when documents are still missing (status: needs more information).
  const submitted = app && (FINAL.includes(app.status) || (justSubmitted && app.status === 'NEEDS_MORE_INFORMATION'));
  const editing = !submitted;

  const locate = async () => {
    setBusy('locate'); setMessage('');
    try {
      const hit = await findOnMap([form.address, form.city, form.pincode].filter(Boolean).join(', '));
      if (hit) setPin(hit); else setMessage('We could not find that address. Drag the pin to your shop instead.');
    } catch { setMessage('The map search is not available right now. Drag the pin to your shop instead.'); }
    setBusy('');
  };

  const save = async () => {
    setBusy('save'); setErrors({}); setMessage('');
    try {
      const { data } = await api.post('/seller/applications', {
        ...form, storeLatitude: pin.lat, storeLongitude: pin.lng,
        plannedProducts: form.plannedProducts.filter((p) => p.name.trim()).map((p) => ({ ...p, approxPrice: Number(p.approxPrice) || 0, stock: Number(p.stock) || 0 })),
      });
      setApp(data);
      return true;
    } catch (e) {
      const errs = e?.response?.data?.errors || {};
      setErrors(errs);
      setMessage(e?.response?.data?.detail || 'We could not save your application.');
      const first = Object.keys(errs).map((k) => FIELD_STEP[k]).filter((n) => n !== undefined);
      if (first.length) setStep(Math.min(...first));
      return false;
    } finally { setBusy(''); }
  };

  const next = async () => {
    if (step === 2) { if (!(await save())) return; }
    setStep((s) => Math.min(4, s + 1)); window.scrollTo({ top: 0 });
  };

  const upload = async (type, file) => {
    if (!file || !app) return;
    setBusy(type); setMessage('');
    const body = new FormData(); body.append('docType', type); body.append('file', file);
    try {
      await api.post(`/seller/applications/${app.id}/documents`, body, { headers: { 'Content-Type': 'multipart/form-data' } });
      const { data } = await api.get(`/seller/applications/${app.id}`);
      setApp(data);
    } catch (e) { setMessage(e?.response?.data?.detail || 'That upload did not work. Try a smaller image or PDF.'); }
    setBusy('');
  };

  const submit = async () => {
    if (!agree) {  // say why nothing happened, and show the box
      setSubmitNote('Please tick the confirmation box above, then press Submit again.');
      document.getElementById('agree-box')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    setSubmitNote(''); setBusy('submit'); setMessage('');
    try { const { data } = await api.post(`/seller/applications/${app.id}/submit`); setApp(data); setJustSubmitted(true); window.scrollTo({ top: 0 }); }
    catch (e) { setMessage(e?.response?.data?.detail || 'We could not submit your application.'); }
    setBusy('');
  };

  const [photoBusy, setPhotoBusy] = useState(-1);
  const [submitNote, setSubmitNote] = useState('');
  const planPhoto = async (i, file) => {
    if (!file || !app) { if (!app) setMessage('One moment, your application is still being set up. Try again in a few seconds.'); return; }
    setPhotoBusy(i); setMessage('');
    const body = new FormData(); body.append('image', file);
    try { const { data } = await api.post(`/seller/applications/${app.id}/product-image`, body); setProduct(i, 'image', data.url); }
    catch (e) { setMessage(e?.response?.data?.detail || 'That photo did not upload. Use a JPG or PNG under 5 MB.'); }
    setPhotoBusy(-1);
  };
  const setProduct = (i, k, v) => set('plannedProducts', form.plannedProducts.map((p, n) => (n === i ? { ...p, [k]: v } : p)));

  if (loading) return <div className="ac ac-page"><div className="ac-wrap"><div className="ac-skel" style={{ height: 320 }} /></div></div>;

  if (!user) {
    return (
      <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 720 }}>
        <h1 className="ac-display">Sell on AutoCart</h1>
        <details className="ac-howfold"><summary>How selling works and what it costs (tap to open)</summary><HowItWorks compact /></details>
        <p className="ac-sub">Reach shoppers near your store. Sign in or create an account first, then tell us about your shop.</p>
        <div className="ac-row" style={{ marginTop: 24 }}>
          <Link to="/login" state={{ from: '/seller/apply' }} className="ac-btn ac-btn-blue">Sign in</Link>
          <Link to="/register" className="ac-btn ac-btn-outline">Create an account</Link>
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
            <p className="ac-warn" style={{ fontSize: 16 }}>Still needed: {app.missingDocuments.map((t) => DOCS.find((d) => d.type === t)?.label || t).join(', ')}. Your application is saved and our team can see it. Add these when you have them and it moves forward.</p>
          )}
          <p className="ac-muted">Store: {app.storeName || app.companyName} · {app.address}, {app.city} {app.pincode}</p>
          <div className="ac-row">
            {app.status === 'NEEDS_MORE_INFORMATION' && <button className="ac-btn ac-btn-blue" onClick={() => { setJustSubmitted(false); setStep(3); window.scrollTo({ top: 0 }); }}>Add the missing documents</button>}
            {app.status === 'APPROVED' && <Link to="/seller/dashboard" className="ac-btn ac-btn-blue">Go to your seller dashboard</Link>}
            {['REJECTED', 'SUSPENDED'].includes(app.status) && <Link to="/support" className="ac-btn ac-btn-blue">Contact support</Link>}
            <Link to="/" className="ac-btn ac-btn-outline">Back to the store</Link>
          </div>
        </div>
        {app.comparison?.checks?.length > 0 && (
          <div className="ac-box">
            <h2>What we checked</h2>
            <div className="ac-scroll-x"><table className="ac-table"><tbody>{app.comparison.checks.map((c) => (
              <tr key={c.label}><td>{c.label}</td><td><span className="ac-chip-status" data-tone={c.status === 'match' ? 'ok' : c.status === 'mismatch' ? 'bad' : 'warn'}>{c.status === 'match' ? 'Matches' : c.status === 'mismatch' ? 'Does not match' : 'Could not read'}</span></td></tr>))}</tbody></table></div>
          </div>
        )}
      </div></div>
    );
  }

  const status = app?.status && STATUS_COPY[app.status];
  const docsDone = DOCS.filter((d) => docByType[d.type] && docByType[d.type].ocrStatus !== 'REJECTED').length;

  return (
    <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 900 }}>
      <h1 className="ac-display">Sell on AutoCart</h1>
      <details className="ac-howfold"><summary>How selling works and what it costs (tap to open)</summary><HowItWorks compact /></details>
      <p className="ac-sub" style={{ marginTop: 18 }}>Tell us about your shop, add your documents, and our team will review your application. It usually takes a few minutes to fill in.</p>

      <ol className="ac-steps-bar" aria-label="Application steps" style={{ listStyle: 'none', padding: 0 }}>
        {STEPS.map((s, i) => <li key={s}><span data-on={i === step} data-done={i < step}>{i < step ? '✓ ' : ''}{i + 1}. {s}</span></li>)}
      </ol>

      {step !== 3 && (
        <div className="ac-box ac-docsneeded" role="note" style={{ marginBottom: 20 }}>
          <b>Keep these ready. You will upload them in step 4 (Documents).</b>
          <ul>{DOCS.map((d) => <li key={d.type}><span><Upload size={14} /></span> <b>{d.label}</b><small className="ac-muted"> {d.hint}</small></li>)}</ul>
          <p className="ac-muted" style={{ margin: '8px 0 0', fontSize: 14 }}>The upload section opens after you save steps 1 to 3 (it needs your application to exist first). Your Aadhaar must be the masked copy: we only keep the last 4 digits.</p>
        </div>
      )}

      {status && app.status === 'NEEDS_MORE_INFORMATION' && (
        <div className="ac-box" style={{ marginBottom: 20, borderColor: 'var(--gold)' }}>
          <b>{status[1]}</b><p style={{ margin: '6px 0 0' }}>{app.adminNotes || app.aiAssessment || status[2]}</p>
        </div>
      )}
      {message && <div className="ac-box" role="alert" style={{ marginBottom: 20, borderColor: 'var(--coral)' }}>{message}</div>}

      {step === 0 && (
        <div className="ac-box"><h2>About your business</h2>
          <div className="ac-grid-2" style={{ marginTop: 16 }}>
            <Field id="companyName" label="Business name" error={errors.companyName}><input id="companyName" className="ac-input" aria-invalid={!!errors.companyName} value={form.companyName} onChange={(e) => set('companyName', e.target.value)} placeholder="Sharma Electronics" /></Field>
            <Field id="storeName" label="Store name on AutoCart" hint="Leave empty to use the business name."><input id="storeName" className="ac-input" value={form.storeName} onChange={(e) => set('storeName', e.target.value)} /></Field>
            <Field id="contactName" label="Your full name" hint="As it appears on your Aadhaar and PAN." error={errors.contactName}><input id="contactName" className="ac-input" aria-invalid={!!errors.contactName} value={form.contactName} onChange={(e) => set('contactName', e.target.value)} /></Field>
            <Field id="phone" label="Phone number" error={errors.phone}><input id="phone" className="ac-input" inputMode="tel" aria-invalid={!!errors.phone} value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="9820012345" /></Field>
            <Field id="email" label="Business email" error={errors.email}><input id="email" type="email" className="ac-input" aria-invalid={!!errors.email} value={form.email} onChange={(e) => set('email', e.target.value)} /></Field>
            <Field id="businessType" label="Type of business"><select id="businessType" className="ac-select" value={form.businessType} onChange={(e) => set('businessType', e.target.value)}>
              {['Retailer', 'Wholesaler', 'Brand or manufacturer', 'Individual seller'].map((t) => <option key={t}>{t}</option>)}</select></Field>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="ac-box"><h2>Store location and tax details</h2>
          <div className="ac-grid-2" style={{ marginTop: 16 }}>
            <Field id="gstin" label="GSTIN" hint="15 characters, for example 27ABCDE1234F1Z5." error={errors.gstin}><input id="gstin" className="ac-input" maxLength={15} aria-invalid={!!errors.gstin} value={form.gstin} onChange={(e) => set('gstin', e.target.value.toUpperCase())} /></Field>
            <Field id="pan" label="PAN" hint="10 characters, for example ABCDE1234F." error={errors.pan}><input id="pan" className="ac-input" maxLength={10} aria-invalid={!!errors.pan} value={form.pan} onChange={(e) => set('pan', e.target.value.toUpperCase())} /></Field>
            <div style={{ gridColumn: '1 / -1' }}><Field id="address" label="Store address" error={errors.address}><input id="address" className="ac-input" aria-invalid={!!errors.address} value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="12 Hill Road, Andheri East" /></Field></div>
            <Field id="city" label="City"><input id="city" className="ac-input" value={form.city} onChange={(e) => set('city', e.target.value)} /></Field>
            <Field id="state" label="State"><input id="state" className="ac-input" value={form.state} onChange={(e) => set('state', e.target.value)} /></Field>
            <Field id="pincode" label="PIN code" error={errors.pincode}><input id="pincode" className="ac-input" inputMode="numeric" maxLength={6} aria-invalid={!!errors.pincode} value={form.pincode} onChange={(e) => set('pincode', e.target.value.replace(/\D/g, ''))} placeholder="400069" /></Field>
          </div>
          <div style={{ marginTop: 20 }}>
            <div className="ac-row-between" style={{ marginBottom: 10 }}>
              <b>Where is your store?</b>
              <button type="button" className="ac-btn ac-btn-outline ac-btn-small" onClick={locate} disabled={busy === 'locate' || !form.address}>{busy === 'locate' ? 'Searching…' : 'Find my address on the map'}</button>
            </div>
            <LocationPinMap lat={pin.lat} lng={pin.lng} onChange={(lat, lng) => setPin({ lat, lng })} />
            <p className="ac-muted" style={{ fontSize: 14, margin: '8px 0 0' }}>Click the map or drag the pin to your shop’s door. Customers use this to find you. ({pin.lat}, {pin.lng})</p>
            {errors.location && <span className="ac-err ac-warn" role="alert">{errors.location}</span>}
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="ac-box"><h2>What will you sell?</h2>
          <p className="ac-muted">Pick your categories and list a few products to start. You can add more after you are approved.</p>
          <div className="ac-row" style={{ margin: '14px 0' }}>
            {categories.map((c) => {
              const on = form.productCategories.includes(c.name);
              return <button type="button" key={c.id} className={`ac-act ${on ? 'ac-btn-blue' : ''}`} style={on ? { background: 'var(--brand)', color: '#fff', borderColor: 'var(--brand)' } : {}} aria-pressed={on}
                onClick={() => set('productCategories', on ? form.productCategories.filter((x) => x !== c.name) : [...form.productCategories, c.name])}>{c.name}</button>;
            })}
          </div>
          {form.plannedProducts.map((p, i) => (
            <div className="ac-plan" key={i}>
              <div className="ac-grid-2" style={{ gridTemplateColumns: 'minmax(0,2fr) minmax(0,1.3fr) minmax(0,1fr) auto', alignItems: 'end' }}>
                <Field id={`pn${i}`} label="Product name"><input id={`pn${i}`} className="ac-input" placeholder="Wireless mouse" value={p.name} onChange={(e) => setProduct(i, 'name', e.target.value)} /></Field>
                <Field id={`pc${i}`} label="Category"><select id={`pc${i}`} className="ac-select" value={p.category} onChange={(e) => setProduct(i, 'category', e.target.value)}><option value="">Choose</option>{categories.map((c) => <option key={c.id}>{c.name}</option>)}</select></Field>
                <Field id={`pp${i}`} label="Price (₹)"><input id={`pp${i}`} className="ac-input" inputMode="numeric" value={p.approxPrice} onChange={(e) => setProduct(i, 'approxPrice', e.target.value.replace(/\D/g, ''))} /></Field>
                <button type="button" className="ac-btn ac-btn-outline ac-btn-small" aria-label="Remove product" disabled={form.plannedProducts.length === 1} onClick={() => set('plannedProducts', form.plannedProducts.filter((_, n) => n !== i))}><Trash2 size={16} /></button>
              </div>
              <div className="ac-plan-row">
                <Field id={`ps${i}`} label="Units in stock"><input id={`ps${i}`} className="ac-input" inputMode="numeric" placeholder="e.g. 25" value={p.stock ?? ''} onChange={(e) => setProduct(i, 'stock', e.target.value.replace(/\D/g, ''))} /></Field>
                <div>
                  <span className="ac-lbl">Product photo</span>
                  <label className="ac-photo-pick">
                    {p.image ? <img src={p.image} alt="" /> : <Upload size={18} />}
                    <span>{photoBusy === i ? 'Uploading…' : p.image ? 'Change photo' : 'Add a photo'}</span>
                    <input type="file" accept="image/*" className="ac-sr" onChange={(e) => { planPhoto(i, e.target.files?.[0]); e.target.value = ''; }} />
                  </label>
                </div>
              </div>
            </div>
          ))}
          {errors.plannedProducts && <span className="ac-err ac-warn" role="alert">{errors.plannedProducts}</span>}
          <button type="button" className="ac-btn ac-btn-soft ac-btn-small" style={{ marginTop: 16 }} onClick={() => set('plannedProducts', [...form.plannedProducts, { name: '', category: '', approxPrice: '', stock: '', image: '' }])}><Plus size={16} /> Add another product</button>
        </div>
      )}

      {step === 3 && (
        <div className="ac-box"><h2>Upload your documents</h2>
          <p className="ac-muted">We read each file and show you what we found, so you can fix a mistake straight away. Files are private: only you and our review team can open them. {docsDone} of {DOCS.length} added.</p>
          {DOCS.map((d) => {
            const doc = docByType[d.type];
            const fields = doc?.extractedFields || {};
            const rejected = doc?.ocrStatus === 'REJECTED';
            return (
              <div className="ac-doc" key={d.type}>
                <div>
                  <b>{d.label}</b> {doc && !rejected && <span className="ac-chip-status" data-tone={doc.ocrStatus === 'DONE' || doc.ocrStatus === 'NOT_REQUIRED' ? 'ok' : 'warn'}>{doc.ocrStatus === 'NOT_REQUIRED' ? 'Added' : doc.ocrStatus === 'DONE' ? 'Read' : 'Needs a person to read'}</span>}
                  <div className="ac-muted" style={{ fontSize: 14 }}>{d.hint}</div>
                  {busy === d.type && <div className="ac-muted" role="status">Reading your document. This can take up to 20 seconds…</div>}
                  {doc && Object.keys(fields).length > 0 && (
                    <dl>{Object.entries(fields).map(([k, v]) => <React.Fragment key={k}><dt>{k.replace(/([A-Z])/g, ' $1').toLowerCase()}</dt><dd>{String(v)}</dd></React.Fragment>)}</dl>
                  )}
                  {doc?.warnings?.map((w) => <div className="ac-warn" key={w} role="alert">{w}</div>)}
                </div>
                <label className="ac-btn ac-btn-outline ac-btn-small" style={{ cursor: 'pointer' }}>
                  <Upload size={16} /> {doc && !rejected ? 'Replace' : 'Choose file'}
                  <input type="file" className="ac-sr" accept={d.type === 'STORE_PHOTO' ? 'image/*' : 'image/*,.pdf'} disabled={!!busy} onChange={(e) => { upload(d.type, e.target.files?.[0]); e.target.value = ''; }} />
                </label>
              </div>
            );
          })}
        </div>
      )}

      {step === 4 && (
        <div className="ac-box"><h2>Check and submit</h2>
          <div className="ac-scroll-x"><table className="ac-table"><tbody>
            {[['Business', `${form.companyName}${form.storeName ? ` (${form.storeName})` : ''}`], ['Contact', `${form.contactName}, ${form.phone}, ${form.email}`], ['Store address', `${form.address}, ${form.city}, ${form.state} ${form.pincode}`],
              ['Map pin', `${pin.lat}, ${pin.lng}`], ['GSTIN / PAN', `${form.gstin} / ${form.pan}`], ['Categories', form.productCategories.join(', ') || '-'],
              ['Products', form.plannedProducts.filter((p) => p.name).map((p) => p.name).join(', ')], ['Documents', `${docsDone} of ${DOCS.length} added`]].map(([k, v]) => <tr key={k}><th>{k}</th><td>{v}</td></tr>)}
          </tbody></table></div>
          {docsDone < DOCS.length && <p className="ac-warn">Some documents are missing. You can still submit, but we will ask you for them.</p>}
          <label className="ac-check" id="agree-box" style={{ marginTop: 16 }}><input type="checkbox" checked={agree} onChange={(e) => { setAgree(e.target.checked); if (e.target.checked) setSubmitNote(''); }} />
            <span>I confirm these details are correct, and I agree that my documents are read automatically and reviewed by AutoCart staff. We keep only the last 4 digits of your Aadhaar.</span></label>
        </div>
      )}

      {submitNote && step === 4 && <div className="ac-warn" role="alert" style={{ marginTop: 14 }}>{submitNote}</div>}
      <div className="ac-row-between" style={{ marginTop: 24, paddingBottom: 40 }}>
        <button className="ac-btn ac-btn-outline" disabled={step === 0 || !!busy} onClick={() => setStep(step - 1)}>Back</button>
        {step < 4
          ? <button className="ac-btn ac-btn-blue" disabled={!!busy || (step === 3 && !app)} onClick={next}>{busy === 'save' ? 'Saving…' : step === 2 ? 'Save and continue' : 'Continue'}</button>
          : <button className="ac-btn ac-btn-blue" disabled={!!busy || !app} onClick={submit}>{busy === 'submit' ? 'Submitting…' : <><Check size={18} /> Submit application</>}</button>}
      </div>
    </div></div>
  );
}
