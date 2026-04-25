/**
 * ListPage — virtual-scrolling table of leads, sorted by score.
 *
 * Peer surface to MapPage. Shares FilterBar (desktop strip) +
 * FilterSheet (mobile) so filter state flows between map/list/plan
 * via URL. Tap a row → opens DetailSheet via 'open-lead-detail'
 * event with { id }.
 *
 * Mobile chrome: PageFiltersHeader + Filters button → FilterSheet.
 * BottomNav (rendered globally in App.jsx) sits below the list, so
 * we add `pb-14 lg:pb-0` to the page root for clearance.
 *
 * Virtual scroll keeps the list responsive at 10K+ leads on
 * low-end mobile.
 */
import { useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import PageFiltersHeader from '../components/shared/PageFiltersHeader';
import FilterSheet from '../components/shared/FilterSheet';
import TierBadge from '../components/ui/TierBadge';
import { useLeads } from '../hooks/useLeads';
import { useLeadFilters } from '../hooks/useLeadFilters';

export default function ListPage() {
  const { filters } = useLeadFilters();
  // High limit so the virtual-scroll table can sort across the full set
  // rather than paginating. TanStack Virtual only renders visible rows,
  // so 12k in memory is fine.
  const { data, isLoading, error } = useLeads({ ...filters, limit: 12000 });
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);

  // API returns { leads, count, total } — normalize
  const rows = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    return data.leads || [];
  }, [data]);

  // Score-sorted. Higher score = more promising.
  const sorted = useMemo(
    () => [...rows].sort((a, b) => (b.lead_score ?? 0) - (a.lead_score ?? 0)),
    [rows],
  );

  const parentRef = useRef(null);
  const virtualizer = useVirtualizer({
    count: sorted.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 72,
    overscan: 10,
  });

  return (
    <div className="flex flex-col h-screen pb-14 lg:pb-0">
      <ViewToggle />
      <PageFiltersHeader onFiltersClick={() => setFilterSheetOpen(true)} />
      <FilterBar />

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-slate-500">
          Loading leads…
        </div>
      )}
      {error && (
        <div className="flex-1 flex items-center justify-center text-red-600 p-4 text-center">
          Error loading leads: {error.message}
        </div>
      )}
      {!isLoading && !error && sorted.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-slate-500 p-4 text-center">
          No leads match the current filters.
        </div>
      )}

      {!isLoading && !error && sorted.length > 0 && (
        <div ref={parentRef} className="flex-1 overflow-auto bg-white">
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const lead = sorted[virtualRow.index];
              return (
                <div
                  key={lead.id}
                  data-testid="lead-row"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className="border-b border-slate-100 px-4 py-3 flex items-center justify-between hover:bg-slate-50 cursor-pointer"
                  onClick={() => {
                    const evt = new CustomEvent('open-lead-detail', { detail: { id: lead.id } });
                    window.dispatchEvent(evt);
                  }}
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">
                      {lead.property_address || lead.owner_name || '(no address)'}
                    </div>
                    <div className="text-xs text-slate-500 truncate">
                      {lead.owner_name}
                      {lead.hvac_age_years != null && (
                        <>
                          {' · '}HVAC {lead.hvac_age_years}y
                          {lead.properties?.score_source === 'permit' && (
                            <span className="text-emerald-700 ml-1" title="Confirmed via HVAC permit">✓</span>
                          )}
                          {lead.properties?.score_source === 'year_built' && (
                            <span className="text-amber-600 ml-1" title="Estimated from year built">ⓘ</span>
                          )}
                        </>
                      )}
                      {lead.lead_status && (
                        <>{' · '}{lead.lead_status.replace(/_/g, ' ')}</>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pl-3">
                    <TierBadge tier={lead.lead_tier} />
                    <span className="text-slate-400 text-sm tabular-nums">
                      {lead.lead_score ?? 0}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <FilterSheet open={filterSheetOpen} onClose={() => setFilterSheetOpen(false)} />
    </div>
  );
}
