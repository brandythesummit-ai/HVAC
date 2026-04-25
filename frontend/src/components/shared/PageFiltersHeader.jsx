import { Menu, Filter } from 'lucide-react';
import IconButton from '../ui/IconButton';
import ActiveFilterChips from './ActiveFilterChips';
import { useLeadFilters } from '../../hooks/useLeadFilters';

/**
 * Stripped-down MapTopBar for /list and /plan on mobile.
 *
 * Same chrome shape (hamburger + Filters button) but no search input
 * — those pages don't have a map-specific search affordance, and the
 * FilterSheet's own Search field handles text queries when needed.
 *
 * Renders nothing on lg: and above, where the desktop sidebar +
 * top-header already provide navigation chrome.
 */
const PageFiltersHeader = ({ onMenuClick, onFiltersClick }) => {
  const { filters } = useLeadFilters();
  const activeFilterCount = Object.keys(filters).length;

  return (
    <div className="lg:hidden border-b border-slate-200 bg-white pt-[env(safe-area-inset-top)] sticky top-0 z-30">
      <div className="flex items-center gap-2 px-2 py-2">
        {onMenuClick && (
          <IconButton aria-label="Open menu" onClick={onMenuClick} size="md">
            <Menu className="w-5 h-5" />
          </IconButton>
        )}
        <button
          type="button"
          onClick={onFiltersClick}
          className="relative inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 min-h-touch focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
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
      </div>
      <ActiveFilterChips />
    </div>
  );
};

export default PageFiltersHeader;
