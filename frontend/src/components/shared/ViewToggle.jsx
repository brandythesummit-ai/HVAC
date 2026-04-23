/**
 * View toggle — switches between /map and /list. Lives in a thin
 * header above both surfaces so a buddy can flip contexts without
 * losing the current filter.
 */
import { NavLink } from 'react-router-dom';
import { Map as MapIcon, List as ListIcon, Calendar } from 'lucide-react';

const linkClass = ({ isActive }) =>
  'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ' +
  (isActive
    ? 'bg-blue-600 text-white'
    : 'bg-slate-100 text-slate-700 hover:bg-slate-200');

export default function ViewToggle() {
  return (
    <div className="flex gap-1 px-3 py-2 bg-white border-b border-slate-200">
      <NavLink to="/map" className={linkClass}>
        <MapIcon size={16} />
        <span>Map</span>
      </NavLink>
      <NavLink to="/list" className={linkClass}>
        <ListIcon size={16} />
        <span>List</span>
      </NavLink>
      <NavLink to="/plan" className={linkClass}>
        <Calendar size={16} />
        <span>Plan today</span>
      </NavLink>
    </div>
  );
}
