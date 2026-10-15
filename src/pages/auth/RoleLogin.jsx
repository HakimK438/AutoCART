import React, { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, Store, ClipboardCheck, LifeBuoy, PackageCheck, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { BrandLink } from '../../storefront/Brand';
import '../../storefront/storefront.css';
import '../../storefront/forms.css';
import '../../storefront/pages.css';

const CONFIG = {
  admin: {
    title: 'Admin sign in', kicker: 'AutoCart console', landing: '/admin', allowed: ['ADMIN', 'STAFF'], Icon: ShieldCheck,
    pitch: 'Run the marketplace',
    points: [[ClipboardCheck, 'Review seller applications and documents'], [LifeBuoy, 'Answer support tickets and customer questions'], [PackageCheck, 'Watch orders, stock and payments']],
    wrong: 'This account is not an administrator. Customers sign in on the main sign-in page.',
    demo: ['admin@auracart.com', 'admin123'],
  },
  seller: {
    title: 'Seller sign in', kicker: 'AutoCart seller centre', landing: '/seller/dashboard', allowed: ['SELLER', 'ADMIN'], Icon: Store,
    pitch: 'Sell to shoppers near you',
    points: [[Store, 'See your store on the nearby-store map'], [LifeBuoy, 'Answer customer questions about your products'], [PackageCheck, 'Track your stock and orders']],
    wrong: 'This account is not an approved seller yet.',
    demo: null,
  },
};

export default function RoleLogin({ role }) {
  const cfg = CONFIG[role];
  const { login, logout, user } = useAuth();
  const navigate = useNavigate();
  const { state } = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(state?.denied ? cfg.wrong : '');

  useEffect(() => { document.title = `${cfg.title} | AutoCart`; }, [cfg.title]);
  if (user && cfg.allowed.includes(user.role) && !busy) return <Navigate to={state?.from?.pathname || cfg.landing} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const data = await login(email.trim(), password);
      if (!cfg.allowed.includes(data.user.role)) { logout(); setError(cfg.wrong); setBusy(false); return; }
      navigate(state?.from?.pathname || cfg.landing, { replace: true });
    } catch (err) {
      setError(err?.response?.status === 429 ? 'Too many tries. Please wait a minute and try again.' : err?.response?.data?.detail || 'We could not sign you in. Check your email and password.');
      setBusy(false);
    }
  };

  return (
    <div className="ac ac-rolelogin">
      <aside className="ac-rl-side">
        <BrandLink />
        <div>
          <p className="ac-rl-kicker">{cfg.kicker}</p>
          <h1 className="ac-display">{cfg.pitch}.</h1>
          <ul>{cfg.points.map(([Icon, text]) => <li key={text}><Icon size={20} /> {text}</li>)}</ul>
        </div>
        <small>{role === 'admin' ? 'Staff only. Every action is recorded.' : 'Not a seller yet? Apply in a few minutes.'}</small>
      </aside>

      <main className="ac-rl-main">
        <form className="ac-rl-card" onSubmit={submit} noValidate>
          <cfg.Icon size={34} color="var(--brand)" />
          <h2 className="ac-display">{cfg.title}</h2>
          <p className="ac-muted" style={{ margin: '6px 0 22px' }}>{role === 'admin' ? 'Use your administrator account.' : 'Use the account you applied with.'}</p>
          {error && <div className="ac-box" role="alert" style={{ borderColor: 'var(--coral)', color: 'var(--coral)', marginBottom: 16, padding: 14, fontWeight: 600 }}>{error}</div>}
          <div className="ac-field"><label htmlFor="rl-email">Email</label>
            <input id="rl-email" type="email" className="ac-input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required /></div>
          <div className="ac-field" style={{ marginTop: 14 }}><label htmlFor="rl-pw">Password</label>
            <div style={{ position: 'relative' }}>
              <input id="rl-pw" type={show ? 'text' : 'password'} className="ac-input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required style={{ paddingRight: 48 }} />
              <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="ac-eye">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div></div>
          <button className="ac-btn ac-btn-blue" style={{ width: '100%', marginTop: 22 }} disabled={busy || !email || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
          {import.meta.env.DEV && cfg.demo && (
            <button type="button" className="ac-textlink" style={{ border: 0, background: 'none', marginTop: 14, display: 'block' }} onClick={() => { setEmail(cfg.demo[0]); setPassword(cfg.demo[1]); }}>Fill the demo account (development only)</button>
          )}
          <div className="ac-rl-links">
            {role === 'seller' && <Link to="/seller/apply">Apply to sell</Link>}
            <Link to="/login">Customer sign in</Link>
            <Link to="/">Back to the store</Link>
          </div>
        </form>
      </main>
    </div>
  );
}
