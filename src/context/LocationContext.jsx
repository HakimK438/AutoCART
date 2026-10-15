import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const LocationContext = createContext();

const DEFAULT_LOCATION = {
  lat: 19.1136,
  lng: 72.8697,
  city: 'Mumbai',
  area: 'Andheri East',
  pincode: '400069',
  displayName: 'Andheri East, Mumbai (400069)',
  source: 'default', // 'browser' | 'manual' | 'default'
  permissionStatus: 'prompt', // 'prompt' | 'granted' | 'denied'
};

export const LocationProvider = ({ children }) => {
  const [location, setLocation] = useState(() => {
    try {
      const saved = localStorage.getItem('autocart_customer_location');
      return saved ? JSON.parse(saved) : DEFAULT_LOCATION;
    } catch {
      return DEFAULT_LOCATION;
    }
  });
  const [selectedStore, setSelectedStore] = useState(() => {
    try {
      const saved = localStorage.getItem('autocart_selected_store');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const saveLocation = (loc) => {
    setLocation(loc);
    try {
      localStorage.setItem('autocart_customer_location', JSON.stringify(loc));
    } catch (e) {
      console.warn('Could not persist location', e);
    }
  };

  const updateSelectedStore = (store) => {
    setSelectedStore(store);
    try {
      if (store) {
        localStorage.setItem('autocart_selected_store', JSON.stringify(store));
      } else {
        localStorage.removeItem('autocart_selected_store');
      }
    } catch (e) {
      console.warn('Could not persist selected store', e);
    }
  };

  /**
   * Requests coordinates via the browser Geolocation API
   */
  const requestBrowserLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;

        try {
          // Resolve nearest known store / city from backend
          const res = await api.get(`/stores/nearby?lat=${lat}&lng=${lng}&radius=35`);
          const nearest = (res.data?.stores || [])[0];
          const newLoc = {
            lat,
            lng,
            city: nearest?.city || 'Bengaluru',
            area: nearest?.address?.split(',')[0] || 'Nearby Location',
            pincode: nearest?.pincode || '',
            displayName: nearest ? `${nearest.city} (~${nearest.distanceKm} km to store)` : 'Live GPS Location',
            source: 'browser',
            permissionStatus: 'granted',
          };
          saveLocation(newLoc);
        } catch {
          saveLocation({
            lat,
            lng,
            city: 'Current Location',
            area: 'Local Area',
            pincode: '',
            displayName: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
            source: 'browser',
            permissionStatus: 'granted',
          });
        } finally {
          setLoading(false);
        }
      },
      (err) => {
        setLoading(false);
        const reason = err.code === 1 ? 'Permission denied by user' : 'Position unavailable or timed out';
        setError(reason);
        setLocation((prev) => ({ ...prev, permissionStatus: 'denied' }));
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  /**
   * Sets location manually via Indian PIN code or city name
   */
  const setManualLocation = async (pinOrCity) => {
    if (!pinOrCity?.trim()) return false;
    setLoading(true);
    setError(null);

    try {
      const res = await api.get(`/stores/nearby?pinCode=${encodeURIComponent(pinOrCity.trim())}&radius=50`);
      const custLoc = res.data?.customerLocation || {};
      const nearest = (res.data?.stores || [])[0];

      const newLoc = {
        lat: custLoc.lat || 12.9716,
        lng: custLoc.lng || 77.5946,
        city: nearest?.city || pinOrCity,
        area: nearest?.address?.split(',')[0] || pinOrCity,
        pincode: custLoc.pinCode || '',
        displayName: `${pinOrCity.toUpperCase()} (Serviceable)`,
        source: 'manual',
        permissionStatus: 'prompt',
      };
      saveLocation(newLoc);
      return true;
    } catch (err) {
      setError('Could not verify serviceability for this PIN/city.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  return (
    <LocationContext.Provider
      value={{
        location,
        selectedStore,
        updateSelectedStore,
        loading,
        error,
        requestBrowserLocation,
        setManualLocation,
      }}
    >
      {children}
    </LocationContext.Provider>
  );
};

export const useLocation = () => {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error('useLocation must be used within a LocationProvider');
  }
  return context;
};

export default LocationContext;
