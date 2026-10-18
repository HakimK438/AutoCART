import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Send, X, RefreshCw, AlertTriangle, TrendingUp, Lightbulb } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import './munim.css';

const OPTIONS = [
  'Analyse my sales this week',
  'What should I do next?',
  'Which products are not selling?',
  'Which products will run out soon?',
  'Are my prices right?',
  'What is my profit?',
];
const keyFor = (u) => `munim_chat_${u?.id || u?.email}`;
const load = (k) => { try { return JSON.parse(localStorage.getItem(k) || '[]'); } catch { return []; } };

const Rich = ({ text }) => String(text).split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : p));

/** Revenue per day as small bars, with the numbers available to screen readers. */
const Bars = ({ data }) => {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <figure className="mn-bars" aria-label={`Revenue per day: ${data.map((d) => `${d.label} ${d.value} rupees`).join(', ')}`}>
      <div>{data.map((d) => <i key={d.label} title={`${d.label}: ₹${d.value.toLocaleString('en-IN')}`} style={{ height: `${Math.max(4, (d.value / max) * 100)}%` }} />)}</div>
      <figcaption><span>{data[0]?.label}</span><span>Daily revenue</span><span>{data[data.length - 1]?.label}</span></figcaption>
    </figure>
  );
};

const ICON = { high: AlertTriangle, medium: TrendingUp, low: Lightbulb };
const Recs = ({ items }) => (
  <ul className="mn-recs">
    {items.map((r) => {
      const Icon = ICON[r.priority] || Lightbulb;
      return (
        <li key={r.title} data-p={r.priority}>
          <Icon size={16} aria-hidden="true" />
          <div><b>{r.title}</b><span>{r.detail}</span></div>
          {r.link && <Link to={r.link} className="mn-open">Open</Link>}
        </li>
      );
    })}
  </ul>
);

/**
 * Munim, the seller's shop assistant. It floats on every page a signed-in seller visits (storefront and seller centre),
 * keeps its conversation until the seller signs out, and answers from the seller's own products and orders.
 */
export default function MunimChat() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [log, setLog] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  const k = user ? keyFor(user) : '';

  useEffect(() => { if (k) setLog(load(k)); }, [k]);
  useEffect(() => { if (k) { try { localStorage.setItem(k, JSON.stringify(log.slice(-40))); } catch { /* ignore */ } } }, [log, k]);
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }); }, [log, busy, open]);
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener('autocart:open-assistant', onOpen);
    return () => window.removeEventListener('autocart:open-assistant', onOpen);
  }, []);

  if (!user || user.role !== 'SELLER') return null;
  const first = user.name?.split(' ')[0];

  const ask = async (q) => {
    let question = (q ?? text).trim();
    if (!question || busy) return;
    setText('');
    if (question === '0') { setLog([]); return; }
    setBusy(true);
    setLog((l) => [...l, { q: question }]);
    try {
      const { data } = await api.post('/seller/assistant', { message: question });
      setLog((l) => [...l, { a: data.answer, columns: data.columns || [], rows: data.rows || [], chart: data.chart || [], recs: data.recommendations || [] }]);
    } catch (e) {
      setLog((l) => [...l, { a: e?.response?.data?.detail || 'I could not answer that right now. Please try again.', columns: [], rows: [] }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="mn-root">
      {!open && <button className="mn-fab" onClick={() => setOpen(true)} aria-label="Open Munim, your shop assistant"><BarChart3 size={20} /><span>Munim</span></button>}
      {open && (
        <aside className="mn-panel" role="dialog" aria-label="Munim, your shop assistant">
          <header className="mn-head">
            <span className="mn-ava"><BarChart3 size={20} /></span>
            <div><b>Munim</b><small>Your shop assistant · sales, stock, orders</small></div>
            <button onClick={() => setLog([])} aria-label="New chat" title="New chat (type 0)"><RefreshCw size={16} /></button>
            <button onClick={() => setOpen(false)} aria-label="Close Munim"><X size={18} /></button>
          </header>
          <div className="mn-body" aria-live="polite">
            {log.length === 0 && (
              <div className="mn-welcome">
                <h3>Namaste{first ? `, ${first}` : ''}.</h3>
                <p>I watch your sales, stock and prices, and tell you what to do next. Ask in your own words.</p>
              </div>
            )}
            {log.map((m, i) => (m.q
              ? <div key={i} className="mn-msg mn-me">{m.q}</div>
              : (
                <div key={i} className="mn-msg mn-bot">
                  <Rich text={m.a} />
                  {m.chart?.length > 0 && <Bars data={m.chart} />}
                  {m.rows?.length > 0 && (
                    <table><thead><tr>{m.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                      <tbody>{m.rows.map((r, j) => <tr key={j}>{r.map((v, c) => <td key={c}>{v}</td>)}</tr>)}</tbody></table>
                  )}
                  {m.recs?.length > 0 && <Recs items={m.recs} />}
                </div>
              )))}
            {busy && <div className="mn-msg mn-bot mn-typing"><i /><i /><i /></div>}
            <div className="mn-opts">
              {OPTIONS.map((o) => <button key={o} onClick={() => ask(o)}>{o}</button>)}
            </div>
            <div ref={end} />
          </div>
          <form className="mn-form" onSubmit={(e) => { e.preventDefault(); ask(); }}>
            <label className="ac-sr" htmlFor="mn-in">Ask Munim</label>
            <input id="mn-in" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about sales, stock, prices or orders" maxLength={300} autoComplete="off" />
            <button disabled={busy || !text.trim()} aria-label="Send"><Send size={18} /></button>
          </form>
        </aside>
      )}
    </div>
  );
}
