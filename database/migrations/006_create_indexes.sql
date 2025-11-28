-- Migration 006: Create indexes for performance optimization
-- These indexes optimize common query patterns in the application

-- Counties table indexes
CREATE INDEX IF NOT EXISTS idx_counties_agency_id ON counties(agency_id);
CREATE INDEX IF NOT EXISTS idx_counties_status ON counties(status);
CREATE INDEX IF NOT EXISTS idx_counties_is_active ON counties(is_active);

-- Permits table indexes
CREATE INDEX IF NOT EXISTS idx_permits_county_id ON permits(county_id);
CREATE INDEX IF NOT EXISTS idx_permits_opened_date ON permits(opened_date);
CREATE INDEX IF NOT EXISTS idx_permits_accela_record_id ON permits(accela_record_id);
CREATE INDEX IF NOT EXISTS idx_permits_permit_type ON permits(permit_type);
CREATE INDEX IF NOT EXISTS idx_permits_status ON permits(status);

-- JSONB indexes for raw_data queries (if needed for filtering)
CREATE INDEX IF NOT EXISTS idx_permits_raw_data_gin ON permits USING GIN(raw_data);

-- Leads table indexes
CREATE INDEX IF NOT EXISTS idx_leads_permit_id ON leads(permit_id);
CREATE INDEX IF NOT EXISTS idx_leads_county_id ON leads(county_id);
CREATE INDEX IF NOT EXISTS idx_leads_summit_sync_status ON leads(summit_sync_status);
CREATE INDEX IF NOT EXISTS idx_leads_summit_contact_id ON leads(summit_contact_id);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);

-- Sync config table indexes
CREATE INDEX IF NOT EXISTS idx_sync_config_agency_id ON sync_config(agency_id);
CREATE INDEX IF NOT EXISTS idx_sync_config_is_active ON sync_config(is_active);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_permits_county_date ON permits(county_id, opened_date DESC);
CREATE INDEX IF NOT EXISTS idx_leads_county_status ON leads(county_id, summit_sync_status);

-- Comments
COMMENT ON INDEX idx_permits_raw_data_gin IS 'GIN index for JSONB queries on raw permit data';
COMMENT ON INDEX idx_permits_county_date IS 'Composite index for filtering permits by county and date range';
COMMENT ON INDEX idx_leads_county_status IS 'Composite index for filtering leads by county and sync status';
