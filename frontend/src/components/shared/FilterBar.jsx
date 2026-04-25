/**
 * FilterBar — desktop-only filter strip + drawer.
 *
 * Renders nothing on mobile (hidden sm:block). Mobile filtering is
 * handled by FilterSheet, which is opened via the Filters button in
 * MapTopBar / PageFiltersHeader. Both the mobile sheet and desktop
 * strip read/write through useLeadFilters → URL, so state always
 * syncs across surfaces without prop plumbing.
 *
 * Filter set (post parcels-first pivot):
 *   search, status[], tier[], permit dateFrom/dateTo,
 *   HVAC age min/max, value min/max, ZIP, owner_occupied,
 *   year_built min/max, has_permit_history.
 *
 * The legacy "Year Built (Signal B)" greyed placeholder is dropped —
 * the parcels-first migration enabled real year_built columns, and
 * the new yearBuiltMin/Max inputs replace it.
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
    <div className="hidden lg:block bg-white border-b border-slate-200 sticky top-0 z-20">
      <div className="flex items-center gap-2 px-3 py-2 overflow-x-auto">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 rounded-lg hover:bg-slate-200 flex-shrink-0"
        >
          <Filter size={16} />
          <span className="text-sm">Filters</span>
          {hasActive && (
            <span className="bg-primary-600 text-white text-xs rounded-full px-1.5 py-0.5">
              {Object.keys(filters).length}
            </span>
          )}
        </button>

        <input
          type="text"
          placeholder="Address, owner, or permit #"
          value={filters.search || ''}
          onChange={(e) => setFilter('search', e.target.value)}
          className="flex-1 min-w-[160px] px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:border-primary-500 outline-none"
        />

        {hasActive && (
          <button
            type="button"
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
                    type="button"
                    onClick={() => setFilter('status', toggleInArray(filters.status, s))}
                    className={
                      'px-2 py-1 text-xs rounded-full border ' +
                      (active
                        ? 'bg-primary-600 text-white border-primary-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-primary-500')
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
                    type="button"
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

          {/* Year built — replaces the deferred Signal B placeholder.
              Parcels-first migration (034) enables real year_built data. */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Year built min</label>
              <input
                type="number"
                min="1900"
                max={new Date().getFullYear()}
                value={filters.yearBuiltMin ?? ''}
                onChange={(e) => setFilter('yearBuiltMin', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Year built max</label>
              <input
                type="number"
                min="1900"
                max={new Date().getFullYear()}
                value={filters.yearBuiltMax ?? ''}
                onChange={(e) => setFilter('yearBuiltMax', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          {/* ZIP + owner occupied + permit history */}
          <div className="grid grid-cols-3 gap-2">
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
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Permit history</label>
              <select
                value={filters.hasPermitHistory == null ? '' : String(filters.hasPermitHistory)}
                onChange={(e) => {
                  const v = e.target.value;
                  setFilter('hasPermitHistory', v === '' ? undefined : v === 'true');
                }}
                className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg"
              >
                <option value="">Any</option>
                <option value="true">With permits</option>
                <option value="false">No permits</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
