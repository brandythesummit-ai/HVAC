import { CircleMarker } from 'react-leaflet';
import { TIER_MARKER } from '../../constants/visual';

/**
 * Single-parcel pin. Reads its color from TIER_MARKER (constants/visual.js)
 * so the palette is centralized.
 *
 * No onClick: the existing PinClickHandler at the map level owns click
 * detection (per-marker onClick is unreliable under preferCanvas=true
 * + react-leaflet 5 + React 19, see MapPage.jsx:81-112). Preserve that
 * contract — clusters get their own click handler in SuperclusterLayer.
 *
 * Visual: 7px filled circle + 2px white stroke = 9px visual weight,
 * matching the previous 8px-radius look but with halo for tile-color
 * contrast.
 */
const TierMarker = ({ pin }) => {
  const tier = pin.lead_tier || 'COOL';
  const conf = TIER_MARKER[tier] || TIER_MARKER.COOL;

  return (
    <CircleMarker
      center={[pin.latitude, pin.longitude]}
      radius={7}
      pathOptions={{
        color: conf.stroke,
        fillColor: conf.fill,
        fillOpacity: 0.9,
        weight: 2,
        opacity: 1,
      }}
    />
  );
};

export default TierMarker;
