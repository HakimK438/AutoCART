import React, { useState, useEffect, useMemo } from 'react';
import { Search, ShoppingBag, IndianRupee, TrendingUp, Truck, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import adminService from '../../services/adminService';
import OrdersTable from '../../admin/components/OrdersTable';
import Loader from '../../components/common/Loader';
import formatPrice from '../../utils/formatPrice';
import { downloadCsv } from '../../utils/csv';
import { StatCard, Panel, ExportButton, Pill } from '../../admin/components/ui';

const STATUSES = ['Pending', 'Confirmed', 'Processing', 'Shipped', 'Out for Delivery', 'Delivered', 'Cancelled'];
const BAR = { Pending: 'bg-amber-400', Confirmed: 'bg-sky-400', Processing: 'bg-blue-600', Shipped: 'bg-fuchsia-500', 'Out for Delivery': 'bg-teal-500', Delivered: 'bg-emerald-600', Cancelled: 'bg-rose-500' };  // one clearly different colour per stage
const REFRESH_MS = 30000;  // new orders appear on their own: nobody has to press refresh

export const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [updated, setUpdated] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = async (first) => {
      try {
        const data = await adminService.getAllOrders();
        if (alive) { setOrders(data); setUpdated(new Date()); }
      } finally { if (alive && first) setLoading(false); }
    };
    load(true);
    const timer = setInterval(() => load(false), REFRESH_MS);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  const stats = useMemo(() => {
    const live = orders.filter((o) => o.status !== 'Cancelled');
    const revenue = live.reduce((n, o) => n + (o.totalAmount || 0), 0);
    const by = Object.fromEntries(STATUSES.map((s) => [s, orders.filter((o) => o.status === s).length]));
    return {
      revenue, by, avg: live.length ? revenue / live.length : 0,
      inProgress: orders.filter((o) => ['Pending', 'Confirmed', 'Processing', 'Shipped', 'Out for Delivery'].includes(o.status)).length,
    };
  }, [orders]);

  const filtered = orders.filter((o) => {
    const q = search.toLowerCase();
    return (o.id.toLowerCase().includes(q) || (o.customerName || '').toLowerCase().includes(q)) && (statusFilter === 'All' || o.status === statusFilter);
  });

  const exportCsv = () => downloadCsv('orders', [
    ['Order ID', (o) => o.id], ['Customer', (o) => o.customerName], ['Phone', (o) => o.customerPhone], ['Date', (o) => o.date],
    ['Payment method', (o) => o.paymentMethod], ['Payment status', (o) => o.paymentStatus], ['Amount (INR)', (o) => o.totalAmount], ['Status', (o) => o.status],
  ], filtered);

  if (loading) return <Loader fullScreen text="Loading orders database..." />;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatCard icon={ShoppingBag} label="Total orders" value={orders.length} hint={`${stats.inProgress} in progress`} tone="indigo" />
        <StatCard icon={IndianRupee} label="Revenue" value={formatPrice(stats.revenue)} hint="Excludes cancelled" tone="indigo" />
        <StatCard icon={TrendingUp} label="Average order" value={formatPrice(Math.round(stats.avg))} hint="Per completed or active order" tone="indigo" />
        <StatCard icon={CheckCircle2} label="Delivered" value={stats.by.Delivered} hint={orders.length ? `${Math.round((stats.by.Delivered / orders.length) * 100)}% of all orders` : ''} tone="emerald" />
        <StatCard icon={XCircle} label="Cancelled" value={stats.by.Cancelled} hint={orders.length ? `${Math.round((stats.by.Cancelled / orders.length) * 100)}% of all orders` : ''} tone="rose" />
      </div>

      <Panel title="Where every order stands" subtitle="Click a stage to filter the list below."
        action={<span className="inline-flex items-center gap-1.5 text-xs text-gray-400"><RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> Updates itself every 30s{updated ? ` · ${updated.toLocaleTimeString()}` : ''}</span>}>
        {orders.length > 0 && (
          <div className="flex h-3 rounded-full overflow-hidden bg-gray-100 mb-4" role="img" aria-label="Orders by status">
            {STATUSES.filter((s) => stats.by[s]).map((s) => <div key={s} className={BAR[s]} style={{ width: `${(stats.by[s] / orders.length) * 100}%` }} title={`${s}: ${stats.by[s]}`} />)}
          </div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {STATUSES.map((s) => (
            <button key={s} onClick={() => setStatusFilter(statusFilter === s ? 'All' : s)} aria-pressed={statusFilter === s}
              className={`text-left rounded-xl border px-3 py-2 transition hover:border-indigo-300 ${statusFilter === s ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 bg-white'}`}>
              <span className="flex items-center gap-1.5 text-xs text-gray-500"><span className={`w-2 h-2 rounded-full ${BAR[s]}`} />{s}</span>
              <span className="text-xl font-extrabold text-gray-900 tabular-nums">{stats.by[s]}</span>
            </button>
          ))}
        </div>
      </Panel>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Pill active={statusFilter === 'All'} onClick={() => setStatusFilter('All')}>All ({orders.length})</Pill>
          <span className="text-sm text-gray-500 inline-flex items-center gap-1.5"><Truck className="w-4 h-4" aria-hidden="true" /> Showing {filtered.length}</span>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-80">
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by order ID or customer name..." aria-label="Search orders"
              className="w-full pl-9 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl bg-white shadow-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none" />
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" aria-hidden="true" />
          </div>
          <ExportButton onClick={exportCsv} disabled={!filtered.length} />
        </div>
      </div>

      <OrdersTable orders={filtered} />
    </div>
  );
};

export default Orders;
