import React from 'react';

const HUES = [[24, 'ea580c'], [262, '7c3aed'], [199, '0284c7'], [152, '059669'], [340, 'db2777'], [43, 'ca8a04'], [221, '2563eb'], [174, '0d9488']];
const hue = (s) => [...String(s || '?')].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length;
const initials = (s) => String(s || '?').replace(/[^A-Za-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';

/** A seller's profile picture (DP). Shows their store photo when there is one, otherwise a coloured circle with their initials and a small shop badge. */
export default function SellerDP({ name, src, size = 48, ring = false }) {
  const [, c] = HUES[hue(name)];
  const font = Math.round(size * 0.38);
  return (
    <span className="relative inline-flex shrink-0" style={{ width: size, height: size }} role="img" aria-label={`${name || 'Seller'} profile picture`}>
      {src
        ? <img src={src} alt="" className="rounded-full object-cover w-full h-full" style={{ boxShadow: ring ? `0 0 0 3px #fff, 0 0 0 5px #${c}` : undefined }} />
        : <span className="rounded-full w-full h-full flex items-center justify-center font-extrabold text-white select-none"
          style={{ background: `linear-gradient(135deg, #${c}, #${c}b3)`, fontSize: font, boxShadow: ring ? `0 0 0 3px #fff, 0 0 0 5px #${c}` : undefined }}>{initials(name)}</span>}
      {size >= 40 && (
        <span className="absolute -right-0.5 -bottom-0.5 rounded-full bg-white flex items-center justify-center" style={{ width: size * 0.34, height: size * 0.34 }} aria-hidden="true">
          <svg viewBox="0 0 24 24" width={size * 0.22} height={size * 0.22} fill="none" stroke={`#${c}`} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l1.5-5h15L21 9M4 9v11h16V9M3 9a3 3 0 006 0 3 3 0 006 0 3 3 0 006 0" /></svg>
        </span>
      )}
    </span>
  );
}
