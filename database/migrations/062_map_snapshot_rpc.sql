-- 062_map_snapshot_rpc.sql
--
-- Pre-computed snapshot of all HOT/WARM residential pins for the map's
-- once-per-session client cache. The frontend fetches this blob, holds
-- it in memory + IndexedDB, and does all bbox/tier filtering locally —
-- so pan/zoom is sub-millisecond after first load.
--
-- Why a materialized view instead of an inline RPC:
-- An inline json_agg over ~300K rows takes ~10s every call. Pre-computing
-- the JSON once and storing it in a materialized view drops per-request
-- read cost to ~500ms (just text serialization of the stored row). Build
-- cost is paid by REFRESH calls, not by every snapshot request.
--
-- Pin shape is intentionally LEAN (id, lat, lng, lead_tier, lead_score)
-- to keep heap reasonable on phones. Detail-fetch on click via
-- /api/leads/by-property/{id} stays for rich fields like owner_name and
-- normalized_address.
--
-- Refresh strategy: backend admin endpoint calls refresh_map_snapshot()
-- after permit-ingest jobs land. Manual fallback: any user can trigger
-- via the "Sync now" UI affordance. CONCURRENT refresh keeps reads
-- non-blocking during the rebuild.

-- Covering index for the underlying scan during MV refresh
CREATE INDEX IF NOT EXISTS properties_snapshot_covering
  ON properties (lead_tier)
  INCLUDE (id, latitude, longitude, lead_score)
  WHERE is_residential = true
    AND lead_tier IN ('HOT', 'WARM')
    AND latitude IS NOT NULL
    AND longitude IS NOT NULL;

-- The materialized view. `singleton` column is a constant 1 so we can
-- create a unique index on it (required for REFRESH ... CONCURRENTLY).
CREATE MATERIALIZED VIEW IF NOT EXISTS map_snapshot_mv AS
SELECT
  1 AS singleton,
  COALESCE(to_char(MAX(updated_at), 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '1970-01-01T00:00:00Z') AS version,
  COALESCE(
    json_agg(json_build_object(
      'id',         id,
      'lat',        latitude,
      'lng',        longitude,
      'lead_tier',  lead_tier,
      'lead_score', lead_score
    )),
    '[]'::json
  ) AS pins
FROM properties
WHERE is_residential = true
  AND lead_tier IN ('HOT', 'WARM')
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS map_snapshot_mv_singleton ON map_snapshot_mv (singleton);

-- Read full snapshot — ~500ms (serializes the stored JSON column)
CREATE OR REPLACE FUNCTION public.map_snapshot_v1()
RETURNS json
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
  SELECT json_build_object('version', version, 'pins', pins)
  FROM map_snapshot_mv
  LIMIT 1;
$$;

-- Cheap version-only read — ~1ms (for "is the cache stale?" checks)
CREATE OR REPLACE FUNCTION public.map_snapshot_version_v1()
RETURNS json
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
  SELECT json_build_object('version', version)
  FROM map_snapshot_mv
  LIMIT 1;
$$;

-- Rebuild the snapshot. Call after permit ingest jobs or on demand
-- via an admin endpoint. CONCURRENT keeps reads non-blocking; takes
-- ~10s at current scale (~300K HOT/WARM rows).
CREATE OR REPLACE FUNCTION public.refresh_map_snapshot()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'pg_temp'
AS $$
DECLARE
  t_start timestamptz := clock_timestamp();
  t_end timestamptz;
  result_version text;
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY map_snapshot_mv;
  SELECT version INTO result_version FROM map_snapshot_mv LIMIT 1;
  t_end := clock_timestamp();
  RETURN json_build_object(
    'version', result_version,
    'duration_ms', extract(milliseconds from t_end - t_start)::int
  );
END;
$$;
