/**
 * Map snapshot persistent storage. Wraps idb-keyval with schema-version
 * gating so old caches invalidate when the pin shape changes.
 *
 * The snapshot is one big object: { schemaVersion, version, pins }.
 * - schemaVersion: bumped when the pin field set changes; mismatched
 *   caches are auto-cleared on next read.
 * - version: server-provided MAX(updated_at) timestamp. Used to compare
 *   against the live RPC for "is your cache stale?" decisions.
 * - pins: the lean pin array — { id, lat, lng, lead_tier, lead_score }.
 *
 * Failure modes are non-fatal: any error throws back to the caller, who
 * is expected to fall back to a live fetch (the fetch path doesn't
 * depend on this layer at all).
 */
import { get, set, del } from 'idb-keyval';

// Bump this whenever the pin shape or the snapshot envelope changes.
// Old caches with a mismatched version are auto-cleared.
export const SCHEMA_VERSION = 1;

const KEY = 'map-snapshot-v1';

/**
 * Read the cached snapshot. Returns null if no cache exists, the
 * schema version mismatches, or anything throws (e.g. Safari quota
 * pressure, serialization failure).
 */
export async function getSnapshot() {
  try {
    const raw = await get(KEY);
    if (!raw) return null;
    if (raw.schemaVersion !== SCHEMA_VERSION) {
      // Schema drifted — drop the stale cache silently. Next call will
      // refetch from the API.
      await del(KEY).catch(() => {});
      return null;
    }
    return raw;
  } catch (err) {
    // IDB throws on quota / corruption / Safari oddities. Treat as cache miss.
    console.warn('[snapshotStore] getSnapshot failed:', err);
    return null;
  }
}

/**
 * Write the snapshot. Failure (e.g. quota exceeded) is logged but not
 * thrown — the caller has the in-memory copy and can keep using it
 * for the current session even if persistence fails.
 */
export async function setSnapshot({ version, pins }) {
  try {
    await set(KEY, { schemaVersion: SCHEMA_VERSION, version, pins });
    return true;
  } catch (err) {
    console.warn('[snapshotStore] setSnapshot failed (likely quota):', err);
    return false;
  }
}

/**
 * Drop the cache. Used by the manual "Sync now" path before a refetch.
 */
export async function clearSnapshot() {
  try {
    await del(KEY);
  } catch (err) {
    console.warn('[snapshotStore] clearSnapshot failed:', err);
  }
}
