import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import api from '../../services/api';

const CATS = ['Electronics', 'Fashion', 'Home & Kitchen', 'Beauty & Personal Care', 'Sports & Fitness', 'Books & Stationery', 'Grocery & Gourmet'];
const EMPTY = { name: '', category: CATS[0], brand: '', price: '', stock: '', description: '' };

/** List a new product. It starts with no rating or reviews; those have to be earned from real buyers. */
export default function AddProduct({ onAdded }) {
  const [f, setF] = useState(EMPTY);
  const [msg, setMsg] = useState('');
  const [errs, setErrs] = useState({});
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault(); setErrs({}); setMsg('');
    try {
      const { data } = await api.post('/seller/products', f);
      setMsg(`${data.name} is now live in the store.`); setF(EMPTY); onAdded?.();
    } catch (err) {
      setErrs(err?.response?.data?.errors || {}); setMsg(err?.response?.data?.detail || 'That did not save.');
    }
  };
  const field = (k, label, props = {}) => (
    <div><label htmlFor={`ap-${k}`}>{label}</label>
      <input id={`ap-${k}`} className="ac-input" value={f[k]} onChange={set(k)} aria-invalid={!!errs[k]} {...props} />
      {errs[k] && <small role="alert" style={{ color: 'var(--coral)' }}>{errs[k]}</small>}</div>
  );
  return (
    <details className="ac-box" style={{ marginTop: 24 }}>
      <summary style={{ cursor: 'pointer', fontWeight: 700 }}><Plus size={16} style={{ verticalAlign: '-3px' }} /> Add a product</summary>
      <form onSubmit={submit} style={{ display: 'grid', gap: 12, marginTop: 14, maxWidth: 560 }}>
        {field('name', 'Product name')}
        <div><label htmlFor="ap-category">Category</label>
          <select id="ap-category" className="ac-input" value={f.category} onChange={set('category')}>{CATS.map((c) => <option key={c}>{c}</option>)}</select></div>
        {field('brand', 'Brand (optional)')}
        {field('price', 'Price (₹)', { inputMode: 'decimal' })}
        {field('stock', 'Units in stock', { inputMode: 'numeric' })}
        <div><label htmlFor="ap-description">Description (optional)</label>
          <textarea id="ap-description" className="ac-input" rows={3} value={f.description} onChange={set('description')} /></div>
        <button className="ac-btn ac-btn-blue" style={{ justifySelf: 'start' }}>Add product</button>
        {msg && <p role="status">{msg}</p>}
      </form>
    </details>
  );
}
