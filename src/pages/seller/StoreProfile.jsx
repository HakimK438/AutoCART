import React from 'react';
import { MapPin, Phone, Mail, Store, Boxes } from 'lucide-react';
import StoreMap from '../../storefront/StoreMap';

/** The seller's own business card: who they are, where the store is on the map, and how many products they list. */
export default function StoreProfile({ profile, productsCount }) {
  if (!profile) return null;
  const has = profile.lat != null && profile.lng != null;
  const address = [profile.address, profile.city, profile.state, profile.pincode].filter(Boolean).join(', ');
  return (
    <section className="ac-box" aria-labelledby="store-h" style={{ marginTop: 24 }}>
      <div className="ac-row-between" style={{ alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ minWidth: 260, flex: 1 }}>
          <h2 id="store-h" style={{ display: 'flex', gap: 8, alignItems: 'center' }}><Store size={22} /> {profile.storeName}</h2>
          <span className="ac-chip-status" data-tone={profile.status === 'Approved' ? 'ok' : 'warn'}>{profile.status === 'Approved' ? 'Approved seller' : profile.status || 'Not approved yet'}</span>
          <dl className="ac-sum" style={{ marginTop: 14 }}>
            <div><dt>Owner</dt><dd>{profile.ownerName}</dd></div>
            {profile.company && profile.company !== profile.storeName && <div><dt>Business</dt><dd>{profile.company}</dd></div>}
            {profile.phone && <div><dt><Phone size={14} /> Phone</dt><dd><a href={`tel:${profile.phone}`}>{profile.phone}</a></dd></div>}
            {profile.email && <div><dt><Mail size={14} /> Email</dt><dd>{profile.email}</dd></div>}
            {address && <div><dt><MapPin size={14} /> Address</dt><dd>{address}</dd></div>}
            <div><dt><Boxes size={14} /> Products listed</dt><dd><b>{productsCount}</b></dd></div>
          </dl>
        </div>
        <div style={{ flex: '1 1 340px', minWidth: 280 }}>
          {has
            ? <StoreMap stores={[{ storeId: 'me', storeName: profile.storeName, address, latitude: profile.lat, longitude: profile.lng }]} height={240} selectedId="me" />
            : <div className="ac-storebox" role="note">Your store location is not set yet, so customers cannot find you on the map. Contact support to add it.</div>}
        </div>
      </div>
    </section>
  );
}
