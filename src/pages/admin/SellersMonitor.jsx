import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Store, MapPin, Phone, AlertTriangle, ClipboardCheck, PackageCheck, IndianRupee, Boxes } from 'lucide-react';
import api from '../../services/api';
import formatPrice from '../../utils/formatPrice';
import Loader from '../../components/common/Loader';
import StoreMap from '../../storefront/StoreMap';
import SellerDetailModal from './SellerDetailModal';

const MUMBAI = [19.076, 72.8777];  // the map opens on Mumbai; zoom and drag still work everywhere

const Tile = ({ icon: Icon, n, label, tone, to }) => {
  const body = (
    <div className={`rounded-2xl border p-4 flex items-center gap-3 bg-white ${tone === 'warn' ? 'border-amber-300' : 'border-gray-200'}`}>
      <span className={`w-10 h-10 rounded-xl grid place-items-center ${tone === 'warn' ? 'bg-amber-100 text-amber-700' : 'bg-indigo-50 text-indigo-700'}`}><Icon className="w-5 h-5" /></span>
      <div><div className="text-2xl font-extrabold tabular-nums text-gray-900">{n}</div><div className="text-xs text-gray-500">{label}</div></div>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
};

/** Every seller at a glance: who they are, where they are, how many products, what is selling and what needs attention. */
export default function SellersMonitor() {
  const [data, setData] = useState(null);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(null);
  const [profile, setProfile] = useState(null);  // the seller whose full profile is open
  const [error, setError] = useState('');

  useEffect(() => { api.get('/admin/sellers-overview').then((r) => setData(r.data)).catch(() => setError('Could not load sellers.')); }, []);
  const rows = useMemo(() => (data?.sellers || []).filter((s) => `${s.companyName} ${s.name} ${s.city} ${s.phone}`.toLowerCase().includes(q.toLowerCase())), [data, q]);
  const mapStores = useMemo(() => rows.filter((s) => s.lat != null).map((s) => ({ storeId: s.id, storeName: s.companyName, address: s.address || s.city, latitude: s.lat, longitude: s.lng })), [rows]);

  if (error) return <div role="alert" className="px-4 py-3 rounded-xl bg-red-50 text-red-800 text-sm">{error}</div>;
  if (!data) return <Loader text="Loading sellers..." />;
  const t = data.totals;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Tile icon={Store} n={t.sellers} label="Active sellers" />
        <Tile icon={Boxes} n={t.products} label="Products listed" />
        <Tile icon={IndianRupee} n={formatPrice(t.revenue)} label="Sales through sellers" />
        <Tile icon={PackageCheck} n={t.ordersToPack} label="Orders waiting to be packed" tone={t.ordersToPack ? 'warn' : ''} />
        <Tile icon={ClipboardCheck} n={t.pendingApplications + t.stillFilling} label={`Applications (${t.pendingApplications} to review)`} tone={t.pendingApplications ? 'warn' : ''} to="/admin/sellers?tab=applications" />
      </div>

      {mapStores.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-white p-4" aria-label="Seller locations">
          <h2 className="font-bold text-gray-900 mb-2 flex items-center gap-2"><MapPin className="w-4 h-4" /> Where your sellers are</h2>
          <StoreMap stores={mapStores} height={400} selectedId={open?.id} center={MUMBAI} zoom={11} fitAll={false} />
        </section>
      )}

      <div className="relative w-full sm:w-96">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by store, owner, city or phone..." aria-label="Search sellers" className="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:ring-1 focus:ring-indigo-500 focus:outline-none" />
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
          <thead className="bg-gray-50 font-bold uppercase text-gray-500 tracking-wider text-xs">
            <tr><th className="px-4 py-3">Seller</th><th className="px-4 py-3">Contact</th><th className="px-4 py-3">Products</th><th className="px-4 py-3">Units sold</th><th className="px-4 py-3">Sales</th><th className="px-4 py-3">Needs attention</th></tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-700">
            {rows.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No sellers match.</td></tr>}
            {rows.map((s) => (
              <tr key={s.id} tabIndex={0} role="button" onClick={() => { setOpen(s); setProfile(s.id); }} className="hover:bg-indigo-50 cursor-pointer" onMouseEnter={() => setOpen(s)}>
                <td className="px-4 py-3"><p className="font-bold text-gray-900">{s.companyName}</p><p className="text-xs text-gray-500 flex items-center gap-1"><MapPin className="w-3 h-3" /> {s.city || 'No city'}{s.lat == null && ' · no map pin'}</p></td>
                <td className="px-4 py-3 text-xs"><div>{s.name}</div>{s.phone && <div className="flex items-center gap-1"><Phone className="w-3 h-3" /> {s.phone}</div>}</td>
                <td className="px-4 py-3 font-bold">{s.products}</td>
                <td className="px-4 py-3 font-bold">{s.unitsSold}</td>
                <td className="px-4 py-3 font-bold text-gray-900">{formatPrice(s.revenue)}</td>
                <td className="px-4 py-3 space-x-1">
                  {s.ordersToPack > 0 && <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">{s.ordersToPack} to pack</span>}
                  {s.outOfStock > 0 && <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800">{s.outOfStock} out of stock</span>}
                  {s.lowStock > 0 && <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-800"><AlertTriangle className="inline w-3 h-3" /> {s.lowStock} low</span>}
                  {!s.ordersToPack && !s.outOfStock && !s.lowStock && <span className="text-xs text-green-700 font-semibold">All good</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Click a seller to open their full profile, documents and product stock.</p>
      {profile && <SellerDetailModal id={profile} onClose={() => setProfile(null)} />}
    </div>
  );
}

