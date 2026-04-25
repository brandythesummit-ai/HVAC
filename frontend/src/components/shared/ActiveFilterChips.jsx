import { X } from 'lucide-react';
import { useLeadFilters } from '../../hooks/useLeadFilters';

/**
 * Horizontal overflow row of active-filter chips. Each chip is a
 * tap target that removes its filter when pressed.
 *
 * Renders nothing when no filters are active — the row doesn't
 * eat real estate by default.
 *
 * Used under MapTopBar (mobile) and could be reused on other
 * mobile surfaces if they want the same affordance.
 */

function buildChips(filters) {
  const chips = [];

  if (filters.search) {
    chips.push({ key: 'search', label: `Search: "${filters.search}"` });
  }
  if (filters.status?.length) {
    const head = filters.status[0].replace(/_/g, ' ');
    const more = filters.status.length > 1 ? ` +${filters.status.length - 1}` : '';
    chips.push({ key: 'status', label: `Status: ${head}${more}` });
  }
  if (filters.tier?.length) {
    chips.push({ key: 'tier', label: `Tier: ${filters.tier.join(', ')}` });
  }
  if (filters.dateFrom || filters.dateTo) {
    const from = filters.dateFrom || '…';
    const to = filters.dateTo || '…';
    chips.push({ key: 'dateRange', label: `Permit: ${from} → ${to}`,
      onRemove: (setFilter) => { setFilter('dateFrom', undefined); setFilter('dateTo', undefined); } });
  }
  if (filters.minAge != null || filters.maxAge != null) {
    chips.push({ key: 'ageRange', label: `Age: ${filters.minAge ?? '0'}–${filters.maxAge ?? '∞'}y`,
      onRemove: (setFilter) => { setFilter('minAge', undefined); setFilter('maxAge', undefined); } });
  }
  if (filters.valueMin != null || filters.valueMax != null) {
    const fmt = (n) => n != null ? `$${(n / 1000).toFixed(0)}K` : '∞';
    chips.push({ key: 'valueRange', label: `Value: ${fmt(filters.valueMin)}–${fmt(filters.valueMax)}`,
      onRemove: (setFilter) => { setFilter('valueMin', undefined); setFilter('valueMax', undefined); } });
  }
  if (filters.yearBuiltMin != null || filters.yearBuiltMax != null) {
    chips.push({ key: 'yearBuiltRange', label: `Built: ${filters.yearBuiltMin ?? '…'}–${filters.yearBuiltMax ?? '…'}`,
      onRemove: (setFilter) => { setFilter('yearBuiltMin', undefined); setFilter('yearBuiltMax', undefined); } });
  }
  if (filters.zip) {
    chips.push({ key: 'zip', label: `ZIP: ${filters.zip}` });
  }
  if (filters.ownerOccupied === true) {
    chips.push({ key: 'ownerOccupied', label: 'Homestead' });
  } else if (filters.ownerOccupied === false) {
    chips.push({ key: 'ownerOccupied', label: 'Rental' });
  }
  if (filters.hasPermitHistory === true) {
    chips.push({ key: 'hasPermitHistory', label: 'With permits' });
  } else if (filters.hasPermitHistory === false) {
    chips.push({ key: 'hasPermitHistory', label: 'No permits' });
  }

  return chips;
}

const ActiveFilterChips = ({ className = '' }) => {
  const { filters, setFilter } = useLeadFilters();
  const chips = buildChips(filters);

  if (chips.length === 0) return null;

  return (
    <div
      className={[
        'flex items-center gap-1.5 overflow-x-auto px-3 py-2',
        'scrollbar-none whitespace-nowrap',
        className,
      ].join(' ')}
    >
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={() => {
            if (chip.onRemove) {
              chip.onRemove(setFilter);
            } else {
              setFilter(chip.key, undefined);
            }
          }}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-slate-300 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 flex-shrink-0 min-h-touch focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
        >
          <span>{chip.label}</span>
          <X className="w-3 h-3 text-slate-400" aria-hidden="true" />
          <span className="sr-only">Remove filter</span>
        </button>
      ))}
    </div>
  );
};

export default ActiveFilterChips;
