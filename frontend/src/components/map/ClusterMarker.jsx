import { useMemo } from 'react';
import L from 'leaflet';
import { Marker } from 'react-leaflet';
import { TIER_MARKER, TIER_RANK } from '../../constants/visual';

/**
 * A cluster bubble. Uses Leaflet's L.divIcon with inline-styled HTML
 * (Tailwind classes don't apply inside divIcon HTML, so colors are
 * inline-styled from JS).
 *
 * Tier-weighted color: if ≥80% of children are one tier, the cluster
 * bubble takes that tier's color. Otherwise it's neutral slate-700.
 * Threshold matches the plan and prevents a single contrarian pin
 * from dragging a 50/50 cluster off-tone.
 *
 * Click: flyTo(center, expansionZoom) via the parent SuperclusterLayer.
 * (Tested-fallback note: if flyTo doesn't animate under react-leaflet 5
 * + React 19, the parent should fall back to setView with animate:true.)
 */

function buildClusterHTML(count, fillColor, size) {
  const fontSize = size >= 48 ? 14 : 12;
  return `<div style="
    width:${size}px;height:${size}px;
    background:${fillColor};
    border:2px solid #fff;
    border-radius:9999px;
    box-shadow:0 1px 3px rgba(0,0,0,0.25);
    display:flex;align-items:center;justify-content:center;
    color:#fff;font-weight:600;font-size:${fontSize}px;
    line-height:1;
  ">${count}</div>`;
}

function pickClusterColor(tierCounts) {
  let total = 0;
  let dominantTier = null;
  let dominantCount = 0;
  let dominantRank = -1;

  for (const [tier, count] of Object.entries(tierCounts || {})) {
    total += count;
    const rank = TIER_RANK[tier] ?? -1;
    // On tie-count, the higher-ranked tier wins (HOT > WARM > COOL > COLD).
    if (count > dominantCount || (count === dominantCount && rank > dominantRank)) {
      dominantCount = count;
      dominantTier = tier;
      dominantRank = rank;
    }
  }

  const homogeneous = total > 0 && dominantCount / total >= 0.8;
  return homogeneous && TIER_MARKER[dominantTier]
    ? TIER_MARKER[dominantTier].fill
    : '#334155'; // slate-700 — neutral when mixed
}

const ClusterMarker = ({ feature, onClick }) => {
  const [lng, lat] = feature.geometry.coordinates;
  const { point_count: count, tierCounts } = feature.properties;

  // Memoize the divIcon so we don't recreate it on every render —
  // L.divIcon allocates DOM nodes each time and react-leaflet will
  // remount the marker if the icon identity changes.
  const icon = useMemo(() => {
    const size = count < 10 ? 32 : count < 100 ? 40 : 48;
    const fill = pickClusterColor(tierCounts);
    return L.divIcon({
      html: buildClusterHTML(count, fill, size),
      className: 'cluster-marker-icon',
      iconSize: [size, size],
    });
  }, [count, tierCounts]);

  return (
    <Marker
      position={[lat, lng]}
      icon={icon}
      eventHandlers={{ click: () => onClick?.(feature) }}
    />
  );
};

export default ClusterMarker;
