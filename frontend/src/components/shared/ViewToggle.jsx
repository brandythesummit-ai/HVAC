/**
 * View toggle — switches between /map, /list, /plan on desktop.
 *
 * On lg: only — mobile uses the global <BottomNav /> (mounted at the
 * App root) which provides identical navigation but with thumb-reach
 * ergonomics for the field.
 *
 * Visual: the ui/SegmentedControl primitive — pill-shape with the
 * active option lifted onto a white card. Uses useNavigate+useLocation
 * for routing rather than NavLink so we can pass `value`/`onChange`
 * to the primitive without coupling it to react-router internals.
 */
import { useLocation, useNavigate } from 'react-router-dom';
import { Map as MapIcon, List as ListIcon, Calendar } from 'lucide-react';
import SegmentedControl from '../ui/SegmentedControl';

const OPTIONS = [
  { value: '/map',  label: 'Map',  icon: MapIcon },
  { value: '/list', label: 'List', icon: ListIcon },
  { value: '/plan', label: 'Plan', icon: Calendar },
];

export default function ViewToggle() {
  const location = useLocation();
  const navigate = useNavigate();

  // Exact match preferred over startsWith — `/mapping` would otherwise
  // wrongly highlight the Map tab. Falls back to '/map' when the
  // current path is something the toggle doesn't represent (e.g.
  // /counties), so the segmented control still has a default visible
  // selection rather than rendering with nothing active.
  const current =
    OPTIONS.find((o) => location.pathname === o.value)?.value || '/map';

  return (
    <div className="hidden lg:flex px-3 py-2 bg-white border-b border-slate-200">
      <SegmentedControl
        options={OPTIONS}
        value={current}
        onChange={(value) => navigate(value)}
        ariaLabel="View"
      />
    </div>
  );
}
