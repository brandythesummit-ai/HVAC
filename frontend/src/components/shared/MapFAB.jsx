import { useState } from 'react';
import { Crosshair, Loader2 } from 'lucide-react';
import { useMap } from 'react-leaflet';

/**
 * "Re-center on my location" floating action button.
 *
 * Renders inside <MapContainer> so it can grab the map instance via
 * useMap. Positioned absolute at bottom-right of the map; bottom-20
 * clears the BottomNav (h-14 + safe-area). The leaflet-container
 * acts as the offset parent.
 *
 * Geolocation permission denial is handled gracefully — we just stop
 * the spinner and don't pan. We don't surface a toast because field
 * sales users on a denied permission don't need a recurring nag.
 */
const MapFAB = () => {
  const map = useMap();
  const [loading, setLoading] = useState(false);

  const recenter = () => {
    if (!navigator.geolocation) return;
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        map.flyTo(
          [pos.coords.latitude, pos.coords.longitude],
          17,
          { duration: 0.6 },
        );
        setLoading(false);
      },
      () => { setLoading(false); },
      { timeout: 6000, maximumAge: 30000 },
    );
  };

  return (
    <button
      type="button"
      aria-label="Re-center on my location"
      disabled={loading}
      onClick={recenter}
      className="absolute bottom-20 lg:bottom-4 right-3 z-[1001] w-12 h-12 min-h-touch min-w-touch rounded-full bg-white text-slate-700 shadow-lg border border-slate-200 flex items-center justify-center hover:bg-slate-50 active:scale-95 transition-transform disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
    >
      {loading
        ? <Loader2 className="w-5 h-5 animate-spin" />
        : <Crosshair className="w-5 h-5" />
      }
    </button>
  );
};

export default MapFAB;
