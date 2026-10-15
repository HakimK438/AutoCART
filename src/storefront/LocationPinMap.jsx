import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import './storefront.css';

// Bundlers lose Leaflet's default marker paths, so point them at the packaged images.
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

const Recenter = ({ lat, lng }) => {
  const map = useMap();
  useEffect(() => { map.setView([lat, lng], map.getZoom()); }, [lat, lng, map]);
  return null;
};

const Picker = ({ onChange }) => {
  useMapEvents({ click: (e) => onChange?.(+e.latlng.lat.toFixed(6), +e.latlng.lng.toFixed(6)) });
  return null;
};

/** A map with one pin. Pass onChange to let people click or drag the pin; leave it off for a read-only view. */
export default function LocationPinMap({ lat, lng, onChange, height = 320, zoom = 15 }) {
  const editable = typeof onChange === 'function';
  return (
    <div className="ac-map" style={{ height }}>
      <MapContainer center={[lat, lng]} zoom={zoom} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Marker position={[lat, lng]} draggable={editable}
          eventHandlers={editable ? { dragend: (e) => { const p = e.target.getLatLng(); onChange(+p.lat.toFixed(6), +p.lng.toFixed(6)); } } : {}} />
        {editable && <Picker onChange={onChange} />}
        <Recenter lat={lat} lng={lng} />
      </MapContainer>
    </div>
  );
}

/** Finds a place on the map from an address, using free OpenStreetMap search. Only runs when the person asks. */
export async function findOnMap(query) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=in&q=${encodeURIComponent(query)}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  const rows = await res.json();
  return rows[0] ? { lat: +parseFloat(rows[0].lat).toFixed(6), lng: +parseFloat(rows[0].lon).toFixed(6) } : null;
}
