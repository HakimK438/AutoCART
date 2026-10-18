import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Check, Circle, PartyPopper } from 'lucide-react';
import api from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import OrderRouteMap from '../../storefront/OrderRouteMap';
import StoreMap from '../../storefront/StoreMap';
import UpiPay from '../../storefront/UpiPay';
import RazorpayTest from '../../storefront/RazorpayTest';
import { money, sized, firstImage } from '../../storefront/parts';
import { statusTone } from './Orders';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

export const OrderDetails = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const [order, setOrder] = useState(null);
  const [track, setTrack] = useState(null);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [paying, setPaying] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/orders/${id}`);
      setOrder(data);
      api.get(`/orders/${id}/tracking`).then((r) => setTrack(r.data)).catch(() => {});
    } catch { setError('We could not find that order.'); }
  }, [id]);
  useEffect(() => { document.title = `Order ${id} | AutoCart`; load(); }, [id, load]);
  // Follow the order while it is on its way: the seller's next step shows up here without a refresh.
  const finished = order && ['Delivered', 'Completed', 'Cancelled', 'Returned', 'Return Requested'].includes(order.status);
  useEffect(() => {
    if (!order || finished) return undefined;
    const t = window.setInterval(load, 15000);
    return () => window.clearInterval(t);
  }, [order, finished, load]);

  const act = async (path, label) => {
    setNote('');
    try { const { data } = await api.post(`/orders/${id}/${path}`); setNote(data.message || `${label} done.`); await load(); }
    catch (e) { setNote(e?.response?.data?.detail || `Could not ${label.toLowerCase()}.`); }
  };

  if (error) return <div className="ac ac-page"><div className="ac-wrap"><div className="ac-box" role="alert">{error} <Link to="/orders" className="ac-textlink">Back to orders</Link></div></div></div>;
  if (!order) return <div className="ac ac-page"><div className="ac-wrap"><div className="ac-skel" style={{ height: 300 }} /></div></div>;

  const isUpi = order.paymentMethod.startsWith('UPI (');
  const isOnline = order.paymentMethod.startsWith('Razorpay');
  const needsPayment = (isUpi || isOnline) && ['Awaiting Payment', 'Failed'].includes(order.paymentStatus) && order.status !== 'Cancelled';
  const canCancel = ['Pending', 'Confirmed', 'Processing'].includes(order.status);
  const store = track?.storeLocation;
  const steps = track?.timeline?.length ? track.timeline : order.timeline || [];

  return (
    <div className="ac ac-page"><div className="ac-wrap" style={{ maxWidth: 1000 }}>
      <Link to="/orders" className="ac-textlink">All orders</Link>
      <div className="ac-row-between" style={{ margin: '8px 0 24px' }}>
        <h1 className="ac-display">Order {order.id}</h1>
        <div className="ac-row"><span className="ac-chip-status" data-tone={statusTone(order.status)}>{order.status}</span><span className="ac-chip-status" data-tone={order.paymentStatus === 'Paid' ? 'ok' : statusTone(order.paymentStatus)}>{order.paymentStatus}</span></div>
      </div>
      {note && <div className="ac-box" role="status" style={{ marginBottom: 16, borderColor: 'var(--brand)' }}>{note}</div>}
      {order.status === 'Delivered' && (
        <div className="ac-box" role="status" style={{ marginBottom: 16, borderColor: 'var(--ok)', background: '#effaf3', display: 'flex', gap: 14, alignItems: 'center' }}>
          <PartyPopper size={30} color="var(--ok)" aria-hidden="true" />
          <div><b style={{ fontSize: 18 }}>Your product has reached you</b><p className="ac-muted" style={{ margin: '2px 0 0' }}>Order {order.id} is delivered. We hope you love it. If something is not right, you can return it within 7 days using the button on the right.</p></div>
        </div>
      )}
      {['Out for Delivery', 'Ready for Pickup'].includes(order.status) && (
        <div className="ac-box" role="status" style={{ marginBottom: 16, borderColor: 'var(--brand)' }}><b>{order.status === 'Out for Delivery' ? 'Your order is on its way.' : 'Your order is ready to collect from the store.'}</b> This page updates by itself.</div>
      )}

      <div className="ac-twocol">
        <div>
          <div className="ac-box">
            <h2>Where it is</h2>
            <ol className="ac-timeline">
              {steps.map((s, i) => (
                <li key={i} data-done={!!s.completed}><span>{s.completed ? <Check size={14} /> : <Circle size={10} />}</span><div><b>{s.status}</b>{s.time && <small>{s.time}</small>}</div></li>
              ))}
            </ol>
            {track && <p className="ac-muted" style={{ fontSize: 14, margin: '8px 0 0' }}>Tracking {track.trackingNumber} · about {track.estimatedDeliveryMinutes} minutes once it leaves the store.</p>}
          </div>

          {track?.fulfilledBy?.storeName && (
            <div className="ac-box">
              <h2>Your order is with</h2>
              <p style={{ margin: '8px 0 0', fontWeight: 700, fontSize: 18 }}>{track.fulfilledBy.storeName}</p>
              {track.fulfilledBy.predictedNearest && <p className="ac-muted" style={{ margin: '2px 0 0', fontSize: 14 }}>Nearest store to you, picked automatically.</p>}
              <dl className="ac-sum" style={{ marginTop: 10 }}>
                {track.fulfilledBy.sellerName && <div><dt>Seller</dt><dd>{track.fulfilledBy.sellerName}</dd></div>}
                {track.fulfilledBy.address && <div><dt>Store address</dt><dd>{track.fulfilledBy.address}</dd></div>}
                {track.fulfilledBy.phone && <div><dt>Phone</dt><dd><a href={`tel:${track.fulfilledBy.phone}`}>{track.fulfilledBy.phone}</a></dd></div>}
                {track.fulfilledBy.distanceKm != null && <div><dt>Distance to you</dt><dd>{track.fulfilledBy.distanceKm} km</dd></div>}
                {track.trackingNumber && <div><dt>Tracking ID</dt><dd>{track.trackingNumber}</dd></div>}
              </dl>
            </div>
          )}

          {(track?.pickup && track?.customerLocation) && (
            <div className="ac-box">
              <h2>Route from the store to you</h2>
              <p className="ac-muted" style={{ margin: '4px 0 12px' }}>{track.pickup.name} packs your order and brings it to you.</p>
              <OrderRouteMap pickup={track.pickup} drop={track.customerLocation} height={300} />
            </div>
          )}

          {!(track?.pickup && track?.customerLocation) && store?.latitude != null && (
            <div className="ac-box">
              <h2>Fulfilled from</h2>
              <p className="ac-muted" style={{ margin: '4px 0 12px' }}>{store.name}, {store.address}{store.phone ? ` · ${store.phone}` : ''}</p>
              {track?.customerLocation
                ? <OrderRouteMap pickup={{ name: store.name, address: store.address, lat: store.latitude, lng: store.longitude }} drop={track.customerLocation} height={300} />
                : <StoreMap stores={[{ storeId: 'x', storeName: store.name, address: store.address, latitude: store.latitude, longitude: store.longitude }]} height={280} selectedId="x" />}
            </div>
          )}

          <div className="ac-box">
            <h2>Items</h2>
            {(order.items || []).map((i) => (
              <div className="ac-mini-line" key={i.id} style={{ padding: '12px 0' }}><img src={sized(firstImage(i), 100)} alt="" /><span><Link to={`/products/${i.id}`}>{i.name}</Link><small> × {i.quantity}</small></span><b>{money(i.price * i.quantity)}</b></div>
            ))}
          </div>
        </div>

        <aside>
          {/* Not .ac-summary: that class is sticky (right for checkout) and made this card slide over the boxes below it. */}
          <div className="ac-box">
            <h2>Payment</h2>
            <dl className="ac-sum">
              <div><dt>Subtotal</dt><dd>{money(order.subtotal)}</dd></div>
              {order.discountAmount > 0 && <div><dt>Discount</dt><dd>-{money(order.discountAmount)}</dd></div>}
              <div><dt>Delivery</dt><dd>{order.shippingFee ? money(order.shippingFee) : 'Free'}</dd></div>
              <div className="ac-sum-total"><dt>Total</dt><dd>{money(order.totalAmount)}</dd></div>
            </dl>
            <p className="ac-muted" style={{ fontSize: 14 }}>{order.paymentMethod}</p>
            {needsPayment && <button className="ac-btn ac-btn-blue" style={{ width: '100%' }} onClick={() => setPaying(true)}>{order.paymentStatus === 'Failed' ? `Pay again${isUpi ? ' with UPI' : ''}` : `Pay now${isUpi ? ' with UPI' : ''}`}</button>}
            {isUpi && order.paymentStatus === 'Verifying' && <p className="ac-muted" role="status">Waiting for the seller to confirm your UPI payment.</p>}
            {isUpi && order.paymentStatus === 'Failed' && <p className="ac-warn" role="alert">The seller could not find this payment. Check the UPI reference and try again.</p>}
            {canCancel && <button className="ac-btn ac-btn-outline ac-btn-small" style={{ width: '100%', marginTop: 10 }} onClick={() => act('cancel', 'Cancel')}>Cancel order</button>}
            {['Delivered', 'Completed'].includes(order.status) && <button className="ac-btn ac-btn-outline ac-btn-small" style={{ width: '100%', marginTop: 10 }} onClick={() => act('return', 'Return')}>Return an item</button>}
          </div>
          <div className="ac-box">
            <h2>Delivery</h2>
            <p className="ac-muted" style={{ margin: '6px 0 0' }}>
              <b style={{ color: 'var(--ink)' }}>{order.customerName}</b>{order.customerPhone ? <> · <a href={`tel:${order.customerPhone}`}>{order.customerPhone}</a></> : null}<br />
              {order.shippingAddress?.addressLine
                ? [order.shippingAddress.addressLine, order.shippingAddress.landmark && `Near ${order.shippingAddress.landmark}`, order.shippingAddress.city, order.shippingAddress.state, order.shippingAddress.pinCode].filter(Boolean).join(', ')
                : order.shippingAddress?.storeName ? `Pickup at ${order.shippingAddress.storeName}` : '-'}
            </p>
          </div>
          <div className="ac-box">
            <h2>Need help?</h2>
            <p className="ac-muted" style={{ margin: '6px 0 12px' }}>Ask us about this order and a person will reply.</p>
            <Link to="/support" className="ac-btn ac-btn-outline ac-btn-small">Open a support ticket</Link>
          </div>
        </aside>
      </div>
      {paying && (isOnline
        ? <RazorpayTest order={order} user={user} onPaid={() => { setPaying(false); setNote('Payment received. Thank you!'); load(); }} onClose={() => setPaying(false)} />
        : <UpiPay order={order} onSubmitted={() => { setPaying(false); setNote('Thanks. The seller will confirm your payment shortly.'); load(); }} onClose={() => setPaying(false)} />)}
    </div></div>
  );
};

export default OrderDetails;
