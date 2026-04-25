-- 060_properties_score_source_column.sql
--
-- Backfill the schema migration that creates `properties.score_source`.
-- The column was added directly to production via MCP execute_sql earlier
-- in the parcels-first pivot work, but no migration file ever recorded
-- the DDL. Migration 056 (backfill) and 059 (auto-fill trigger) both
-- assume the column exists. Without this migration, applying the repo
-- to a fresh database fails on 056.
--
-- Idempotent so re-applying against production (where the column is
-- already present) is a no-op.

ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS score_source text;

COMMENT ON COLUMN properties.score_source IS
  'How lead_tier/lead_score were derived: ''permit'' (from most_recent_hvac_date) or ''year_built'' (fallback). NULL = no signal — lead is hidden by the HOT/WARM filter.';
