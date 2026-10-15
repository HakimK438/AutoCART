import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle, RefreshCw, CreditCard } from 'lucide-react';
import api from '../../services/api';

const MODE = {
  demo: ['bg-amber-100 text-amber-800', 'Demo mode', 'No Razorpay keys are set, so checkout uses a local demo of the Razorpay flow. No request goes to Razorpay.'],
  test: ['bg-green-100 text-green-800', 'Razorpay test mode', 'Checkout opens Razorpay\'s own test window. No real money moves.'],
  blocked: ['bg-red-100 text-red-800', 'Live keys blocked', 'A live key (rzp_live_) was found. This app only runs in test mode, so online payments are switched off until you use test keys.'],
};
const rupee = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

export default function Payments() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setBusy(true); setError('');
    try { setData((await api.get('/payments/status')).data); }
    catch (e) { setError(e?.response?.status === 403 ? 'Only administrators can see this.' : 'Could not load payment status.'); }
    setBusy(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const mode = data ? MODE[data.mode] : null;
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Payments</h1>
          <p className="text-gray-600 text-sm mt-1">Razorpay test-mode checkout. Customers can also pay by cash on delivery or at the store.</p>
        </div>
        <button onClick={load} disabled={busy} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm font-semibold hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /> Check again
        </button>
      </div>
      {error && <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{error}</div>}

      {data && (
        <>
          <section className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 flex-wrap">
              <CreditCard className="w-6 h-6 text-indigo-600" />
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${mode[0]}`}>{mode[1]}</span>
              {data.keyIdHint && <span className="text-sm text-gray-500">Key {data.keyIdHint}</span>}
            </div>
            <p className="text-gray-700 mt-3">{mode[2]}</p>
            {data.connection && (
              <div className={`mt-4 flex items-start gap-3 rounded-xl p-4 ${data.connection.ok ? 'bg-green-50 text-green-900' : 'bg-red-50 text-red-900'}`} role="status">
                {data.connection.ok ? <CheckCircle2 className="w-5 h-5 mt-0.5" /> : <AlertTriangle className="w-5 h-5 mt-0.5" />}
                <div><b>{data.connection.ok ? 'Connected to Razorpay' : 'Not connected'}</b><div className="text-sm">{data.connection.message}</div></div>
              </div>
            )}
          </section>

          {data.mode !== 'test' && (
            <section className="bg-white rounded-2xl border border-gray-200 p-6">
              <h2 className="font-bold text-gray-900">Switch to the real Razorpay test checkout</h2>
              <ol className="mt-3 space-y-2 text-sm text-gray-700 list-decimal pl-5">
                <li>Create a free account at razorpay.com and switch the dashboard to <b>Test mode</b>.</li>
                <li>Open <b>Account and Settings, then API Keys</b>, and generate a key pair. Copy the Key ID (starts with <code>rzp_test_</code>) and the Secret.</li>
                <li>Add them to the <code>.env</code> file in the project folder:
                  <pre className="mt-2 bg-gray-900 text-gray-100 rounded-xl p-3 overflow-x-auto text-xs">{`RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx\nRAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx`}</pre></li>
                <li>Restart the backend, then press <b>Check again</b> here. It should say "Connected to Razorpay".</li>
              </ol>
              <p className="text-xs text-gray-500 mt-3">Keep the secret out of the code and out of screenshots. Test payments use Razorpay's test cards and UPI ids, for example card 4111 1111 1111 1111.</p>
            </section>
          )}

          <section className="bg-white rounded-2xl border border-gray-200 p-6">
            <h2 className="font-bold text-gray-900 mb-3">Recent payments</h2>
            {data.recent.length === 0 ? <p className="text-sm text-gray-500">No online payments yet. They appear here when a customer pays with Razorpay.</p> : (
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-left text-gray-500"><th className="py-2 pr-4">Order</th><th className="pr-4">Amount</th><th className="pr-4">Status</th><th className="pr-4">Mode</th><th>When</th></tr></thead>
                <tbody>{data.recent.map((p) => (
                  <tr key={p.id} className="border-t border-gray-100">
                    <td className="py-2 pr-4 font-medium">{p.orderId}</td><td className="pr-4">{rupee.format(p.amount)}</td>
                    <td className="pr-4"><span className={`px-2 py-0.5 rounded-full text-xs font-bold ${p.status === 'PAID' ? 'bg-green-100 text-green-800' : p.status === 'FAILED' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-700'}`}>{p.status}</span></td>
                    <td className="pr-4">{p.provider === 'razorpay' ? 'Razorpay test' : 'Demo'}</td><td>{new Date(p.createdAt).toLocaleString()}</td>
                  </tr>))}</tbody></table></div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
