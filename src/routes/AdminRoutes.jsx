import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import TabbedPage from '../admin/components/TabbedPage';
import SellersMonitor from '../pages/admin/SellersMonitor';
import AdminLayout from '../admin/components/AdminLayout';
import ProtectedRoute from '../components/layout/ProtectedRoute';

import Dashboard from '../pages/admin/Dashboard';
import Products from '../pages/admin/Products';
import AddProduct from '../pages/admin/AddProduct';
import EditProduct from '../pages/admin/EditProduct';
import Categories from '../pages/admin/Categories';
import Orders from '../pages/admin/Orders';
import OrderDetails from '../pages/admin/OrderDetails';
import Users from '../pages/admin/Users';
import Sellers from '../pages/admin/Sellers';
import Inventory from '../pages/admin/Inventory';
import Reviews from '../pages/admin/Reviews';
import Coupons from '../pages/admin/Coupons';
import Analytics from '../pages/admin/Analytics';
import SellerReports from '../pages/admin/SellerReports';
import Settings from '../pages/admin/Settings';
import SellerOnboardingAI from '../pages/admin/SellerOnboardingAI';
import SupportInbox from '../pages/admin/SupportInbox';
import Enquiries from '../pages/admin/Enquiries';
import Payments from '../pages/admin/Payments';

const Sellers_ = () => <TabbedPage title="Sellers" subtitle="Everyone who sells on AutoCart: where they are, what they list, what sells and what needs attention."
  tabs={[{ key: 'overview', label: 'Overview', Component: SellersMonitor }, { key: 'directory', label: 'Seller profiles', Component: Sellers },
    { key: 'applications', label: 'Seller onboarding', Component: SellerOnboardingAI }]} />;
const Orders_ = () => <TabbedPage title="Orders and payments" tabs={[{ key: 'orders', label: 'Orders', Component: Orders }, { key: 'payments', label: 'Payments', Component: Payments }]} />;
const Catalog_ = () => <TabbedPage title="Products" tabs={[{ key: 'products', label: 'All products', Component: Products }, { key: 'categories', label: 'Categories', Component: Categories },
  { key: 'stock', label: 'Stock levels', Component: Inventory }]} />;
const Support_ = () => <TabbedPage title="Customer care" tabs={[{ key: 'tickets', label: 'Support tickets', Component: SupportInbox }, { key: 'questions', label: 'Product questions', Component: Enquiries },
  { key: 'reviews', label: 'Reviews', Component: Reviews }]} />;
const Growth_ = () => <TabbedPage title="Reports and offers" tabs={[{ key: 'analytics', label: 'Sales reports', Component: Analytics }, { key: 'sellers', label: 'Seller reports', Component: SellerReports }, { key: 'coupons', label: 'Coupons', Component: Coupons }]} />;

export const AdminRoutes = () => {
  return (
    <ProtectedRoute requireAdmin={true}>
      <AdminLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sellers" element={<Sellers_ />} />
          <Route path="/orders" element={<Orders_ />} />
          <Route path="/orders/:id" element={<OrderDetails />} />
          <Route path="/products" element={<Catalog_ />} />
          <Route path="/products/add" element={<AddProduct />} />
          <Route path="/products/edit/:id" element={<EditProduct />} />
          <Route path="/users" element={<Users />} />
          <Route path="/support" element={<Support_ />} />
          <Route path="/reports" element={<Growth_ />} />
          <Route path="/settings" element={<Settings />} />
          {/* old addresses keep working */}
          <Route path="/ai-seller-onboarding" element={<Navigate to="/admin/sellers?tab=applications" replace />} />
          <Route path="/categories" element={<Navigate to="/admin/products?tab=categories" replace />} />
          <Route path="/inventory" element={<Navigate to="/admin/products?tab=stock" replace />} />
          <Route path="/payments" element={<Navigate to="/admin/orders?tab=payments" replace />} />
          <Route path="/enquiries" element={<Navigate to="/admin/support?tab=questions" replace />} />
          <Route path="/reviews" element={<Navigate to="/admin/support?tab=reviews" replace />} />
          <Route path="/analytics" element={<Navigate to="/admin/reports" replace />} />
          <Route path="/coupons" element={<Navigate to="/admin/reports?tab=coupons" replace />} />
        </Routes>
      </AdminLayout>
    </ProtectedRoute>
  );
};

export default AdminRoutes;
