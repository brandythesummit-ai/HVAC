-- Migration 026: GHL handoff tracking fields on leads
-- When a lead transitions to INTERESTED, the M13 GHL client creates
-- a Contact + Opportunity in GHL. These fields track that handoff
-- and enable de-duplication across re-knocks.

ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS ghl_contact_id TEXT;

ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS ghl_opportunity_id TEXT;

ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS last_pushed_to_ghl_at TIMESTAMP WITH TIME ZONE;

-- Indexes support:
--   - checking "is this lead already in GHL?" at status-change time
--   - finding the Contact when a re-knock creates a new Opportunity
CREATE INDEX IF NOT EXISTS idx_leads_ghl_contact_id
    ON leads(ghl_contact_id) WHERE ghl_contact_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_ghl_opportunity_id
    ON leads(ghl_opportunity_id) WHERE ghl_opportunity_id IS NOT NULL;
