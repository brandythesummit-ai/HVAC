import { Menu, Filter, Search, X } from 'lucide-react';
import IconButton from '../ui/IconButton';

/**
 * Top-bar for /map mobile.
 *
 * Layout (left → right):
 *   [☰ menu (optional)]  [🎛 Filters · N]  [🔍 search input]
 *
 * Self-positioning: the component does NOT include outer absolute
 * positioning — consumers (MapPage) wrap it with `lg:hidden absolute
 * top-0 inset-x-0 z-filter` so they can compose it with ActiveFilterChips
 * below, and so this primitive can be reused in other contexts.
 *
 * iOS safe-area: `pt-[env(safe-area-inset-top)]` is applied inside so
 * the bar floats below the notch even when the consumer's wrapper is
 * just `top-0`.
 */
const MapTopBar = ({
  onMenuClick,
  onFiltersClick,
  activeFilterCount = 0,
  searchValue = '',
  onSearchChange,
}) => (
  <div className="px-2 pt-[env(safe-area-inset-top)]">
    <div className="mt-2 flex items-center gap-1 bg-white/95 backdrop-blur rounded-full shadow-md border border-slate-200 pl-1 pr-2 py-1">
      {onMenuClick && (
        <IconButton aria-label="Open menu" onClick={onMenuClick} size="md">
          <Menu className="w-5 h-5" />
        </IconButton>
      )}

      <button
        type="button"
        onClick={onFiltersClick}
        className="relative inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors min-h-touch focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
      >
        <Filter className="w-4 h-4" aria-hidden="true" />
        <span>Filters</span>
        {activeFilterCount > 0 && (
          <span
            aria-label={`${activeFilterCount} active filters`}
            className="ml-1 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-primary-600 text-white text-xs font-semibold"
          >
            {activeFilterCount}
          </span>
        )}
      </button>

      <div className="flex-1 relative">
        <Search
          aria-hidden="true"
          className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none"
        />
        <input
          type="text"
          inputMode="search"
          value={searchValue}
          onChange={(e) => onSearchChange?.(e.target.value || undefined)}
          placeholder="Address or owner"
          aria-label="Search address or owner"
          className="w-full pl-8 pr-7 py-1.5 text-base rounded-full bg-slate-100 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-primary-400"
        />
        {searchValue && (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => onSearchChange?.(undefined)}
            className="absolute right-1 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  </div>
);

export default MapTopBar;
