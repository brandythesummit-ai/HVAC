-- 056_backfill_score_source.sql
--
-- Populates `properties.score_source` ('permit' or 'year_built') for the
-- existing 391,968 residential parcels. Migration 048 added the column;
-- nothing wrote to it until now. The PropertyAggregator (Python) now writes
-- 'permit' on every permit-driven create/update; this migration backfills
-- the historical state.
--
-- Logic:
--   - 'permit'      if most_recent_hvac_permit_id IS NOT NULL
--   - 'year_built'  else if year_built IS NOT NULL
--   - NULL          else (no signal available)
--
-- The UPDATE is chunked by year_built decade because the full 290K UPDATE
-- exceeded MCP's 2-min client cap when fired as one statement. Each chunk
-- runs server-side with statement_timeout=0 so commits land even if a
-- client connection times out — but smaller chunks reduce blast radius.

-- Permit-driven (high-confidence): runs first so a more-recent permit on
-- a property always wins over the year_built fallback below.
UPDATE properties
SET score_source = 'permit'
WHERE source = 'hcpao_parcel'
  AND is_residential = true
  AND most_recent_hvac_permit_id IS NOT NULL
  AND score_source IS DISTINCT FROM 'permit';

-- Year_built fallback in 4 decade-shaped chunks
UPDATE properties
SET score_source = 'year_built'
WHERE source = 'hcpao_parcel'
  AND is_residential = true
  AND most_recent_hvac_permit_id IS NULL
  AND year_built IS NOT NULL
  AND year_built < 1980
  AND score_source IS DISTINCT FROM 'year_built';

UPDATE properties
SET score_source = 'year_built'
WHERE source = 'hcpao_parcel'
  AND is_residential = true
  AND most_recent_hvac_permit_id IS NULL
  AND year_built >= 1980 AND year_built < 2000
  AND score_source IS DISTINCT FROM 'year_built';

UPDATE properties
SET score_source = 'year_built'
WHERE source = 'hcpao_parcel'
  AND is_residential = true
  AND most_recent_hvac_permit_id IS NULL
  AND year_built >= 2000 AND year_built < 2010
  AND score_source IS DISTINCT FROM 'year_built';

UPDATE properties
SET score_source = 'year_built'
WHERE source = 'hcpao_parcel'
  AND is_residential = true
  AND most_recent_hvac_permit_id IS NULL
  AND year_built >= 2010
  AND score_source IS DISTINCT FROM 'year_built';
