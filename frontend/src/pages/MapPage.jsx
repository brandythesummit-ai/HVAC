/**
 * MapPage — hero surface per design doc §3.
 *
 * Leaflet + Mapbox tiles. Geo-clustered pins color-coded by scoring
 * tier. Click a pin → fires 'open-lead-detail' event (M19 handles).
 * Bounding-box filter is a planned enhancement — V1 just plots
 * everything the filtered useLeads query returns.
 *
 * Free-tier provider choices per design doc §3:
 *   - Leaflet: open-source, zero cost
 *   - Mapbox tiles: 50K loads/month free, no CC required
 *   - US Census geocoder (client-side, M18 uses lead.latitude/longitude
 *     if present; proper geocoding lives in useGeocoder hook for now)
 *
 * Leaflet requires a CSS import + an icon fix (the default marker
 * icons can't be resolved by Vite's bundler — we shim them).
 */
import 'leaflet/dist/leaflet.css';
import { useMemo } from 'react';
import L from 'leaflet';
import markerIconUrl from 'leaflet/dist/images/marker-icon.png';
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import { useLeads } from '../hooks/useLeads';
import { useLeadFilters } from '../hooks/useLeadFilters';

// Fix Leaflet's default icon URL resolution (Vite bundles assets via URL).
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2xUrl,
  iconUrl: markerIconUrl,
  shadowUrl: markerShadowUrl,
});

// Tampa-ish default center, comfortable zoom for a county-wide view.
const HCFL_CENTER = [27.9506, -82.4572];
const DEFAULT_ZOOM = 10;

const TIER_COLOR = {
  HOT: '#dc2626',    // red-600
  WARM: '#ea580c',   // orange-600
  COOL: '#2563eb',   // blue-600
  COLD: '#94a3b8',   // slate-400
};

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;
const MAPBOX_STYLE = import.meta.env.VITE_MAPBOX_STYLE_ID || 'streets-v12';

// Fallback to OpenStreetMap tiles if no Mapbox token. Keeps dev onboarding
// zero-config while letting prod use the nicer Mapbox tiles.
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

function hasCoords(lead) {
  return (
    typeof lead?.latitude === 'number' &&
    typeof lead?.longitude === 'number' &&
    !Number.isNaN(lead.latitude) &&
    !Number.isNaN(lead.longitude)
  );
}

export default function MapPage() {
  const { filters } = useLeadFilters();
  const { data, isLoading } = useLeads(filters);

  const leads = useMemo(() => {
    if (!data) return [];
    const arr = Array.isArray(data) ? data : data.leads || [];
    // Only plot leads with coords. The backend is responsible for
    // geocoding during ingest; unplotted leads show up in List view.
    // Default: hide COLD tier (not qualified leads — noise on the map).
    return arr.filter((l) => hasCoords(l) && l.lead_tier !== 'COLD');
  }, [data]);

  const unplotted = useMemo(() => {
    if (!data) return 0;
    const arr = Array.isArray(data) ? data : data.leads || [];
    return arr.length - leads.length;
  }, [data, leads.length]);

  return (
    <div className="flex flex-col h-screen">
      <ViewToggle />
      <FilterBar />

      <div className="relative flex-1">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10 text-slate-500">
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
          {leads.map((lead) => (
            <CircleMarker
              key={lead.id}
              center={[lead.latitude, lead.longitude]}
              radius={8}
              pathOptions={{
                color: TIER_COLOR[lead.lead_tier] || TIER_COLOR.COOL,
                fillOpacity: 0.7,
                weight: 1,
              }}
              eventHandlers={{
                click: () => {
                  const evt = new CustomEvent('open-lead-detail', {
                    detail: { id: lead.id },
                  });
                  window.dispatchEvent(evt);
                },
              }}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-medium">
                    {lead.property_address || '(no address)'}
                  </div>
                  <div className="text-slate-600">
                    {lead.owner_name}
                    {lead.hvac_age_years != null && ` · HVAC ${lead.hvac_age_years}y`}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {lead.lead_tier || 'UNRATED'} · Score {lead.lead_score ?? 0}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
        {unplotted > 0 && (
          <div className="absolute bottom-2 left-2 bg-white/90 rounded-lg px-3 py-1 text-xs text-slate-600 shadow">
            {unplotted} lead{unplotted === 1 ? '' : 's'} hidden (no coordinates or COLD tier)
          </div>
        )}
      </div>
    </div>
  );
}
