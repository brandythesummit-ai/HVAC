-- 031: scrape priority for hcfl_streets so the job processor hits
-- high-value residential streets (KENNEDY, DALE MABRY, etc) before
-- Tampa's long tail of ordinal numbered avenues (110TH, 111TH, ...).
--
-- First live run spent 6+ minutes processing 25 ordinal streets with
-- 5,789 observed permits and zero HVAC matches — the named residential
-- streets are where the HVAC prefixes (FCM, NMC, NME) actually live.

ALTER TABLE hcfl_streets ADD COLUMN IF NOT EXISTS scrape_priority INTEGER NOT NULL DEFAULT 10;

-- Priority tiers:
--   1  = known HVAC-active named residential corridors (from M4 + M9)
--   10 = default for named streets
--   100 = ordinal numbered streets (10TH, 101ST, etc.) — lowest priority
UPDATE hcfl_streets SET scrape_priority = 1 WHERE street_name IN (
    'KENNEDY', 'DALE MABRY', 'BUSCH', 'NEBRASKA', 'HOWARD',
    'HARBOUR ISLAND', 'BAYSHORE', 'COLUMBUS', 'HILLSBOROUGH',
    'LINEBAUGH', 'ARMENIA', 'HIMES', 'WATERS', 'FLORIDA',
    'FLETCHER', 'FOWLER', 'MEMORIAL', 'BRUCE B DOWNS',
    'PLATT', 'AZEELE', 'SWANN', 'SLIGH', 'TAMPA', 'GANDY'
);

UPDATE hcfl_streets SET scrape_priority = 100
WHERE scrape_priority = 10 AND street_name ~ '^[0-9]';
