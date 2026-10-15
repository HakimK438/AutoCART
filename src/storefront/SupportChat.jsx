import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { X, Send, Search, PackageSearch, RotateCcw, Headset, Plus, Check, RefreshCw, ArrowDown } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useCart } from '../hooks/useCart';
import { money, sized } from './parts';
import { LogoMark } from './Brand';
import './storefront.css';

const SESSION_KEY = 'autocart_support_session';
const STARTERS = [
  { icon: Search, title: 'Find something', text: 'Find a gift under ₹1,500' },
  { icon: PackageSearch, title: 'Track an order', text: 'Track my order' },
  { icon: RotateCcw, title: 'Return an item', text: 'Return an item' },
  { icon: Headset, title: 'Talk to a person', text: 'Talk to a person' },
];

const readSession = (email) => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || '{}'); return s.email === (email || '') ? s.id || '' : ''; } catch { return ''; } };
const saveSession = (email, id) => { try { localStorage.setItem(SESSION_KEY, JSON.stringify({ email: email || '', id })); } catch { /* storage may be blocked */ } };
const clock = () => new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

/** The assistant writes **bold** and line breaks; show them properly instead of as raw symbols. */
const Rich = ({ text }) => text.split('\n').map((line, i) => (
  <React.Fragment key={i}>
    {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) => (part.startsWith('**') && part.endsWith('**') ? <strong key={j}>{part.slice(2, -2)}</strong> : part.replace(/\*([^*]+)\*/g, '$1')))}
    {i < text.split('\n').length - 1 && <br />}
  </React.Fragment>
));

const ProductCard = ({ c, onClose }) => {
  const { addToCart } = useCart();
  const [added, setAdded] = useState(false);
  const off = c.originalPrice > c.price;
  return (
    <div className="ac-mini-card ac-pcard">
      {c.image ? <img src={sized(c.image, 200)} alt="" /> : <div className="ac-pcard-ph" aria-hidden="true" />}
      <div style={{ minWidth: 0 }}>
        <Link to={`/products/${c.id}`} onClick={onClose}><b>{c.name}</b></Link>
        <span>{money(c.price)}{off && <s> {money(c.originalPrice)}</s>} · {Number(c.rating || 0).toFixed(1)} ★{c.stock > 0 && c.stock <= 10 ? ` · only ${c.stock} left` : ''}</span>
        <div className="ac-row" style={{ gap: 8, marginTop: 8 }}>
          <button className="ac-btn ac-btn-blue ac-btn-small ac-pcard-btn" disabled={c.stock <= 0}
            onClick={() => { addToCart({ id: c.id, name: c.name, price: c.price, originalPrice: c.originalPrice, rating: c.rating, stock: c.stock, images: c.image ? [c.image] : [] }, 1); setAdded(true); window.setTimeout(() => setAdded(false), 1600); }}>
            {added ? <><Check size={14} /> Added</> : <><Plus size={14} /> Add to cart</>}
          </button>
          <Link to={`/products/${c.id}`} className="ac-btn ac-btn-outline ac-btn-small ac-pcard-btn" onClick={onClose}>View</Link>
        </div>
      </div>
    </div>
  );
};

export default function SupportChat({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cartItems } = useCart();
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
  const showMemory = () => api.get('/support/memory').then((r) => setMemory(r.data)).catch(() => setMemory({ error: true }));
  const forget = () => api.delete('/support/memory').then(() => setMemory({ name: user?.name?.split(' ')[0], interests: [], recentSearches: [], budgetMax: null, chats: 0 })).catch(() => {});
  const body = useRef(null);
  const end = useRef(null);
  const field = useRef(null);

  useEffect(() => { if (isOpen) { setSessionId(readSession(user?.email)); window.setTimeout(() => field.current?.focus(), 350); } }, [isOpen, user?.email]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, busy, handoff]);
  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput(''); setError(''); setBusy(true); setActions([]);
    setMessages((m) => [...m, { from: 'user', text: message, at: clock() }]);
    try {
      const { data } = await api.post('/support/chat', { message, sessionId, cartItems: (cartItems || []).map((i) => ({ id: i.id, price: i.price, quantity: i.quantity })) });
      setSessionId(data.sessionId); saveSession(user?.email, data.sessionId);
      setMessages((m) => [...m, { from: 'bot', text: data.reply, cards: data.cards || [], at: clock() }]);
      setActions(data.suggestedActions || []);
    } catch {
      setError('We could not reach support just now. Check your connection and try again.');
    } finally { setBusy(false); }
  };

  const newChat = () => { setMessages([]); setActions([]); setSessionId(''); saveSession(user?.email, ''); setRating(0); setHandoff(null); setError(''); field.current?.focus(); };

  const onAction = (label) => {
    if (label === 'Talk to a person') return openHandoff();
    if (label === 'See my tickets') { onClose(); return navigate('/support'); }
    if (label === 'Sign in') { onClose(); return navigate('/login'); }
    return send(label);
  };

  const openHandoff = () => {
    if (!user) { setMessages((m) => [...m, { from: 'bot', text: 'To bring in a person I need to know who you are. Please sign in first.', at: clock() }]); setActions(['Sign in']); return; }
    const lastUser = [...messages].reverse().find((m) => m.from === 'user');
    setHandoff({ subject: (lastUser?.text || '').slice(0, 80), message: lastUser?.text || '', orderId: '', preferredContact: 'Reply here', consent: false, saving: false });
  };

  const submitHandoff = async (e) => {
    e.preventDefault();
    setHandoff((h) => ({ ...h, saving: true })); setError('');
    try {
      const { data } = await api.post('/support/tickets', { ...handoff, sessionId, consent: handoff.consent === true });
      setHandoff(null);
      setMessages((m) => [...m, { from: 'bot', text: `Done. Your ticket is **${data.id}**. A person will reply in your tickets list. They can see this chat, so you do not need to repeat yourself.`, at: clock() }]);
      setActions(['See my tickets']);
    } catch (err) {
      setError(err?.response?.data?.detail || 'We could not create the ticket. Please try again.');
      setHandoff((h) => ({ ...h, saving: false }));
    }
  };

  const rate = async (n) => { setRating(n); try { await api.post(`/support/chat/${sessionId}/rating`, { rating: n }); } catch { /* the thank-you still shows */ } };
  const onScroll = (e) => setAway(e.target.scrollHeight - e.target.scrollTop - e.target.clientHeight > 160);

  if (!isOpen) return null;
  const replies = messages.filter((m) => m.from === 'bot').length;
  const first = user?.name?.split(' ')[0];

  return (
    <>
      <div className="ac-sc-back" onClick={onClose} aria-hidden="true" />
      <aside className="ac-sc" role="dialog" aria-modal="true" aria-label="Saathi, the AutoCart assistant">
        <div className="ac-sc-head">
          <div className="ac-sc-avatar"><LogoMark size={40} /><i className="ac-online" aria-hidden="true" /></div>
          <div><b>Saathi</b><small>Your AutoCart shopping companion · online</small></div>
          <div className="ac-row" style={{ marginLeft: 'auto', gap: 6 }}>
            {messages.length > 0 && <button className="ac-sc-x ac-sc-ghost" onClick={newChat} aria-label="Start a new chat" title="New chat"><RefreshCw size={17} /></button>}
            <button className="ac-sc-x" onClick={onClose} aria-label="Close assistant"><X size={20} /></button>
          </div>
        </div>

        <div className="ac-sc-body" aria-live="polite" ref={body} onScroll={onScroll}>
          {messages.length === 0 && (
            <div className="ac-welcome">
              <h3 className="ac-display">{first ? `Hi ${first}.` : 'Hi there.'}<br />What can I help with?</h3>
              <p className="ac-muted">I answer from our real catalogue{user ? ' and your own orders' : ''}. I never guess prices or stock.</p>
              <div className="ac-sugg">
                {STARTERS.map((s) => (
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
                  {m.cards.map((c) => c.type === 'product' ? <ProductCard key={c.id} c={c} onClose={onClose} /> : (
                    <Link key={c.id} to={`/orders/${c.id}`} className="ac-mini-card" onClick={onClose}>
                      <div style={{ gridColumn: '1 / -1' }}><b>Order {c.id}</b><span>{c.status} · {money(c.total)} · {c.payment}</span></div>
                    </Link>
                  ))}
                </div>
              )}
            </React.Fragment>
          ))}
          {busy && <div className="ac-typing" aria-label="Typing"><i /><i /><i /></div>}

          {handoff && (
            <form className="ac-handoff" onSubmit={submitHandoff}>
              <b>Talk to a person</b>
              <div className="ac-field"><label htmlFor="h-sub">What is this about?</label>
                <input id="h-sub" className="ac-input" value={handoff.subject} onChange={(e) => setHandoff({ ...handoff, subject: e.target.value })} required /></div>
              <div className="ac-field"><label htmlFor="h-ord">Order number (if any)</label>
                <input id="h-ord" className="ac-input" placeholder="ORD-2026-1234" value={handoff.orderId} onChange={(e) => setHandoff({ ...handoff, orderId: e.target.value })} /></div>
              <div className="ac-field"><label htmlFor="h-msg">Tell us what happened</label>
                <textarea id="h-msg" className="ac-textarea" value={handoff.message} onChange={(e) => setHandoff({ ...handoff, message: e.target.value })} required /></div>
              <div><b style={{ fontSize: 14 }}>What we will save on your ticket</b>
                <ul><li>Your name and email ({user?.email})</li><li>The subject, order number and message above</li><li>This chat, so you do not repeat yourself</li></ul></div>
              <label className="ac-check"><input type="checkbox" checked={handoff.consent} onChange={(e) => setHandoff({ ...handoff, consent: e.target.checked })} />
                <span>I agree that AutoCart saves these details to help with my request.</span></label>
              <div className="ac-row">
                <button className="ac-btn ac-btn-blue ac-btn-small" disabled={!handoff.consent || handoff.saving}>{handoff.saving ? 'Sending…' : 'Send to support'}</button>
                <button type="button" className="ac-btn ac-btn-soft ac-btn-small" onClick={() => setHandoff(null)}>Cancel</button>
              </div>
            </form>
          )}

          {!handoff && actions.length > 0 && <div className="ac-actions-row">{actions.map((a) => <button key={a} className="ac-act" onClick={() => onAction(a)}>{a}</button>)}</div>}

          {!handoff && replies >= 2 && sessionId && (
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
            <input id="sc-in" ref={field} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about a product or an order" autoComplete="off" />
            <button className="ac-sc-send" disabled={!input.trim() || busy} aria-label="Send"><Send size={19} /></button>
          </form>
          <div className="ac-sc-links">
            <button onClick={() => openHandoff()}>Talk to a person</button>
            <button onClick={() => { onClose(); navigate('/support'); }}>My tickets</button>
            {user && <button onClick={() => (memory ? setMemory(null) : showMemory())}>What Saathi remembers</button>}
          </div>
        </div>
      </aside>
    </>
  );
}
