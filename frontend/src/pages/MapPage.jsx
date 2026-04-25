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
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import SuperclusterLayer from '../components/map/SuperclusterLayer';
import MapStatusBar from '../components/map/MapStatusBar';
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

// Tier color now lives in constants/visual.js (TIER_MARKER) and is
// consumed by TierMarker / ClusterMarker. The local TIER_COLOR map
// was removed in PR 2 of the redesign.

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

/** Map-level click → nearest pin detection.
 *
 * react-leaflet 5 + preferCanvas=true is unreliable for per-marker
 * eventHandlers.click (the click event silently doesn't fire in
 * production builds). We listen at the map level instead: when the
 * user clicks anywhere, convert click→latlng, find the nearest pin
 * by great-circle distance, and if it's within a reasonable pixel
 * threshold of the click, dispatch the same open-lead-detail event
 * the old CircleMarker handler used to.
 */
function PinClickHandler({ pins, tolerancePx = 14 }) {
  const map = useMap();
  useMapEvents({
    click(e) {
      if (!pins || pins.length === 0) return;
      const { latlng } = e;
      let closest = null;
      let closestDistMeters = Infinity;
      for (const p of pins) {
        const d = latlng.distanceTo([p.latitude, p.longitude]);
        if (d < closestDistMeters) {
          closestDistMeters = d;
          closest = p;
        }
      }
      if (!closest) return;
      // Translate pixel tolerance to meters at the current zoom + lat.
      // Earth circumference cos(lat) / 2^(zoom+8) is meters per tile-pixel.
      const metersPerPx =
        (40075016.686 * Math.cos((latlng.lat * Math.PI) / 180)) /
        Math.pow(2, map.getZoom() + 8);
      const toleranceMeters = tolerancePx * metersPerPx;
      if (closestDistMeters <= toleranceMeters) {
        const evt = new CustomEvent('open-lead-detail', {
          detail: { propertyId: closest.id },
        });
        window.dispatchEvent(evt);
      }
    },
  });
  return null;
}

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

  // MapStatusBar takes raw inputs and applies its own priority logic
  // (searching > tooBroad > noMatch > belowMinZoom > truncated > pinned).
  // The previous concatenated-prose hintText is gone — MapStatusBar
  // now renders distinct visual treatments per state.
  const trimmedSearch = (filters.search || '').trim();
  const hasSearch = trimmedSearch.length >= 2;
  // `noMatch` is gated on `searched` — the 350ms debounce window in
  // useAddressSearchBounds sits between "user typed" and "loading=true",
  // and reading just `!loading && !found && !tooBroad` would flash
  // "No matches for X" to the user during that gap.
  const statusBarProps = {
    searching: hasSearch && (searchResult.loading || !searchResult.searched),
    tooBroad: hasSearch && searchResult.tooBroad,
    noMatch:
      hasSearch
      && searchResult.searched
      && !searchResult.loading
      && !searchResult.found
      && !searchResult.tooBroad,
    belowMinZoom: !shouldFetch,
    truncated: shouldFetch && truncated,
    searchQuery: trimmedSearch,
    searchCount: searchResult.count,
    pinnedCount: displayPins.length,
  };

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
          <PinClickHandler pins={displayPins} />
          <SuperclusterLayer pins={displayPins} bbox={bbox} zoom={zoom} />
        </MapContainer>

        <MapStatusBar {...statusBarProps} />
      </div>
    </div>
  );
}
