-- 030: accept 'hcfl_legacy_backfill' as a valid job_type
--
-- M6 (commit 17bff21) wired the hcfl_legacy_backfill job into the
-- processor's elif branch and added it to the Python router's
-- valid_job_types list — but the DB's original CHECK constraint
-- (from migration 011) was never updated, so POST attempts failed
-- with "new row … violates check constraint background_jobs_job_type_check".
--
-- Fix: drop + recreate the constraint with the additional value.

ALTER TABLE background_jobs DROP CONSTRAINT IF EXISTS background_jobs_job_type_check;
ALTER TABLE background_jobs ADD CONSTRAINT background_jobs_job_type_check
    CHECK (job_type = ANY (ARRAY[
        'initial_pull',
        'incremental_pull',
        'property_aggregation',
        'hcfl_legacy_backfill'
    ]));
