-- 054_security_lockdown.sql
--
-- Security audit follow-up. Three classes of fix:
--
-- 1. CLOSE THE ANON BACKDOOR on properties/permits/leads. The existing policies
--    contained `current_user_agency_id() IS NULL` which lets anon-key callers
--    (no JWT) pass through. Magic-link auth is now in place — the bypass is
--    obsolete and exposes all property/permit/lead data to anyone with the
--    public anon key (which ships in the frontend bundle).
--
-- 2. ENABLE RLS on 10 currently-unprotected tables. Five contain real secrets
--    or PII: `agencies` (Summit/GHL token), `app_settings` (Accela app secret),
--    `counties` (Accela refresh_token + access_token), `profiles` (user PII),
--    `sync_config` (GHL config). Five are internal-only and don't need user
--    visibility: `background_jobs`, `county_pull_schedules`, `hcfl_streets`,
--    `lead_status_cooldowns`, `pull_history`.
--
-- 3. PIN search_path on three SECURITY DEFINER functions to prevent
--    function-name hijacking via custom schemas.
--
-- The backend Python code uses SUPABASE_KEY (service_role JWT), which bypasses
-- RLS automatically. Frontend uses VITE_SUPABASE_ANON_KEY + magic-link JWT.
-- Authenticated users get scoped access via current_user_agency_id().

-- ============================================================================
-- 1. Replace the anon-bypass policies on properties/permits/leads
-- ============================================================================

-- Properties: SELECT scoped to own agency; INSERT/UPDATE/DELETE service-role
DROP POLICY IF EXISTS properties_select ON properties;
DROP POLICY IF EXISTS properties_insert ON properties;
DROP POLICY IF EXISTS properties_update ON properties;

CREATE POLICY properties_select ON properties FOR SELECT
  USING (
    auth.role() = 'service_role'
    OR current_user_agency_id() = (
      SELECT agency_id FROM counties WHERE counties.id = properties.county_id
    )
  );
CREATE POLICY properties_insert ON properties FOR INSERT
  WITH CHECK (auth.role() = 'service_role');
CREATE POLICY properties_update ON properties FOR UPDATE
  USING (auth.role() = 'service_role');
CREATE POLICY properties_delete ON properties FOR DELETE
  USING (auth.role() = 'service_role');

-- Permits: same shape as properties (read-only from frontend)
DROP POLICY IF EXISTS permits_select ON permits;
DROP POLICY IF EXISTS permits_insert ON permits;
DROP POLICY IF EXISTS permits_update ON permits;

CREATE POLICY permits_select ON permits FOR SELECT
  USING (
    auth.role() = 'service_role'
    OR current_user_agency_id() = (
      SELECT agency_id FROM counties WHERE counties.id = permits.county_id
    )
  );
CREATE POLICY permits_insert ON permits FOR INSERT
  WITH CHECK (auth.role() = 'service_role');
CREATE POLICY permits_update ON permits FOR UPDATE
  USING (auth.role() = 'service_role');
CREATE POLICY permits_delete ON permits FOR DELETE
  USING (auth.role() = 'service_role');

-- Leads: SELECT and UPDATE allowed to own agency; INSERT/DELETE service-role
-- (Frontend writes to leads via the status machine — UPDATE only.)
DROP POLICY IF EXISTS leads_select ON leads;
DROP POLICY IF EXISTS leads_insert ON leads;
DROP POLICY IF EXISTS leads_update ON leads;

CREATE POLICY leads_select ON leads FOR SELECT
  USING (
    auth.role() = 'service_role'
    OR current_user_agency_id() = (
      SELECT counties.agency_id
      FROM counties JOIN properties ON properties.county_id = counties.id
      WHERE properties.id = leads.property_id LIMIT 1
    )
  );
CREATE POLICY leads_update ON leads FOR UPDATE
  USING (
    auth.role() = 'service_role'
    OR current_user_agency_id() = (
      SELECT counties.agency_id
      FROM counties JOIN properties ON properties.county_id = counties.id
      WHERE properties.id = leads.property_id LIMIT 1
    )
  );
CREATE POLICY leads_insert ON leads FOR INSERT
  WITH CHECK (auth.role() = 'service_role');
CREATE POLICY leads_delete ON leads FOR DELETE
  USING (auth.role() = 'service_role');

-- ============================================================================
-- 2. Enable RLS on 10 tables + appropriate policies
-- ============================================================================

-- Sensitive config (5 tables): user can read scoped, only service_role writes
ALTER TABLE agencies ENABLE ROW LEVEL SECURITY;
CREATE POLICY agencies_select ON agencies FOR SELECT
  USING (auth.role() = 'service_role' OR id = current_user_agency_id());
CREATE POLICY agencies_modify ON agencies FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE counties ENABLE ROW LEVEL SECURITY;
CREATE POLICY counties_select ON counties FOR SELECT
  USING (auth.role() = 'service_role' OR agency_id = current_user_agency_id());
CREATE POLICY counties_modify ON counties FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profiles_select_own ON profiles FOR SELECT
  USING (auth.role() = 'service_role' OR id = auth.uid());
CREATE POLICY profiles_update_own ON profiles FOR UPDATE
  USING (auth.role() = 'service_role' OR id = auth.uid())
  WITH CHECK (auth.role() = 'service_role' OR id = auth.uid());
CREATE POLICY profiles_insert_delete_service ON profiles FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE sync_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY sync_config_select ON sync_config FOR SELECT
  USING (auth.role() = 'service_role' OR agency_id = current_user_agency_id());
CREATE POLICY sync_config_modify ON sync_config FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY app_settings_service_only ON app_settings FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- Internal tables (5): service_role only — frontend never reads/writes these
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY background_jobs_service_only ON background_jobs FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE county_pull_schedules ENABLE ROW LEVEL SECURITY;
CREATE POLICY county_pull_schedules_service_only ON county_pull_schedules FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE hcfl_streets ENABLE ROW LEVEL SECURITY;
CREATE POLICY hcfl_streets_service_only ON hcfl_streets FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE lead_status_cooldowns ENABLE ROW LEVEL SECURITY;
CREATE POLICY lead_status_cooldowns_service_only ON lead_status_cooldowns FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE pull_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY pull_history_service_only ON pull_history FOR ALL TO public
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- 3. Pin search_path on the 3 SECURITY DEFINER functions
-- ============================================================================

ALTER FUNCTION public.current_user_agency_id() SET search_path = public, pg_catalog;
ALTER FUNCTION public.touch_leads_updated_at() SET search_path = public, pg_catalog;
ALTER FUNCTION public.touch_properties_updated_at() SET search_path = public, pg_catalog;
