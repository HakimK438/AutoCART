import React, { useEffect, useState } from 'react';
import { PackageCheck, Route, Truck, CheckCircle2, Zap } from 'lucide-react';
import api from '../../services/api';
import OrderRouteMap from '../../storefront/OrderRouteMap';
import { money } from '../../storefront/parts';

const WHEN = (iso) => new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

/** Autopilot: the seller's switch for "pack new orders for me", one-click "pack all", and a plain list of what it already did. */
function Autopilot({ orders, onChange }) {
  const [auto, setAuto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const load = () => api.get('/seller/automation').then((r) => setAuto(r.data)).catch(() => setAuto(null));
  useEffect(() => { load(); }, [orders]);  // refresh after any order change
  if (!auto) return null;

  const toggle = async () => {
    setBusy(true); setNote('');
    try {
      const { data } = await api.put('/seller/automation', { autoPackOrders: !auto.autoPackOrders });
      setAuto(data);
      setNote(data.autoPackOrders ? (data.packedNow ? `Auto-pack is on. ${data.packedNow} waiting order${data.packedNow === 1 ? ' was' : 's were'} packed.` : 'Auto-pack is on. New orders will be packed for you.') : 'Auto-pack is off. You pack orders yourself.');
      if (data.packedNow) await onChange();
    } catch { setNote('Could not change auto-pack. Please try again.'); }
    setBusy(false);
  };
  const packAll = async () => {
    setBusy(true); setNote('');
    try { const { data } = await api.post('/seller/orders/pack-all'); setNote(`${data.packed} order${data.packed === 1 ? '' : 's'} confirmed and packed.`); await onChange(); await load(); }
    catch { setNote('Could not pack the orders. Please try again.'); }
    setBusy(false);
  };

  return (
    <div className="ac-storebox" style={{ margin: '14px 0 4px', display: 'block' }} aria-label="Autopilot">
      <div className="ac-row" style={{ justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0, flex: '1 1 280px' }}>
          <b><Zap size={16} aria-hidden="true" style={{ verticalAlign: '-2px' }} /> Auto-pack my orders {auto.autoPackOrders ? <span className="ac-chip-status" data-tone="ok">On</span> : <span className="ac-chip-status" data-tone="info">Off</span>}</b>
          <p className="ac-muted" style={{ margin: '4px 0 0', fontSize: 14 }}>
            {auto.autoPackOrders
              ? 'Every new order is accepted and marked packed for you, and the customer is told. You only send it out and mark it delivered.'
              : 'Turn this on and you no longer press "Confirm & pack" on every order. Online orders wait until the money arrives.'}
            {auto.autoRestockProducts > 0 && <> Auto-restock is on for {auto.autoRestockProducts} product{auto.autoRestockProducts === 1 ? '' : 's'}.</>}
          </p>
        </div>
        <div className="ac-row" style={{ gap: 8 }}>
          {auto.waitingToPack > 0 && <button className="ac-btn ac-btn-blue" disabled={busy} onClick={packAll}><PackageCheck size={17} /> Pack all {auto.waitingToPack} ready</button>}
          <button className="ac-btn ac-btn-outline" disabled={busy} role="switch" aria-checked={auto.autoPackOrders} onClick={toggle}>{auto.autoPackOrders ? 'Turn off' : 'Turn on'}</button>
        </div>
      </div>
      {note && <p role="status" style={{ margin: '8px 0 0', fontSize: 14 }}>{note}</p>}
      {auto.events.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ cursor: 'pointer', fontSize: 14 }}>What was done for you automatically ({auto.events.length})</summary>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 14 }}>
            {auto.events.map((e) => <li key={e.id}>{e.summary} <small className="ac-muted">{WHEN(e.createdAt)}</small></li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

/** Orders that contain this seller's products. One click confirms packing; then the route to the customer opens on a map. */
export default function SellerOrders({ orders, onChange }) {
  const [busy, setBusy] = useState('');
  const [open, setOpen] = useState('');
  const [route, setRoute] = useState(null);
  const [err, setErr] = useState('');

  const pack = async (id) => {
    setBusy(id); setErr('');
    try { await api.post(`/seller/orders/${id}/pack`); await onChange(); await show(id); }
    catch (e) { setErr(e?.response?.data?.detail || 'Could not update that order.'); }
    setBusy('');
  };
  // The next steps after packing. The customer is notified each time.
  const advance = async (id, step) => {
    setBusy(id); setErr('');
    try { await api.post(`/seller/orders/${id}/${step}`); await onChange(); }
    catch (e) { setErr(e?.response?.data?.detail || 'Could not update that order.'); }
    setBusy('');
  };
  const payment = async (id, action) => {
    setBusy(id); setErr('');
    try { await api.post(`/orders/${id}/payment`, { action }); await onChange(); }
    catch (e) { setErr(e?.response?.data?.detail || 'Could not update that payment.'); }
    setBusy('');
  };
  const show = async (id) => {
    if (open === id) { setOpen(''); return; }
    setOpen(id); setRoute(null);
    try { setRoute((await api.get(`/seller/orders/${id}/route`)).data); }
    catch (e) { setRoute({ note: e?.response?.data?.detail || 'Could not load the route.' }); }
  };

  const todo = orders.filter((o) => o.canPack || o.canDispatch || o.canDeliver).length;
  return (
    <section id="orders" className="ac-box" aria-labelledby="ord-h" style={{ marginTop: 24 }}>
      <h2 id="ord-h">Your orders {todo > 0 && <span className="ac-chip-status" data-tone="warn">{todo} need your action</span>}</h2>
      <p className="ac-muted" style={{ margin: '4px 0 0', fontSize: 14 }}>Each order has three steps: <b>Confirm and pack</b>, then <b>Out for delivery</b>, then <b>Mark delivered</b>. The customer gets a notification at every step, and the sale is complete once it is delivered.</p>
      <Autopilot orders={orders} onChange={onChange} />
      {err && <p role="alert" style={{ color: 'var(--coral)' }}>{err}</p>}
      {orders.length === 0 ? <p className="ac-muted">No orders yet. When someone buys from you, it shows up here.</p> : (
        <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
          {orders.map((o) => (
            <article key={o.id} className="ac-ordercard" data-open={open === o.id}>
              <div className="ac-ordercard-top">
                <div>
                  <b>{o.id}</b> <span className="ac-chip-status" data-tone={o.status === 'Delivered' ? 'ok' : (o.canPack || o.canDispatch || o.canDeliver) ? 'warn' : 'info'}>{o.status}</span>
                  <p style={{ margin: '4px 0 0' }}>{o.items.map((i) => `${i.name} × ${i.quantity}`).join(', ')}</p>
                  <div className="ac-storebox" style={{ margin: '8px 0', padding: '10px 12px' }}>
                    <div style={{ minWidth: 0 }}>
                      <b>{o.customerName || o.customerFirstName}</b>{o.customerPhone && <> · <a href={`tel:${o.customerPhone}`}>{o.customerPhone}</a></>}
                      {o.deliveryAddress && <div className="ac-muted" style={{ fontSize: 14 }}>{o.pickup ? '' : 'Deliver to: '}{o.deliveryAddress}</div>}
                    </div>
                  </div>
                  <small className="ac-muted">{o.date} · your share {money(o.yourShare)}{o.pickup ? ' · customer pickup' : ''} · {o.paymentMethod}</small>
                  {o.paymentMethod === 'UPI (Scan & Pay)' && (
                    <p style={{ margin: '6px 0 0' }}>
                      {o.paymentStatus === 'Awaiting Payment' && <span className="ac-chip-status" data-tone="warn">Waiting for the customer to pay</span>}
                      {o.paymentStatus === 'Verifying' && <span className="ac-chip-status" data-tone="warn">Check your UPI account: reference <b>{o.utr}</b></span>}
                      {o.paymentStatus === 'Paid' && <span className="ac-chip-status" data-tone="ok">Payment received</span>}
                      {o.paymentStatus === 'Failed' && <span className="ac-chip-status" data-tone="bad">Marked not received</span>}
                    </p>
                  )}
                </div>
                <div className="ac-row" style={{ gap: 8 }}>
                  {o.paymentStatus === 'Verifying' && o.paymentMethod === 'UPI (Scan & Pay)' && (
                    <>
                      <button className="ac-btn ac-btn-blue" disabled={busy === o.id} onClick={() => payment(o.id, 'received')}>Payment received</button>
                      <button className="ac-btn ac-btn-outline" disabled={busy === o.id} onClick={() => payment(o.id, 'not_received')}>Not received</button>
                    </>
                  )}
                  {o.canDispatch && <button className="ac-btn ac-btn-blue" disabled={busy === o.id} onClick={() => advance(o.id, 'dispatch')}><Truck size={17} /> {busy === o.id ? 'Saving…' : o.pickup ? 'Ready for pickup' : 'Out for delivery'}</button>}
                  {o.canDeliver && <button className="ac-btn ac-btn-blue" disabled={busy === o.id} onClick={() => advance(o.id, 'deliver')}><CheckCircle2 size={17} /> {busy === o.id ? 'Saving…' : o.pickup ? 'Mark collected' : 'Mark delivered'}</button>}
                  {o.canPack && <button className="ac-btn ac-btn-blue" disabled={busy === o.id} onClick={() => pack(o.id)}><PackageCheck size={17} /> {busy === o.id ? 'Saving…' : 'Confirm & pack'}</button>}
                  <button className="ac-btn ac-btn-outline" onClick={() => show(o.id)} aria-expanded={open === o.id}><Route size={17} /> {open === o.id ? 'Hide route' : 'View route'}</button>
                </div>
              </div>
              {open === o.id && (
                <div style={{ marginTop: 14 }}>
                  {!route && <div className="ac-skel" style={{ height: 200 }} />}
                  {route?.pickup && route?.drop && <OrderRouteMap pickup={route.pickup} drop={route.drop} />}
                  {route && !(route.pickup && route.drop) && <p className="ac-muted" role="status">{route.note || 'No map location is available for this order.'}</p>}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
