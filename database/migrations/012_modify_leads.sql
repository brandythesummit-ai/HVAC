-- Migration 012: Modify leads table to reference properties instead of permits
-- Purpose: Transform from 1:1 permit-to-lead to 1:1 property-to-lead mapping

-- Add new property-based columns
ALTER TABLE leads ADD COLUMN IF NOT EXISTS property_id UUID REFERENCES properties(id) ON DELETE CASCADE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_score INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_tier TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS qualification_reason TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS disqualified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS disqualification_reason TEXT;

-- Add check constraint for lead_tier
ALTER TABLE leads ADD CONSTRAINT check_lead_tier CHECK (lead_tier IN ('HOT', 'WARM', 'COOL', 'COLD') OR lead_tier IS NULL);

-- Add check constraint for lead_score range
ALTER TABLE leads ADD CONSTRAINT check_lead_score CHECK (lead_score >= 0 AND lead_score <= 100 OR lead_score IS NULL);

-- Create indexes on new columns
CREATE INDEX IF NOT EXISTS idx_leads_property_id ON leads(property_id);
CREATE INDEX IF NOT EXISTS idx_leads_lead_tier ON leads(lead_tier);
CREATE INDEX IF NOT EXISTS idx_leads_lead_score ON leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_disqualified_at ON leads(disqualified_at);

-- Composite indexes for filtering
CREATE INDEX IF NOT EXISTS idx_leads_county_tier ON leads(county_id, lead_tier) WHERE lead_tier IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_county_score ON leads(county_id, lead_score DESC) WHERE lead_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_tier_sync_status ON leads(lead_tier, summit_sync_status) WHERE lead_tier IN ('HOT', 'WARM');

-- Comments for documentation
COMMENT ON COLUMN leads.property_id IS 'Reference to property (one lead per property). Replaces permit_id for property-level lead tracking.';
COMMENT ON COLUMN leads.lead_score IS 'Denormalized from property.lead_score for filtering performance. 0-100 scale.';
COMMENT ON COLUMN leads.lead_tier IS 'Denormalized from property.lead_tier: HOT (15-20+ yrs), WARM (10-15 yrs), COOL (5-10 yrs), COLD (<5 yrs)';
COMMENT ON COLUMN leads.qualification_reason IS 'Human-readable explanation of why lead qualified. Example: "HVAC 18 years old, property value $350K"';
COMMENT ON COLUMN leads.disqualified_at IS 'Timestamp when lead was disqualified (e.g., new HVAC system detected via newer permit)';
COMMENT ON COLUMN leads.disqualification_reason IS 'Explanation of why lead was disqualified. Example: "New HVAC installed 2025-01-15 (permit #HC-BTR-25-0123456)"';

-- Note: permit_id column will be removed in a future migration after data migration is complete
-- This allows gradual transition from permit-based to property-based leads
COMMENT ON COLUMN leads.permit_id IS 'DEPRECATED: Will be removed after migration to property-based leads. Use property_id instead.';
