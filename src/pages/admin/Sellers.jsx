import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Mail, Phone, Inbox, Boxes, ChevronRight, Store, ShieldCheck, Clock } from 'lucide-react';
import api from '../../services/api';
import adminService from '../../services/adminService';
import formatPrice from '../../utils/formatPrice';
import { downloadCsv } from '../../utils/csv';
import Loader from '../../components/common/Loader';
import { StatCard, Pill, ExportButton } from '../../admin/components/ui';
import SellerDetailModal from './SellerDetailModal';
import SellerDP from './SellerDP';

const FILTERS = [['', 'All sellers'], ['Pending', 'Waiting for approval']];  // only the two that matter
const TONE = { Approved: 'bg-green-100 text-green-800', Pending: 'bg-amber-100 text-amber-800', Suspended: 'bg-gray-200 text-gray-800', Rejected: 'bg-red-100 text-red-800' };

/** Seller profiles: every seller as a card (name and product total up front); open one for everything about them. Same layout as Seller onboarding. */
export const Sellers = () => {
  const [sellerList, setSellerList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState(null);
  const [params] = useSearchParams();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/admin/sellers-overview');  // live product counts, not the figures stored with each seller
        setSellerList(data.sellers.map((s) => ({ ...s, productsCount: s.products })));
      } catch { setSellerList(await adminService.getAllSellers()); } finally { setLoading(false); }
    })();
  }, []);

  const rows = useMemo(() => sellerList
    .filter((s) => !status || s.status === status)
    .filter((s) => `${s.name} ${s.companyName} ${s.city}`.toLowerCase().includes(search.trim().toLowerCase()))
    .sort((a, b) => b.productsCount - a.productsCount || a.name.localeCompare(b.name)), [sellerList, status, search]);

  const openSeller = (id) => setSelected(id);
  const close = useCallback(() => setSelected(null), []);

  // A link from elsewhere (?open=seller-1) opens that seller straight away.
  useEffect(() => {
    const wanted = params.get('open');
    if (wanted && sellerList.some((s) => s.id === wanted)) openSeller(wanted);
  }, [sellerList]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Loader fullScreen text="Loading sellers directory..." />;
  const count = (key) => (key ? sellerList.filter((s) => s.status === key).length : sellerList.length);
  const totalProducts = sellerList.reduce((n, s) => n + (s.productsCount || 0), 0);
  const inMumbai = sellerList.filter((s) => s.city === 'Mumbai').length;

  const exportCsv = () => downloadCsv('sellers', [
    ['Seller', (s) => s.name], ['Store / company', (s) => s.companyName], ['City', (s) => s.city], ['Status', (s) => s.status],
    ['Products listed', (s) => s.productsCount], ['Units sold', (s) => s.unitsSold], ['Item sales (INR)', (s) => s.revenue], ['Email', (s) => s.email], ['Phone', (s) => s.phone],
  ], rows);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" aria-label="Seller totals">
        <StatCard icon={Store} label="Sellers in Mumbai" value={inMumbai} hint={`${sellerList.length} sellers on AutoCart`} tone="indigo" />
        <StatCard icon={Boxes} label="Products listed" value={totalProducts.toLocaleString('en-IN')} hint="Across every seller" tone="indigo" />
        <StatCard icon={ShieldCheck} label="Approved" value={count('Approved')} hint="Selling now" tone="emerald" />
        <StatCard icon={Clock} label="Pending" value={count('Pending')} hint="Waiting for a decision" tone="amber" />
      </div>

      <div className="flex gap-2 flex-wrap items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {FILTERS.map(([key, name]) => <Pill key={key || 'all'} active={status === key} onClick={() => setStatus(key)}>{name} <span className="opacity-70">({count(key)})</span></Pill>)}
        </div>
        <ExportButton onClick={exportCsv} disabled={!rows.length} />
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" aria-hidden="true" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, store or city" aria-label="Search sellers" className="w-full pl-10 pr-3 py-2.5 rounded-xl bg-white border border-gray-200 text-sm shadow-sm" />
      </div>

      <div className="space-y-3" role="list" aria-label="Sellers">
        {rows.length === 0 && <div className="bg-white rounded-2xl border border-dashed border-gray-300 p-12 text-center text-sm text-gray-500"><Inbox className="w-9 h-9 mx-auto mb-2 text-gray-300" />No sellers match.</div>}
        {rows.map((s) => (
          <button key={s.id} role="listitem" onClick={() => openSeller(s.id)} aria-label={`Open ${s.name}, ${s.productsCount} products`}
            className="group w-full text-left bg-white rounded-2xl border border-gray-200 px-5 py-4 flex items-center gap-4 shadow-sm hover:shadow-md hover:border-indigo-300 hover:-translate-y-0.5 transition">
            <SellerDP name={s.name} size={56} />
            <div className="min-w-0 flex-1 basis-56">
              <b className="text-gray-900 text-lg block truncate">{s.name}</b>
              <div className="text-sm text-gray-500 truncate">{s.companyName} · {s.city || 'No city'}</div>
            </div>
            <div className="hidden md:block min-w-0 w-60 text-sm text-gray-600">
              {s.email && <div className="flex items-center gap-1.5 truncate"><Mail className="w-3.5 h-3.5 text-gray-400 shrink-0" />{s.email}</div>}
              {s.phone && <div className="flex items-center gap-1.5 mt-0.5"><Phone className="w-3.5 h-3.5 text-gray-400 shrink-0" />{s.phone}</div>}
            </div>
            <div className="flex flex-col items-center justify-center rounded-xl bg-indigo-50 border border-indigo-100 px-4 py-2 min-w-[92px]">
              <span className="text-2xl font-extrabold text-indigo-700 tabular-nums leading-none">{s.productsCount}</span>
              <span className="text-[11px] font-semibold text-indigo-600 mt-1">{s.productsCount === 1 ? 'product' : 'products'}</span>
            </div>
            <div className="hidden sm:flex flex-col items-start gap-1.5 w-28">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${TONE[s.status] || TONE.Pending}`}>{s.status}</span>
              {s.revenue > 0 && <span className="text-xs text-gray-500">{formatPrice(s.revenue)} sold</span>}
            </div>
            <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-indigo-600 shrink-0" aria-hidden="true" />
          </button>
        ))}
      </div>

      {selected && <SellerDetailModal id={selected} onClose={close} />}
    </div>
  );
};

export default Sellers;
