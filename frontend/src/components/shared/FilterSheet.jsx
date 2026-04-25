import { useLeadFilters } from '../../hooks/useLeadFilters';
import Sheet from '../ui/Sheet';
import Input from '../ui/Input';
import Select from '../ui/Select';
import ChipGroup from '../ui/ChipGroup';

/**
 * Mobile filter sheet — the full filter form rendered inside a
 * snap-point Sheet primitive. Filters write to the same URL-synced
 * state as the desktop FilterBar via useLeadFilters; consumers don't
 * need to coordinate.
 *
 * Adds the post-pivot parcels-first filters (yearBuiltMin/Max,
 * hasPermitHistory) since the parcels-first migration enabled them
 * server-side. The legacy "Year Built (Signal B coming soon)"
 * placeholder from FilterBar is dropped here on mobile — the real
 * yearBuiltMin/Max sliders replace it.
 */

// Full 10-status list matches DetailSheet.KNOCK_ACTIONS + the lead
// status machine. KNOCKED_WRONG_PERSON sits between NON_DM and
// NOT_INTERESTED so users who marked a knock as wrong-person can
// later filter to find it.
const LEAD_STATUSES = [
  'NEW',
  'KNOCKED_NO_ANSWER',
  'KNOCKED_SPOKE_TO_NON_DM',
  'KNOCKED_WRONG_PERSON',
  'KNOCKED_NOT_INTERESTED',
  'INTERESTED',
  'APPOINTMENT_SET',
  'QUOTED',
  'WON',
  'LOST',
];

const TIER_OPTIONS = [
  { value: 'HOT',  label: 'HOT',  activeClass: 'bg-rose-50 text-rose-700 border-rose-200' },
  { value: 'WARM', label: 'WARM', activeClass: 'bg-amber-50 text-amber-700 border-amber-200' },
  { value: 'COOL', label: 'COOL', activeClass: 'bg-sky-50 text-sky-700 border-sky-200' },
  { value: 'COLD', label: 'COLD', activeClass: 'bg-slate-100 text-slate-700 border-slate-300' },
];

const STATUS_OPTIONS = LEAD_STATUSES.map((s) => ({
  value: s,
  label: s.replace(/_/g, ' '),
}));

const FilterSheet = ({ open, onClose }) => {
  const { filters, setFilter, clearAll } = useLeadFilters();
  const activeCount = Object.keys(filters).length;

  return (
    <Sheet
      open={open}
      onClose={onClose}
      side="bottom"
      snapPoints={[0.92]}
      ariaLabel="Filters"
      showCloseButton={false}
    >
      <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-slate-200 sticky top-0 bg-white z-10">
        <div>
          <h2 className="text-lg font-semibold">Filters</h2>
          {activeCount > 0 && (
            <p className="text-xs text-slate-500">{activeCount} active</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="text-sm text-slate-500 hover:text-slate-800 px-2 py-1 min-h-touch"
            >
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="text-sm font-semibold text-primary-600 hover:text-primary-800 px-3 py-1 min-h-touch"
          >
            Done
          </button>
        </div>
      </div>

      <div className="p-4 space-y-5">
        {/* Search */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Search</label>
          <Input
            type="text"
            value={filters.search || ''}
            onChange={(e) => setFilter('search', e.target.value || undefined)}
            placeholder="Address, owner, or permit #"
          />
        </div>

        {/* Status */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Status</label>
          <ChipGroup
            options={STATUS_OPTIONS}
            value={filters.status || []}
            onChange={(v) => setFilter('status', v)}
            ariaLabel="Lead status"
          />
        </div>

        {/* Tier */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Tier</label>
          <ChipGroup
            options={TIER_OPTIONS}
            value={filters.tier || []}
            onChange={(v) => setFilter('tier', v)}
            ariaLabel="Lead tier"
          />
        </div>

        {/* Permit date range */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Permit from</label>
            <Input
              type="date"
              value={filters.dateFrom || ''}
              onChange={(e) => setFilter('dateFrom', e.target.value || undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Permit to</label>
            <Input
              type="date"
              value={filters.dateTo || ''}
              onChange={(e) => setFilter('dateTo', e.target.value || undefined)}
            />
          </div>
        </div>

        {/* HVAC age */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">HVAC min (yrs)</label>
            <Input
              type="number"
              min="0"
              max="60"
              value={filters.minAge ?? ''}
              onChange={(e) => setFilter('minAge', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">HVAC max (yrs)</label>
            <Input
              type="number"
              min="0"
              max="60"
              value={filters.maxAge ?? ''}
              onChange={(e) => setFilter('maxAge', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Property value */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Value min ($)</label>
            <Input
              type="number"
              min="0"
              step="25000"
              value={filters.valueMin ?? ''}
              onChange={(e) => setFilter('valueMin', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Value max ($)</label>
            <Input
              type="number"
              min="0"
              step="25000"
              value={filters.valueMax ?? ''}
              onChange={(e) => setFilter('valueMax', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Year built — parcels-first replacement for the deferred Signal B placeholder */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Year built min</label>
            <Input
              type="number"
              min="1900"
              max={new Date().getFullYear()}
              value={filters.yearBuiltMin ?? ''}
              onChange={(e) => setFilter('yearBuiltMin', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Year built max</label>
            <Input
              type="number"
              min="1900"
              max={new Date().getFullYear()}
              value={filters.yearBuiltMax ?? ''}
              onChange={(e) => setFilter('yearBuiltMax', e.target.value ? Number(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* ZIP + Owner occupied */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">ZIP</label>
            <Input
              type="text"
              maxLength={5}
              pattern="[0-9]*"
              inputMode="numeric"
              value={filters.zip || ''}
              onChange={(e) => setFilter('zip', e.target.value || undefined)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Owner occupied</label>
            <Select
              value={filters.ownerOccupied == null ? '' : String(filters.ownerOccupied)}
              onChange={(e) => {
                const v = e.target.value;
                setFilter('ownerOccupied', v === '' ? undefined : v === 'true');
              }}
            >
              <option value="">Any</option>
              <option value="true">Yes (homestead)</option>
              <option value="false">No (rental)</option>
            </Select>
          </div>
        </div>

        {/* Permit history */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Permit history</label>
          <Select
            value={filters.hasPermitHistory == null ? '' : String(filters.hasPermitHistory)}
            onChange={(e) => {
              const v = e.target.value;
              setFilter('hasPermitHistory', v === '' ? undefined : v === 'true');
            }}
          >
            <option value="">Any</option>
            <option value="true">With HVAC permits</option>
            <option value="false">No permits on record</option>
          </Select>
        </div>
      </div>
    </Sheet>
  );
};

export default FilterSheet;
