import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { X, Send, Search, PackageSearch, RotateCcw, Headset, Plus, Check, RefreshCw, ArrowDown, Phone, MapPin, Ticket, Sparkles, ShieldCheck } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useCart } from '../hooks/useCart';
import { useLocation as useCustomerLocation } from '../context/LocationContext';
import { orderService } from '../services/orderService';
import { money, sized, firstImage } from './parts';
import { LogoMark } from './Brand';
import './storefront.css';
import './saathi.css';

export const SUPPORT_PHONE = import.meta.env.VITE_SUPPORT_PHONE || '+91 22 4890 2278';
export const SUPPORT_HOURS = '9 AM to 9 PM, every day';
const SESSION_KEY = 'autocart_support_session';
const PENDING_KEY = 'autocart_pending_buy';
const STARTERS = [
  { icon: Search, title: 'Find something', text: 'Find a gift under ₹1,500' },
  { icon: PackageSearch, title: 'Track an order', text: 'Track my order' },
  { icon: RotateCcw, title: 'Return an item', text: 'Return an item' },
  { icon: Headset, title: 'Talk to a person', text: 'Talk to a person' },
];
// Short replies that mean "go ahead" — used to carry on a purchase without making the shopper repeat themselves.
const ACK_RE = /^\s*(done|ok(ay)?|k|yes|yeah|yep|sure|go ahead|proceed|confirm|place( the)? order|order it|buy it|signed in|logged in|i('m| am| have)? (signed|logged) in|haan|ha|theek hai)\W*$/i;
const CANCEL_RE = /^\s*(cancel|stop|no|nahi|don'?t)\W*$/i;

const readSession = (email) => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || '{}'); return s.email === (email || '') ? s.id || '' : ''; } catch { return ''; } };
const saveSession = (email, id) => { try { localStorage.setItem(SESSION_KEY, JSON.stringify({ email: email || '', id })); } catch { /* storage may be blocked */ } };
const readPending = () => { try { return JSON.parse(localStorage.getItem(PENDING_KEY) || 'null'); } catch { return null; } };
const savePending = (card) => { try { if (card) localStorage.setItem(PENDING_KEY, JSON.stringify(card)); else localStorage.removeItem(PENDING_KEY); } catch { /* ignore */ } };
const clock = () => new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
const asCartItem = (c) => ({ id: c.id, name: c.name, price: c.price, originalPrice: c.originalPrice, rating: c.rating, stock: c.stock, images: c.image ? [c.image] : [] });

/** The assistant writes **bold** and line breaks; show them properly instead of as raw symbols. */
const Rich = ({ text }) => text.split('\n').map((line, i, all) => (
  <React.Fragment key={i}>
    {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => (part.startsWith('**') && part.endsWith('**') ? <strong key={j}>{part.slice(2, -2)}</strong> : part.replace(/\*([^*]+)\*/g, '$1')))}
    {i < all.length - 1 && <br />}
  </React.Fragment>
));

const telHref = (n) => `tel:${String(n).replace(/[^\d+]/g, '').replace(/^(\d{10})$/, '+91$1')}`;

const Thumb = ({ src, name, size = 78 }) => {
  const [bad, setBad] = useState(false);
  return src && !bad
    ? <img src={sized(src, size * 2)} alt={name || ''} width={size} height={size} loading="lazy" onError={() => setBad(true)} />
    : <div className="ac-pcard-ph" aria-hidden="true"><span>{(name || '?').trim().charAt(0).toUpperCase()}</span></div>;
};

const ProductCard = ({ c, n, onClose, onBuy }) => {
  const { addToCart } = useCart();
  const [added, setAdded] = useState(false);
  const off = c.originalPrice > c.price ? Math.round((1 - c.price / c.originalPrice) * 100) : 0;
  const img = firstImage({ id: c.id, images: c.images?.length ? c.images : [c.image] });
  return (
    <div className="ac-mini-card ac-pcard">
      <Link to={`/products/${c.id}`} onClick={onClose} className="ac-pcard-img" aria-label={`View ${c.name}`}><Thumb src={img || c.image} name={c.name} />{c.badge && <em>{c.badge}</em>}</Link>
      <div style={{ minWidth: 0 }}>
        <Link to={`/products/${c.id}`} onClick={onClose}><b>{n ? <span className="ac-num">{n}</span> : null}{c.name}</b></Link>
        <span className="ac-pcard-price"><strong>{money(c.price)}</strong>{off > 0 && <> <s>{money(c.originalPrice)}</s> <i>{off}% off</i></>}</span>
        <span className="ac-pcard-meta">{c.rating ? `${Number(c.rating).toFixed(1)} ★${c.reviewCount ? ` (${Number(c.reviewCount).toLocaleString('en-IN')})` : ''}` : 'New'}{c.stock > 0 && c.stock <= 10 ? ` · only ${c.stock} left` : ''}{c.stock <= 0 ? ' · out of stock' : ''}</span>
        {c.near && <span className="ac-pcard-near"><MapPin size={13} /> {c.near.store} · {c.near.km} km · ~{c.near.minutes} min</span>}
        <div className="ac-row" style={{ gap: 8, marginTop: 8 }}>
          <button className="ac-btn ac-btn-blue ac-btn-small ac-pcard-btn" disabled={c.stock <= 0} onClick={() => onBuy?.(c)}>Buy now</button>
          <button className="ac-btn ac-btn-outline ac-btn-small ac-pcard-btn" disabled={c.stock <= 0}
            onClick={() => { addToCart(asCartItem(c), 1); setAdded(true); window.setTimeout(() => setAdded(false), 1600); }}>
            {added ? <><Check size={14} /> Added</> : <><Plus size={14} /> Cart</>}
          </button>
          <Link to={`/products/${c.id}`} onClick={onClose} className="ac-pcard-more">Details</Link>
        </div>
      </div>
    </div>
  );
};

/** One order in the chat: its photo, items, status, the store packing it and the next steps, without opening the order page. */
const OrderCard = ({ c, onClose, onAsk }) => {
  const done = ['Delivered', 'Cancelled', 'Returned'].includes(c.status);
  return (
    <div className="ac-mini-card ac-ordercard2" data-placed={!!c.placed}>
      <Link to={`/orders/${c.id}`} onClick={onClose} className="ac-pcard-img" aria-label={`Open order ${c.id}`}><Thumb src={c.image} name={c.item} size={64} />{c.itemCount > 1 && <em>+{c.itemCount - 1} more</em>}</Link>
      <div style={{ minWidth: 0 }}>
        <small className="ac-muted">{c.placed ? '✓ Order placed' : 'Order'} · {c.id}</small>
        <b>{c.item || 'Your order'}{c.qty > 1 && c.itemCount === 1 ? ` × ${c.qty}` : ''}</b>
        <span className="ac-ord-line"><i className="ac-ord-status" data-tone={done ? (c.status === 'Delivered' ? 'ok' : 'off') : 'live'}>{c.status}</i> {money(c.total)} · {c.payment}</span>
        {c.store?.name && <span className="ac-pcard-near"><MapPin size={13} /> Packed by {c.store.name}{c.etaMinutes ? ` · ~${c.etaMinutes} min` : ''}</span>}
        {c.placed && (
          <ol className="ac-steps" aria-label="Order progress"><li data-done="true">Placed</li><li>Store packs it</li><li>On the way</li><li>Delivered</li></ol>
        )}
        <div className="ac-row ac-ord-actions">
          <Link to={`/orders/${c.id}`} onClick={onClose} className="ac-btn ac-btn-blue ac-btn-small ac-pcard-btn"><MapPin size={14} /> Track on map</Link>
          {c.canCancel && <button type="button" className="ac-btn ac-btn-outline ac-btn-small ac-pcard-btn" onClick={() => onAsk(`Cancel ${c.id}`)}>Cancel</button>}
          {c.canReturn && <button type="button" className="ac-btn ac-btn-outline ac-btn-small ac-pcard-btn" onClick={() => onAsk(`Return ${c.id}`)}>Return</button>}
          {c.store?.phone && <a href={telHref(c.store.phone)} className="ac-btn ac-btn-soft ac-btn-small ac-pcard-btn" aria-label={`Call ${c.store.name}`}><Phone size={14} /> Call store</a>}
        </div>
      </div>
    </div>
  );
};

/** Phone numbers for details the assistant would rather not guess: support, the store near you, the seller. */
const ContactCard = ({ c }) => (
  <div className="ac-contactcard" role="group" aria-label={c.title}>
    <b><Phone size={16} /> {c.title}</b>
    {c.lines.map((l) => (
      <a key={l.label + l.phone} href={telHref(l.phone)} className="ac-callcard">
        <span className="ac-callicon"><Phone size={18} /></span>
        <span><b>{l.label}</b><small>{l.phone}{l.note ? ` · ${l.note}` : ''}</small></span>
      </a>
    ))}
  </div>
);

export default function SupportChat({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cartItems } = useCart();
  const { location } = useCustomerLocation();
  const { addToCart } = useCart();
  const [messages, setMessages] = useState([]);
  const [actions, setActions] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [rating, setRating] = useState(0);
  const [handoff, setHandoff] = useState(null);
  const [error, setError] = useState('');
  const [away, setAway] = useState(false);
  const [memory, setMemory] = useState(null);
  const [buying, setBuying] = useState(null); // { card, qty, address, source, saving, error }
  const [ordered, setOrdered] = useState([]); // product ids ordered in this chat, so "ok" never orders twice
  const showMemory = () => api.get('/support/memory').then((r) => setMemory(r.data)).catch(() => setMemory({ error: true }));
  const forget = () => api.delete('/support/memory').then(() => setMemory({ name: user?.name?.split(' ')[0], interests: [], recentSearches: [], budgetMax: null, chats: 0 })).catch(() => {});
  const say = (text, extra = {}) => setMessages((m) => [...m, { from: 'bot', text, at: clock(), ...extra }]);
  const echo = (text) => setMessages((m) => [...m, { from: 'user', text, at: clock() }]);
  const first = user?.name?.split(' ')[0];

  const body = useRef(null);
  const end = useRef(null);
  const field = useRef(null);

  /** Where to deliver: the last order's address, else the location the shopper set on the site. */
  const findAddress = async () => {
    try {
      const { data } = await api.get('/support/last-address');
      if (data.address) return { address: data.address, source: 'your last order' };
    } catch { /* fall through to the saved location */ }
    if (location?.pincode && (location.line || location.area)) {
      return {
        address: { fullName: user?.name || '', phone: user?.phone || '', addressLine: location.line || location.area, city: location.city || 'Mumbai', state: location.state || 'Maharashtra',
          pinCode: location.pincode, latitude: location.lat, longitude: location.lng, fulfillment: 'delivery' },
        source: location.source === 'browser' ? 'your current location' : 'the location you chose',
      };
    }
    return null;
  };

  /** Start ordering from the chat. Everything is filled in; the shopper only presses Confirm (or types "yes"). */
  const startBuy = async (card) => {
    if (!user) {
      savePending(card);
      say(`Sign in with your customer account and I will carry on with **${card.name}** right where we left off. No need to type it again.`);
      setActions(['Sign in']); return;
    }
    if (!['CUSTOMER', 'SELLER'].includes(user.role)) { say('Administrator accounts cannot place orders. Sign in with a customer or seller account to buy.'); return; }
    savePending(null);
    if (card.stock <= 0) { say(`${card.name} is out of stock right now. Tell me and I will find something similar.`); return; }
    const found = await findAddress();
    if (!found) {
      addToCart(asCartItem(card), 1);
      say(`I added **${card.name}** to your cart. I need a delivery address once, so I am opening checkout.`);
      window.setTimeout(() => { onClose(); navigate('/checkout'); }, 900); return;
    }
    setBuying({ card, qty: 1, address: found.address, source: found.source, saving: false, error: '' });
    setActions([]);
  };

  const confirmBuy = async () => {
    const b = buying;
    if (!b || b.saving) return;
    setBuying({ ...b, saving: true, error: '' });
    try {
      const order = await orderService.createOrder({ items: [{ id: b.card.id, quantity: b.qty }], paymentMethod: 'Cash on Delivery', shippingAddress: b.address });
      say(`Done${first ? `, ${first}` : ''}! Order **${order.id}** is placed: ${b.card.name}${b.qty > 1 ? ` × ${b.qty}` : ''}, total ${money(order.totalAmount)}, pay on delivery. The nearest store has been told to pack it. Tap the card to watch it on the map.`,
        { cards: [{ type: 'order', placed: true, id: order.id, status: order.status, total: order.totalAmount, payment: order.paymentStatus, item: b.card.name, qty: b.qty }] });
      setOrdered((o) => [...o, b.card.id]);
      setBuying(null); setActions(['Track my order', 'Find something else']);
    } catch (e) {
      setBuying({ ...b, saving: false, error: e?.response?.data?.detail || 'We could not place the order. Please try again.' });
    }
  };

  useEffect(() => { if (isOpen) { setSessionId(readSession(user?.email)); window.setTimeout(() => field.current?.focus(), 350); } }, [isOpen, user?.email]);
  // Came back after signing in with a purchase half done: pick it up automatically.
  useEffect(() => {
    const pending = readPending();
    if (isOpen && user && pending && !buying) {
      say(`Welcome back${first ? `, ${first}` : ''}. Carrying on with **${pending.name}**.`);
      startBuy(pending);
    }
  }, [isOpen, user?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, busy, handoff, buying]);
  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const lettered = messages.length === 0 && actions.length === 0 ? STARTERS.map((s) => s.text) : actions.filter((a) => !/^\d+$/.test(a)).slice(0, 4);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput(''); setError('');

    if (message === '0') { newChat(); return; }
    // While the confirm box is open, "yes" places the order and "no" cancels it.
    if (buying && ACK_RE.test(message)) { echo(message); confirmBuy(); return; }
    if (buying && CANCEL_RE.test(message)) { echo(message); setBuying(null); say('No problem, I have cancelled that. What else can I find for you?'); return; }
    // "done" after being asked to sign in: carry on with the product we were buying.
    const pending = readPending();
    if (pending && ACK_RE.test(message)) {
      echo(message);
      if (user) startBuy(pending); else { say('I still cannot see you signed in. Tap **Sign in**, then come back here.'); setActions(['Sign in']); }
      return;
    }

    setBusy(true); setActions([]);
    echo(message);
    try {
      const where = location?.lat ? { lat: location.lat, lng: location.lng, pincode: location.pincode, area: location.area || location.city } : undefined;
      const { data } = await api.post('/support/chat', { message, sessionId, location: where, cartItems: (cartItems || []).map((i) => ({ id: i.id, price: i.price, quantity: i.quantity })) });
      setSessionId(data.sessionId); saveSession(user?.email, data.sessionId);
      const wanted = data.buyProductId && (data.cards || []).find((c) => c.id === data.buyProductId);
      if (data.buyProductId && ordered.includes(data.buyProductId) && ACK_RE.test(message)) {
        say('That order is already placed. Anything else I can find for you?'); setActions(['Track my order', 'Find something else']);
      } else {
        setMessages((m) => [...m, { from: 'bot', text: data.reply, cards: data.cards || [], at: clock() }]);
        setActions(data.suggestedActions || []);
        if (wanted) startBuy(wanted);
        else if (data.buyProductId) { // "done" pointed at a product from earlier: fetch it and carry on
          api.get(`/products/${data.buyProductId}`).then((r) => startBuy({ ...r.data, image: (r.data.images || [])[0] })).catch(() => {});
        }
      }
    } catch {
      setError('We could not reach support just now. Check your connection and try again.');
    } finally { setBusy(false); }
  };

  const newChat = () => { setMessages([]); setActions([]); setSessionId(''); saveSession(user?.email, ''); setRating(0); setHandoff(null); setBuying(null); setError(''); field.current?.focus(); };

  function onAction(label) {
    if (label === 'Talk to a person') return openHandoff();
    if (label === 'Call me back') return openHandoff();
    if (label === 'See my tickets') { onClose(); return navigate('/support'); }
    if (label === 'Sign in') { onClose(); return navigate('/login'); }
    if (label === 'Find something else') { say('Sure. Tell me what you are looking for, like "running shoes under 3000".'); setActions(['Show me popular products']); return undefined; }
    return send(label);
  }

  function openHandoff() {
    const lastUser = [...messages].reverse().find((m) => m.from === 'user' && !/^(talk to a person|call me back|[a-h0-9])$/i.test(m.text));
    setHandoff({ subject: (lastUser?.text || 'Help with my order').slice(0, 80), message: lastUser?.text || '', orderId: '', phone: user?.phone || '', write: false, saving: false });
  }

  const createTicket = async (payload, done) => {
    setHandoff((h) => ({ ...h, saving: true })); setError('');
    try {
      const { data } = await api.post('/support/tickets', { ...payload, sessionId, consent: true });
      setHandoff(null); say(done(data.id)); setActions(['See my tickets']);
    } catch (err) {
      setError(err?.response?.data?.detail || 'We could not create the ticket. Please try again.');
      setHandoff((h) => ({ ...h, saving: false }));
    }
  };

  const requestCallback = () => {
    if (!/\d{10}/.test((handoff.phone || '').replace(/\D/g, ''))) { setError('Enter a 10-digit phone number so we can call you.'); return; }
    createTicket({ subject: `Call back: ${handoff.subject}`.slice(0, 120), message: `Please call me on ${handoff.phone}. ${handoff.message || ''}`.trim(), orderId: handoff.orderId, preferredContact: `Phone call ${handoff.phone}`, priority: 'HIGH' },
      (id) => `Done. A person will call you on **${handoff.phone}** soon (${SUPPORT_HOURS}). Your ticket is **${id}**, and they can see this chat.`);
  };

  const submitWritten = (e) => {
    e.preventDefault();
    createTicket({ subject: handoff.subject, message: handoff.message, orderId: handoff.orderId, preferredContact: 'Reply here' },
      (id) => `Done. Your ticket is **${id}**. A person will reply in your tickets list. They can see this chat, so you do not need to repeat yourself.`);
  };

  const rate = async (n) => { setRating(n); try { await api.post(`/support/chat/${sessionId}/rating`, { rating: n }); } catch { /* the thank-you still shows */ } };
  const onScroll = (e) => setAway(e.target.scrollHeight - e.target.scrollTop - e.target.clientHeight > 160);

  if (!isOpen) return null;
  const replies = messages.filter((m) => m.from === 'bot').length;
  const tel = `tel:${SUPPORT_PHONE.replace(/[^\d+]/g, '')}`;

  return (
    <>
      <div className="ac-sc-back" onClick={onClose} aria-hidden="true" />
      <aside className="ac-sc" role="dialog" aria-modal="true" aria-label="Saathi, the AutoCart assistant">
        <header className="ac-sc-head">
          <div className="ac-sc-avatar"><LogoMark size={34} /><i className="ac-online" aria-hidden="true" /></div>
          <div className="ac-sc-title"><b>Saathi</b><small>AutoCart shopping assistant<span aria-hidden="true"> · </span><em>Online</em></small></div>
          <div className="ac-sc-tools">
            <a className="ac-sc-x" href={tel} aria-label={`Call support on ${SUPPORT_PHONE}`} title={`Call ${SUPPORT_PHONE}`}><Phone size={17} /></a>
            {messages.length > 0 && <button className="ac-sc-x" onClick={newChat} aria-label="Start a new chat" title="New chat"><RefreshCw size={17} /></button>}
            <button className="ac-sc-x" onClick={onClose} aria-label="Close assistant"><X size={19} /></button>
          </div>
        </header>

        <div className="ac-sc-body" aria-live="polite" ref={body} onScroll={onScroll}>
          {messages.length === 0 && (
            <div className="ac-welcome">
              <h3 className="ac-display">{first ? `Hi ${first}.` : 'Hi there.'}<br />What can I help with?</h3>
              <p className="ac-muted">Ask in your own words, spelling mistakes are fine. I check our real catalogue, stock near you{user ? ' and your own orders' : ''}, and give you a number to call when a detail needs a person.</p>
              <div className="ac-sugg">
                {STARTERS.map((s, i) => (
                  <button key={s.title} onClick={() => onAction(s.text)}><s.icon size={20} /><b>{s.title}</b><span>{s.text}</span></button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <React.Fragment key={i}>
              <div className={`ac-msgrow ${m.from === 'user' ? 'is-user' : ''}`}>
                {m.from === 'bot' && <span className="ac-msg-ava"><LogoMark size={26} /></span>}
                <div><div className="ac-msg" data-from={m.from}><Rich text={m.text} /></div><small className="ac-time">{m.at}</small></div>
              </div>
              {m.cards?.length > 0 && (
                <div className="ac-cardrow">
                  {m.cards.map((c, idx) => (c.type === 'product'
                    ? <ProductCard key={c.id} c={c} n={m.cards.filter((x) => x.type === 'product').length > 1 ? idx + 1 : 0} onClose={onClose} onBuy={startBuy} />
                    : c.type === 'contact' ? <ContactCard key="contact" c={c} />
                      : <OrderCard key={c.id} c={c} onClose={onClose} onAsk={send} />))}
                </div>
              )}
            </React.Fragment>
          ))}

          {buying && (
            <div className="ac-buybox" role="region" aria-label="Confirm your order">
              <small className="ac-muted" aria-label="Progress">✓ Product chosen &nbsp;→&nbsp; <b>2. Confirm</b> &nbsp;→&nbsp; 3. Order placed</small>
              <div className="ac-row" style={{ gap: 12, alignItems: 'center' }}>
                {buying.card.image && <img src={sized(buying.card.image, 120)} alt="" className="ac-buy-img" />}
                <div style={{ flex: 1, minWidth: 0 }}><b>{buying.card.name}</b><div className="ac-muted" style={{ fontSize: 14 }}>{money(buying.card.price)} each</div></div>
                <span className="ac-row" style={{ gap: 6 }}>
                  <button type="button" aria-label="Fewer" onClick={() => setBuying((b) => ({ ...b, qty: Math.max(1, b.qty - 1) }))}>−</button>
                  <b>{buying.qty}</b>
                  <button type="button" aria-label="More" onClick={() => setBuying((b) => ({ ...b, qty: Math.min(5, b.qty + 1, b.card.stock || 5) }))}>+</button>
                </span>
              </div>
              <small>Item total {money(buying.card.price * buying.qty)}. Free delivery above ₹499.</small>
              <small>Deliver to: <b>{[buying.address.addressLine, buying.address.city, buying.address.pinCode].filter(Boolean).join(', ')}</b> (from {buying.source})</small>
              <small>Pay: Cash on delivery</small>
              {buying.error && <small role="alert" style={{ color: 'var(--coral)' }}>{buying.error}</small>}
              <div className="ac-row">
                <button className="ac-btn ac-btn-blue ac-btn-small" onClick={confirmBuy} disabled={buying.saving}>{buying.saving ? 'Placing…' : 'Confirm order'}</button>
                <button className="ac-btn ac-btn-soft ac-btn-small" onClick={() => { addToCart(asCartItem(buying.card), buying.qty); setBuying(null); onClose(); navigate('/checkout'); }}>Change address or payment</button>
                <button className="ac-btn ac-btn-soft ac-btn-small" onClick={() => setBuying(null)}>Cancel</button>
              </div>
              <small className="ac-muted">Or just type <b>yes</b> to confirm, <b>no</b> to cancel.</small>
            </div>
          )}
          {busy && <div className="ac-typing" aria-label="Typing"><i /><i /><i /></div>}

          {handoff && (
            <div className="ac-handoff" role="region" aria-label="Talk to a person">
              <b>Talk to a person</b>
              <a className="ac-callcard" href={tel}>
                <span className="ac-callicon"><Phone size={20} /></span>
                <span><b>Call {SUPPORT_PHONE}</b><small>{SUPPORT_HOURS} · orders, returns, payments</small></span>
              </a>
              {user ? (
                <>
                  <div className="ac-field"><label htmlFor="h-ph">Or we call you. Your number</label>
                    <input id="h-ph" className="ac-input" inputMode="tel" value={handoff.phone} onChange={(e) => setHandoff({ ...handoff, phone: e.target.value })} placeholder="10-digit mobile number" /></div>
                  <button className="ac-btn ac-btn-blue ac-btn-small" onClick={requestCallback} disabled={handoff.saving}>{handoff.saving ? 'Sending…' : 'Call me back'}</button>
                  <small className="ac-muted">We save your name, this number and this chat on a ticket, so the person calling already knows the story.</small>
                  <details open={handoff.write} onToggle={(e) => setHandoff({ ...handoff, write: e.target.open })}>
                    <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Or write to us instead</summary>
                    <form onSubmit={submitWritten} style={{ display: 'grid', gap: 10, marginTop: 10 }}>
                      <div className="ac-field"><label htmlFor="h-sub">What is this about?</label>
                        <input id="h-sub" className="ac-input" value={handoff.subject} onChange={(e) => setHandoff({ ...handoff, subject: e.target.value })} required /></div>
                      <div className="ac-field"><label htmlFor="h-ord">Order number (if any)</label>
                        <input id="h-ord" className="ac-input" placeholder="ORD-2026-1234" value={handoff.orderId} onChange={(e) => setHandoff({ ...handoff, orderId: e.target.value })} /></div>
                      <div className="ac-field"><label htmlFor="h-msg">Tell us what happened</label>
                        <textarea id="h-msg" className="ac-textarea" value={handoff.message} onChange={(e) => setHandoff({ ...handoff, message: e.target.value })} required /></div>
                      <button className="ac-btn ac-btn-outline ac-btn-small" disabled={handoff.saving}>{handoff.saving ? 'Sending…' : 'Send to support'}</button>
                    </form>
                  </details>
                </>
              ) : <small className="ac-muted">Sign in and we can also call you back or open a ticket with this chat attached.</small>}
              <button type="button" className="ac-btn ac-btn-soft ac-btn-small" onClick={() => setHandoff(null)}>Close</button>
            </div>
          )}

          {!handoff && lettered.length > 0 && messages.length > 0 && !busy && (
            <div className="ac-actions-row">
              {lettered.map((a) => <button key={a} className="ac-act" onClick={() => onAction(a)}>{a}</button>)}
            </div>
          )}

          {!handoff && replies >= 3 && sessionId && !busy && (
            <div className="ac-stars">{rating ? 'Thanks for rating this chat.' : 'How was this chat?'}
              {!rating && [1, 2, 3, 4, 5].map((n) => <button key={n} onClick={() => rate(n)} aria-label={`${n} star${n > 1 ? 's' : ''}`}>★</button>)}
            </div>
          )}
          {error && <div className="ac-warn" role="alert">{error}</div>}
          <div ref={end} />
        </div>

        {away && <button className="ac-jump" onClick={() => end.current?.scrollIntoView({ behavior: 'smooth' })} aria-label="Jump to the latest message"><ArrowDown size={18} /></button>}

        {memory && (
          <div className="ac-memory" role="region" aria-label="What Saathi remembers about you">
            {memory.error ? <p>Could not load this right now.</p> : (
              <>
                <b>What Saathi remembers, {memory.name}</b>
                <p>{memory.interests.length || memory.budgetMax || memory.recentSearches.length
                  ? `${memory.interests.length ? `You look at ${memory.interests.join(', ')}. ` : ''}${memory.budgetMax ? `Your usual budget is about ₹${memory.budgetMax}. ` : ''}${memory.recentSearches.length ? `Recent: ${memory.recentSearches.join(' · ')}.` : ''}`
                  : 'Nothing yet. It only saves categories, a budget and your last few searches, to help you faster.'}</p>
                <button onClick={forget}>Forget everything</button>
              </>
            )}
          </div>
        )}
        <div className="ac-sc-foot">
          <form className="ac-sc-form" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <label className="ac-sr" htmlFor="sc-in">Type your message</label>
            <input id="sc-in" ref={field} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about a product, an order, or anything" autoComplete="off" />
            <button className="ac-sc-send" disabled={!input.trim() || busy} aria-label="Send"><Send size={19} /></button>
          </form>
          <nav className="ac-sc-links2" aria-label="More ways to get help">
            <a href={tel} title={`Call ${SUPPORT_PHONE}`}><Phone size={14} /> Call support</a>
            <button onClick={() => openHandoff()}><Headset size={14} /> Talk to a person</button>
            <button onClick={() => { onClose(); navigate('/support'); }}><Ticket size={14} /> Tickets</button>
            {user && <button onClick={() => (memory ? setMemory(null) : showMemory())}><Sparkles size={14} /> Memory</button>}
          </nav>
          <p className="ac-sc-note"><ShieldCheck size={12} /> Answers come from our live catalogue and your own orders.</p>
        </div>
      </aside>
    </>
  );
}
