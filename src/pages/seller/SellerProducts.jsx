import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, Check, History, PackagePlus, Search, Zap } from 'lucide-react';
import api from '../../services/api';
import { sized } from '../../storefront/parts';

const REASON = { sale: 'Sold to a customer', manual: 'You changed it', 'auto-restock': 'Auto-restock rule', 'cancelled-order': 'Order cancelled' };

/** One product: photo, price, stock (manual), and an auto-restock rule (automatic). */
function Row({ p, onChanged, flash }) {
  const [price, setPrice] = useState(String(p.price));
  const [cost, setCost] = useState(p.costPrice ? String(p.costPrice) : '');
  const [stock, setStock] = useState(String(p.stock));
  const [auto, setAuto] = useState(!!p.autoRestock);
  const [level, setLevel] = useState(String(p.reorderLevel ?? 5));
  const [qty, setQty] = useState(String(p.restockQty ?? 20));
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [err, setErr] = useState({});
  const file = useRef(null);

  const dirty = cost !== (p.costPrice ? String(p.costPrice) : '') || price !== String(p.price) || stock !== String(p.stock) || auto !== !!p.autoRestock || level !== String(p.reorderLevel ?? 5) || qty !== String(p.restockQty ?? 20);
  const save = async (extra = {}) => {
    setErr({});
    try {
      await api.patch(`/seller/products/${p.id}`, { price, costPrice: cost || 0, stock, autoRestock: auto, reorderLevel: level, restockQty: qty, ...extra });
      flash(`${p.name} updated.`); onChanged();
    } catch (e) { setErr(e?.response?.data?.errors || {}); flash(e?.response?.data?.detail || 'That did not save.'); }
  };
  const photo = (f) => {
    if (!f) return;
    const body = new FormData(); body.append('image', f);
    api.patch(`/seller/products/${p.id}`, body).then(() => { flash('Photo updated.'); onChanged(); })
      .catch((e) => flash(e?.response?.data?.errors?.image || e?.response?.data?.detail || 'The photo did not upload.'));
  };
  const showHistory = async () => {
    setOpen((o) => !o);
    if (!history) { try { setHistory((await api.get(`/seller/products/${p.id}/stock-log`)).data.history); } catch { setHistory([]); } }
  };
  const bump = (n) => setStock(String(Math.max(0, (parseInt(stock, 10) || 0) + n)));

  return (
    <article className="ac-prodrow">
      <div className="ac-prodrow-main">
        <div className="ac-prodcell">
          <button type="button" className="ac-photo" onClick={() => file.current?.click()} aria-label={`Change photo of ${p.name}`} title="Change photo">
            {p.image ? <img src={sized(p.image, 120)} alt="" /> : <span><Camera size={20} /><small>Add photo</small></span>}
          </button>
          <input ref={file} type="file" accept="image/*" hidden onChange={(e) => photo(e.target.files?.[0])} />
          <div style={{ minWidth: 0 }}>
            <Link to={`/products/${p.id}`} className="ac-prodname">{p.name}</Link>
            <small className="ac-muted">{Number(p.rating || 0).toFixed(1)} ★ · {p.reviewCount} reviews</small>
            <div className="ac-row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
              <span className="ac-chip-status" data-tone={p.stock <= 0 ? 'bad' : p.stock <= 10 ? 'warn' : 'ok'}>{p.stockStatus || (p.stock <= 0 ? 'Out of stock' : 'In stock')} · {p.stock} left</span>
              <span className="ac-chip-status" data-tone={p.unitsSold ? 'info' : undefined}>{p.unitsSold ? `Bought: ${p.unitsSold} sold in ${p.orderCount} order${p.orderCount > 1 ? 's' : ''}${p.lastBought ? ` · last ${p.lastBought}` : ''}` : 'Not bought yet'}</span>
              {p.openOrders > 0 && <span className="ac-chip-status" data-tone="warn">{p.openOrders} order{p.openOrders > 1 ? 's' : ''} to pack</span>}
            </div>
            {p.buyers?.length > 0 && (
              <details style={{ marginTop: 6 }}><summary className="ac-muted" style={{ cursor: 'pointer', fontSize: 14 }}>Who bought it ({p.buyers.length}{p.orderCount > p.buyers.length ? ` of ${p.orderCount}` : ''})</summary>
                <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 14 }}>{p.buyers.map((b) => <li key={b.orderId}>{b.name} × {b.quantity}{b.phone ? ` · ${b.phone}` : ''} · {b.date} · {b.status} · {b.orderId}</li>)}</ul>
              </details>
            )}
          </div>
        </div>
        <label className="ac-fld"><span>Price (₹)</span><input className="ac-input ac-cell-input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} aria-invalid={!!err.price} /></label>
        <label className="ac-fld"><span>Cost price (₹)</span><input className="ac-input ac-cell-input" inputMode="decimal" placeholder="for profit" value={cost} onChange={(e) => setCost(e.target.value)} aria-invalid={!!err.costPrice} /></label>
        <div className="ac-fld"><span>Stock (manual)</span>
          <div className="ac-stepper">
            <button type="button" onClick={() => bump(-1)} aria-label="One less">−</button>
            <input className="ac-input ac-cell-input" inputMode="numeric" value={stock} onChange={(e) => setStock(e.target.value)} aria-label={`Stock of ${p.name}`} aria-invalid={!!err.stock} />
            <button type="button" onClick={() => bump(1)} aria-label="One more">+</button>
            <button type="button" onClick={() => bump(10)} aria-label="Ten more">+10</button>
          </div>
          {p.stock <= 0 ? <small className="ac-warn">Out of stock</small> : p.stock <= 10 ? <small className="ac-warn">Almost gone</small> : null}
        </div>
        <label className="ac-switch" title="Automatic: AutoCart tops up your stock after a sale brings it down to your reorder level">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /><span><Zap size={15} /> Auto-restock</span>
        </label>
        <div className="ac-row" style={{ gap: 8 }}>
          {dirty && <button className="ac-btn ac-btn-blue ac-btn-small" onClick={() => save()}>Save</button>}
          <button className="ac-btn ac-btn-soft ac-btn-small" onClick={showHistory} aria-expanded={open}><History size={15} /> History</button>
        </div>
      </div>
      {(auto || open) && (
        <div className="ac-prodrow-more">
          {auto && (
            <div className="ac-autobox">
              <b>Automatic restock</b>
              <p className="ac-muted">After a sale, if stock is at or below <input className="ac-input ac-mini-input" inputMode="numeric" value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Reorder level" aria-invalid={!!err.reorderLevel} /> units,
                add <input className="ac-input ac-mini-input" inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value)} aria-label="Units to add" aria-invalid={!!err.restockQty} /> units.</p>
              <small className="ac-muted">Use this only if your supplier reliably tops you up by that amount. AutoCart adds the units to your shelf count and logs it in History.</small>
              {(err.reorderLevel || err.restockQty) && <small role="alert" style={{ color: 'var(--coral)' }}>{err.reorderLevel || err.restockQty}</small>}
            </div>
          )}
          {open && (
            <div className="ac-histbox">
              <b>Stock history</b>
              {!history ? <p className="ac-muted">Loading…</p> : history.length === 0 ? <p className="ac-muted">No changes recorded yet.</p> : (
                <ul>{history.map((h, i) => <li key={i}><span className={h.change > 0 ? 'up' : 'down'}>{h.change > 0 ? '+' : ''}{h.change}</span> <span>{REASON[h.reason] || h.reason}</span> <small className="ac-muted">now {h.stockAfter} · {new Date(h.at).toLocaleString()}</small></li>)}</ul>
              )}
            </div>
          )}
        </div>
      )}
      {err.image && <small role="alert" style={{ color: 'var(--coral)' }}>{err.image}</small>}
    </article>
  );
}

export default function SellerProducts({ products, onChanged }) {
  const [saved, setSaved] = useState('');
  const [q, setQ] = useState('');
  const [view, setView] = useState('all');
  const flash = (t) => { setSaved(t); window.setTimeout(() => setSaved(''), 3000); };
  const shown = products.filter((p) => (!q || `${p.name} ${p.category}`.toLowerCase().includes(q.toLowerCase()))
    && (view === 'all' || (view === 'low' && p.stock > 0 && p.stock <= 10) || (view === 'out' && p.stock <= 0)));
  const low = products.filter((p) => p.stock > 0 && p.stock <= 10).length;
  const out = products.filter((p) => p.stock <= 0).length;
  return (
    <section id="products" className="ac-box" aria-labelledby="prod-h" style={{ marginTop: 24 }}>
      <div className="ac-row-between"><h2 id="prod-h">Your products ({products.length})</h2>{saved && <span className="ac-chip-status" data-tone="ok" role="status"><Check size={13} />&nbsp;{saved}</span>}</div>
      {products.length === 0 ? (
        <div className="ac-emptyprod">
          <PackagePlus size={40} />
          <b>No products yet</b>
          <p className="ac-muted">Add your first product above: a name, price, stock and a photo. It appears in the store straight away, and this is where you will update stock and prices later.</p>
          <a href="#add-product" className="ac-btn ac-btn-blue ac-btn-small" onClick={() => document.getElementById('add-product')?.setAttribute('open', '')}>Add your first product</a>
        </div>
      ) : (
        <>
          <p className="ac-muted" style={{ marginTop: 4 }}>Change stock by hand any time, or switch on <b>Auto-restock</b> and AutoCart tops it up for you after sales.</p>
          <div className="ac-row" style={{ gap: 10, flexWrap: 'wrap', marginTop: 12 }}>
            <label className="ac-search ac-prodsearch"><Search size={16} aria-hidden="true" /><span className="ac-sr">Search your products</span><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search your products" /></label>
            <div className="ac-seg ac-seg-sm" role="group" aria-label="Show">
              <button data-on={view === 'all'} onClick={() => setView('all')}>All</button>
              <button data-on={view === 'low'} onClick={() => setView('low')}>Almost gone ({low})</button>
              <button data-on={view === 'out'} onClick={() => setView('out')}>Out of stock ({out})</button>
            </div>
          </div>
          <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
            {shown.map((p) => <Row key={`${p.id}-${p.stock}-${p.price}-${p.image}`} p={p} onChanged={onChanged} flash={flash} />)}
            {shown.length === 0 && <p className="ac-muted">No product matches.</p>}
          </div>
        </>
      )}
    </section>
  );
}
