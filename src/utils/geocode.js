/**
 * Turn GPS coordinates into a street address with free OpenStreetMap (Nominatim) search.
 * Called only when the customer asks to use their location. Returns null if the service cannot be reached.
 */
export async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&addressdetails=1&zoom=18&lat=${lat}&lon=${lng}`, { headers: { Accept: 'application/json' } });
    if (!res.ok) return null;
    const a = (await res.json()).address || {};
    const area = a.suburb || a.neighbourhood || a.city_district || a.quarter || '';
    const line = [a.house_number, a.road, area].filter(Boolean).join(', ');
    const city = a.city || a.town || a.village || a.county || a.state_district || '';
    return { line, area, city, state: a.state || '', pincode: (a.postcode || '').replace(/\D/g, '').slice(0, 6) };
  } catch {
    return null;
  }
}

/**
 * Look up an Indian PIN code (free api.postalpincode.in). Returns { city, state, areas[] } or null when unknown / unreachable.
 */
export async function lookupPin(pin) {
  try {
    const res = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
    const d = (await res.json())?.[0];
    if (d?.Status !== 'Success' || !d.PostOffice?.length) return null;
    const o = d.PostOffice[0];
    return { city: o.District || o.Division || '', state: o.State || '', areas: d.PostOffice.map((x) => x.Name) };
  } catch {
    return null;
  }
}

/** True when the PIN's district/area text and the typed city refer to the same place (Mumbai PINs report "Mumbai", "Thane" etc.). */
export const pinMatchesCity = (info, city) => {
  const c = (city || '').toLowerCase().trim();
  if (!info || !c) return true;
  const hay = [info.city, ...(info.areas || [])].join(' ').toLowerCase();
  const MMR = /mumbai|thane|raigad|navi|kalyan|dombivli|dombivali|bhiwandi|ulhasnagar|ambernath|badlapur|mira|bhayandar|vasai|virar|panvel|kharghar|palghar/;  // one metropolitan region: a PIN in any of these is fine for any other
  return hay.includes(c) || c.includes((info.city || '').toLowerCase()) || (MMR.test(c) && MMR.test(hay));
};
