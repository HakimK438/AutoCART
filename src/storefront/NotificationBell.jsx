import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, PackageCheck, Truck, PartyPopper, ShoppingBag, X } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import './storefront.css';
import './bell.css';

const POLL_MS = 15000;
const ago = (iso) => {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
};
const iconFor = (t = '') => (/reached|collecting/i.test(t) ? PartyPopper : /on its way|collect/i.test(t) ? Truck : /packed/i.test(t) ? PackageCheck : ShoppingBag);

/**
 * The bell in the header: order updates (placed, packed, on the way, delivered) for the signed-in user.
 * It checks every 15 seconds, and a new update pops up as a short message so "your product has reached you" is never missed.
 */
export default function NotificationBell() {
  const { user } = useAuth();
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const seen = useRef(null);
  const box = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data: d } = await api.get('/notifications');
      setData(d);
      const newest = d.items.find((n) => !n.read);
      if (seen.current !== null && newest && newest.id > seen.current) setToast(newest);
      const top = d.items.reduce((m, n) => Math.max(m, n.id), 0);
      seen.current = Math.max(seen.current || 0, top);
    } catch { /* offline or signed out: the bell just stays quiet */ }
  }, []);

  useEffect(() => {
    if (!user) { seen.current = null; setData({ unread: 0, items: [] }); return undefined; }
    load();
    const t = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(t);
  }, [user, load]);
  useEffect(() => { if (!toast) return undefined; const t = window.setTimeout(() => setToast(null), 9000); return () => window.clearTimeout(t); }, [toast]);
  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc); };
  }, [open]);

  if (!user) return null;
  const read = async (id) => { try { await api.post('/notifications/read', id ? { id } : {}); } catch { /* shown again next time */ } load(); };
  const ToastIcon = toast ? iconFor(toast.title) : Bell;

  return (
    <div className="ac-bell" ref={box}>
      <button className="ac-icon-btn" onClick={() => setOpen((o) => !o)} aria-label={`Notifications, ${data.unread} unread`} aria-expanded={open} aria-haspopup="true">
        <Bell size={20} />{data.unread > 0 && <span className="ac-count">{data.unread > 9 ? '9+' : data.unread}</span>}
        <span className="ac-label">Updates</span>
      </button>
      {open && (
        <div className="ac-bell-panel" role="dialog" aria-label="Notifications">
          <div className="ac-bell-head"><b>Updates</b>{data.unread > 0 && <button onClick={() => read()}>Mark all read</button>}</div>
          {data.items.length === 0 ? <p className="ac-muted" style={{ padding: 16, margin: 0 }}>Nothing yet. When you order something, you will see each step here: packed, on the way, delivered.</p> : (
            <ul>
              {data.items.map((n) => {
                const I = iconFor(n.title);
                return (
                  <li key={n.id} data-unread={!n.read}>
                    <Link to={n.orderId ? `/orders/${n.orderId}` : '/orders'} onClick={() => { setOpen(false); if (!n.read) read(n.id); }}>
                      <span className="ac-bell-ico"><I size={17} /></span>
                      <span><b>{n.title}</b><small>{n.body}</small><em>{ago(n.createdAt)}</em></span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
      {toast && (
        <div className="ac-bell-toast" role="status" aria-live="polite">
          <span className="ac-bell-ico"><ToastIcon size={18} /></span>
          <Link to={toast.orderId ? `/orders/${toast.orderId}` : '/orders'} onClick={() => { read(toast.id); setToast(null); }}><b>{toast.title}</b><small>{toast.body}</small></Link>
          <button onClick={() => setToast(null)} aria-label="Dismiss"><X size={16} /></button>
        </div>
      )}
    </div>
  );
}
