import React, { useState, useEffect } from 'react';
import adminService from '../../services/adminService';
import Badge from '../../components/common/Badge';
import formatPrice from '../../utils/formatPrice';
import formatDate from '../../utils/formatDate';
import Loader from '../../components/common/Loader';
import { Search, Store } from 'lucide-react';

export const Sellers = () => {
  const [sellerList, setSellerList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchSellers = async () => {
      setLoading(true);
      try {
        const data = await adminService.getAllSellers();
        setSellerList(data);
      } finally {
        setLoading(false);
      }
    };
    fetchSellers();
  }, []);

  const toggleApproval = (id) => {
    setSellerList((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: s.status === 'Approved' ? 'Pending' : 'Approved' } : s))
    );
  };

  const filtered = sellerList.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.companyName.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <Loader fullScreen text="Loading sellers directory..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Seller Management</h1>
        <p className="text-xs text-gray-500 mt-0.5">Manage multi-vendor partner accounts and store performance</p>
      </div>

      <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
        <div className="relative w-full sm:w-80">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sellers by store name..."
            className="w-full pl-9 pr-4 py-2 text-xs border rounded-lg focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          />
          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-gray-400" />
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
          <thead className="bg-gray-50 font-bold uppercase text-gray-500 tracking-wider">
            <tr>
              <th className="px-4 py-3">Store / Company</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Products</th>
              <th className="px-4 py-3">Orders</th>
              <th className="px-4 py-3">Gross Revenue</th>
              <th className="px-4 py-3">Rating</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 font-medium text-gray-700">
            {filtered.map((sel) => (
              <tr key={sel.id} className="hover:bg-gray-50 transition">
                <td className="px-4 py-3">
                  <p className="font-bold text-gray-900 flex items-center gap-1.5">
                    <Store className="w-3.5 h-3.5 text-indigo-600" /> {sel.name}
                  </p>
                  <p className="text-[10px] text-gray-400">{sel.companyName}</p>
                </td>
                <td className="px-4 py-3">{sel.city}</td>
                <td className="px-4 py-3 font-bold">{sel.productsCount} Items</td>
                <td className="px-4 py-3 font-bold">{sel.ordersCount} Orders</td>
                <td className="px-4 py-3 font-extrabold text-gray-900">{formatPrice(sel.totalRevenue)}</td>
                <td className="px-4 py-3 font-bold text-amber-500">★ {sel.rating}</td>
                <td className="px-4 py-3">
                  <Badge variant={sel.status === 'Approved' ? 'green' : 'yellow'}>{sel.status}</Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => toggleApproval(sel.id)}
                    className="text-xs font-bold text-indigo-600 hover:underline"
                  >
                    {sel.status === 'Approved' ? 'Suspend' : 'Approve'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Sellers;
