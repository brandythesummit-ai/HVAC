/**
 * MapPage — parcels-first viewport-scoped map.
 *
 * Pre-pivot, this fetched 12K leads and rendered all at once. With
 * ~450K residential parcels, we fetch per-viewport via /api/map-pins,
 * debounced on pan/zoom. The render path receives lean pins
 * ({id, latitude, longitude, lead_tier, lead_score} — about 1MB for
 * 10K markers). The full property record is fetched on click by
 * DetailSheet, which listens for the 'open-lead-detail' event.
 *
 * Search → viewport: the MapContainer is keyed on the search result's
 * bbox. When a new address-search resolves, we pass a fresh key (and a
 * `bounds` prop) so react-leaflet fully re-initializes the map at the
 * target subdivision. Imperative flyToBounds on an already-mounted map
 * turned out to be a no-op under react-leaflet 5 + React 19 — key-based
 * remount is the reliable path.
 */
import 'leaflet/dist/leaflet.css';
import { useState, useMemo, useCallback, useEffect } from 'react';
import L from 'leaflet';
import markerIconUrl from 'leaflet/dist/images/marker-icon.png';
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png';
import { MapContainer, TileLayer, CircleMarker, useMap, useMapEvents } from 'react-leaflet';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import { useMapPins } from '../hooks/useMapPins';
import { useLeadFilters } from '../hooks/useLeadFilters';
import { useAddressSearchBounds } from '../hooks/useAddressSearchBounds';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
});

const HCFL_CENTER = [27.9506, -82.4572];
const DEFAULT_ZOOM = 10;

// Below this zoom, the viewport covers too much area for useful pin
// rendering (a county-wide view of 450K pins). Show a "zoom in" hint
// instead of fetching.
const MIN_FETCH_ZOOM = 13;

const TIER_COLOR = {
  HOT: '#dc2626',
  WARM: '#ea580c',
  COOL: '#2563eb',
  COLD: '#94a3b8',
};

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;
const MAPBOX_STYLE = import.meta.env.VITE_MAPBOX_STYLE_ID || 'streets-v12';

const tileProps = MAPBOX_TOKEN
  ? {
      url: `https://api.mapbox.com/styles/v1/mapbox/${MAPBOX_STYLE}/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`,
      attribution:
        '© <a href="https://www.mapbox.com/about/maps/">Mapbox</a> © ' +
        '<a href="https://www.openstreetmap.org/about/">OpenStreetMap</a>',
      tileSize: 512,
      zoomOffset: -1,
    }
  : {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    };

/** Pushes the current map bounds up to the parent via onBboxChange.
 *
 * Uses `useMap()` + a mount-time effect rather than the `load` event,
 * because `load` fires very early (before useMapEvents can subscribe
 * after a keyed remount), leaving the parent without the initial
 * bbox/zoom and keeping shouldFetch=false.
 */
function BboxWatcher({ onBboxChange, onZoomChange }) {
  const map = useMap();

  const pushBbox = useCallback((m) => {
    const b = m.getBounds();
    const z = m.getZoom();
    onBboxChange({
      ne_lat: b.getNorth(),
      ne_lng: b.getEast(),
      sw_lat: b.getSouth(),
      sw_lng: b.getWest(),
    });
    onZoomChange(z);
  }, [onBboxChange, onZoomChange]);

  useEffect(() => {
    if (map) pushBbox(map);
  }, [map, pushBbox]);

  useMapEvents({
    moveend: (e) => pushBbox(e.target),
    zoomend: (e) => pushBbox(e.target),
  });
  return null;
}

export default function MapPage() {
  const { filters } = useLeadFilters();
  const [bbox, setBbox] = useState(null);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

  // Search text → bbox of matching parcels. When this resolves, the
  // bbox becomes part of the MapContainer key, forcing a full remount
  // with the subdivision bounds as the initial view.
  const searchResult = useAddressSearchBounds(filters.search);

  const shouldFetch = bbox && zoom >= MIN_FETCH_ZOOM;
  const { pins, isLoading, truncated } = useMapPins({
    bbox,
    filters,
    enabled: shouldFetch,
  });

  const displayPins = useMemo(() => {
    return pins.filter((p) =>
      typeof p.latitude === 'number' && typeof p.longitude === 'number'
      && !Number.isNaN(p.latitude) && !Number.isNaN(p.longitude),
    );
  }, [pins]);

  // Derive a stable key + the initial view props for MapContainer.
  // A change in searchResult.bounds (including clearing it) flips the
  // key, triggering a fresh Leaflet init. This is heavier than an
  // imperative flyTo but works reliably under react-leaflet 5 +
  // React 19 where effect-driven flyToBounds didn't animate.
  const mapViewProps = useMemo(() => {
    const b = searchResult.bounds;
    if (b) {
      return {
        viewKey: `b:${b.sw_lat.toFixed(5)},${b.sw_lng.toFixed(5)},${b.ne_lat.toFixed(5)},${b.ne_lng.toFixed(5)}`,
        bounds: [[b.sw_lat, b.sw_lng], [b.ne_lat, b.ne_lng]],
        boundsOptions: { maxZoom: 16, padding: [40, 40] },
      };
    }
    return {
      viewKey: 'default',
      center: HCFL_CENTER,
      zoom: DEFAULT_ZOOM,
    };
  }, [searchResult.bounds]);

  // Precedence: active search feedback wins over generic map-state
  // hints, so the user understands what their search did before we
  // surface anything about zoom or pin count.
  const trimmedSearch = (filters.search || '').trim();
  const hasSearch = trimmedSearch.length >= 2;
  let hintText;
  if (hasSearch && searchResult.loading) {
    hintText = 'Searching addresses…';
  } else if (hasSearch && searchResult.tooBroad) {
    hintText = `“${trimmedSearch}” matches ${searchResult.count.toLocaleString()}+ parcels — refine your search`;
  } else if (hasSearch && !searchResult.found) {
    hintText = `No matches for “${trimmedSearch}”`;
  } else if (!shouldFetch) {
    hintText = `Zoom in to load pins (zoom ≥ ${MIN_FETCH_ZOOM})`;
  } else {
    hintText = `${displayPins.length.toLocaleString()} pinned${
      truncated ? ' · showing first 10K (zoom in for more)' : ''
    }`;
  }

  const { viewKey, ...containerProps } = mapViewProps;

  return (
    <div className="flex flex-col h-screen">
      <ViewToggle />
      <FilterBar />

      <div className="relative flex-1">
        {isLoading && (
          <div className="absolute top-2 right-2 bg-white/90 rounded-lg px-3 py-1 text-xs text-slate-600 shadow z-10">
            Loading pins…
          </div>
        )}
        <MapContainer
          key={viewKey}
          {...containerProps}
          preferCanvas
          className="w-full h-full"
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer {...tileProps} />
          <BboxWatcher onBboxChange={setBbox} onZoomChange={setZoom} />
          {displayPins.map((p) => (
            <CircleMarker
              key={p.id}
              center={[p.latitude, p.longitude]}
              radius={8}
              pathOptions={{
                color: TIER_COLOR[p.lead_tier] || TIER_COLOR.COOL,
                fillOpacity: 0.7,
                weight: 1,
              }}
              eventHandlers={{
                click: () => {
                  // DetailSheet listens for this event and fetches the
                  // full property record by id. We intentionally do NOT
                  // render a <Popup> here — with 10K markers, react-
                  // leaflet would eagerly render 10K popup subtrees
                  // into the DOM, tanking reconciliation perf.
                  const evt = new CustomEvent('open-lead-detail', {
                    detail: { propertyId: p.id },
                  });
                  window.dispatchEvent(evt);
                },
              }}
            />
          ))}
        </MapContainer>

        <div className="absolute bottom-2 left-2 bg-white/90 rounded-lg px-3 py-1 text-xs text-slate-600 shadow z-10">
          {hintText}
        </div>
      </div>
    </div>
  );
}
