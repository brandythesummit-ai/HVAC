-- 029: geocoding columns on properties
-- Populated by scripts/geocode_properties.py via US Census geocoder.
-- MapPage reads these through the leads→properties join so pins render.

ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS geocode_source TEXT;

CREATE INDEX IF NOT EXISTS idx_properties_geocoded_at
    ON properties(geocoded_at) WHERE geocoded_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_properties_latlng
    ON properties(latitude, longitude) WHERE latitude IS NOT NULL;

COMMENT ON COLUMN properties.latitude IS 'WGS84 latitude, populated by geocode_properties.py';
COMMENT ON COLUMN properties.longitude IS 'WGS84 longitude, populated by geocode_properties.py';
COMMENT ON COLUMN properties.geocode_source IS 'Which service returned the coords — us_census | nominatim | manual';
