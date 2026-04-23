/**
 * ListPage — virtual-scrolling table of leads, sorted by score.
 *
 * Peer surface to MapPage. Shares FilterBar so filter state flows
 * between them via URL. Tap a row → opens DetailSheet (M19).
 *
 * Virtual scroll keeps the list responsive at 10K+ leads on
 * low-end mobile.
 */
import { useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

import FilterBar from '../components/shared/FilterBar';
import ViewToggle from '../components/shared/ViewToggle';
import { useLeads } from '../hooks/useLeads';
import { useLeadFilters } from '../hooks/useLeadFilters';

const TIER_COLOR = {
  HOT: 'bg-red-100 text-red-800',
  WARM: 'bg-orange-100 text-orange-800',
  COOL: 'bg-blue-100 text-blue-800',
  COLD: 'bg-slate-100 text-slate-600',
};

function tierBadge(tier) {
  const cls = TIER_COLOR[tier] || 'bg-slate-100 text-slate-600';
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {tier || '—'}
    </span>
  );
}

export default function ListPage() {
  const { filters } = useLeadFilters();
  const { data, isLoading, error } = useLeads(filters);

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
    <div className="flex flex-col h-screen">
      <ViewToggle />
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
                    // M19 will mount DetailSheet here. For now, a
                    // placeholder — no-op until the sheet lands.
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
                        <>{' · '}HVAC {lead.hvac_age_years}y</>
                      )}
                      {lead.lead_status && (
                        <>{' · '}{lead.lead_status.replace(/_/g, ' ')}</>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pl-3">
                    {tierBadge(lead.lead_tier)}
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
    </div>
  );
}
