-- Migration 028: DESTRUCTIVE — Remove 8 non-HCFL counties
--
-- ================================================================
-- ⚠️  THIS MIGRATION DELETES DATA ⚠️
-- ================================================================
-- Per user direction (grill-me session, 2026-04-21):
--   "Kill the other eight counties."
--
-- Pre-deletion snapshot (qrrfjfoirfyjxqicsold on 2026-04-22):
--   county_code | permits | leads | note
--   ------------+---------+-------+------------------------------
--   BOCC        |       0 |     0 | Charlotte County — unused shell
--   HCFL        |  19,549 | 11,800| ⭐ KEEP — the production county
--   LEECO       |       0 |     0 | Lee County — unused shell
--   LEONCO      |       0 |     0 | Leon County — unused shell
--   MARTINCO    |       0 |     0 | Martin County — unused shell
--   PASCO       |       0 |     0 | Pasco County — unused shell
--   PINELLAS    |       0 |     0 | Pinellas County — unused shell
--   POLKCO      |       0 |     0 | Polk County — unused shell
--   SARASOTA    |       0 |     0 | Sarasota County — unused shell
--
-- All 8 counties targeted have ZERO permits and ZERO leads, so this
-- migration deletes only metadata (OAuth token shells, county config
-- rows). No permit or lead data is lost.
--
-- Safety approach:
--   1. Refuse to run if HCFL has unexpectedly low permit count.
--   2. Explicit county_code list (not a negative match on HCFL) so
--      a future typo in HCFL's code doesn't silently wipe it.
--   3. CASCADE-safe: counties' FK relationships to permits, leads,
--      and background_jobs use ON DELETE CASCADE already, so
--      removing a county with data would cascade-delete its permits.
--      Our explicit zero-count check catches that before it starts.

DO $$
DECLARE
    hcfl_permit_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO hcfl_permit_count
    FROM permits p
    JOIN counties c ON c.id = p.county_id
    WHERE c.county_code = 'HCFL';

    IF hcfl_permit_count < 10000 THEN
        RAISE EXCEPTION 'Refusing to run: HCFL has only % permits (expected >= 10000). '
                        'Migration aborted to prevent accidental data loss.',
                        hcfl_permit_count;
    END IF;

    -- Defensive zero-data check on targeted counties
    IF EXISTS (
        SELECT 1 FROM counties c
        WHERE c.county_code IN ('BOCC','LEECO','LEONCO','MARTINCO','PASCO','PINELLAS','POLKCO','SARASOTA')
          AND EXISTS (SELECT 1 FROM permits WHERE permits.county_id = c.id)
    ) THEN
        RAISE EXCEPTION 'Refusing to run: one of the targeted non-HCFL counties has permits. '
                        'Investigate before retrying.';
    END IF;
END $$;

-- Delete. CASCADE handles the metadata chain:
--   counties → county_pull_schedules, county_refresh_tokens, etc.
-- FKs with ON DELETE CASCADE, already defined in migrations 001-015.
DELETE FROM counties
WHERE county_code IN (
    'BOCC',
    'LEECO',
    'LEONCO',
    'MARTINCO',
    'PASCO',
    'PINELLAS',
    'POLKCO',
    'SARASOTA'
);

-- Post-deletion sanity check: should have exactly 1 county left (HCFL)
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_count FROM counties;
    IF remaining_count != 1 THEN
        RAISE EXCEPTION 'Post-deletion sanity check failed: expected 1 county, found %',
                        remaining_count;
    END IF;
END $$;

COMMENT ON TABLE counties IS
    'County configurations. V1 is HCFL-only (Hillsborough County, FL). '
    'Migration 028 removed 8 dead county shells. Multi-tenant primitives '
    'preserved for V2 where new counties will be onboarded.';
