-- HVAC Lead Generation Platform - Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor to create all required tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- agencies table
-- Stores agency-level configuration (for future multi-tenant support)
CREATE TABLE IF NOT EXISTS agencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    summit_api_key TEXT,
    summit_location_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- counties table
-- Stores county information and Accela API credentials
CREATE TABLE IF NOT EXISTS counties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency_id UUID REFERENCES agencies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    accela_environment TEXT NOT NULL,
    accela_app_id TEXT NOT NULL,
    accela_app_secret TEXT NOT NULL,  -- Encrypted
    accela_access_token TEXT,  -- Encrypted
    token_expires_at TIMESTAMP,
    last_pull_at TIMESTAMP,
    status TEXT DEFAULT 'connected',  -- 'connected', 'token_expired', 'error'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- permits table
-- Stores permit data pulled from Accela API
CREATE TABLE IF NOT EXISTS permits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id) ON DELETE CASCADE,
    accela_record_id TEXT UNIQUE NOT NULL,
    raw_data JSONB,  -- FULL permit JSON from Accela
    permit_type TEXT,
    description TEXT,
    opened_date DATE,
    status TEXT,
    job_value NUMERIC,
    property_address TEXT,
    year_built INTEGER,
    square_footage INTEGER,
    property_value NUMERIC,
    bedrooms INTEGER,
    bathrooms NUMERIC,
    lot_size NUMERIC,
    owner_name TEXT,
    owner_phone TEXT,
    owner_email TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- leads table
-- Stores leads created from permits, with Summit.AI sync status
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permit_id UUID REFERENCES permits(id) ON DELETE CASCADE,
    county_id UUID REFERENCES counties(id) ON DELETE CASCADE,
    summit_sync_status TEXT DEFAULT 'pending',  -- 'pending', 'synced', 'failed'
    summit_contact_id TEXT,
    summit_synced_at TIMESTAMP,
    sync_error_message TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- sync_config table (optional - for future automated sync)
-- Stores sync configuration for agencies
CREATE TABLE IF NOT EXISTS sync_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency_id UUID REFERENCES agencies(id) ON DELETE CASCADE,
    sync_mode TEXT DEFAULT 'manual',  -- 'manual', 'realtime', 'scheduled'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_permits_opened_date ON permits(opened_date);
CREATE INDEX IF NOT EXISTS idx_permits_county_id ON permits(county_id);
CREATE INDEX IF NOT EXISTS idx_permits_accela_record_id ON permits(accela_record_id);

CREATE INDEX IF NOT EXISTS idx_leads_sync_status ON leads(summit_sync_status);
CREATE INDEX IF NOT EXISTS idx_leads_county_id ON leads(county_id);
CREATE INDEX IF NOT EXISTS idx_leads_permit_id ON leads(permit_id);

CREATE INDEX IF NOT EXISTS idx_counties_agency_id ON counties(agency_id);
CREATE INDEX IF NOT EXISTS idx_counties_is_active ON counties(is_active);

-- Optional: Row Level Security (RLS) policies
-- Uncomment if you want to enable RLS for added security

-- ALTER TABLE agencies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE counties ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE permits ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sync_config ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (adjust based on your auth requirements)
-- CREATE POLICY "Allow all operations for authenticated users" ON agencies
--     FOR ALL USING (auth.role() = 'authenticated');

-- Verify tables were created
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE columns.table_name = tables.table_name) as column_count
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name IN ('agencies', 'counties', 'permits', 'leads', 'sync_config')
ORDER BY table_name;

-- Show all indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('agencies', 'counties', 'permits', 'leads', 'sync_config')
ORDER BY tablename, indexname;
