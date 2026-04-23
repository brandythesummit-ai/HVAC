-- 032: INSERT/UPDATE policies on permits, properties, leads.
--
-- Root cause: migration 027 enabled RLS on these three tables with
-- only SELECT policies (using the `current_user_agency_id() IS NULL`
-- escape hatch for the anon-key backend). INSERT/UPDATE/DELETE were
-- never policy-granted, so they're denied by default.
--
-- Surfaced live when the HCFL legacy scraper started running in
-- production: every permit upsert failed with
--   "new row violates row-level security policy for table permits"
--   (SQLSTATE 42501)
-- Over 60 HVAC permits (NME*, NMC* prefixes on KENNEDY / DALE MABRY
-- et al) were blocked in the first minute.
--
-- Fix: mirror the SELECT escape hatch on INSERT/UPDATE. Same
-- reasoning as 027c — V1 safe because backend is the only anon
-- caller over CORS-protected channels. V2 should migrate Railway
-- to service_role and tighten write policies to authenticated-only.

DROP POLICY IF EXISTS permits_insert ON permits;
CREATE POLICY permits_insert ON permits FOR INSERT WITH CHECK (
    auth.role() = 'service_role'
    OR auth.role() = 'authenticated'
    OR current_user_agency_id() IS NULL
);

DROP POLICY IF EXISTS permits_update ON permits;
CREATE POLICY permits_update ON permits FOR UPDATE USING (
    auth.role() = 'service_role'
    OR auth.role() = 'authenticated'
    OR current_user_agency_id() IS NULL
);

DROP POLICY IF EXISTS properties_insert ON properties;
CREATE POLICY properties_insert ON properties FOR INSERT WITH CHECK (
    auth.role() = 'service_role'
    OR auth.role() = 'authenticated'
    OR current_user_agency_id() IS NULL
);

DROP POLICY IF EXISTS properties_update ON properties;
CREATE POLICY properties_update ON properties FOR UPDATE USING (
    auth.role() = 'service_role'
    OR auth.role() = 'authenticated'
    OR current_user_agency_id() IS NULL
);

DROP POLICY IF EXISTS leads_insert ON leads;
CREATE POLICY leads_insert ON leads FOR INSERT WITH CHECK (
    auth.role() = 'service_role'
    OR auth.role() = 'authenticated'
    OR current_user_agency_id() IS NULL
);
