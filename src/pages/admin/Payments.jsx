import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw, Wallet, Banknote, Smartphone, Store, QrCode, CreditCard, BadgeCheck, Hourglass, PieChart } from 'lucide-react';
import api from '../../services/api';
import adminService from '../../services/adminService';
import { downloadCsv } from '../../utils/csv';
import { StatCard, Panel, ExportButton } from '../../admin/components/ui';

const rupee = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const REFRESH_MS = 30000;  // the page keeps itself current: a UPI payment waiting for confirmation shows up without a refresh

// One look per way of paying: icon, colours and a plain explanation.
const METHOD = {
  'Cash on Delivery': { icon: Banknote, how: 'Customer pays cash when it arrives.' },
  'UPI or Card on Delivery': { icon: CreditCard, how: 'Customer pays by UPI or card when it arrives.' },
  'Pay at Store': { icon: Store, how: 'Customer pays at the store when collecting.' },
  'Razorpay (Test Mode)': { icon: CreditCard, how: 'Customer pays online (UPI, card or net banking) in test mode. Confirmed automatically once the signature checks out.' },
  'UPI (Scan & Pay)': { icon: QrCode, how: 'Customer pays the seller directly by UPI. The seller confirms the money arrived.' },
};
const FALLBACK = { icon: Smartphone, how: '' };
const PAY_TONE = { Paid: 'bg-emerald-100 text-emerald-800', Pending: 'bg-amber-100 text-amber-800', 'Awaiting Payment': 'bg-orange-100 text-orange-800', Failed: 'bg-rose-100 text-rose-800' };

/** How customers pay, money collected and still to collect, and UPI payments waiting for a seller to confirm. Online payments run through Razorpay in test mode. */
export default function Payments() {
  const [data, setData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');

  const load = useCallback(async () => {
    setBusy(true); setError('');
    try {
      setData((await api.get('/payments/status')).data);
      setOrders(await adminService.getAllOrders());
    } catch (e) { setError(e?.response?.status === 403 ? 'Only administrators can see this.' : 'Could not load payments.'); }
    setBusy(false);
  }, []);
  useEffect(() => { load(); const t = setInterval(load, REFRESH_MS); return () => clearInterval(t); }, [load]);

  const decide = async (orderId, action) => {
    setNote('');
    try { await api.post(`/orders/${orderId}/payment`, { action }); setNote(action === 'received' ? `Order ${orderId} marked as paid.` : `Order ${orderId} marked as not received.`); load(); }
    catch (e) { setNote(e?.response?.data?.detail || 'That did not work.'); }
  };

  const money = useMemo(() => {
    const live = orders.filter((o) => o.status !== 'Cancelled');
    const paid = live.filter((o) => o.paymentStatus === 'Paid');
    const sum = (list) => list.reduce((n, o) => n + (o.totalAmount || 0), 0);
    return { collected: sum(paid), toCollect: sum(live.filter((o) => o.paymentStatus !== 'Paid')), paidCount: paid.length, total: live.length, all: sum(live) };
  }, [orders]);

  const exportCsv = () => downloadCsv('payments', [
    ['Order ID', (o) => o.id], ['Customer', (o) => o.customerName], ['Date', (o) => o.date], ['Payment method', (o) => o.paymentMethod],
    ['Payment status', (o) => o.paymentStatus], ['Order status', (o) => o.status], ['Amount (INR)', (o) => o.totalAmount],
  ], orders);

  const totalOrders = (data?.methods || []).reduce((n, m) => n + m.orders, 0);
  const recent = orders.slice(0, 8);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <p className="text-gray-600 text-sm max-w-xl">Customers can pay online (Razorpay{data?.razorpay ? `, ${{ demo: 'local demo, no keys set', test: 'test keys', blocked: 'live keys blocked' }[data.razorpay.mode] || data.razorpay.mode}` : ''}), by UPI straight to the seller, on delivery, or at the store.{data?.razorpay?.connection ? ` ${data.razorpay.connection.message}` : ''}</p>
        <div className="flex gap-2">
          <button onClick={load} disabled={busy} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold hover:bg-gray-50"><RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /> Refresh</button>
          <ExportButton onClick={exportCsv} disabled={!orders.length} />
        </div>
      </div>
      {error && <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{error}</div>}
      {note && <div role="status" className="px-4 py-3 rounded-xl bg-green-50 text-green-800 text-sm font-semibold">{note}</div>}

      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard icon={BadgeCheck} label="Money collected" value={rupee.format(money.collected)} hint={`${money.paidCount} of ${money.total} orders paid`} tone="emerald" />
            <StatCard icon={Hourglass} label="Still to collect" value={rupee.format(money.toCollect)} hint="Cash on delivery and unconfirmed" tone="indigo" />
            <StatCard icon={Wallet} label="UPI to confirm" value={data.waiting.length} hint={data.waiting.length ? 'Waiting for the seller' : 'All confirmed'} tone="indigo" />
            <StatCard icon={PieChart} label="Order value" value={rupee.format(money.all)} hint="All active orders" tone="indigo" />
          </div>

          <Panel title="How customers are paying" subtitle="Share of orders, money received and what each method means.">
            {data.methods.length === 0 ? <p className="text-sm text-gray-500">No orders yet.</p> : (
              <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {data.methods.map((m) => {
                  const v = METHOD[m.method] || FALLBACK;
                  const share = totalOrders ? Math.round((m.orders / totalOrders) * 100) : 0;
                  const paidPct = m.orders ? Math.round((m.paid / m.orders) * 100) : 0;
                  return (
                    <div key={m.method} className="rounded-2xl border border-gray-200 bg-white p-5 hover:border-indigo-300 transition">
                      <div className="flex items-center gap-3">
                        <span className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600"><v.icon className="w-5 h-5" aria-hidden="true" /></span>
                        <div className="min-w-0"><div className="font-bold text-gray-900 leading-tight">{m.method}</div><div className="text-xs text-gray-400">{share}% of orders</div></div>
                      </div>
                      <div className="mt-4 flex items-baseline gap-2"><span className="text-3xl font-extrabold tabular-nums text-gray-900">{m.orders}</span><span className="text-sm text-gray-500">orders</span></div>
                      <div className="text-sm font-semibold text-gray-700">{rupee.format(m.amount)}</div>
                      <div className="mt-3 h-1.5 rounded-full bg-gray-100 overflow-hidden" role="img" aria-label={`${paidPct}% marked paid`}><div className="h-full rounded-full bg-indigo-600" style={{ width: `${paidPct}%` }} /></div>
                      <div className="flex justify-between text-xs mt-1.5 text-gray-500"><span>{m.paid} marked paid</span><span>{paidPct}%</span></div>
                      {v.how && <p className="text-xs text-gray-400 mt-3">{v.how}</p>}
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>

          <Panel title={`UPI payments waiting for confirmation (${data.waiting.length})`} subtitle="The seller normally confirms these. You can confirm too if the seller is away, after checking the reference in the seller's account.">
            {data.waiting.length === 0 ? <p className="text-sm text-gray-500">Nothing is waiting. New UPI payments appear here on their own.</p> : (
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-left text-gray-500"><th className="py-2 pr-4">Order</th><th className="pr-4">Customer</th><th className="pr-4">Seller</th><th className="pr-4">Amount</th><th className="pr-4">UPI reference</th><th /></tr></thead>
                <tbody>{data.waiting.map((w) => (
                  <tr key={w.orderId} className="border-t border-gray-100">
                    <td className="py-2 pr-4 font-semibold">{w.orderId}</td><td className="pr-4">{w.customer}</td><td className="pr-4">{w.seller}</td>
                    <td className="pr-4">{rupee.format(w.amount)}</td><td className="pr-4 font-mono">{w.utr}</td>
                    <td className="whitespace-nowrap">
                      <button onClick={() => decide(w.orderId, 'received')} className="px-3 py-1.5 rounded-lg bg-green-600 text-white font-semibold mr-2">Received</button>
                      <button onClick={() => decide(w.orderId, 'not_received')} className="px-3 py-1.5 rounded-lg border border-gray-300 font-semibold">Not received</button>
                    </td>
                  </tr>))}</tbody>
              </table></div>
            )}
          </Panel>

          <Panel title="Latest payments" subtitle="The most recent orders and where their payment stands. Download the CSV for the full list.">
            {recent.length === 0 ? <p className="text-sm text-gray-500">No orders yet.</p> : (
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-left text-gray-500"><th className="py-2 pr-4">Order</th><th className="pr-4">Customer</th><th className="pr-4">Method</th><th className="pr-4">Amount</th><th>Payment</th></tr></thead>
                <tbody>{recent.map((o) => (
                  <tr key={o.id} className="border-t border-gray-100">
                    <td className="py-2 pr-4 font-mono font-semibold text-indigo-600">{o.id}</td><td className="pr-4">{o.customerName}</td><td className="pr-4">{o.paymentMethod}</td>
                    <td className="pr-4 font-semibold">{rupee.format(o.totalAmount)}</td>
                    <td><span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${PAY_TONE[o.paymentStatus] || 'bg-gray-100 text-gray-700'}`}>{o.paymentStatus}</span></td>
                  </tr>))}</tbody>
              </table></div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
