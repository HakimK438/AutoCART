import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck, X, CreditCard } from 'lucide-react';
import api from '../services/api';
import { money } from './parts';
import { themeColor } from './theme';
import './storefront.css';
import './forms.css';

const loadCheckoutJs = () => new Promise((resolve, reject) => {
  if (window.Razorpay) return resolve();
  const s = document.createElement('script');
  s.src = 'https://checkout.razorpay.com/v1/checkout.js';
  s.onload = resolve;
  s.onerror = () => reject(new Error('Could not load Razorpay.'));
  document.body.appendChild(s);
});

/**
 * Pays an order that is waiting for payment, in Razorpay TEST MODE.
 * - With rzp_test_ keys in the backend .env this opens Razorpay's own test checkout.
 * - Without keys it shows a clearly labelled local demo of the same flow (no money, no Razorpay account).
 * Either way the server creates the order and checks the signature; this page never decides that a payment worked.
 */
export default function RazorpayTest({ order, user, onPaid, onClose }) {
  const [stage, setStage] = useState('starting'); // starting | demo | working | error
  const [session, setSession] = useState(null);
  const [error, setError] = useState('');
  const started = useRef(false);

  const verify = async (payload) => {
    setStage('working');
    try {
      const { data } = await api.post('/payments/razorpay/verify', { orderId: order.id, ...payload });
      onPaid(data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'We could not confirm the payment.');
      setStage('error');
    }
  };

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const { data } = await api.post('/payments/razorpay/order', { orderId: order.id });
        setSession(data);
        if (data.demo) { setStage('demo'); return; }
        await loadCheckoutJs();
        const rz = new window.Razorpay({
          key: data.keyId, amount: data.amount, currency: data.currency, name: data.name, description: data.description, order_id: data.razorpayOrderId,
          prefill: { name: user?.name, email: user?.email, contact: user?.phone },
          theme: { color: themeColor('brand') },
          handler: (res) => verify(res),
          modal: { ondismiss: () => onClose?.() },
        });
        rz.on('payment.failed', (r) => { setError(r?.error?.description || 'The payment failed.'); setStage('error'); });
        rz.open();
        setStage('working');
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || 'We could not start the payment.');
        setStage('error');
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const demoPay = async (outcome) => {
    setStage('working'); setError('');
    try {
      const { data } = await api.post('/payments/razorpay/demo-sign', { orderId: order.id, razorpayOrderId: session.razorpayOrderId, outcome });
      await verify(data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'The test payment did not go through.');
      setStage('error');
    }
  };

  if (stage === 'working' && session && !session.demo) return null; // Razorpay's own window is on screen

  return (
    <div className="ac ac-host" style={{ display: 'contents' }}>
      <div className="ac-sc-back" style={{ zIndex: 95 }} aria-hidden="true" />
      <div className="ac-rzp" role="dialog" aria-modal="true" aria-label="Test payment">
        <div className="ac-rzp-head">
          <div><b>AutoCart</b><small>Order {order.id}</small></div>
          <button className="ac-sc-x" style={{ background: 'rgba(255,255,255,.18)', color: '#fff' }} onClick={onClose} aria-label="Close payment"><X size={18} /></button>
        </div>
        <div className="ac-rzp-body">
          <div className="ac-rzp-banner"><ShieldCheck size={16} /> Test mode. No real money moves.{session?.demo ? ' This is a local demo of the Razorpay flow.' : ''}</div>
          <div className="ac-rzp-amount">{money(order.totalAmount)}</div>

          {stage === 'starting' && <p className="ac-muted">Setting up your payment…</p>}
          {stage === 'working' && <p className="ac-muted" role="status">Confirming your payment…</p>}

          {stage === 'demo' && (
            <>
              <div className="ac-field"><label htmlFor="rz-card">Card number</label><input id="rz-card" className="ac-input" defaultValue="4111 1111 1111 1111" readOnly /></div>
              <div className="ac-grid-2" style={{ marginTop: 12 }}>
                <div className="ac-field"><label htmlFor="rz-exp">Expiry</label><input id="rz-exp" className="ac-input" defaultValue="12 / 30" readOnly /></div>
                <div className="ac-field"><label htmlFor="rz-cvv">CVV</label><input id="rz-cvv" className="ac-input" defaultValue="123" readOnly /></div>
              </div>
              <p className="ac-muted" style={{ fontSize: 13 }}>Razorpay's test card is filled in for you. To use Razorpay's real test checkout, add your <code>rzp_test_</code> keys to <code>.env</code>.</p>
              <button className="ac-btn ac-btn-blue" style={{ width: '100%' }} onClick={() => demoPay('success')}><CreditCard size={18} /> Pay {money(order.totalAmount)}</button>
              <button className="ac-btn ac-btn-outline ac-btn-small" style={{ width: '100%', marginTop: 10 }} onClick={() => demoPay('failure')}>Simulate a failed payment</button>
            </>
          )}

          {stage === 'error' && (
            <>
              <p className="ac-warn" role="alert" style={{ fontSize: 15 }}>{error}</p>
              <p className="ac-muted" style={{ fontSize: 14 }}>You have not been charged. Your order is saved, so you can try again from your orders.</p>
              <div className="ac-row">
                {session?.demo && <button className="ac-btn ac-btn-blue ac-btn-small" onClick={() => { setError(''); setStage('demo'); }}>Try again</button>}
                <button className="ac-btn ac-btn-outline ac-btn-small" onClick={onClose}>Pay later</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
