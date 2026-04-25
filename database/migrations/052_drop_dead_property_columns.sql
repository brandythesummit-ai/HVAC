-- 052_drop_dead_property_columns.sql
--
-- Drop 6 dead columns on properties.
--
-- WHY:
-- - owner_phone, owner_email — never wired to a data source. Skip-tracing was
--   never purchased; the columns sat at 0% population across all 447,626 rows.
--   If skip-tracing is later added, re-introduce the columns at that time.
-- - contact_completeness, affluence_tier, recommended_pipeline,
--   pipeline_confidence — added by migration 020 as a pipeline-intelligence
--   experiment. Only 350 of 447,626 rows ever got values (the small set that
--   came through the permits-first aggregator path before the parcels-first
--   pivot). Experiment was abandoned; the values that exist now are stale.
--
-- The columns being present in the schema is misleading — the UI/queries can
-- falsely assume data exists. Dropping them aligns the schema with what we
-- actually populate.

ALTER TABLE properties
  DROP COLUMN IF EXISTS owner_phone,
  DROP COLUMN IF EXISTS owner_email,
  DROP COLUMN IF EXISTS contact_completeness,
  DROP COLUMN IF EXISTS affluence_tier,
  DROP COLUMN IF EXISTS recommended_pipeline,
  DROP COLUMN IF EXISTS pipeline_confidence;
