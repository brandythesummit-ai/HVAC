/**
 * FilterBar — 9 functional filters + 1 greyed placeholder.
 *
 * Design doc §3 spec. Shared between MapPage and ListPage. All state
 * lives in URL params via useLeadFilters so the filter is reload- and
 * share-safe.
 *
 * Layout is mobile-first: a collapsible drawer on small screens, a
 * horizontal strip on desktops. Each filter is a labeled input;
 * multi-select fields (status, tier) use chips.
 */
import { useState } from 'react';
import { Filter, X } from 'lucide-react';
import { useLeadFilters } from '../../hooks/useLeadFilters';

const LEAD_STATUSES = [
  'NEW',
  'KNOCKED_NO_ANSWER',
  'KNOCKED_SPOKE_TO_NON_DM',
  'KNOCKED_NOT_INTERESTED',
  'INTERESTED',
  'APPOINTMENT_SET',
  'QUOTED',
  'WON',
  'LOST',
];

const TIER_OPTIONS = ['HOT', 'WARM', 'COOL', 'COLD'];

function toggleInArray(arr = [], value) {
  return arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
}

export default function FilterBar() {
  const { filters, setFilter, clearAll } = useLeadFilters();
  const [open, setOpen] = useState(false);

  const hasActive = Object.keys(filters).length > 0;

  return (
    <div className="bg-white border-b border-slate-200 sticky top-0 z-20">
      <div className="flex items-center gap-2 px-3 py-2 overflow-x-auto">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200 flex-shrink-0"
        >
          <Filter size={16} />
          <span className="text-sm">Filters</span>
          {hasActive && (
            <span className="bg-blue-600 text-white text-xs rounded-full px-1.5 py-0.5">
              {Object.keys(filters).length}
            </span>
          )}
        </button>

        <input
          type="text"
          placeholder="Address, owner, or permit #"
          value={filters.search || ''}
          onChange={(e) => setFilter('search', e.target.value)}
          className="flex-1 min-w-[160px] px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:border-blue-500 outline-none"
        />

        {hasActive && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-slate-500 hover:text-slate-700 flex-shrink-0"
            title="Clear all filters"
          >
            <X size={16} />
            <span className="text-sm">Clear</span>
          </button>
        )}
      </div>

      {open && (
        <div className="border-t border-slate-100 p-3 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Status multiselect */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
            <div className="flex flex-wrap gap-1">
              {LEAD_STATUSES.map((s) => {
                const active = (filters.status || []).includes(s);
                return (
                  <button
                    key={s}
                    onClick={() =>
                      setFilter('status', toggleInArray(filters.status, s))
                    }
                    className={
                      'px-2 py-1 text-xs rounded-full border ' +
                      (active
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-blue-500')
                    }
                  >
                    {s.replace(/_/g, ' ')}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tier */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Tier</label>
            <div className="flex gap-1">
              {TIER_OPTIONS.map((t) => {
                const active = (filters.tier || []).includes(t);
                return (
                  <button
                    key={t}
                    onClick={() => setFilter('tier', toggleInArray(filters.tier, t))}
                    className={
                      'px-2 py-1 text-xs rounded-full border ' +
                      (active
                        ? 'bg-orange-600 text-white border-orange-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-orange-500')
                    }
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Permit from</label>
              <input
                type="date"
                value={filters.dateFrom || ''}
                onChange={(e) => setFilter('dateFrom', e.target.value || undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Permit to</label>
              <input
                type="date"
                value={filters.dateTo || ''}
                onChange={(e) => setFilter('dateTo', e.target.value || undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          {/* HVAC age */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">HVAC age (min yrs)</label>
              <input
                type="number"
                min="0"
                max="60"
                value={filters.minAge ?? ''}
                onChange={(e) => setFilter('minAge', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">HVAC age (max yrs)</label>
              <input
                type="number"
                min="0"
                max="60"
                value={filters.maxAge ?? ''}
                onChange={(e) => setFilter('maxAge', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          {/* Property value range */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Value min</label>
              <input
                type="number"
                min="0"
                step="25000"
                value={filters.valueMin ?? ''}
                onChange={(e) => setFilter('valueMin', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Value max</label>
              <input
                type="number"
                min="0"
                step="25000"
                value={filters.valueMax ?? ''}
                onChange={(e) => setFilter('valueMax', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          {/* ZIP + owner occupied */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">ZIP</label>
              <input
                type="text"
                maxLength={5}
                pattern="[0-9]*"
                inputMode="numeric"
                value={filters.zip || ''}
                onChange={(e) => setFilter('zip', e.target.value || undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Owner occupied</label>
              <select
                value={filters.ownerOccupied == null ? '' : String(filters.ownerOccupied)}
                onChange={(e) => {
                  const v = e.target.value;
                  setFilter('ownerOccupied', v === '' ? undefined : v === 'true');
                }}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              >
                <option value="">Any</option>
                <option value="true">Yes (homestead)</option>
                <option value="false">No (rental)</option>
              </select>
            </div>
          </div>

          {/* Year Built — greyed, deferred to Signal B per design doc */}
          <div className="opacity-60">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Year Built <span className="text-slate-400">(Signal B coming soon)</span>
            </label>
            <input
              type="number"
              disabled
              placeholder="Requires Signal B (GIS)"
              className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg bg-slate-50 cursor-not-allowed"
            />
          </div>
        </div>
      )}
    </div>
  );
}
