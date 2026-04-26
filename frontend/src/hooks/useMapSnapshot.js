/**
 * Once-per-session full-county pin snapshot. Pairs with /api/map-snapshot
 * + idb-keyval persistence (snapshotStore.js) so the second-and-later
 * sessions are instant.
 *
 * Lifecycle on mount:
 *   1. Try IndexedDB cache. If hit → state is hydrated immediately
 *      (no network), source = 'cache'.
 *   2. If no cache (or schema mismatch / IDB error) → fetch from API,
 *      write to IDB, swap into state. source = 'fresh'.
 *   3. error: set when both paths fail. The MapPage falls back to the
 *      bbox-scoped useMapPins hook in this case.
 *
 * Manual `refresh()` exposed for a "Sync now" button: clears cache,
 * refetches, rewrites cache. Lets the user force a refresh after they
 * know the backend has new data (e.g. just ingested permits).
 *
 * The hook deliberately avoids version polling. The user's V1 cadence
 * is "permits update weekly" — we accept up-to-7-days staleness for
 * the buddy-with-a-cached-app use case. Version-stamp comparison is
 * available via the /api/map-snapshot/version endpoint if we ever
 * need it later; for now, manual refresh is enough.
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import apiClient from '../api/client';
import { getSnapshot, setSnapshot, clearSnapshot } from '../lib/snapshotStore';

export function useMapSnapshot({ enabled = true } = {}) {
  const [pins, setPins] = useState(null);     // null = not yet hydrated
  const [version, setVersion] = useState(null);
  const [source, setSource] = useState(null); // 'cache' | 'fresh' | null
  const [isLoading, setIsLoading] = useState(false);
  // When disabled (kill-switch from VITE_DISABLE_SNAPSHOT_CACHE), surface a
  // synthetic error so MapPage's `needsBboxFallback = !!snapshot.error || ...`
  // flips to true and routes through useMapPins(bbox) instead. No network
  // is consumed; no IndexedDB read happens.
  const [error, setError] = useState(enabled ? null : new Error('snapshot_disabled'));
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const fetchFresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await apiClient.get('/api/map-snapshot');
      if (!mountedRef.current) return;
      const data = resp.data?.data;
      if (!data || !Array.isArray(data.pins)) {
        throw new Error('Snapshot response missing pins array');
      }
      setPins(data.pins);
      setVersion(data.version);
      setSource('fresh');
      // Write-through to IDB. Failure here is non-fatal — we have the
      // in-memory copy regardless.
      void setSnapshot({ version: data.version, pins: data.pins });
    } catch (e) {
      if (mountedRef.current) {
        console.warn('[useMapSnapshot] fetch failed:', e);
        setError(e);
      }
    } finally {
      if (mountedRef.current) setIsLoading(false);
    }
  }, []);

  // Cache-first hydration on mount.
  useEffect(() => {
    if (!enabled) return; // Kill-switch: skip the entire snapshot path
    let cancelled = false;
    (async () => {
      const cached = await getSnapshot();
      if (cancelled) return;
      if (cached?.pins) {
        // Hydrate from cache instantly — no network needed.
        setPins(cached.pins);
        setVersion(cached.version);
        setSource('cache');
        return;
      }
      // No cache — fetch fresh.
      await fetchFresh();
    })();
    return () => { cancelled = true; };
  }, [enabled, fetchFresh]);

  /**
   * Manual refresh — clears IDB, refetches, rewrites. Used by a
   * "Sync now" UI affordance.
   */
  const refresh = useCallback(async () => {
    await clearSnapshot();
    await fetchFresh();
  }, [fetchFresh]);

  return {
    pins,
    version,
    source,
    isLoading,
    error,
    isHydrated: pins !== null,
    refresh,
  };
}
