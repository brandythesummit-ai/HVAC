-- 061_postgis_spatial_index.sql
--
-- Spatial-index the map_pins_in_bbox RPC. The current query takes ~2s
-- because the planner picks the lead_tier index, scans all 270K HOT+WARM
-- rows, then post-filters by bbox — discarding ~83K rows per call. With
-- a true 2D GIST index, the bbox check happens at index time and the
-- query drops to <100ms.
--
-- Steps:
--   1. Install PostGIS (3.3.7 is preinstalled-available on Supabase)
--   2. Add a STORED generated `geom` column derived from lat/lng. This
--      keeps lat/lng as the source of truth; geom auto-populates on
--      every insert/update.
--   3. GIST index on geom, partial (residential + has-coords only) so
--      it stays small and matches the RPC's WHERE clauses.
--   4. Rewrite map_pins_in_bbox to use the && bbox-intersection
--      operator, which the planner recognises as GIST-eligible.

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)
  GENERATED ALWAYS AS (
    CASE
      WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
      ELSE NULL
    END
  ) STORED;

CREATE INDEX IF NOT EXISTS properties_geom_gist
  ON properties USING GIST (geom)
  WHERE is_residential = true AND geom IS NOT NULL;

-- Replace the RPC. Keeps the same signature so backend code is unchanged.
CREATE OR REPLACE FUNCTION public.map_pins_in_bbox(
  p_ne_lat double precision,
  p_ne_lng double precision,
  p_sw_lat double precision,
  p_sw_lng double precision,
  p_lead_tiers text[] DEFAULT NULL,
  p_owner_occupied boolean DEFAULT NULL,
  p_year_built_min integer DEFAULT NULL,
  p_year_built_max integer DEFAULT NULL,
  p_limit integer DEFAULT 15000
)
RETURNS jsonb
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path TO 'public', 'pg_temp', 'extensions'
AS $$
  SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]'::jsonb)
  FROM (
    SELECT p.id, p.latitude, p.longitude, p.lead_tier, p.lead_score
    FROM public.properties p
    WHERE p.is_residential = true
      AND p.geom && ST_MakeEnvelope(p_sw_lng, p_sw_lat, p_ne_lng, p_ne_lat, 4326)
      AND (p_lead_tiers IS NULL OR p.lead_tier = ANY(p_lead_tiers))
      AND (p_owner_occupied IS NULL OR p.owner_occupied = p_owner_occupied)
      AND (p_year_built_min IS NULL OR p.year_built >= p_year_built_min)
      AND (p_year_built_max IS NULL OR p.year_built <= p_year_built_max)
    ORDER BY hashtext(p.id::text)
    LIMIT GREATEST(1, LEAST(p_limit, 20000))
  ) t;
$$;
