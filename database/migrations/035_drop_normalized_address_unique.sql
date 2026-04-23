-- Migration 035: drop the legacy (county_id, normalized_address) UNIQUE.
--
-- Parcels-first makes (county_id, folio) the new primary identity.
-- Multiple parcels can share a normalized mailing address (condo units,
-- gated-community addresses, PO-box situs addresses, etc.), so the
-- address-based unique constraint blocks the HCPAO loader.
--
-- Keep a non-unique index for address-based lookups (permit → parcel
-- linkage in Phase 3).

ALTER TABLE properties DROP CONSTRAINT IF EXISTS unique_property_address;

CREATE INDEX IF NOT EXISTS properties_county_normalized_address
    ON properties (county_id, normalized_address)
    WHERE normalized_address IS NOT NULL;

NOTIFY pgrst, 'reload schema';
