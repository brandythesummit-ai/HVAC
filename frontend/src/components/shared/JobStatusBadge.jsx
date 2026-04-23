/**
 * Floating job status badge.
 *
 * Shows whether a background job is running for HCFL county, with
 * live progress. Polls every 10 seconds while visible. Auto-hides
 * when no job is running and no job ran in the last hour.
 *
 * Placement: bottom-right of Map / List / Plan pages. Small, non-
 * intrusive — the buddy can see "Pull: 34% · 1,240 permits · 42min"
 * at a glance without leaving the current view.
 */
import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Activity, CheckCircle2, XCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// M22 only ships HCFL — county id is static. When V2 adds more
// counties, this becomes a prop or context-driven value.
const HCFL_COUNTY_ID = '07e876b9-938e-4f53-b0dc-7bb9ce7e9cdd';

function formatElapsed(startedAt) {
  if (!startedAt) return '—';
  const start = new Date(startedAt).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - start) / 1000));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function statusColor(status) {
  switch (status) {
    case 'running': return 'bg-blue-600';
    case 'pending': return 'bg-amber-500';
    case 'completed': return 'bg-emerald-600';
    case 'failed': return 'bg-red-600';
    case 'cancelled': return 'bg-slate-500';
    default: return 'bg-slate-400';
  }
}

function statusIcon(status) {
  if (status === 'running' || status === 'pending') return <Activity size={14} className="animate-pulse" />;
  if (status === 'completed') return <CheckCircle2 size={14} />;
  if (status === 'failed' || status === 'cancelled') return <XCircle size={14} />;
  return null;
}

export default function JobStatusBadge() {
  const [dismissed, setDismissed] = useState(false);

  const { data } = useQuery({
    queryKey: ['hcfl-latest-job'],
    queryFn: async () => {
      const { data } = await axios.get(
        `${API_BASE}/api/background-jobs/counties/${HCFL_COUNTY_ID}/jobs?limit=1`,
      );
      // Route returns an array; take the most recent
      return Array.isArray(data) ? data[0] : (data?.data?.[0] ?? null);
    },
    refetchInterval: 10_000,
    staleTime: 5_000,
  });

  // Force re-render every second so elapsed time updates live
  const [, forceRerender] = useState(0);
  useEffect(() => {
    const id = setInterval(() => forceRerender((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const hideForAge = useMemo(() => {
    if (!data) return true;
    if (data.status === 'running' || data.status === 'pending') return false;
    // Show terminal statuses for 1 hour after completion
    const finishedAt = data.completed_at || data.updated_at;
    if (!finishedAt) return false;
    return Date.now() - new Date(finishedAt).getTime() > 60 * 60 * 1000;
  }, [data]);

  if (!data || dismissed || hideForAge) return null;

  const pct = data.progress_percent ?? 0;
  const pulled = data.permits_pulled ?? 0;
  const saved = data.permits_saved ?? 0;
  const label = {
    hcfl_legacy_backfill: 'Legacy backfill',
    initial_pull: 'Initial pull',
    incremental_pull: 'Incremental pull',
    property_aggregation: 'Property aggregation',
  }[data.job_type] || data.job_type;

  return (
    <div className="fixed bottom-4 right-4 z-30 bg-white shadow-lg rounded-lg border border-slate-200 text-sm overflow-hidden w-72">
      <div className={`${statusColor(data.status)} text-white px-3 py-1.5 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          {statusIcon(data.status)}
          <span className="font-medium">{label}</span>
        </div>
        <span className="text-xs uppercase tracking-wide">{data.status}</span>
      </div>
      <div className="px-3 py-2 space-y-1.5">
        {/* Progress bar */}
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-600">
          <span>{pct}%</span>
          <span>{formatElapsed(data.started_at)}</span>
        </div>
        <div className="text-xs text-slate-500 space-y-0.5">
          <div>Permits: <span className="font-mono">{pulled.toLocaleString()}</span> pulled · <span className="font-mono">{saved.toLocaleString()}</span> saved</div>
          {data.error_message && (
            <div className="text-red-600 truncate" title={data.error_message}>
              Error: {data.error_message}
            </div>
          )}
        </div>
      </div>
      {(data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') && (
        <button
          onClick={() => setDismissed(true)}
          className="w-full text-xs text-slate-500 hover:bg-slate-50 py-1 border-t border-slate-100"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
