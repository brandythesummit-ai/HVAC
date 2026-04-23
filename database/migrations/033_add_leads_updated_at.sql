-- Migration 033: Add updated_at column to leads.
--
-- Context: the property_aggregator's _update_lead writes updated_at
-- on every tier/score/status refresh. The column was never declared,
-- so PostgREST returned PGRST204 and the ENTIRE aggregation update
-- path silently failed. Existing leads' tiers drifted away from the
-- authoritative `properties.lead_tier`. 582 tier-drifts and 975 score-
-- drifts had accumulated by the time we caught it.
--
-- Fix: add the column, default NOW() so historical rows are sensible,
-- and add a BEFORE UPDATE trigger so callers that forget to write it
-- stay consistent. Ends with NOTIFY pgrst to reload the schema cache.

ALTER TABLE leads
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION touch_leads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS leads_touch_updated_at ON leads;
CREATE TRIGGER leads_touch_updated_at
BEFORE UPDATE ON leads
FOR EACH ROW EXECUTE FUNCTION touch_leads_updated_at();

NOTIFY pgrst, 'reload schema';
