import React, { useEffect, useMemo, useState } from 'react';
import { TrendingUp, IndianRupee, ShoppingBag, Users, AlertTriangle, Info } from 'lucide-react';
import api from '../../services/api';
import formatPrice from '../../utils/formatPrice';
import SellerDP from './SellerDP';

const Tile = ({ icon: Icon, label, value, sub }) => (
  <div className="rounded-2xl border border-gray-200 bg-white p-4">
    <div className="flex items-center gap-2 text-xs text-gray-500"><Icon className="w-4 h-4" aria-hidden="true" />{label}</div>
    <div className="text-2xl font-extrabold tabular-nums text-gray-900 mt-1">{value}</div>
    {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
  </div>
);

/** A tiny 30-day line of sales. The label gives the same facts in words for screen readers. */
const Spark = ({ data, label }) => {
  const max = Math.max(...data, 1);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${28 - (v / max) * 26}`).join(' ');
  return (
    <svg viewBox="0 0 100 30" className="w-28 h-8" role="img" aria-label={label} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={max > 1 ? '#4f46e5' : '#d1d5db'} strokeWidth="1.8" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
};

const SORTS = { revenue: 'Sales', orders: 'Orders', commission: 'Commission', products: 'Products' };

/** Seller reports: who sells, how much, what AutoCart earns, and who needs attention. Everything comes from real orders. */
export default function SellerReports() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [sort, setSort] = useState('revenue');
  useEffect(() => { api.get('/admin/seller-report').then((r) => setData(r.data)).catch(() => setError('Could not load the seller report.')); }, []);
  const rows = useMemo(() => (data ? [...data.sellers].sort((a, b) => b[sort] - a[sort]) : []), [data, sort]);
  if (error) return <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{error}</div>;
  if (!data) return <div className="p-10 text-center text-gray-500">Building the report...</div>;
  const t = data.totals;
  const best = Math.max(...rows.map((r) => r.revenue), 1);

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-600">Numbers are worked out from real orders in the last 30 days of trend, and all time for totals. Cancelled orders are not counted as sales.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Tile icon={IndianRupee} label="Seller sales" value={formatPrice(t.revenue)} sub={`${t.orders} orders`} />
        <Tile icon={TrendingUp} label="AutoCart commission" value={formatPrice(t.commission)} sub={t.revenue ? `${Math.round((100 * t.commission) / t.revenue)}% of sales` : ''} />
        <Tile icon={Users} label="Sellers with sales" value={`${t.sellersWithSales} of ${t.sellers}`} />
        <Tile icon={ShoppingBag} label="Average order" value={t.orders ? formatPrice(Math.round(t.revenue / t.orders)) : '-'} />
      </div>

      {data.insights.length > 0 && (
        <section aria-label="What stands out" className="rounded-2xl border border-gray-200 bg-white p-4">
          <h3 className="font-bold text-gray-900 mb-2">What stands out</h3>
          <ul className="space-y-1.5">{data.insights.map((i, k) => (
            <li key={k} className="flex gap-2 text-sm text-gray-700">{i.level === 'warn' ? <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" /> : <Info className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />}<span>{i.text}</span></li>))}</ul>
        </section>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white overflow-hidden" aria-label="Seller leaderboard">
        <div className="p-4 flex flex-wrap items-center justify-between gap-3 border-b border-gray-100">
          <h3 className="font-bold text-gray-900">Seller leaderboard</h3>
          <div className="flex gap-1.5 flex-wrap" role="group" aria-label="Sort by">{Object.entries(SORTS).map(([k, name]) => (
            <button key={k} onClick={() => setSort(k)} aria-pressed={sort === k} className={`px-3 py-1 rounded-full text-xs font-semibold border ${sort === k ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200'}`}>{name}</button>))}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left">
            <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr><th className="px-4 py-3">Seller</th><th className="px-4 py-3 min-w-[170px]">Sales</th><th className="px-4 py-3">Orders</th><th className="px-4 py-3">Commission</th><th className="px-4 py-3">Delivered</th><th className="px-4 py-3">Stock</th><th className="px-4 py-3">Last 30 days</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="px-4 py-3"><div className="flex items-center gap-3"><SellerDP name={r.name} size={38} />
                    <div className="min-w-0"><b className="text-gray-900 block truncate max-w-[220px]">{r.name}</b><span className="text-xs text-gray-500">{r.city || 'No city'} · {r.status}{r.topProduct ? ` · top: ${r.topProduct.slice(0, 26)}` : ''}</span></div></div></td>
                  <td className="px-4 py-3"><div className="font-bold tabular-nums">{formatPrice(r.revenue)}</div>
                    <div className="h-1.5 rounded-full bg-gray-100 mt-1.5 overflow-hidden" aria-hidden="true"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${(r.revenue / best) * 100}%` }} /></div></td>
                  <td className="px-4 py-3 tabular-nums">{r.orders}</td>
                  <td className="px-4 py-3 tabular-nums">{formatPrice(r.commission)}</td>
                  <td className="px-4 py-3">{r.deliveredPercent == null ? <span className="text-gray-400">No orders</span> : <span className={r.deliveredPercent < 50 ? 'text-amber-700 font-semibold' : ''}>{r.deliveredPercent}%</span>}{r.cancelled > 0 && <span className="block text-xs text-gray-500">{r.cancelled} cancelled</span>}</td>
                  <td className="px-4 py-3 text-xs">{r.products} listed{r.outOfStock > 0 && <span className="block text-red-600 font-semibold">{r.outOfStock} out</span>}{r.lowStock > 0 && <span className="block text-amber-700">{r.lowStock} low</span>}</td>
                  <td className="px-4 py-3"><Spark data={r.trend} label={`${r.name}: ${formatPrice(r.trend.reduce((a, b) => a + b, 0))} in the last 30 days`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
