-- Migration 024: Indexes supporting dual-source aggregation performance
-- permits.source: common filter (e.g., "how many permits from the scraper?")
-- permits.permit_type: filtering to HVAC subset during aggregation
-- permits(county_id, opened_date): property_aggregator sorts by opened_date

CREATE INDEX IF NOT EXISTS idx_permits_source ON permits(source);
CREATE INDEX IF NOT EXISTS idx_permits_permit_type ON permits(permit_type);
CREATE INDEX IF NOT EXISTS idx_permits_county_opened_date ON permits(county_id, opened_date DESC);

-- property_address is the fallback aggregation key before normalization; speeds
-- up aggregator lookups during bulk ingestion.
CREATE INDEX IF NOT EXISTS idx_permits_county_property_address
    ON permits(county_id, property_address) WHERE property_address IS NOT NULL;
