-- 059_auto_fill_scoring_on_property_insert.sql
--
-- Auto-fill lead_tier / lead_score / hvac_age_years / is_qualified /
-- score_source on every newly-inserted property when the row arrives
-- with no scoring fields set. Closes the gap that produced 5,897
-- "lead_tier IS NULL" leads — they were HCPAO parcels ingested AFTER
-- migration 047's bulk rescore, so 047 never saw them. Migration 056
-- backfilled their score_source but didn't compute tier/score.
--
-- Logic mirrors migration 047 exactly: compute age from
-- most_recent_hvac_date if present, fall back to year_built.
--
-- BEFORE INSERT only — we never want to overwrite a row's tier on
-- update (the property_aggregator's permit-driven path is authoritative
-- for properties with permits). The trigger runs only when lead_tier
-- IS NULL on the incoming NEW row, so an explicit lead_tier in the
-- INSERT payload also wins.

CREATE OR REPLACE FUNCTION fill_property_scoring_on_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  computed_age int;
BEGIN
  -- Only fill if not already provided. PropertyAggregator inserts come
  -- with everything pre-computed; this trigger only catches HCPAO bulk
  -- loads that supply year_built but no scoring.
  IF NEW.lead_tier IS NOT NULL THEN
    RETURN NEW;
  END IF;

  computed_age := CASE
    WHEN NEW.most_recent_hvac_date IS NOT NULL
      THEN GREATEST(0, EXTRACT(YEAR FROM age(CURRENT_DATE, NEW.most_recent_hvac_date))::int)
    WHEN NEW.year_built IS NOT NULL
      THEN GREATEST(0, EXTRACT(YEAR FROM age(CURRENT_DATE, make_date(NEW.year_built, 1, 1)))::int)
    ELSE NULL
  END;

  -- No usable signal — leave everything NULL. The lead won't be
  -- visible because the HOT/WARM filter excludes NULL tiers.
  IF computed_age IS NULL THEN
    RETURN NEW;
  END IF;

  NEW.hvac_age_years := computed_age;
  NEW.lead_tier := CASE
    WHEN computed_age >= 12 THEN 'HOT'
    WHEN computed_age >= 8  THEN 'WARM'
    WHEN computed_age >= 4  THEN 'COOL'
    ELSE 'COLD'
  END;
  NEW.lead_score := CASE
    WHEN computed_age >= 20 THEN 100
    WHEN computed_age >= 12 THEN 75 + (computed_age - 12) * 3
    WHEN computed_age >= 8  THEN 50 + (computed_age - 8)  * 8
    WHEN computed_age >= 4  THEN 25 + (computed_age - 4)  * 8
    ELSE computed_age * 8
  END;
  NEW.is_qualified := (computed_age >= 4);

  -- Preserve any explicit score_source (e.g. PropertyAggregator
  -- supplying 'permit'). Default to 'year_built' since that's the
  -- only path through this trigger that fills tier.
  IF NEW.score_source IS NULL THEN
    NEW.score_source := CASE
      WHEN NEW.most_recent_hvac_date IS NOT NULL THEN 'permit'
      ELSE 'year_built'
    END;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS properties_fill_scoring ON properties;
CREATE TRIGGER properties_fill_scoring
BEFORE INSERT ON properties
FOR EACH ROW
EXECUTE FUNCTION fill_property_scoring_on_insert();
