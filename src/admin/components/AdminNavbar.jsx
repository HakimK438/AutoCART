import React, { useState, useRef, useEffect } from 'react';
import { Menu, Bell, Search, Sparkles, AlertTriangle, AlertCircle, ShoppingBag, CheckCheck, Trash2, X, ChevronRight } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const INITIAL_NOTIFICATIONS = [
  {
    id: 'notif-1',
    type: 'critical',
    title: 'High-Risk Seller Flagged (Score: 85/100)',
    message: 'Direct Import Hub: Missing legal business name, verified email, and GSTIN tax credentials.',
    time: '10m ago',
    unread: true,
    link: '/admin/ai-seller-onboarding',
    actionText: 'Review in Agent C',
  },
  {
    id: 'notif-2',
    type: 'critical',
    title: 'Offshore Vendor Compliance Warning',
    message: 'Shadow Dropship Express: Disposable email domain (mailcatch.xyz) and unverified offshore address.',
    time: '35m ago',
    unread: true,
    link: '/admin/ai-seller-onboarding',
    actionText: 'Inspect Application',
  },
  {
    id: 'notif-3',
    type: 'warning',
    title: 'Low Stock Inventory Alert',
    message: '3 catalog products are running critically low (Milton Thermosteel, Boldfit Sipper).',
    time: '1h ago',
    unread: true,
    link: '/admin/products',
    actionText: 'Manage Inventory',
  },
  {
    id: 'notif-4',
    type: 'info',
    title: 'New Customer Order #ORD-2026-9042',
    message: 'Verified order for ₹3,499 received from customer via Cash on Delivery.',
    time: '2h ago',
    unread: false,
    link: '/admin/orders',
    actionText: 'View Order',
  },
];

export const AdminNavbar = ({ onToggleSidebar }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const [filter, setFilter] = useState('all'); // 'all' | 'unread'
  const dropdownRef = useRef(null);

  const unreadCount = notifications.filter(n => n.unread).length;

  // Close dropdown on outside click or Esc key
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setNotificationsOpen(false);
      }
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setNotificationsOpen(false);
      }
    };

    if (notificationsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [notificationsOpen]);

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
  };

  const markAsRead = (id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, unread: false } : n));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  const handleNotificationClick = (item) => {
    markAsRead(item.id);
    setNotificationsOpen(false);
    if (item.link) {
      navigate(item.link);
    }
  };

  const displayedNotifications = filter === 'unread'
    ? notifications.filter(n => n.unread)
    : notifications;

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-gray-200 h-16 flex items-center justify-between px-4 sm:px-8 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 text-indigo-700 text-[10px] font-extrabold border border-indigo-100">
          <Sparkles className="w-3 h-3" /> AI Marketplace Operations
        </div>
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition"
          aria-label="Toggle Navigation Sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Admin Search Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const term = e.currentTarget.elements.adminSearch.value.trim();
            if (term) {
              navigate(`/admin/products?search=${encodeURIComponent(term)}`);
            }
          }}
          className="relative hidden sm:block w-72"
        >
          <input
            name="adminSearch"
            type="text"
            placeholder="Search products, brands, orders (Press Enter)..."
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-gray-100 border border-gray-200 rounded-full focus:bg-white focus:border-indigo-500 focus:outline-none transition shadow-xs"
          />
          <Search className="absolute left-3 top-2 w-3.5 h-3.5 text-gray-400" />
        </form>
      </div>

      {/* Admin Profile & Notifications */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Interactive Notification Bell */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setNotificationsOpen(prev => !prev)}
            className={`relative p-2 rounded-full transition ${
              notificationsOpen
                ? 'bg-indigo-50 text-indigo-600 ring-2 ring-indigo-500/20'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
            }`}
            title="Marketplace Notifications"
            aria-label="Open notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-extrabold flex items-center justify-center shadow-sm animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notification Dropdown Panel */}
          {notificationsOpen && (
            <div className="absolute right-0 mt-3 w-80 sm:w-96 bg-white rounded-2xl shadow-2xl border border-gray-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
              {/* Header */}
              <div className="p-4 border-b border-gray-100 bg-gray-50/70 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-extrabold text-sm text-gray-900">Admin Alerts</h3>
                    {unreadCount > 0 && (
                      <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 text-[10px] font-extrabold">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">Real-time marketplace monitoring</p>
                </div>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-white rounded-lg transition"
                      title="Mark all as read"
                    >
                      <CheckCheck className="w-4 h-4" />
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      onClick={clearAllNotifications}
                      className="p-1.5 text-gray-400 hover:text-rose-600 hover:bg-white rounded-lg transition"
                      title="Clear notifications"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => setNotificationsOpen(false)}
                    className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-white rounded-lg transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Filter tabs */}
              <div className="flex items-center px-4 py-2 border-b border-gray-100 bg-white gap-2 text-xs">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    filter === 'all'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  All ({notifications.length})
                </button>
                <button
                  onClick={() => setFilter('unread')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    filter === 'unread'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Unread ({unreadCount})
                </button>
              </div>

              {/* List */}
              <div className="max-h-[360px] overflow-y-auto divide-y divide-gray-100">
                {displayedNotifications.length === 0 ? (
                  <div className="py-12 px-4 text-center">
                    <Bell className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                    <p className="text-xs font-bold text-gray-700">No alerts right now</p>
                    <p className="text-[11px] text-gray-400 mt-1">
                      All seller applications, orders, and inventory systems are in check.
                    </p>
                  </div>
                ) : (
                  displayedNotifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => handleNotificationClick(notif)}
                      className={`p-3.5 hover:bg-gray-50 cursor-pointer transition flex items-start gap-3 ${
                        notif.unread ? 'bg-indigo-50/30' : 'bg-white'
                      }`}
                    >
                      {/* Icon */}
                      <div className="mt-0.5 flex-shrink-0">
                        {notif.type === 'critical' ? (
                          <div className="w-8 h-8 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center">
                            <AlertTriangle className="w-4 h-4" />
                          </div>
                        ) : notif.type === 'warning' ? (
                          <div className="w-8 h-8 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center">
                            <AlertCircle className="w-4 h-4" />
                          </div>
                        ) : (
                          <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                            <ShoppingBag className="w-4 h-4" />
                          </div>
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p className={`text-xs font-bold truncate ${notif.unread ? 'text-gray-900' : 'text-gray-700'}`}>
                            {notif.title}
                          </p>
                          {notif.unread && (
                            <span className="w-2 h-2 rounded-full bg-indigo-600 flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-[11px] text-gray-500 mt-1 line-clamp-2 leading-relaxed">
                          {notif.message}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          <span className="text-[10px] text-gray-400 font-medium">{notif.time}</span>
                          <span className="inline-flex items-center gap-1 text-[11px] font-extrabold text-indigo-600 hover:text-indigo-800">
                            {notif.actionText} <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="p-2.5 bg-gray-50 border-t border-gray-100 text-center">
                <Link
                  to="/admin/ai-seller-onboarding"
                  onClick={() => setNotificationsOpen(false)}
                  className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 transition"
                >
                  Open AI Seller Onboarding Workspace →
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="h-6 w-px bg-gray-200" />

        {/* Profile */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'A'}
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-xs font-bold text-gray-900 leading-tight">{user?.name || 'Admin User'}</p>
            <p className="text-[10px] text-gray-400 font-semibold uppercase">Administrator</p>
          </div>
        </div>
      </div>
    </header>
  );
};

export default AdminNavbar;
