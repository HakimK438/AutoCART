import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapPin, Store, Truck, Banknote, CreditCard, ShieldCheck } from 'lucide-react';
import { useCart } from '../../hooks/useCart';
import { useAuth } from '../../hooks/useAuth';
import { useLocation } from '../../context/LocationContext';
import { MumbaiStoreMap } from '../../components/map/MumbaiStoreMap';
import RazorpayTest from '../../storefront/RazorpayTest';
import { money, sized, firstImage } from '../../storefront/parts';
import orderService from '../../services/orderService';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

const METHODS = {
  delivery: [
    { id: 'Cash on Delivery', icon: Banknote, title: 'Cash on delivery', text: 'Pay in cash when it arrives.' },
    { id: 'Razorpay (Test Mode)', icon: CreditCard, title: 'Pay online (Razorpay test)', text: 'UPI, card or net banking in test mode. No real money.' },
  ],
  pickup: [
    { id: 'Pay at Store', icon: Store, title: 'Pay at the store', text: 'Pay when you collect your order.' },
    { id: 'Razorpay (Test Mode)', icon: CreditCard, title: 'Pay online (Razorpay test)', text: 'UPI, card or net banking in test mode. No real money.' },
  ],
};

export const Checkout = () => {
  const { cartItems, subtotal, discountAmount, deliveryCharge, finalTotal, coupon, clearCart } = useCart();
  const { user } = useAuth();
  const { location, selectedStore } = useLocation();
  const navigate = useNavigate();

  const [mode, setMode] = useState('delivery');
  const [method, setMethod] = useState('Cash on Delivery');
  const [mapOpen, setMapOpen] = useState(false);
  const [addr, setAddr] = useState({ fullName: user?.name || '', phone: user?.phone || '', addressLine: '', city: location?.city || 'Mumbai', state: 'Maharashtra', pinCode: location?.pincode || '' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toPay, setToPay] = useState(null);

  useEffect(() => { document.title = 'Checkout | AutoCart'; }, []);
  useEffect(() => { if (cartItems.length === 0 && !toPay) navigate('/cart', { replace: true }); }, [cartItems.length, toPay, navigate]);

  const set = (k, v) => setAddr((a) => ({ ...a, [k]: v }));
  const storeId = selectedStore?.storeId || selectedStore?.id;
  const storeName = selectedStore?.storeName || selectedStore?.name;

  const switchMode = (m) => { setMode(m); setMethod(METHODS[m][0].id); };

  const validate = () => {
    const e = {};
    if (!addr.fullName.trim()) e.fullName = 'Enter your name.';
    if (addr.phone.replace(/\D/g, '').length < 10) e.phone = 'Enter a 10-digit phone number.';
    if (mode === 'delivery') {
      if (!addr.addressLine.trim()) e.addressLine = 'Enter your delivery address.';
      if (!/^[1-9]\d{5}$/.test(addr.pinCode)) e.pinCode = 'Enter a 6-digit PIN code.';
    }
    if (mode === 'pickup' && !storeId) e.store = 'Choose the store where you will collect your order.';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const place = async () => {
    if (!validate()) return;
    setBusy(true); setError('');
    try {
      const order = await orderService.createOrder({
        items: cartItems.map((i) => ({ id: i.id, quantity: i.quantity })), couponCode: coupon?.code || '', paymentMethod: method,
        shippingAddress: { ...addr, fulfillment: mode }, storeId: storeId || undefined,
      });
      if (order.paymentRequired) { setToPay(order); } else { clearCart(); navigate('/order-success', { state: { order } }); }
    } catch (e) {
      setError(e?.response?.data?.detail || 'We could not place your order. Please try again.');
    }
    setBusy(false);
  };

  const finishPaid = (order) => { clearCart(); navigate('/order-success', { state: { order } }); };
  const leaveUnpaid = () => { const id = toPay.id; clearCart(); setToPay(null); navigate(`/orders/${id}`); };

  return (
    <div className="ac ac-page"><div className="ac-wrap">
      <h1 className="ac-display">Checkout</h1>
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
            {errors.store && <div className="ac-warn" role="alert">{errors.store}</div>}
          </div>

          <div className="ac-box">
            <h2>{mode === 'delivery' ? 'Delivery details' : 'Your details'}</h2>
            <div className="ac-grid-2" style={{ marginTop: 14 }}>
              <div className="ac-field"><label htmlFor="c-name">Full name</label><input id="c-name" className="ac-input" aria-invalid={!!errors.fullName} value={addr.fullName} onChange={(e) => set('fullName', e.target.value)} autoComplete="name" />{errors.fullName && <span className="ac-err" role="alert">{errors.fullName}</span>}</div>
              <div className="ac-field"><label htmlFor="c-phone">Phone</label><input id="c-phone" className="ac-input" inputMode="tel" aria-invalid={!!errors.phone} value={addr.phone} onChange={(e) => set('phone', e.target.value)} autoComplete="tel" />{errors.phone && <span className="ac-err" role="alert">{errors.phone}</span>}</div>
              {mode === 'delivery' && (
                <>
                  <div className="ac-field" style={{ gridColumn: '1 / -1' }}><label htmlFor="c-addr">Address</label><input id="c-addr" className="ac-input" aria-invalid={!!errors.addressLine} value={addr.addressLine} onChange={(e) => set('addressLine', e.target.value)} placeholder="Flat, building, street, area" autoComplete="street-address" />{errors.addressLine && <span className="ac-err" role="alert">{errors.addressLine}</span>}</div>
                  <div className="ac-field"><label htmlFor="c-city">City</label><input id="c-city" className="ac-input" value={addr.city} onChange={(e) => set('city', e.target.value)} /></div>
                  <div className="ac-field"><label htmlFor="c-pin">PIN code</label><input id="c-pin" className="ac-input" inputMode="numeric" maxLength={6} aria-invalid={!!errors.pinCode} value={addr.pinCode} onChange={(e) => set('pinCode', e.target.value.replace(/\D/g, ''))} autoComplete="postal-code" />{errors.pinCode && <span className="ac-err" role="alert">{errors.pinCode}</span>}</div>
                </>
              )}
            </div>
          </div>

          <div className="ac-box">
            <h2>Payment</h2>
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }} role="radiogroup" aria-label="Payment method">
              {METHODS[mode].map((m) => (
                <label key={m.id} className="ac-pay" data-on={method === m.id}>
                  <input type="radio" name="pay" checked={method === m.id} onChange={() => setMethod(m.id)} />
                  <m.icon size={22} color="var(--brand)" />
                  <span><b>{m.title}</b><small>{m.text}</small></span>
                </label>
              ))}
            </div>
            <p className="ac-muted" style={{ fontSize: 13, margin: '12px 0 0' }}><ShieldCheck size={14} /> Online payments run in test mode only. Cash and pay-at-store orders stay unpaid until you pay.</p>
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
          {error && <div className="ac-warn" role="alert" style={{ marginBottom: 10 }}>{error}</div>}
          <button className="ac-btn ac-btn-blue" style={{ width: '100%' }} onClick={place} disabled={busy}>{busy ? 'Placing your order…' : method.startsWith('Razorpay') ? 'Continue to payment' : 'Place order'}</button>
          <Link to="/cart" className="ac-textlink" style={{ display: 'block', textAlign: 'center', marginTop: 12 }}>Back to cart</Link>
        </aside>
      </div>

      {mapOpen && <MumbaiStoreMap isOpen onClose={() => setMapOpen(false)} />}
      {toPay && <RazorpayTest order={toPay} user={user} onPaid={finishPaid} onClose={leaveUnpaid} />}
    </div></div>
  );
};

export default Checkout;
