import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { Mail, Phone, MapPin, Boxes, IndianRupee, PackageCheck, AlertTriangle, ArrowLeft, X, Search, Layers, ShoppingBag } from 'lucide-react';
import api from '../../services/api';
import formatPrice from '../../utils/formatPrice';
import { downloadCsv } from '../../utils/csv';
import { StatCard, Panel, ExportButton, Pill } from '../../admin/components/ui';
import SellerProfileView from './SellerProfileView';
import SellerDP from './SellerDP';

const TONE = { Approved: 'bg-green-100 text-green-800', Pending: 'bg-amber-100 text-amber-800', Suspended: 'bg-gray-200 text-gray-800', Rejected: 'bg-red-100 text-red-800' };
const STOCK = { 'In stock': 'bg-emerald-100 text-emerald-800', 'Low stock': 'bg-amber-100 text-amber-800', 'Out of stock': 'bg-rose-100 text-rose-800' };

/** Product-by-product stock picture: totals, a health bar, then every product with its stock status and units sold. */
function ProductStatus({ d }) {
  const [filter, setFilter] = useState('');
  const [q, setQ] = useState('');
  const list = useMemo(() => d.products
    .filter((p) => !filter || p.status === filter)
    .filter((p) => `${p.name} ${p.category}`.toLowerCase().includes(q.trim().toLowerCase())), [d.products, filter, q]);
  const L = d.live;
  const total = L.products || 1;
  const exportCsv = () => downloadCsv(`${d.seller.name}-products`, [
    ['Product', (p) => p.name], ['Category', (p) => p.category], ['Price (INR)', (p) => p.price], ['In stock', (p) => p.stock], ['Stock status', (p) => p.status], ['Units sold', (p) => p.sold],
  ], d.products);

  return (
    <Panel title={`Products and stock (${L.products})`} subtitle="Every product this seller lists, with how much is left and how much has sold."
      action={<ExportButton onClick={exportCsv} disabled={!d.products.length} label="Products CSV" />}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <StatCard icon={Boxes} label="Products" value={L.products} />
        <StatCard icon={Layers} label="Units in stock" value={(L.stockUnits ?? 0).toLocaleString('en-IN')} />
        <StatCard icon={ShoppingBag} label="Units sold" value={L.units ?? 0} />
        <StatCard icon={AlertTriangle} label="Need restock" value={L.lowStock + L.outOfStock} hint={`${L.outOfStock} out, ${L.lowStock} low`} tone={L.outOfStock ? 'rose' : 'amber'} />
      </div>
      {L.products > 0 && (
        <div className="mb-4">
          <div className="flex h-2.5 rounded-full overflow-hidden bg-gray-100" role="img" aria-label={`${L.inStock} in stock, ${L.lowStock} low, ${L.outOfStock} out of stock`}>
            <div className="bg-emerald-500" style={{ width: `${(L.inStock / total) * 100}%` }} />
            <div className="bg-amber-400" style={{ width: `${(L.lowStock / total) * 100}%` }} />
            <div className="bg-rose-500" style={{ width: `${(L.outOfStock / total) * 100}%` }} />
          </div>
          <div className="flex gap-4 text-xs text-gray-500 mt-1.5">
            <span><i className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />{L.inStock} in stock</span>
            <span><i className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />{L.lowStock} low (10 or fewer)</span>
            <span><i className="inline-block w-2 h-2 rounded-full bg-rose-500 mr-1" />{L.outOfStock} out of stock</span>
          </div>
        </div>
      )}
      {d.products.length === 0 ? <p className="text-sm text-gray-500">This seller has not listed any products yet.</p> : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex gap-2 flex-wrap">
              <Pill active={!filter} onClick={() => setFilter('')}>All</Pill>
              <Pill active={filter === 'Low stock'} onClick={() => setFilter('Low stock')}>Low</Pill>
              <Pill active={filter === 'Out of stock'} onClick={() => setFilter('Out of stock')}>Out</Pill>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" aria-label="Search products" className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-200 text-sm" />
            </div>
          </div>
          <div className="overflow-auto max-h-96 rounded-xl border border-gray-100">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-xs font-bold uppercase text-gray-500 tracking-wider sticky top-0"><tr><th className="px-4 py-2.5 text-left">Product</th><th className="px-3 py-2.5 text-left">Category</th><th className="px-3 py-2.5 text-right">Price</th><th className="px-3 py-2.5 text-right">Stock</th><th className="px-3 py-2.5 text-left">Status</th><th className="px-3 py-2.5 text-right">Sold</th></tr></thead>
              <tbody className="divide-y divide-gray-100">
                {list.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No products match.</td></tr>}
                {list.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2"><div className="flex items-center gap-3 min-w-0">{p.image ? <img src={p.image} alt="" className="w-9 h-9 rounded-lg object-cover bg-gray-100 shrink-0" loading="lazy" /> : <span className="w-9 h-9 rounded-lg bg-gray-100 shrink-0" />}<span className="truncate max-w-[280px] font-medium text-gray-900">{p.name}</span></div></td>
                    <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{p.category}</td>
                    <td className="px-3 py-2 text-right tabular-nums whitespace-nowrap">{formatPrice(p.price)}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-semibold">{p.stock}</td>
                    <td className="px-3 py-2"><span className={`px-2.5 py-0.5 rounded-full text-xs font-bold whitespace-nowrap ${STOCK[p.status]}`}>{p.status}</span></td>
                    <td className="px-3 py-2 text-right tabular-nums">{p.sold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 mt-2">Showing {list.length} of {d.products.length}.</p>
        </>
      )}
    </Panel>
  );
}

/** One seller in full, as a full-screen page: who they are, live numbers, risk and documents, then product-by-product stock. */
export default function SellerDetailModal({ id, onClose }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let live = true;
    setD(null); setErr('');
    api.get(`/admin/sellers/${id}/detail`).then((r) => { if (live) setD(r.data); }).catch(() => { if (live) setErr('Could not open that seller.'); });
    return () => { live = false; };
  }, [id]);

  // Escape closes it and the page behind does not scroll.
  useEffect(() => {
    const esc = (e) => { if (e.key === 'Escape') onClose(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', esc);
    return () => { window.removeEventListener('keydown', esc); document.body.style.overflow = prev; };
  }, [onClose]);

  return createPortal(
    <div className="fixed inset-0 z-[90] bg-slate-50 overflow-y-auto" role="dialog" aria-modal="true" aria-label="Seller details">
      <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-5 py-3 flex items-center justify-between gap-3">
          <button onClick={onClose} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm font-semibold hover:bg-gray-50"><ArrowLeft className="w-4 h-4" /> Back</button>
          <b className="text-gray-900 truncate hidden sm:block">{d?.seller.name || 'Loading…'}</b>
          <button onClick={onClose} aria-label="Close" className="p-2 rounded-xl hover:bg-gray-100"><X className="w-5 h-5" /></button>
        </div>
      </div>
      <div className="max-w-5xl mx-auto p-5 space-y-4">
        {err && <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{err}</div>}
        {!d && !err && <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center text-gray-500">Loading…</div>}
        {d && (
          <>
            <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5" aria-label="Seller">
              <div className="flex flex-wrap items-center gap-5">
                <SellerDP name={d.seller.name} size={88} ring />
                <div className="min-w-0 flex-1 basis-64">
                  <div className="text-xs uppercase tracking-wide text-gray-400">Seller {d.seller.id}{d.seller.joinedDate ? ` · joined ${d.seller.joinedDate}` : ''}</div>
                  <h2 className="text-2xl font-extrabold text-gray-900 truncate">{d.seller.name}</h2>
                  <p className="text-sm text-gray-600">{d.seller.companyName}</p>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-700">
                    {d.seller.email && <span className="inline-flex items-center gap-1.5"><Mail className="w-4 h-4 text-gray-400" />{d.seller.email}</span>}
                    {d.seller.phone && <span className="inline-flex items-center gap-1.5"><Phone className="w-4 h-4 text-gray-400" />{d.seller.phone}</span>}
                    {d.seller.city && <span className="inline-flex items-center gap-1.5"><MapPin className="w-4 h-4 text-gray-400" />{d.seller.city}</span>}
                    {!d.seller.email && !d.seller.phone && <span className="text-gray-500">No contact details saved</span>}
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-bold self-start ${TONE[d.seller.status] || TONE.Pending}`}>{d.seller.status}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5" aria-label="Live numbers from real orders">
                <StatCard icon={Boxes} label="Products live" value={d.live.products} />
                <StatCard icon={PackageCheck} label="Orders" value={d.live.orders} hint="With their items" />
                <StatCard icon={IndianRupee} label="Item sales" value={formatPrice(d.live.revenue)} />
                <StatCard icon={IndianRupee} label="Commission" value={formatPrice(d.live.commission)} hint="Earned by AutoCart" />
              </div>
              <p className="text-xs text-gray-400 mt-3">All numbers are worked out from real orders.</p>
            </section>

            {d.application ? (
              <>
                <SellerProfileView p={d.application} showIdentity={false} />
                <p className="text-sm"><Link to="/admin/sellers?tab=applications" onClick={onClose} className="font-bold text-indigo-600 underline">Open in Seller onboarding to decide</Link></p>
              </>
            ) : (
              <section className="bg-white rounded-2xl border border-dashed border-gray-300 p-6 text-sm text-gray-600">
                No onboarding application is linked to this seller, so there are no Aadhaar, PAN or risk records to show. They were added directly.
              </section>
            )}

            <ProductStatus d={d} />
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
