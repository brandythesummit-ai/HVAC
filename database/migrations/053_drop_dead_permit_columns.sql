-- 053_drop_dead_permit_columns.sql
--
-- Drop 7 dead columns on permits.
--
-- WHY:
-- - year_built, square_footage, bedrooms, bathrooms, lot_size — these are
--   property metadata that the original permits-first design pinned to each
--   permit. With the parcels-first pivot (migration 034), property metadata
--   lives on `properties` (year_built, heated_sqft, bedrooms_count,
--   bathrooms_count, lot_size_sqft). Keeping duplicates on permits invited
--   drift and was 100% unpopulated as of audit on 2026-04-25.
-- - owner_phone, owner_email — never wired to a data source. Permits don't
--   carry contact data, and skip-tracing isn't part of V1. Three rows of
--   spurious phone data and nine of email is misleading; better gone.
--
-- The matching write paths in app/workers/job_processor.py:_save_permit have
-- already been updated to omit these fields.

ALTER TABLE permits
  DROP COLUMN IF EXISTS year_built,
  DROP COLUMN IF EXISTS square_footage,
  DROP COLUMN IF EXISTS bedrooms,
  DROP COLUMN IF EXISTS bathrooms,
  DROP COLUMN IF EXISTS lot_size,
  DROP COLUMN IF EXISTS owner_phone,
  DROP COLUMN IF EXISTS owner_email;
