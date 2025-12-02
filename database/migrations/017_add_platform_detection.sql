-- Migration 017: Add Platform Detection Fields to Counties Table
-- Description: Add state organization and platform detection capabilities
-- Date: 2025-12-01

-- Add state/geographic fields for multi-state expansion
ALTER TABLE counties
ADD COLUMN IF NOT EXISTS state TEXT DEFAULT 'FL',
ADD COLUMN IF NOT EXISTS state_full_name TEXT DEFAULT 'Florida';

-- Add platform detection fields
ALTER TABLE counties
ADD COLUMN IF NOT EXISTS platform TEXT
    CHECK (platform IN ('Accela', 'EnerGov', 'eTRAKiT', 'Tyler', 'OpenGov', 'Custom', 'Unknown'))
    DEFAULT 'Unknown',
ADD COLUMN IF NOT EXISTS platform_confidence TEXT
    CHECK (platform_confidence IN ('Confirmed', 'Likely', 'Unknown'))
    DEFAULT 'Unknown',
ADD COLUMN IF NOT EXISTS permit_portal_url TEXT,
ADD COLUMN IF NOT EXISTS building_dept_website TEXT,
ADD COLUMN IF NOT EXISTS platform_detection_notes TEXT;

-- Add indexes for efficient platform and state queries
CREATE INDEX IF NOT EXISTS idx_counties_platform ON counties(platform);
CREATE INDEX IF NOT EXISTS idx_counties_state ON counties(state);

-- Add comments for documentation
COMMENT ON COLUMN counties.platform IS 'Permit system platform used by this county (Accela, EnerGov, etc.)';
COMMENT ON COLUMN counties.platform_confidence IS 'Confidence level in platform detection (Confirmed, Likely, Unknown)';
COMMENT ON COLUMN counties.county_code IS 'Agency code for Accela API (e.g., HCFL for Hillsborough County)';
COMMENT ON COLUMN counties.permit_portal_url IS 'URL to the county''s permit search portal';
COMMENT ON COLUMN counties.platform_detection_notes IS 'Notes about how platform was detected or other details';
COMMENT ON COLUMN counties.state IS 'State abbreviation (e.g., FL for Florida)';
COMMENT ON COLUMN counties.state_full_name IS 'Full state name (e.g., Florida)';
