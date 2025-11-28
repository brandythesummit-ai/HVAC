-- Migration 003: Create permits table
-- This table stores HVAC permits pulled from Accela API
-- Includes enriched property data (parcels, owners, addresses)

CREATE TABLE IF NOT EXISTS permits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID NOT NULL REFERENCES counties(id) ON DELETE CASCADE,

    -- Accela Record Identifiers
    accela_record_id TEXT NOT NULL,  -- Unique identifier from Accela
    raw_data JSONB NOT NULL,  -- FULL permit JSON from Accela API (nothing lost)

    -- Permit Information
    permit_type TEXT,  -- e.g., 'Mechanical', 'HVAC Replacement'
    description TEXT,  -- Permit description
    opened_date DATE,  -- Date permit was opened
    status TEXT,  -- e.g., 'Finaled', 'Issued', 'In Review'
    job_value NUMERIC(12, 2),  -- Estimated job value

    -- Property Information (from Accela parcels API)
    property_address TEXT,
    year_built INTEGER,
    square_footage INTEGER,
    property_value NUMERIC(12, 2),
    bedrooms INTEGER,
    bathrooms NUMERIC(3, 1),  -- Allows for 2.5 bathrooms
    lot_size NUMERIC(12, 2),  -- Square feet or acres

    -- Owner Information (from Accela owners API)
    owner_name TEXT,
    owner_phone TEXT,
    owner_email TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Ensure uniqueness per county
    CONSTRAINT unique_permit_per_county UNIQUE (county_id, accela_record_id)
);

-- Add comments
COMMENT ON TABLE permits IS 'HVAC permits pulled from Accela with enriched property data';
COMMENT ON COLUMN permits.raw_data IS 'Complete permit JSON from Accela API - preserves all original data';
COMMENT ON COLUMN permits.accela_record_id IS 'Unique record ID from Accela (format varies by county)';
COMMENT ON COLUMN permits.job_value IS 'Estimated job value in dollars';
COMMENT ON COLUMN permits.bathrooms IS 'Number of bathrooms (supports half baths like 2.5)';
