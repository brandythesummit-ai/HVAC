-- Migration 023: Create hcfl_streets table
-- Drives the HCFL legacy scraper's iteration strategy. Populated from HCPAO
-- parcel data (see backend/scripts/build_hcfl_streets.py).
-- scraped_at enables resumption: the scraper pulls the next unscraped street
-- and stamps the timestamp on completion.

CREATE TABLE IF NOT EXISTS hcfl_streets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Normalized street name (uppercase, whitespace collapsed). Unique on its own
    -- since we're HCFL-only; multi-county would need county_id in the unique.
    street_name TEXT NOT NULL UNIQUE,

    -- Set after the scraper successfully processes this street. NULL = unscraped.
    scraped_at TIMESTAMP WITH TIME ZONE,

    -- Observed permit count from HCFL search results at scrape time.
    permit_count_at_scrape INTEGER,

    -- Observed HVAC-classified permit count at scrape time.
    hvac_permit_count INTEGER,

    -- Retry bookkeeping
    last_error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hcfl_streets_scraped_at
    ON hcfl_streets(scraped_at) WHERE scraped_at IS NULL;

COMMENT ON TABLE hcfl_streets IS
    'Street name enumeration sourced from HCPAO parcels. Used by the HCFL legacy scraper as its iteration cursor.';
