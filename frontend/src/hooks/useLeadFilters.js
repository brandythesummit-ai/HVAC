/**
 * URL-synced filter state for leads. Reads from URLSearchParams,
 * exposes setter that updates the URL. Shared between MapPage and
 * ListPage so the filter bar drives both views.
 *
 * Why URL-synced: a buddy can bookmark/share a view ("all KNOCKED
 * in 33609 older than 15yr"), reload the page without losing the
 * filter, and navigate with browser back/forward naturally.
 *
 * Design doc §3 filter spec (9 functional + 1 deferred):
 *   search, dateFrom/dateTo, status[], tier[], permitType[],
 *   valueMin/valueMax, ownerOccupied, zip, minAge/maxAge.
 *   year_built is the 10th — greyed out until Signal B (deferred).
 */
import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

const LIST_FIELDS = new Set(['status', 'tier', 'permitType']);

const NUMERIC_FIELDS = new Set([
  'minAge', 'maxAge', 'valueMin', 'valueMax',
  'yearBuiltMin', 'yearBuiltMax',
]);
const BOOL_FIELDS = new Set(['ownerOccupied', 'hasPermitHistory']);

function parseValue(key, raw) {
  if (raw == null) return undefined;
  if (LIST_FIELDS.has(key)) {
    return raw.split(',').filter(Boolean);
  }
  if (NUMERIC_FIELDS.has(key)) {
    const n = Number(raw);
    return Number.isFinite(n) ? n : undefined;
  }
  if (BOOL_FIELDS.has(key)) {
    if (raw === 'true') return true;
    if (raw === 'false') return false;
    return undefined;
  }
  return raw;
}

function serializeValue(value) {
  if (value == null || value === '') return undefined;
  if (Array.isArray(value)) return value.length ? value.join(',') : undefined;
  return String(value);
}

export function useLeadFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => {
    const out = {};
    for (const [key, raw] of searchParams.entries()) {
      const parsed = parseValue(key, raw);
      if (parsed !== undefined) out[key] = parsed;
    }
    return out;
  }, [searchParams]);

  const setFilter = useCallback((key, value) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const serialized = serializeValue(value);
      if (serialized == null) {
        next.delete(key);
      } else {
        next.set(key, serialized);
      }
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const clearAll = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  return { filters, setFilter, clearAll };
}
