-- Migration 034: Parcels-first architecture — expand properties schema.
--
-- The previous model seeded `properties` from permit records, so a house
-- only existed in the DB if a homeowner had filed an HVAC permit. That
-- made most houses invisible (especially the prime door-knock targets:
-- homes built 2005-2010 still running original HVAC with no permit).
--
-- This migration expands `properties` to hold HCPAO parcel fields so we
-- can seed one row per residential parcel in Hillsborough County,
-- regardless of permit history. Permits layer on top via Phase 3 relink.
--
-- Additive only. No existing columns or indexes are dropped here —
-- that happens in migration 035 after parcel loading completes.

-- === New columns on properties ===
ALTER TABLE properties ADD COLUMN IF NOT EXISTS folio TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS dor_code TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS heated_sqft INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS bedrooms_count INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS bathrooms_count NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS stories_count INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS units_count INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS homestead_year INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS owner_occupied BOOLEAN;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS last_sale_date DATE;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS last_sale_amount NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_residential BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS source TEXT;

-- === New indexes ===
-- Unique per-county folio key. Only enforced on rows that have a folio
-- so existing permit-derived properties (folio=NULL) still coexist.
CREATE UNIQUE INDEX IF NOT EXISTS properties_county_folio_unique
    ON properties (county_id, folio)
    WHERE folio IS NOT NULL;

-- Fast filter on residential + tier for the list/map queries.
CREATE INDEX IF NOT EXISTS properties_residential_tier
    ON properties (is_residential, lead_tier)
    WHERE is_residential;

-- Bbox query support: lat/lng range scans for the map's viewport fetch.
-- Partial index keeps the index small by excluding ungeocoded rows.
CREATE INDEX IF NOT EXISTS properties_lat_lng_residential
    ON properties (latitude, longitude)
    WHERE latitude IS NOT NULL
      AND longitude IS NOT NULL
      AND is_residential;

-- Year-built index for scoring fallback queries.
CREATE INDEX IF NOT EXISTS properties_year_built
    ON properties (year_built)
    WHERE year_built IS NOT NULL;

-- === Leads schema: permit_id must be nullable for parcel-first records ===
-- Phase 4 creates leads directly from parcels with no permit lineage.
ALTER TABLE leads ALTER COLUMN permit_id DROP NOT NULL;

-- === properties updated_at trigger ===
-- Current backend writes updated_at manually but migration 033 revealed
-- that isn't reliable at scale. Add a trigger so drift becomes impossible.
CREATE OR REPLACE FUNCTION touch_properties_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS properties_touch_updated_at ON properties;
CREATE TRIGGER properties_touch_updated_at
BEFORE UPDATE ON properties
FOR EACH ROW EXECUTE FUNCTION touch_properties_updated_at();

NOTIFY pgrst, 'reload schema';
