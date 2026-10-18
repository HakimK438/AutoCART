import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapPin, Store, Truck, Banknote, ShieldCheck, QrCode, Smartphone, CreditCard } from 'lucide-react';
import { useCart } from '../../hooks/useCart';
import { useAuth } from '../../hooks/useAuth';
import { useLocation } from '../../context/LocationContext';
import { MumbaiStoreMap } from '../../components/map/MumbaiStoreMap';
import UpiPay from '../../storefront/UpiPay';
import RazorpayTest from '../../storefront/RazorpayTest';
import { money, sized, firstImage } from '../../storefront/parts';
import orderService from '../../services/orderService';
import api from '../../services/api';
import { lookupPin, pinMatchesCity } from '../../utils/geocode';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

const ONLINE = { id: 'Razorpay (Test Mode)', icon: CreditCard, title: 'Pay online (UPI, card, net banking)', text: 'Pay securely now and your order is confirmed at once. Test mode: no real money moves.' };
const UPI_NOW = { id: 'UPI (Scan & Pay)', icon: QrCode, title: 'Pay now with UPI', text: 'Scan a QR and pay the seller directly. They confirm it and pack your order.' };
const METHODS = {
  delivery: [
    ONLINE,
    UPI_NOW,
    { id: 'Cash on Delivery', icon: Banknote, title: 'Cash on delivery', text: 'Pay in cash when it arrives.' },
    { id: 'UPI or Card on Delivery', icon: Smartphone, title: 'UPI or card on delivery', text: 'Pay by UPI or card when it arrives. No cash needed.' },
  ],
  pickup: [
    ONLINE,
    UPI_NOW,
    { id: 'Pay at Store', icon: Store, title: 'Pay at the store', text: 'Pay when you collect your order, by cash, UPI or card.' },
  ],
};

/** Delivery address fields taken from the saved location (empty when the location is only the built-in default). */
const fromLoc = (l) => (l?.source && l.source !== 'default'
  ? { addressLine: l.line || '', city: l.city || 'Mumbai', state: l.state || 'Maharashtra', pinCode: l.pincode || '' }
  : { addressLine: '', city: 'Mumbai', state: 'Maharashtra', pinCode: '' });

export const Checkout = () => {
  const { cartItems, subtotal, discountAmount, deliveryCharge, finalTotal, coupon, clearCart } = useCart();
  const { user } = useAuth();
  const { location, selectedStore, requestBrowserLocation, loading: locating } = useLocation();
  const navigate = useNavigate();

  const [mode, setMode] = useState('delivery');
  const [method, setMethod] = useState(ONLINE.id);
  const [mapOpen, setMapOpen] = useState(false);
  const [addr, setAddr] = useState({ fullName: user?.name || '', phone: user?.phone || '', flat: '', landmark: '', addressLine: fromLoc(location).addressLine, city: fromLoc(location).city, state: fromLoc(location).state, pinCode: fromLoc(location).pinCode });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toPay, setToPay] = useState(null);

  useEffect(() => { document.title = 'Checkout | AutoCart'; }, []);
  useEffect(() => { if (cartItems.length === 0 && !toPay) navigate('/cart', { replace: true }); }, [cartItems.length, toPay, navigate]);

  const set = (k, v) => setAddr((a) => ({ ...a, [k]: v }));

  // Zero typing: name and phone come from the account, the address from the device location (asked once, on arrival).
  useEffect(() => { setAddr((a) => ({ ...a, fullName: a.fullName || user?.name || '', phone: a.phone || user?.phone || '' })); }, [user]);
  useEffect(() => {
    api.get('/support/last-address').then((r) => { const l = r.data?.address; if (l) setAddr((a) => ({ ...a, addressLine: a.addressLine || l.addressLine || '', city: a.city || l.city || '', state: a.state || l.state || '', pinCode: a.pinCode || l.pinCode || '', phone: a.phone || l.phone || '', fullName: a.fullName || l.fullName || '' })); }).catch(() => {});
    if (!(location?.source && location.source !== 'default') && location?.permissionStatus !== 'denied') requestBrowserLocation();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // The PIN code and the city must agree. A valid PIN fills city and state; a PIN from another city is flagged.
  const [pinNote, setPinNote] = useState({ ok: true, text: '' });
  useEffect(() => {
    if (!/^[1-9]\d{5}$/.test(addr.pinCode)) { setPinNote({ ok: true, text: '' }); return undefined; }
    let live = true;
    lookupPin(addr.pinCode).then((info) => {
      if (!live) return;
      if (!info) { setPinNote({ ok: false, text: 'We could not find this PIN code. Check it.' }); return; }
      const ok = pinMatchesCity(info, addr.city);
      setPinNote(ok ? { ok: true, text: `${info.areas[0]}, ${info.city}, ${info.state}` } : { ok: false, text: `This PIN belongs to ${info.city}, ${info.state}, but your city says "${addr.city}".`, fix: info });
    });
    return () => { live = false; };
  }, [addr.pinCode, addr.city]);
  const storeId = selectedStore?.storeId || selectedStore?.id;
  const storeName = selectedStore?.storeName || selectedStore?.name;

  // "Pay now with UPI" works only when the whole cart is from one seller who has added a UPI ID. Ask the server, and explain when it cannot.
  const [upi, setUpi] = useState({ checked: false, available: false, reason: '' });
  const cartKey = cartItems.map((i) => i.id).sort().join(',');
  useEffect(() => {
    let live = true;
    setUpi((u) => ({ ...u, checked: false }));
    api.post('/payments/upi-check', { items: cartItems.map((i) => ({ id: i.id })) })
      .then((r) => { if (live) setUpi({ checked: true, available: !!r.data.available, reason: r.data.reason || '', payee: r.data.payee }); })
      .catch(() => { if (live) setUpi({ checked: true, available: false, reason: 'UPI payment could not be checked right now.' }); });
    return () => { live = false; };
  }, [cartKey]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (upi.checked && !upi.available && method.startsWith('UPI (')) setMethod(METHODS[mode][0].id); }, [upi, method, mode]);

  const switchMode = (m) => { setMode(m); setMethod(METHODS[m][0].id); };

  // Review first: when the saved location already gave a complete address, the form stays closed and the customer only confirms.
  const [editing, setEditing] = useState(null);       // null = decide automatically
  const [payOpen, setPayOpen] = useState(true); // every way to pay is listed up front, online first
  const detailsDone = addr.fullName.trim() && addr.phone.replace(/\D/g, '').length >= 10
    && (mode === 'pickup' || (addr.addressLine.trim() && /^[1-9]\d{5}$/.test(addr.pinCode)));
  const showForm = editing === null ? !detailsDone : editing;
  const chosenMethod = METHODS[mode].find((m) => m.id === method) || METHODS[mode][0];

  const validate = () => {
    const e = {};
    if (!addr.fullName.trim()) e.fullName = 'Enter your name.';
    if (addr.phone.replace(/\D/g, '').length < 10) e.phone = 'Enter a 10-digit phone number.';
    if (mode === 'delivery') {
      if (!addr.addressLine.trim()) e.addressLine = 'Enter your delivery address.';
      if (!/^[1-9]\d{5}$/.test(addr.pinCode)) e.pinCode = 'Enter a 6-digit PIN code.';
      else if (!pinNote.ok) e.pinCode = pinNote.text;
    }
    if (mode === 'pickup' && !storeId) e.store = 'Choose the store where you will collect your order.';
    setErrors(e);
    return e;
  };

  const hasLocation = location?.source && location.source !== 'default';
  const pin = hasLocation ? { latitude: location.lat, longitude: location.lng } : null;
  // Whenever the customer's location is set or updated, the delivery address follows it.
  useEffect(() => {
    if (!hasLocation) return;
    const f = fromLoc(location);
    setAddr((a) => ({ ...a, addressLine: f.addressLine || a.addressLine, city: f.city || a.city, state: f.state || a.state, pinCode: f.pinCode || a.pinCode }));
  }, [location]); // eslint-disable-line react-hooks/exhaustive-deps

  const place = async () => {
    const bad = validate();
    if (Object.keys(bad).length) {
      setEditing(true);
      // Say so right here and take the customer to the first field that needs attention (the form is above this button).
      const order = [['fullName', 'c-name'], ['phone', 'c-phone'], ['addressLine', 'c-addr'], ['pinCode', 'c-pin'], ['store', 'checkout-store']];
      const first = order.find(([k]) => bad[k]);
      setError(`Please complete: ${Object.values(bad).join(' ')}`);
      window.setTimeout(() => { const el = first && document.getElementById(first[1]); el?.scrollIntoView({ block: 'center', behavior: 'smooth' }); if (el && el.focus && el.tagName !== 'DIV') el.focus({ preventScroll: true }); }, 30);
      return;
    }
    setBusy(true); setError('');
    try {
      const order = await orderService.createOrder({
        items: cartItems.map((i) => ({ id: i.id, quantity: i.quantity })), couponCode: coupon?.code || '', paymentMethod: method,
        shippingAddress: { ...addr, addressLine: [addr.flat, addr.addressLine].filter(Boolean).join(', '), ...(pin || {}), fulfillment: mode }, storeId: storeId || undefined,
      });
      if (order.paymentRequired) { setToPay(order); } else { clearCart(); navigate('/order-success', { state: { order } }); }
    } catch (e) {
      setError(e?.response?.data?.detail || 'We could not place your order. Please try again.');
      window.setTimeout(() => document.getElementById('checkout-error')?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 50);
    }
    setBusy(false);
  };

  const finishPaid = (order) => { clearCart(); navigate('/order-success', { state: { order } }); };
  const leaveUnpaid = () => { const id = toPay.id; clearCart(); setToPay(null); navigate(`/orders/${id}`); };

  return (
    <div className="ac ac-page"><div className="ac-wrap">
      <h1 className="ac-display">Review your order</h1>
      <p className="ac-muted" style={{ marginTop: 6 }}>Everything is filled in from your account and location. Check it and place your order.</p>
      <div className="ac-twocol" style={{ marginTop: 28 }}>
        <div>
          <div className="ac-box">
            <h2>How do you want your order?</h2>
            <div className="ac-seg" role="radiogroup" aria-label="Delivery or pickup" style={{ marginTop: 14 }}>
              <button role="radio" aria-checked={mode === 'delivery'} data-on={mode === 'delivery'} onClick={() => switchMode('delivery')}><Truck size={18} /> Deliver to me</button>
              <button role="radio" aria-checked={mode === 'pickup'} data-on={mode === 'pickup'} onClick={() => switchMode('pickup')}><Store size={18} /> I'll pick it up</button>
            </div>

            <div className="ac-storebox" style={{ marginTop: 16 }}>
              <MapPin size={20} color="var(--brand)" />
              <div style={{ flex: 1, minWidth: 0 }}>
                {storeId ? <><b>{storeName}</b><div className="ac-muted" style={{ fontSize: 14 }}>{selectedStore?.address}{selectedStore?.distanceKm ? ` · ${selectedStore.distanceKm} km away` : ''}</div></>
                  : <><b>{mode === 'pickup' ? 'Choose a store to collect from' : 'Choose a store for faster delivery (optional)'}</b><div className="ac-muted" style={{ fontSize: 14 }}>See real stores on the map, with distance and time.</div></>}
              </div>
              <button className="ac-btn ac-btn-outline ac-btn-small" onClick={() => setMapOpen(true)}>{storeId ? 'Change' : 'Open map'}</button>
            </div>
            {errors.store && <div id="checkout-store" className="ac-warn" role="alert">{errors.store}</div>}
          </div>

          {!showForm && (
            <div className="ac-box" aria-label="Delivery summary">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ minWidth: 0 }}>
                  <h2>{mode === 'delivery' ? 'Delivering to' : 'Collecting at'}</h2>
                  <p style={{ margin: '10px 0 2px' }}><b>{addr.fullName}</b> · {addr.phone}</p>
                  {mode === 'delivery'
                    ? <p className="ac-muted" style={{ margin: 0 }}>{[addr.flat, addr.addressLine, addr.landmark && `Near ${addr.landmark}`, addr.city, addr.state].filter(Boolean).join(', ')} {addr.pinCode}</p>
                    : <p className="ac-muted" style={{ margin: 0 }}>{storeId ? `${storeName}${selectedStore?.address ? `, ${selectedStore.address}` : ''}` : 'Choose a store above'}</p>}
                  {mode === 'delivery' && !pinNote.ok && <p className="ac-warn" role="alert" style={{ marginTop: 8 }}>{pinNote.text}</p>}
                </div>
                <button type="button" className="ac-btn ac-btn-outline ac-btn-small" onClick={() => setEditing(true)}><Pencil size={14} /> Change</button>
              </div>
            </div>
          )}

          {showForm && (
          <div className="ac-box">
            <h2>{mode === 'delivery' ? 'Delivery details' : 'Your details'}</h2>
            <div className="ac-grid-2" style={{ marginTop: 14 }}>
              <div className="ac-field"><label htmlFor="c-name">Full name</label><input id="c-name" className="ac-input" aria-invalid={!!errors.fullName} value={addr.fullName} onChange={(e) => set('fullName', e.target.value)} autoComplete="name" />{errors.fullName && <span className="ac-err" role="alert">{errors.fullName}</span>}</div>
              <div className="ac-field"><label htmlFor="c-phone">Phone</label><input id="c-phone" className="ac-input" inputMode="tel" aria-invalid={!!errors.phone} value={addr.phone} onChange={(e) => set('phone', e.target.value)} autoComplete="tel" />{errors.phone && <span className="ac-err" role="alert">{errors.phone}</span>}</div>
              {mode === 'delivery' && (
                <>
                  <div className="ac-field"><label htmlFor="c-flat">Flat / house / building</label><input id="c-flat" className="ac-input" value={addr.flat} onChange={(e) => set('flat', e.target.value)} placeholder="e.g. B-204, Sai Heights" autoComplete="address-line2" /></div>
                  <div className="ac-field"><label htmlFor="c-land">Landmark (optional)</label><input id="c-land" className="ac-input" value={addr.landmark} onChange={(e) => set('landmark', e.target.value)} placeholder="e.g. Near Metro station" /></div>
                  <div className="ac-field" style={{ gridColumn: '1 / -1' }}><label htmlFor="c-addr">Street and area</label><input id="c-addr" className="ac-input" aria-invalid={!!errors.addressLine} value={addr.addressLine} onChange={(e) => set('addressLine', e.target.value)} placeholder="Flat, building, street, area" autoComplete="street-address" />{errors.addressLine && <span className="ac-err" role="alert">{errors.addressLine}</span>}</div>
                  <div className="ac-field" style={{ gridColumn: '1 / -1' }}>
                    <button type="button" className="ac-btn ac-btn-outline ac-btn-small" onClick={requestBrowserLocation} disabled={locating} style={{ justifySelf: 'start' }}>
                      {locating ? 'Finding you…' : hasLocation ? 'Update from my current location' : 'Fill my address from my current location'}
                    </button>
                    <small className="ac-muted" role="status">{hasLocation ? `Using ${location.displayName}. Check the details below and add your flat or building.` : 'We look up your street, area, city and PIN code. Nothing is saved until you place the order.'}</small>
                  </div>
                  <div className="ac-field"><label htmlFor="c-city">City</label><input id="c-city" className="ac-input" value={addr.city} onChange={(e) => set('city', e.target.value)} /></div>
                  <div className="ac-field"><label htmlFor="c-state">State</label><input id="c-state" className="ac-input" value={addr.state} onChange={(e) => set('state', e.target.value)} autoComplete="address-level1" /></div>
                  <div className="ac-field"><label htmlFor="c-pin">PIN code</label><input id="c-pin" className="ac-input" inputMode="numeric" maxLength={6} aria-invalid={!!errors.pinCode} value={addr.pinCode} onChange={(e) => set('pinCode', e.target.value.replace(/\D/g, ''))} autoComplete="postal-code" />{errors.pinCode && <span className="ac-err" role="alert">{errors.pinCode}</span>}
                    {!errors.pinCode && pinNote.text && <small role="status" style={{ color: pinNote.ok ? 'var(--ok)' : 'var(--coral)' }}>{pinNote.ok ? '✓ ' : ''}{pinNote.text}{pinNote.fix && <> <button type="button" className="ac-textlink" onClick={() => setAddr((a) => ({ ...a, city: pinNote.fix.city, state: pinNote.fix.state }))}>Use {pinNote.fix.city}</button></>}</small>}
                  </div>
                </>
              )}
            </div>
            {detailsDone && <button type="button" className="ac-btn ac-btn-outline ac-btn-small" style={{ marginTop: 14 }} onClick={() => setEditing(false)}>Done</button>}
          </div>
          )}

          <div className="ac-box">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <h2>Payment</h2>
            </div>
            {!payOpen && (
              <div className="ac-pay" data-on="true" style={{ marginTop: 14 }}>
                <chosenMethod.icon size={22} color="var(--brand)" />
                <span><b>{chosenMethod.title}</b><small>{chosenMethod.text}</small></span>
              </div>
            )}
            {payOpen && <div style={{ display: 'grid', gap: 10, marginTop: 14 }} role="radiogroup" aria-label="Payment method">
              {METHODS[mode].map((m) => {
                const isUpi = m.id.startsWith('UPI (');
                const off = isUpi && upi.checked && !upi.available;
                return (
                  <label key={m.id} className="ac-pay" data-on={method === m.id} aria-disabled={off} style={off ? { opacity: 0.6, cursor: 'not-allowed' } : undefined}>
                    <input type="radio" name="pay" checked={method === m.id} disabled={off} onChange={() => setMethod(m.id)} />
                    <m.icon size={22} color="var(--brand)" />
                    <span><b>{m.title}</b><small>{off ? `Not available for this cart. ${upi.reason}` : isUpi && upi.payee ? `Scan a QR and pay ${upi.payee} directly. They confirm it and pack your order.` : m.text}</small></span>
                  </label>
                );
              })}
            </div>}
            <p className="ac-muted" style={{ fontSize: 14, margin: '12px 0 0' }}><ShieldCheck size={14} /> Online payments run in test mode, and card details never touch this site. Cash and pay-at-store orders stay unpaid until you pay.</p>
          </div>
        </div>

        <aside className="ac-box ac-summary" aria-label="Order summary">
          <h2>Your order</h2>
          <div style={{ margin: '12px 0' }}>
            {cartItems.map((i) => (
              <div className="ac-mini-line" key={i.id}><img src={sized(firstImage(i), 100)} alt="" /><span>{i.name}<small> × {i.quantity}</small></span><b>{money(i.price * i.quantity)}</b></div>
            ))}
          </div>
          <dl className="ac-sum">
            <div><dt>Subtotal</dt><dd>{money(subtotal)}</dd></div>
            {discountAmount > 0 && <div><dt>Coupon {coupon?.code}</dt><dd style={{ color: 'var(--ok)' }}>-{money(discountAmount)}</dd></div>}
            <div><dt>Delivery</dt><dd>{mode === 'pickup' ? 'None' : deliveryCharge ? money(deliveryCharge) : 'Free'}</dd></div>
            <div className="ac-sum-total"><dt>Total</dt><dd>{money(finalTotal - (mode === 'pickup' ? deliveryCharge : 0))}</dd></div>
          </dl>
          {error && <div id="checkout-error" className="ac-warn" role="alert" style={{ marginBottom: 10 }}>{error}</div>}
          <button className="ac-btn ac-btn-blue" style={{ width: '100%' }} onClick={place} disabled={busy}>{busy ? 'Placing your order…' : method.startsWith('UPI (') ? 'Continue to UPI payment' : method.startsWith('Razorpay') ? 'Continue to payment' : 'Place order'}</button>
          <Link to="/cart" className="ac-textlink" style={{ display: 'block', textAlign: 'center', marginTop: 12 }}>Back to cart</Link>
        </aside>
      </div>

      {mapOpen && <MumbaiStoreMap isOpen onClose={() => setMapOpen(false)} />}
      {toPay && (toPay.paymentMethod?.startsWith('Razorpay')
        ? <RazorpayTest order={toPay} user={user} onPaid={(o) => finishPaid(o || toPay)} onClose={leaveUnpaid} />
        : <UpiPay order={toPay} onSubmitted={() => finishPaid(toPay)} onClose={leaveUnpaid} />)}
    </div></div>
  );
};

export default Checkout;
