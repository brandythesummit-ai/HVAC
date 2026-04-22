-- Migration 022: Add source tracking to permits
-- Enables dual-source ingestion: Accela V4 API (recent) + HCFL legacy scraper (historical).
-- Composite UNIQUE makes scraper retries idempotent without coordinating with the API pipeline.

ALTER TABLE permits
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'accela_api';

ALTER TABLE permits
    ADD COLUMN IF NOT EXISTS source_permit_id TEXT;

-- Backfill source_permit_id from accela_record_id for existing rows.
-- COALESCE guards against a scraper row landing before this migration and
-- having NULL accela_record_id — keeps the subsequent NOT NULL safe on replay.
UPDATE permits
SET source_permit_id = COALESCE(accela_record_id, id::text)
WHERE source_permit_id IS NULL;

-- Make source_permit_id required going forward
ALTER TABLE permits
    ALTER COLUMN source_permit_id SET NOT NULL;

-- Idempotency guarantee: same permit from same source can't be inserted twice.
-- The same physical property permit could theoretically exist in both sources
-- (Accela + legacy scraper both seeing it); that's fine — they're different
-- `source` values so the constraint allows both rows.
DO $$
BEGIN
    ALTER TABLE permits
        ADD CONSTRAINT unique_permit_per_source UNIQUE (county_id, source, source_permit_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON COLUMN permits.source IS
    'Origin of the permit row. One of: accela_api, hcfl_legacy_scraper.';
COMMENT ON COLUMN permits.source_permit_id IS
    'The original permit identifier from the source system (e.g. NME36051 for HCFL legacy).';
