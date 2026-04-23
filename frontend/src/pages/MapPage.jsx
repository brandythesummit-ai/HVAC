/**
 * MapPage — parcels-first viewport-scoped map.
 *
 * Pre-pivot, this fetched 12K leads and rendered all at once. With
 * ~450K residential parcels, we fetch per-viewport via /api/map-pins,
 * debounced on pan/zoom. The user zooms to a subdivision, sees every
 * house as a pin with tier coloring, clicks → DetailSheet opens.
 */
import 'leaflet/dist/leaflet.css';
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import L from 'leaflet';
import markerIconUrl from 'leaflet/dist/images/marker-icon.png';
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, useMapEvents } from 'react-leaflet';

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

/** When the search bounds from useAddressSearchBounds change, fly the
 * map to cover them. Child of MapContainer so it can access the map
 * instance via useMap(). Remembers the last bbox we flew to so we
 * don't re-fly on unrelated state updates (e.g. when filters change
 * but the search text didn't). */
function SearchFlyTo({ bounds }) {
  const map = useMap();
  const lastKey = useRef(null);
  useEffect(() => {
    if (!bounds) return;
    const key = `${bounds.sw_lat},${bounds.sw_lng},${bounds.ne_lat},${bounds.ne_lng}`;
    if (key === lastKey.current) return;
    lastKey.current = key;
    const latLngBounds = L.latLngBounds(
      [bounds.sw_lat, bounds.sw_lng],
      [bounds.ne_lat, bounds.ne_lng],
    );
    // maxZoom caps how far we zoom in — a single-address match would
    // otherwise zoom to z=18 and show one lonely pin; z=16 keeps a
    // subdivision in view.
    map.flyToBounds(latLngBounds, { maxZoom: 16, padding: [40, 40], duration: 0.8 });
  }, [bounds, map]);
  return null;
}

/** Pushes the current map bounds up to the parent via onBboxChange. */
function BboxWatcher({ onBboxChange, onZoomChange }) {
  const pushBbox = useCallback((map) => {
    const b = map.getBounds();
    const z = map.getZoom();
    onBboxChange({
      ne_lat: b.getNorth(),
      ne_lng: b.getEast(),
      sw_lat: b.getSouth(),
      sw_lng: b.getWest(),
    });
    onZoomChange(z);
  }, [onBboxChange, onZoomChange]);

  useMapEvents({
    load: (e) => pushBbox(e.target),
    moveend: (e) => pushBbox(e.target),
    zoomend: (e) => pushBbox(e.target),
  });
  return null;
}

export default function MapPage() {
  const { filters } = useLeadFilters();
  const [bbox, setBbox] = useState(null);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

  // Search text → bbox of matching parcels. Lets a buddy type
  // "newberry grove" and be flown to that subdivision instead of
  // seeing a blank county-wide view.
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
          center={HCFL_CENTER}
          zoom={DEFAULT_ZOOM}
          preferCanvas
          className="w-full h-full"
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer {...tileProps} />
          <BboxWatcher onBboxChange={setBbox} onZoomChange={setZoom} />
          <SearchFlyTo bounds={searchResult.bounds} />
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
                  // DetailSheet listens for this. It'll fetch the full
                  // lead by property_id from /api/leads?property_id=...
                  const evt = new CustomEvent('open-lead-detail', {
                    detail: { propertyId: p.id },
                  });
                  window.dispatchEvent(evt);
                },
              }}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-medium">
                    {p.normalized_address || '(no address)'}
                  </div>
                  {p.owner_name && (
                    <div className="text-slate-600">{p.owner_name}</div>
                  )}
                  <div className="text-xs text-slate-500 mt-1">
                    Built {p.year_built ?? '?'}
                    {p.heated_sqft && ` · ${p.heated_sqft} sqft`}
                    {p.bedrooms_count && ` · ${p.bedrooms_count}BR`}
                    {p.bathrooms_count && `/${p.bathrooms_count}BA`}
                  </div>
                  <div className="text-xs text-slate-500">
                    {p.lead_tier} · Score {p.lead_score ?? 0}
                    {p.owner_occupied && ' · Homestead'}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        <div className="absolute bottom-2 left-2 bg-white/90 rounded-lg px-3 py-1 text-xs text-slate-600 shadow z-10">
          {searchResult.loading && <>Searching addresses…</>}
          {!searchResult.loading && filters.search && filters.search.trim().length >= 2 && !searchResult.found && (
            <>No matches for “{filters.search}”</>
          )}
          {!searchResult.loading && !(filters.search && filters.search.trim().length >= 2 && !searchResult.found) && (
            <>
              {!shouldFetch && (
                <>Zoom in to load pins (zoom ≥ {MIN_FETCH_ZOOM})</>
              )}
              {shouldFetch && (
                <>
                  {displayPins.length.toLocaleString()} pinned
                  {truncated && ' · showing first 10K (zoom in for more)'}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
