-- Migration 021: Add UNIQUE constraint for leads.property_id
-- Required by property_aggregator._create_lead() which upserts with on_conflict='property_id'.
-- Leads are 1:1 with properties under the property-based lead model.

-- Idempotent: ADD CONSTRAINT has no IF NOT EXISTS form, so guard with a catch.
DO $$
BEGIN
    ALTER TABLE leads ADD CONSTRAINT leads_property_id_unique UNIQUE (property_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
