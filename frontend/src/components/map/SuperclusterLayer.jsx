import { useMemo, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import Supercluster from 'supercluster';

import TierMarker from './TierMarker';
import ClusterMarker from './ClusterMarker';

/**
 * Renders pins via supercluster: clusters at low zoom, individual
 * TierMarkers at high zoom.
 *
 * Index lifecycle: rebuilt only when the `pins` array reference changes,
 * which `useMapPins` already guarantees on every successful fetch (it
 * calls `setPins(...)` with a fresh array). No `pinsVersion` counter
 * needed — referential equality is the version signal.
 *
 * Cluster expansion: tap a cluster → flyTo(center, expansionZoom). If
 * flyTo fails to animate under react-leaflet 5 + React 19 (the same
 * trap that broke flyToBounds for the search path), we fall back to
 * setView with animate:true. Verify in real browser before relying.
 *
 * Disable-clustering at street level: getClusters is called with
 * zoom=20 when the actual zoom is ≥17, which forces supercluster to
 * return only individual leaves (since maxZoom=17).
 */

const STREET_LEVEL_ZOOM = 17;
const QUERY_ZOOM_AT_STREET = 20;

function pinsToGeoJson(pins) {
  const features = [];
  for (const p of pins) {
    if (typeof p.latitude !== 'number' || typeof p.longitude !== 'number') continue;
    if (Number.isNaN(p.latitude) || Number.isNaN(p.longitude)) continue;
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.longitude, p.latitude] },
      properties: { pin: p, lead_tier: p.lead_tier || 'COOL' },
    });
  }
  return features;
}

const SuperclusterLayer = ({ pins, bbox, zoom }) => {
  const map = useMap();

  // Build the spatial index. Recomputes when pins identity changes.
  // chunkInterval-style chunked loading isn't part of supercluster's
  // API; the .load() call is synchronous but sub-millisecond at our
  // ≤15K-per-viewport scale (verified empirically on similar datasets).
  const index = useMemo(() => {
    const idx = new Supercluster({
      radius: 60,
      maxZoom: STREET_LEVEL_ZOOM,
      // For each leaf, seed `tierCounts` with a single-tier tally of 1.
      map: (props) => ({ tierCounts: { [props.lead_tier]: 1 } }),
      // Reducer mutates `acc.tierCounts` (supercluster API contract).
      reduce: (acc, props) => {
        for (const [tier, c] of Object.entries(props.tierCounts || {})) {
          acc.tierCounts[tier] = (acc.tierCounts[tier] || 0) + c;
        }
      },
    });
    idx.load(pinsToGeoJson(pins || []));
    return idx;
  }, [pins]);

  // Query the index for the current viewport + zoom.
  const features = useMemo(() => {
    if (!bbox || typeof zoom !== 'number') return [];
    const queryZoom = zoom >= STREET_LEVEL_ZOOM ? QUERY_ZOOM_AT_STREET : Math.floor(zoom);
    const bboxArr = [bbox.sw_lng, bbox.sw_lat, bbox.ne_lng, bbox.ne_lat];
    return index.getClusters(bboxArr, queryZoom);
  }, [index, bbox, zoom]);

  const onClusterClick = useCallback((feature) => {
    const clusterId = feature.properties.cluster_id;
    const expansionZoom = Math.min(
      index.getClusterExpansionZoom(clusterId),
      STREET_LEVEL_ZOOM + 1, // never zoom past street-level — we're already there
    );
    const [lng, lat] = feature.geometry.coordinates;
    // flyTo for the smooth animation; the plan calls out that flyToBounds
    // is broken under react-leaflet 5 + React 19, but flyTo to a point
    // (not bounds) should work. Fallback: setView with animate:true.
    try {
      map.flyTo([lat, lng], expansionZoom, { duration: 0.5 });
    } catch {
      map.setView([lat, lng], expansionZoom, { animate: true });
    }
  }, [index, map]);

  return (
    <>
      {features.map((f) => {
        if (f.properties.cluster) {
          return (
            <ClusterMarker
              key={`c-${f.properties.cluster_id}`}
              feature={f}
              onClick={onClusterClick}
            />
          );
        }
        const pin = f.properties.pin;
        return <TierMarker key={`p-${pin.id}`} pin={pin} />;
      })}
    </>
  );
};

export default SuperclusterLayer;
