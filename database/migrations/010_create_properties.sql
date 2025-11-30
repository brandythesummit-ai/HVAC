-- Migration 010: Create properties table for property-level aggregation
-- Purpose: Group permits by normalized address, track most recent HVAC, calculate lead scores

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID NOT NULL REFERENCES counties(id) ON DELETE CASCADE,

    -- Normalized address for matching
    normalized_address TEXT NOT NULL,

    -- Display address components
    street_number TEXT,
    street_name TEXT,
    street_suffix TEXT,
    unit_number TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,

    -- HVAC tracking (most recent)
    most_recent_hvac_permit_id UUID REFERENCES permits(id) ON DELETE SET NULL,
    most_recent_hvac_date DATE,

    -- Auto-calculated fields (calculated in application code)
    hvac_age_years INTEGER,  -- Calculated as: years between CURRENT_DATE and most_recent_hvac_date

    -- Lead scoring
    lead_score INTEGER,  -- 0-100
    lead_tier TEXT,      -- HOT, WARM, COOL, COLD
    is_qualified BOOLEAN,  -- TRUE if hvac_age_years >= 5

    -- Denormalized owner info (from most recent permit for performance)
    owner_name TEXT,
    owner_phone TEXT,
    owner_email TEXT,

    -- Property metadata (denormalized for performance)
    parcel_number TEXT,
    year_built INTEGER,
    lot_size_sqft INTEGER,
    land_value NUMERIC(12, 2),
    improved_value NUMERIC(12, 2),
    total_property_value NUMERIC(12, 2),

    -- Statistics
    total_hvac_permits INTEGER DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT unique_property_address UNIQUE (county_id, normalized_address)
);

-- Indexes for performance
CREATE INDEX idx_properties_county_id ON properties(county_id);
CREATE INDEX idx_properties_normalized_address ON properties(normalized_address);
CREATE INDEX idx_properties_most_recent_hvac_date ON properties(most_recent_hvac_date);
CREATE INDEX idx_properties_hvac_age ON properties(hvac_age_years);
CREATE INDEX idx_properties_lead_tier ON properties(lead_tier);
CREATE INDEX idx_properties_is_qualified ON properties(is_qualified);
CREATE INDEX idx_properties_updated_at ON properties(updated_at);

-- Composite indexes for common queries
CREATE INDEX idx_properties_county_qualified ON properties(county_id, is_qualified) WHERE is_qualified = TRUE;
CREATE INDEX idx_properties_county_tier ON properties(county_id, lead_tier);
CREATE INDEX idx_properties_county_score ON properties(county_id, lead_score DESC);

-- Comments for documentation
COMMENT ON TABLE properties IS 'Aggregated property records with most recent HVAC permit and lead scoring. One row per unique address per county.';
COMMENT ON COLUMN properties.normalized_address IS 'Standardized address for matching (uppercase, expanded abbreviations). Example: "123 MAIN STREET, ANYTOWN, FL 12345"';
COMMENT ON COLUMN properties.hvac_age_years IS 'Computed column: years since most recent HVAC permit installation';
COMMENT ON COLUMN properties.is_qualified IS 'Computed column: TRUE if HVAC is 5+ years old (qualified lead)';
COMMENT ON COLUMN properties.lead_score IS '0-100 score based on HVAC age. 100=20+ years (HOT), 80-95=15-20 years (HOT), 60-75=10-15 years (WARM), 40-55=5-10 years (COOL), 0-35=<5 years (COLD)';
COMMENT ON COLUMN properties.lead_tier IS 'HOT (15-20+ yrs, replacement soon/urgent), WARM (10-15 yrs, maintenance+potential replacement), COOL (5-10 yrs, maintenance only), COLD (<5 yrs, not qualified)';
COMMENT ON COLUMN properties.total_hvac_permits IS 'Count of all HVAC permits found for this address (helps identify properties with repeat work)';
COMMENT ON COLUMN properties.most_recent_hvac_permit_id IS 'Foreign key to the most recent HVAC permit for this property';
