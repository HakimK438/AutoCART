import React from 'react';

// Self-contained profile illustrations (no network, no stock photos): a person plus a small badge that says who they are.
const LOOK = {
  customer: { bg: ['#dbeafe', '#93c5fd'], skin: '#f2c9a5', hair: '#3b2a20', shirt: '#2563eb', badge: '#2563eb' },
  seller: { bg: ['#ffedd5', '#fdba74'], skin: '#e0ad84', hair: '#1f1a17', shirt: '#ea580c', badge: '#ea580c' },
  admin: { bg: ['#ede9fe', '#c4b5fd'], skin: '#f0c4a0', hair: '#2b2140', shirt: '#4c1d95', badge: '#4c1d95' },
};

/** A round profile picture for a kind of user. `role` is customer, seller or admin. */
export default function ProfileAvatar({ role = 'customer', size = 64, label }) {
  const c = LOOK[role] || LOOK.customer;
  const id = `av-${role}`;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label={label || `${role} profile picture`} style={{ flex: 'none', borderRadius: '50%' }}>
      <defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={c.bg[0]} /><stop offset="1" stopColor={c.bg[1]} /></linearGradient></defs>
      <circle cx="32" cy="32" r="32" fill={`url(#${id})`} />
      <path d="M10 64c0-14 9-22 22-22s22 8 22 22z" fill={c.shirt} />
      <rect x="28" y="36" width="8" height="8" rx="3" fill={c.skin} />
      <circle cx="32" cy="27" r="11" fill={c.skin} />
      <path d="M21 26c0-8 5-12 11-12s11 4 11 12c-3-4-6-5-11-5s-8 1-11 5z" fill={c.hair} />
      {role === 'seller' && <path d="M24 56l8-8 8 8" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />}
      {role === 'admin' && <path d="M32 47l-7 3v5c0 3 3 5 7 6 4-1 7-3 7-6v-5z" fill="#fff" opacity=".92" />}
      <circle cx="52" cy="52" r="9" fill="#fff" />
      <circle cx="52" cy="52" r="7" fill={c.badge} />
      {role === 'customer' && <path d="M48.5 50h7l-.8 5h-5.4zM50 50c0-3 4-3 4 0" fill="none" stroke="#fff" strokeWidth="1.3" strokeLinejoin="round" />}
      {role === 'seller' && <path d="M48.5 53v-3.4h7V53m-8 0h9m-6 0v-2h3v2" fill="none" stroke="#fff" strokeWidth="1.3" strokeLinejoin="round" />}
      {role === 'admin' && <path d="M52 48.5l3.2 1.3v2.4c0 1.8-1.4 2.7-3.2 3.3-1.8-.6-3.2-1.5-3.2-3.3v-2.4z" fill="none" stroke="#fff" strokeWidth="1.3" strokeLinejoin="round" />}
    </svg>
  );
}
