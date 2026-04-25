-- 051_permits_parcel_number.sql
--
-- Add `permits.parcel_number` column for direct property linkage.
--
-- WHY: Address-string joins between permits and properties produce ~24K orphan
-- permits where the parser fell through to city/county (e.g., "HILLSBOROUGH COUNTY",
-- "BRANDON") and never matches a real parcel. Both Accela (raw_data->parcels[0])
-- and the legacy scraper (raw_data->parsed_fields->Parcel) carry parcel numbers
-- in raw_data but never write them to a top-level column. Lifting parcel_number
-- to a real column lets us join on (county_id, parcel_number) — the canonical
-- 1:1 cross-reference — instead of fragile address normalization.
--
-- Format note: parcel numbers normalize to alphanumeric-uppercase (strip "."
-- and any other separators). HCPAO stores "0563620556"; Accela returns
-- "056362.0556"; both reduce to "0563620556" after normalization.

ALTER TABLE permits
  ADD COLUMN IF NOT EXISTS parcel_number TEXT;

CREATE INDEX IF NOT EXISTS idx_permits_county_parcel
  ON permits(county_id, parcel_number)
  WHERE parcel_number IS NOT NULL;

COMMENT ON COLUMN permits.parcel_number IS
  'Normalized alphanumeric parcel number, sourced from raw_data per source. '
  'Used to join permits to properties.parcel_number when address-string join fails. '
  'Backfilled by scripts/backfill_permits_parcel_number.py and populated on insert by '
  'job_processor._enrich_permit_data (Accela) and hcfl_legacy_scraper.parse_permit_detail (legacy).';
