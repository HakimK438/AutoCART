import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Boxes, AlertTriangle, MessageCircleQuestion, ClipboardList, IndianRupee, LogOut, ExternalLink, Check, Circle, LayoutDashboard, Store, Wallet, PackagePlus } from 'lucide-react';
import api from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { BrandLink } from '../../storefront/Brand';
import SalesCharts from './SalesCharts';
import HowItWorks from './HowItWorks';
import SellerOrders from './SellerOrders';
import StoreProfile from './StoreProfile';
import PayoutSettings from './PayoutSettings';
import SellerProducts from './SellerProducts';
import AddProduct from './AddProduct';
import MunimChat from '../../storefront/MunimChat';
import EnquiryInbox from '../../storefront/EnquiryInbox';
import { money, count, sized } from '../../storefront/parts';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

const TONE = { warn: 'warn', info: 'info', good: 'ok', bad: 'bad' };

/** The seller's own workspace. It shows only this seller's products, orders and questions. */
export default function SellerCenter() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [edits, setEdits] = useState({});
  const [saved, setSaved] = useState('');
  const [params, setParams] = useSearchParams();

  const load = useCallback(() => api.get('/seller/overview').then((r) => { setData(r.data); setError(''); })
    .catch((e) => setError(e?.response?.status === 403 ? (e.response.data.detail || 'This area is for approved sellers.') : 'We could not load your seller centre.')), []);
  useEffect(() => { document.title = 'Seller centre | AutoCart'; load(); }, [load]);

  const edit = (id, k, v) => setEdits((e) => ({ ...e, [id]: { ...e[id], [k]: v } }));
  const save = async (p) => {
    const e = edits[p.id] || {};
    try {
      await api.patch(`/seller/products/${p.id}`, { ...(e.price !== undefined ? { price: e.price } : {}), ...(e.stock !== undefined ? { stock: e.stock } : {}) });
      setEdits((x) => { const n = { ...x }; delete n[p.id]; return n; });
      setSaved(`${p.name} updated.`); window.setTimeout(() => setSaved(''), 2500);
      load();
    } catch (err) { setSaved(err?.response?.data?.detail || 'That did not save.'); }
  };

  const cards = data && [
    { tab: 'products', icon: Boxes, big: data.productsCount, label: 'Products live', hint: `${data.outOfStock} out of stock`, tone: data.outOfStock ? 'warn' : '' },
    { tab: 'products', icon: AlertTriangle, big: data.lowStock, label: 'Almost gone', hint: 'Ten or fewer left', tone: data.lowStock ? 'warn' : '' },
    { tab: 'questions', icon: MessageCircleQuestion, big: data.openQuestions, label: 'Questions waiting', hint: 'Customers want an answer', tone: data.openQuestions ? 'warn' : '' },
    { tab: 'orders', icon: ClipboardList, big: data.ordersCount, label: 'Orders with your items', hint: `${count.format(data.unitsSold)} units sold`, tone: '' },
    { tab: 'orders', icon: IndianRupee, big: money(data.revenue), label: 'Your sales', hint: `${money(data.deliveredRevenue || 0)} delivered so far`, tone: '' },
  ];


  const TABS = data && [
    { key: 'overview', label: 'Overview', icon: LayoutDashboard },
    { key: 'products', label: 'Products', icon: Boxes, n: data.productsCount },
    { key: 'orders', label: 'Orders', icon: ClipboardList, n: data.orders.filter((o) => o.canPack).length },
    { key: 'questions', label: 'Questions', icon: MessageCircleQuestion, n: data.openQuestions },
    { key: 'store', label: 'Store & payouts', icon: Store },
  ];
  const tab = (TABS || []).find((t) => t.key === params.get('tab'))?.key || 'overview';
  const go = (key) => { setParams(key === 'overview' ? {} : { tab: key }, { replace: false }); window.scrollTo({ top: 0 }); };

  // A short checklist that ticks itself off, so a new seller always knows the next step.
  const steps = data && [
    { done: true, text: 'Your seller account is approved', sub: 'Your store is on the nearby-store map.' },
    { done: !!(data.profile?.lat != null && data.profile?.lng != null), text: 'Store location is on the map', sub: 'Customers find you by distance.', tab: 'store' },
    { done: data.productsCount > 0, text: 'Add your first product', sub: 'Name, price, units in stock and a photo.', tab: 'products', cta: 'Add a product' },
    { done: data.productsCount >= 5, text: 'List at least 5 products', sub: 'Stores with more choice get more orders.', tab: 'products' },
    { done: data.ordersCount > 0, text: 'Get your first order', sub: 'You are notified here, then you pack it.', tab: 'orders' },
  ];
  const doneCount = steps ? steps.filter((x) => x.done).length : 0;

  return (
    <div className="ac ac-seller">
      <header className="ac-sc-top">
        <div className="ac-wrap ac-row-between" style={{ paddingBlock: 14 }}>
          <div className="ac-row" style={{ gap: 18 }}><BrandLink size={30} /><span className="ac-chip-status" data-tone="info">Seller centre</span></div>
          <div className="ac-row">
            <span className="ac-muted" style={{ fontSize: 14 }}>{data?.company || user?.name}</span>
            <Link to="/" className="ac-btn ac-btn-outline ac-btn-small"><ExternalLink size={15} /> View the store</Link>
            <button className="ac-btn ac-btn-outline ac-btn-small" onClick={() => { logout(); navigate('/seller/login'); }}><LogOut size={15} /> Sign out</button>
          </div>
        </div>
      </header>

      <main className="ac-wrap" style={{ paddingBlock: 36 }}>
        <h1 className="ac-display" style={{ fontSize: 'clamp(32px, 4vw, 48px)' }}>{data ? `Hello, ${user?.name?.split(' ')[0]}` : 'Your seller centre'}</h1>
        {error && <div className="ac-box" role="alert" style={{ marginTop: 20, borderColor: 'var(--coral)' }}>{error}</div>}
        {!data && !error && <div className="ac-skel" style={{ height: 180, marginTop: 24 }} />}

        {data && (
          <>
            <div className="ac-sc-layout">
            <nav className="ac-sc-side" role="tablist" aria-label="Seller centre sections">
              {TABS.map((t) => (
                <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => go(t.key)}>
                  <t.icon size={18} /> <span>{t.label}</span>{t.n > 0 && <em>{t.n}</em>}
                </button>
              ))}
            </nav>
            <div className="ac-sc-main">

            {tab === 'overview' && (
              <>
                <section className="ac-sc-hero">
                  <div><h2>{data.productsCount ? 'Your store at a glance' : 'Let us stock your shelves'}</h2>
                    <p>{data.productsCount ? `${data.productsCount} products live · ${data.ordersCount} orders · ${money(data.revenue)} in sales.` : 'Add your first product in under a minute. It goes live in the store straight away, and you can change price and stock any time.'}</p></div>
                  <div className="ac-row" style={{ gap: 10, flexWrap: 'wrap' }}>
                    <button className="ac-btn ac-btn-blue" onClick={() => go('products')}><PackagePlus size={18} /> Add a product</button>
                    <button className="ac-btn ac-btn-outline" onClick={() => go('products')}><Boxes size={18} /> Update stock</button>
                    <button className="ac-btn ac-btn-outline" onClick={() => go('orders')}><ClipboardList size={18} /> Orders</button>
                  </div>
                </section>
                {data.products.filter((p) => p.stock <= 10).length > 0 && (
                  <section className="ac-box" aria-labelledby="rs-h" style={{ marginTop: 20 }}>
                    <h2 id="rs-h">Restock quickly</h2>
                    <p className="ac-muted" style={{ marginTop: 4 }}>These are almost gone. Add units in one tap.</p>
                    <div className="ac-restock">
                      {data.products.filter((p) => p.stock <= 10).slice(0, 6).map((p) => (
                        <div key={p.id}><span><b>{p.name}</b><small>{p.stock <= 0 ? 'Out of stock' : `${p.stock} left`}</small></span>
                          {[10, 25].map((n) => <button key={n} className="ac-btn ac-btn-soft ac-btn-small" onClick={async () => { try { await api.patch(`/seller/products/${p.id}`, { stock: p.stock + n }); setSaved(`${p.name}: +${n} units`); window.setTimeout(() => setSaved(''), 2500); load(); } catch { setSaved('That did not save.'); } }}>+{n}</button>)}
                        </div>
                      ))}
                    </div>
                    {saved && <p role="status" className="ac-muted">{saved}</p>}
                  </section>
                )}
                {doneCount < steps.length && (
                  <section className="ac-box ac-getstarted" aria-labelledby="gs-h">
                    <div className="ac-row-between"><h2 id="gs-h">Get your store going</h2><span className="ac-chip-status" data-tone="info">{doneCount} of {steps.length} done</span></div>
                    <div className="ac-gsbar" aria-hidden="true"><i style={{ width: `${(doneCount / steps.length) * 100}%` }} /></div>
                    <ul>{steps.map((x) => (
                      <li key={x.text} data-done={x.done}>
                        {x.done ? <Check size={18} /> : <Circle size={18} />}
                        <span><b>{x.text}</b><small>{x.sub}</small></span>
                        {!x.done && x.tab && <button className="ac-btn ac-btn-soft ac-btn-small" onClick={() => go(x.tab)}>{x.cta || 'Open'}</button>}
                      </li>))}
                    </ul>
                  </section>
                )}
                <div className="ac-bigcards">
                  {cards.map((c) => (
                    <button key={c.label} onClick={() => go(c.tab)} className="ac-bigcard" data-tone={c.tone}>
                      <c.icon size={26} /><b>{c.big}</b><span>{c.label}</span><small>{c.hint}</small>
                    </button>
                  ))}
                </div>
                <section className="ac-box" aria-labelledby="tips-h" style={{ marginTop: 24 }}>
                  <h2 id="tips-h">What to do next</h2>
                  <ul className="ac-tips">{data.tips.map((t) => <li key={t.text}><span className="ac-chip-status" data-tone={TONE[t.level]}>{t.level === 'good' ? 'All good' : t.level === 'warn' ? 'Needs you' : 'Heads up'}</span> {t.text}</li>)}</ul>
                  {data.productsCount === 0 && <button className="ac-btn ac-btn-blue" style={{ marginTop: 14 }} onClick={() => go('products')}><PackagePlus size={18} /> Add your first product</button>}
                </section>
                {data.productsCount > 0 && <SalesCharts data={data} />}
                
              </>
            )}

            {tab === 'products' && (
              <>
                <AddProduct onAdded={load} defaultOpen />
                <SellerProducts products={data.products} onChanged={load} />
              </>
            )}

            {tab === 'orders' && <SellerOrders orders={data.orders} onChange={load} />}

            {tab === 'store' && (
              <>
                <StoreProfile profile={data.profile} productsCount={data.productsCount} />
                <PayoutSettings />
                <HowItWorks />
              </>
            )}
            {tab === 'questions' && <div id="questions"><EnquiryInbox title="Questions about your products" allowDraft /></div>}
            </div>
            </div>
          </>
        )}

      </main>
      <MunimChat />
    </div>
  );
}
