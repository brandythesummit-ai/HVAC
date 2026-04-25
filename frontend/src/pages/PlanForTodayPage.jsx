/**
 * Plan for Today — multi-select up to 30 top-ranked leads, compute
 * a nearest-neighbor route, export to Google / Apple Maps.
 *
 * Per design doc §3: "Header button → modal showing top-30 ranked
 * leads → user multi-selects → client-side nearest-neighbor routing
 * → ordered list + export to Google/Apple Maps."
 *
 * Mobile chrome: PageFiltersHeader + FilterSheet on mobile;
 * desktop uses ViewToggle + FilterBar. BottomNav clears via
 * pb-14 lg:pb-0 + a mb-14 lg:mb-0 on the route export footer so
 * neither overlaps the global bottom nav.
 */
import { useMemo, useState } from 'react';
import { ArrowUpRight, Route } from 'lucide-react';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import PageFiltersHeader from '../components/shared/PageFiltersHeader';
import FilterSheet from '../components/shared/FilterSheet';
import { useLeads } from '../hooks/useLeads';
import { useLeadFilters } from '../hooks/useLeadFilters';
import {
  buildAppleMapsUrl,
  buildGoogleMapsUrl,
  orderByNearestNeighbor,
} from '../utils/nearestNeighbor';

const MAX_PLAN_LEADS = 30;

export default function PlanForTodayPage() {
  const { filters } = useLeadFilters();
  const { data, isLoading } = useLeads(filters);
  const [selected, setSelected] = useState(new Set());
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);

  // Top-30 plottable, HVAC-qualified leads sorted by score
  const candidates = useMemo(() => {
    if (!data) return [];
    const arr = Array.isArray(data) ? data : data.leads || [];
    return arr
      .filter(
        (l) =>
          typeof l.latitude === 'number' &&
          typeof l.longitude === 'number' &&
          l.is_qualified !== false && // qualified or unspecified
          l.lead_tier !== 'COLD',
      )
      .sort((a, b) => (b.lead_score ?? 0) - (a.lead_score ?? 0))
      .slice(0, MAX_PLAN_LEADS);
  }, [data]);

  const selectedLeads = useMemo(
    () => candidates.filter((l) => selected.has(l.id)),
    [candidates, selected],
  );

  const { ordered, totalKm } = useMemo(
    () => orderByNearestNeighbor(selectedLeads),
    [selectedLeads],
  );

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(candidates.map((l) => l.id)));
  };

  const clearAll = () => setSelected(new Set());

  return (
    <div className="flex flex-col h-screen pb-14 lg:pb-0">
      <ViewToggle />
      <PageFiltersHeader onFiltersClick={() => setFilterSheetOpen(true)} />
      <FilterBar />

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-10 text-slate-500">
            Loading candidates…
          </div>
        )}
        {!isLoading && candidates.length === 0 && (
          <div className="flex items-center justify-center py-10 text-slate-500 text-center px-4">
            No plottable qualified leads match the current filters.
          </div>
        )}
        {!isLoading && candidates.length > 0 && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold">Top {candidates.length} candidates</h2>
                <div className="text-xs text-slate-500">
                  {selected.size} selected
                  {selected.size > 0 && totalKm > 0 && (
                    <> · ~{totalKm.toFixed(1)} km route</>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-sm text-primary-600 hover:underline"
                >
                  Select all
                </button>
                <button
                  type="button"
                  onClick={clearAll}
                  className="text-sm text-slate-500 hover:underline"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="space-y-1">
              {candidates.map((lead) => {
                const isSelected = selected.has(lead.id);
                const orderIdx = ordered.findIndex((l) => l.id === lead.id);
                return (
                  <label
                    key={lead.id}
                    className={
                      'flex items-center gap-3 p-3 rounded-lg border cursor-pointer ' +
                      (isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-slate-200 hover:border-slate-300')
                    }
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggle(lead.id)}
                      className="w-4 h-4"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">
                        {lead.property_address || '(no address)'}
                      </div>
                      <div className="text-xs text-slate-500">
                        {lead.owner_name}
                        {lead.hvac_age_years != null && ` · HVAC ${lead.hvac_age_years}y`}
                        {lead.lead_tier && ` · ${lead.lead_tier}`}
                      </div>
                    </div>
                    {isSelected && orderIdx >= 0 && (
                      <div className="text-xs bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center">
                        {orderIdx + 1}
                      </div>
                    )}
                    <span className="text-sm text-slate-400 tabular-nums">
                      {lead.lead_score ?? 0}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Route export footer — sticky at bottom when a selection exists */}
      {selectedLeads.length > 0 && (
        <div className="border-t border-slate-200 bg-white p-3 flex gap-2">
          <a
            href={buildGoogleMapsUrl(ordered)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium"
          >
            <Route size={16} />
            Google Maps <ArrowUpRight size={14} />
          </a>
          <a
            href={buildAppleMapsUrl(ordered)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-slate-900 text-white text-sm font-medium"
          >
            <Route size={16} />
            Apple Maps <ArrowUpRight size={14} />
          </a>
        </div>
      )}

      <FilterSheet open={filterSheetOpen} onClose={() => setFilterSheetOpen(false)} />
    </div>
  );
}
