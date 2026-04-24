-- Migration 047: Rescore all properties with FL-tuned tier thresholds.
--
-- Previous thresholds assumed national-average HVAC lifespan (15-20yr).
-- Florida climate (near-continuous runtime, humidity, salt exposure)
-- shortens that to ~10-14yr. The aggregator now uses FL-tuned cuts:
--   HOT ≥12, WARM 8-11, COOL 4-7, COLD <4.
--
-- This migration refreshes the 447K existing hcpao_parcel rows whose
-- tier/score/qualification were computed under the old thresholds.
-- It also smooths the score curve — the new curve is monotonic and has
-- no discontinuity at tier boundaries.
--
-- age source, in priority order:
--   1. most_recent_hvac_date  (permit-based — high-confidence signal)
--   2. year_built fallback   (low-confidence; used for parcels with no permit)
--
-- The 447K UPDATE is slow if every row fires the updated_at trigger,
-- so we disable it for the duration of the bulk refresh and re-enable
-- after. Any row whose tier/score/qualified actually changes still has
-- its updated_at bumped by NOW(); unchanged rows are skipped.

BEGIN;

ALTER TABLE properties DISABLE TRIGGER properties_touch_updated_at;

WITH recomputed AS (
    SELECT
        id,
        CASE
            WHEN most_recent_hvac_date IS NOT NULL
                THEN GREATEST(
                    0,
                    EXTRACT(YEAR FROM age(CURRENT_DATE, most_recent_hvac_date))::int
                )
            WHEN year_built IS NOT NULL
                THEN GREATEST(
                    0,
                    EXTRACT(YEAR FROM age(CURRENT_DATE, make_date(year_built, 1, 1)))::int
                )
            ELSE NULL
        END AS new_age
    FROM properties
    WHERE source = 'hcpao_parcel'
),
scored AS (
    SELECT
        id,
        new_age,
        CASE
            WHEN new_age IS NULL      THEN 'COLD'
            WHEN new_age >= 12        THEN 'HOT'
            WHEN new_age >= 8         THEN 'WARM'
            WHEN new_age >= 4         THEN 'COOL'
            ELSE 'COLD'
        END AS new_tier,
        CASE
            WHEN new_age IS NULL                   THEN 0
            WHEN new_age >= 20                     THEN 100
            WHEN new_age >= 12                     THEN 75 + (new_age - 12) * 3
            WHEN new_age >= 8                      THEN 50 + (new_age - 8)  * 8
            WHEN new_age >= 4                      THEN 25 + (new_age - 4)  * 8
            ELSE new_age * 8
        END AS new_score,
        (new_age IS NOT NULL AND new_age >= 4) AS new_qualified
    FROM recomputed
)
UPDATE properties p
SET
    hvac_age_years = s.new_age,
    lead_tier      = s.new_tier,
    lead_score     = s.new_score,
    is_qualified   = s.new_qualified,
    updated_at     = NOW()
FROM scored s
WHERE p.id = s.id
  AND (
       p.hvac_age_years IS DISTINCT FROM s.new_age
    OR p.lead_tier      IS DISTINCT FROM s.new_tier
    OR p.lead_score     IS DISTINCT FROM s.new_score
    OR p.is_qualified   IS DISTINCT FROM s.new_qualified
  );

ALTER TABLE properties ENABLE TRIGGER properties_touch_updated_at;

COMMIT;

NOTIFY pgrst, 'reload schema';
