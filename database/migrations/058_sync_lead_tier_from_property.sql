-- 058_sync_lead_tier_from_property.sql
--
-- Backfill leads.lead_tier / leads.lead_score from properties + add a trigger
-- so they can never drift again.
--
-- Background: leads has denormalized lead_tier/lead_score copies of the
-- corresponding properties columns. The Python PropertyAggregator._update_lead
-- propagates these on every permit-driven update, but migration 047 (FL-tuned
-- rescore) and migration 056 (year_built fallback backfill) updated properties
-- directly via SQL — bypassing Python. Result as of 2026-04-25: 77,388 leads
-- (20%) with stale lead_tier and 144,996 (37%) with stale lead_score.
--
-- 34,062 of those drifted into a state where leads says HOT but properties
-- says COLD/COOL, surfacing wrong door-knock targets. 0 went the other way
-- (we are not hiding any genuine HOT lead — over-inclusion only).
--
-- Fix:
--   1. Backfill: UPDATE every drifted lead from its property in one shot
--      (chunked by lead_tier to avoid MCP's 2-min client cap)
--   2. Add a trigger on properties that mirrors tier/score to leads on any
--      future change. Future SQL bulk-rescores or Python updates both flow
--      through this — no code path can leave them out of sync.

-- ============================================================================
-- 1. Backfill (chunked by lead.lead_tier to keep each statement small)
-- ============================================================================
UPDATE leads l
SET lead_tier = p.lead_tier,
    lead_score = p.lead_score,
    updated_at = NOW()
FROM properties p
WHERE l.property_id = p.id
  AND l.lead_tier = 'HOT'
  AND (l.lead_tier IS DISTINCT FROM p.lead_tier OR l.lead_score IS DISTINCT FROM p.lead_score);

UPDATE leads l
SET lead_tier = p.lead_tier,
    lead_score = p.lead_score,
    updated_at = NOW()
FROM properties p
WHERE l.property_id = p.id
  AND l.lead_tier = 'WARM'
  AND (l.lead_tier IS DISTINCT FROM p.lead_tier OR l.lead_score IS DISTINCT FROM p.lead_score);

UPDATE leads l
SET lead_tier = p.lead_tier,
    lead_score = p.lead_score,
    updated_at = NOW()
FROM properties p
WHERE l.property_id = p.id
  AND l.lead_tier = 'COOL'
  AND (l.lead_tier IS DISTINCT FROM p.lead_tier OR l.lead_score IS DISTINCT FROM p.lead_score);

UPDATE leads l
SET lead_tier = p.lead_tier,
    lead_score = p.lead_score,
    updated_at = NOW()
FROM properties p
WHERE l.property_id = p.id
  AND l.lead_tier = 'COLD'
  AND (l.lead_tier IS DISTINCT FROM p.lead_tier OR l.lead_score IS DISTINCT FROM p.lead_score);

-- Catch any with l.lead_tier IS NULL (none expected, but be safe)
UPDATE leads l
SET lead_tier = p.lead_tier,
    lead_score = p.lead_score,
    updated_at = NOW()
FROM properties p
WHERE l.property_id = p.id
  AND l.lead_tier IS NULL
  AND (l.lead_tier IS DISTINCT FROM p.lead_tier OR l.lead_score IS DISTINCT FROM p.lead_score);

-- ============================================================================
-- 2. Trigger: keep leads.lead_tier / lead_score in sync going forward
-- ============================================================================
CREATE OR REPLACE FUNCTION sync_lead_from_property()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  UPDATE leads
  SET lead_tier = NEW.lead_tier,
      lead_score = NEW.lead_score,
      updated_at = NOW()
  WHERE property_id = NEW.id
    AND (lead_tier IS DISTINCT FROM NEW.lead_tier
      OR lead_score IS DISTINCT FROM NEW.lead_score);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS properties_sync_leads ON properties;
CREATE TRIGGER properties_sync_leads
AFTER UPDATE ON properties
FOR EACH ROW
WHEN (OLD.lead_tier IS DISTINCT FROM NEW.lead_tier
   OR OLD.lead_score IS DISTINCT FROM NEW.lead_score)
EXECUTE FUNCTION sync_lead_from_property();
