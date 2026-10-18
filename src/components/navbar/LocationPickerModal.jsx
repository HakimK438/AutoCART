import React, { useEffect, useState } from 'react';
import { MapPin, Navigation, X, ShieldCheck, Loader2, Search } from 'lucide-react';
import { useLocation } from '../../context/LocationContext';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

const HUBS = [
  { name: 'Andheri', pin: '400069' },
  { name: 'Bandra', pin: '400050' },
  { name: 'Powai', pin: '400076' },
  { name: 'Borivali', pin: '400092' },
  { name: 'Ghatkopar', pin: '400077' },
  { name: 'Thane', pin: '400601' },
  { name: 'Navi Mumbai (Vashi)', pin: '400703' },
  { name: 'Kalyan', pin: '421301' },
];

/** "Select delivery location" dialog, in the same look as the payment and chat dialogs. */
export const LocationPickerModal = ({ isOpen, onClose }) => {
  const { location, loading, error, requestBrowserLocation, setManualLocation } = useLocation();
  const [pinInput, setPinInput] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const choose = async (value) => {
    if (!value.trim()) return;
    setStatus('Checking which stores can deliver there…');
    const ok = await setManualLocation(value.trim());
    if (ok) { setStatus('Location updated.'); window.setTimeout(() => { setStatus(''); onClose(); }, 600); } else setStatus('');
  };

  const useDevice = () => {
    requestBrowserLocation();
    window.setTimeout(onClose, 1500);
  };

  return (
    <div className="ac">
      <div className="ac-sc-back" style={{ zIndex: 95 }} onClick={onClose} aria-hidden="true" />
      <div className="ac-rzp" style={{ width: 'min(440px, calc(100% - 24px))' }} role="dialog" aria-modal="true" aria-label="Select delivery location">
        <div className="ac-rzp-head">
          <div>
            <b>Select delivery location</b>
            <small style={{ opacity: 0.85 }}>See what local stores near you have in stock</small>
          </div>
          <button className="ac-sc-x" style={{ background: 'rgba(255,255,255,.18)', color: '#fff' }} onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="ac-rzp-body" style={{ display: 'grid', gap: 16 }}>
          <div className="ac-storebox">
            <MapPin size={20} color="var(--brand)" />
            <div style={{ flex: 1, minWidth: 0 }}>
              <small className="ac-muted">Delivering to</small>
              <div><b>{location.displayName || `${location.city} (${location.pincode})`}</b></div>
            </div>
          </div>

          <button className="ac-btn ac-btn-blue" style={{ width: '100%' }} onClick={useDevice} disabled={loading}>
            {loading ? <Loader2 size={18} className="ac-spin" /> : <Navigation size={18} />} Use my current location
          </button>

          <div className="ac-muted" style={{ textAlign: 'center', fontSize: 14 }}>or enter a PIN code or area</div>

          <form className="ac-row" style={{ gap: 8 }} onSubmit={(e) => { e.preventDefault(); choose(pinInput); }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={16} style={{ position: 'absolute', left: 14, top: 16, color: 'var(--slate)' }} />
              <label className="ac-sr" htmlFor="loc-pin">PIN code or area</label>
              <input id="loc-pin" className="ac-input" style={{ paddingLeft: 38 }} placeholder="e.g. 400069 or Andheri" value={pinInput} onChange={(e) => setPinInput(e.target.value)} />
            </div>
            <button className="ac-btn ac-btn-outline" disabled={loading || !pinInput.trim()}>Check</button>
          </form>

          {status && <div className="ac-storebox" role="status">{status}</div>}
          {error && <div className="ac-warn" role="alert">{error}</div>}

          <div>
            <div className="ac-muted" style={{ fontSize: 14, marginBottom: 8 }}>Popular areas</div>
            <div className="ac-row" style={{ gap: 8, flexWrap: 'wrap' }}>
              {HUBS.map((h) => <button key={h.pin} className="ac-act" onClick={() => choose(h.pin)}>{h.name}</button>)}
            </div>
          </div>

          <p className="ac-muted" style={{ fontSize: 13, margin: 0, display: 'flex', gap: 8 }}>
            <ShieldCheck size={16} style={{ flexShrink: 0 }} /> Your location stays on this device. It is used only to find nearby stores and delivery times.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LocationPickerModal;
