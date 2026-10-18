import React, { useState, useEffect, useMemo } from 'react';
import { Search, Users as UsersIcon, UserCheck, IndianRupee, Repeat, Crown, Mail, Phone } from 'lucide-react';
import adminService from '../../services/adminService';
import formatPrice from '../../utils/formatPrice';
import formatDate from '../../utils/formatDate';
import { downloadCsv } from '../../utils/csv';
import Loader from '../../components/common/Loader';
import { StatCard, Panel, ExportButton, Pill } from '../../admin/components/ui';

const ROLE_TONE = { CUSTOMER: 'bg-indigo-50 text-indigo-700', SELLER: 'bg-gray-100 text-gray-700', ADMIN: 'bg-gray-900 text-white', STAFF: 'bg-gray-100 text-gray-700' };
const initials = (n) => String(n || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';

const Avatar = ({ name, size = 40 }) => (
  <span className={`rounded-full bg-indigo-50 text-indigo-700 font-extrabold flex items-center justify-center shrink-0`} style={{ width: size, height: size, fontSize: size * 0.38 }} aria-hidden="true">{initials(name)}</span>
);

export const Users = () => {
  const [userList, setUserList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');

  useEffect(() => {
    (async () => {
      try { setUserList(await adminService.getAllUsers()); } finally { setLoading(false); }
    })();
  }, []);

  const toggleStatus = (id) => setUserList((prev) => prev.map((u) => (u.id === id ? { ...u, status: u.status === 'Active' ? 'Inactive' : 'Active' } : u)));

  const roles = useMemo(() => [...new Set(userList.map((u) => u.role))].filter(Boolean), [userList]);
  const filtered = userList.filter((u) => (!role || u.role === role)
    && `${u.name} ${u.email}`.toLowerCase().includes(search.trim().toLowerCase()));

  const stats = useMemo(() => {
    const spend = userList.reduce((n, u) => n + (u.totalSpent || 0), 0);
    const buyers = userList.filter((u) => (u.ordersCount || 0) > 0);
    return {
      spend, buyers: buyers.length, repeat: userList.filter((u) => (u.ordersCount || 0) > 1).length,
      active: userList.filter((u) => u.status === 'Active').length, avg: buyers.length ? spend / buyers.length : 0,
      top: [...userList].filter((u) => (u.totalSpent || 0) > 0).sort((a, b) => b.totalSpent - a.totalSpent).slice(0, 3),
    };
  }, [userList]);

  const exportCsv = () => downloadCsv('customers', [
    ['Name', (u) => u.name], ['Email', (u) => u.email], ['Phone', (u) => u.phone], ['Role', (u) => u.role], ['Orders', (u) => u.ordersCount],
    ['Total spent (INR)', (u) => u.totalSpent], ['Joined', (u) => u.joinedDate], ['Status', (u) => u.status],
  ], filtered);

  if (loading) return <Loader fullScreen text="Loading user directory..." />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Customers</h1>
        <p className="text-sm text-gray-500 mt-0.5">Everyone with an account: who buys, how often and how much.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard icon={UsersIcon} label="Accounts" value={userList.length} hint={`${stats.active} active`} tone="indigo" />
        <StatCard icon={UserCheck} label="Have ordered" value={stats.buyers} hint={`${stats.repeat} came back for more`} tone="indigo" />
        <StatCard icon={IndianRupee} label="Lifetime spend" value={formatPrice(stats.spend)} hint="All customers together" tone="indigo" />
        <StatCard icon={Repeat} label="Average per buyer" value={formatPrice(Math.round(stats.avg))} hint="Among customers who ordered" tone="indigo" />
      </div>

      {stats.top.length > 0 && (
        <Panel title="Top customers" subtitle="Highest lifetime spend.">
          <div className="grid sm:grid-cols-3 gap-3">
            {stats.top.map((u, i) => (
              <div key={u.id} className="relative flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4">
                <Avatar name={u.name} size={48} />
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-gray-900 truncate">{u.name}</div>
                  <div className="text-xs text-gray-500">{u.ordersCount} orders</div>
                  <div className="font-extrabold text-indigo-700 tabular-nums">{formatPrice(u.totalSpent)}</div>
                </div>
                {i === 0 && <Crown className="w-5 h-5 text-amber-500 absolute top-3 right-3" aria-label="Top customer" />}
              </div>
            ))}
          </div>
        </Panel>
      )}

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex gap-2 flex-wrap">
          <Pill active={!role} onClick={() => setRole('')}>All ({userList.length})</Pill>
          {roles.map((r) => <Pill key={r} active={role === r} onClick={() => setRole(r)}>{r.charAt(0) + r.slice(1).toLowerCase()} ({userList.filter((u) => u.role === r).length})</Pill>)}
        </div>
        <div className="flex items-center gap-3">
          <div className="relative flex-1 lg:w-80">
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or email..." aria-label="Search customers"
              className="w-full pl-9 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl bg-white shadow-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none" />
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" aria-hidden="true" />
          </div>
          <ExportButton onClick={exportCsv} disabled={!filtered.length} />
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-100 text-left text-sm">
          <thead className="bg-gray-50 text-xs font-bold uppercase text-gray-500 tracking-wider">
            <tr><th className="px-5 py-3">Customer</th><th className="px-4 py-3">Contact</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Orders</th><th className="px-4 py-3">Total spent</th><th className="px-4 py-3">Joined</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-700">
            {filtered.length === 0 && <tr><td colSpan={8} className="px-5 py-10 text-center text-gray-500">No customers match.</td></tr>}
            {filtered.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50 transition">
                <td className="px-5 py-3"><div className="flex items-center gap-3"><Avatar name={u.name} /><div className="min-w-0"><p className="font-bold text-gray-900 truncate">{u.name}</p><p className="text-xs text-gray-400 truncate">{u.id}</p></div></div></td>
                <td className="px-4 py-3 text-xs text-gray-600"><div className="flex items-center gap-1.5"><Mail className="w-3 h-3 text-gray-400" aria-hidden="true" />{u.email}</div><div className="flex items-center gap-1.5 mt-0.5"><Phone className="w-3 h-3 text-gray-400" aria-hidden="true" />{u.phone || 'N/A'}</div></td>
                <td className="px-4 py-3"><span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${ROLE_TONE[u.role] || 'bg-gray-100 text-gray-700'}`}>{u.role}</span></td>
                <td className="px-4 py-3 font-bold tabular-nums">{u.ordersCount}</td>
                <td className="px-4 py-3 font-extrabold text-gray-900 tabular-nums">{formatPrice(u.totalSpent)}</td>
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(u.joinedDate)}</td>
                <td className="px-4 py-3"><span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${u.status === 'Active' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>{u.status}</span></td>
                <td className="px-4 py-3 text-right"><button onClick={() => toggleStatus(u.id)} className="text-xs font-bold text-indigo-600 hover:underline">{u.status === 'Active' ? 'Deactivate' : 'Activate'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Users;
