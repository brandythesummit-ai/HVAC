-- 057_rls_perf_fix.sql
--
-- RLS performance fix. After 054 enabled RLS on leads/properties/permits and
-- the year_built fallback grew the leads table from ~12K to 391K rows, even
-- a `SELECT id FROM leads LIMIT 5` started timing out at the 8s authenticator
-- statement_timeout — including service-role calls from the backend.
--
-- Cause: the existing policies put `auth.role() = 'service_role' OR <correlated
-- subquery>` in a single USING clause. Postgres evaluates `auth.role()` once
-- per row instead of once per query, and the OR with a correlated subquery
-- prevents the planner from pushing LIMIT past the join — so even when the
-- caller IS service_role and the policy should short-circuit, the planner
-- still considers the heavy branch.
--
-- Fix per Supabase's RLS perf guide:
-- 1. Wrap auth.role() in `(SELECT auth.role())` to make it an InitPlan
--    (evaluated once, cached for the whole query)
-- 2. Split into separate per-role policies. Postgres OR's policies natively,
--    so this is semantically equivalent but lets the planner short-circuit
--    on service_role without ever touching the agency-scoped branch.

-- ============================================================================
-- LEADS
-- ============================================================================
DROP POLICY IF EXISTS leads_select ON leads;
DROP POLICY IF EXISTS leads_update ON leads;

CREATE POLICY leads_select_service ON leads FOR SELECT
  USING ((SELECT auth.role()) = 'service_role');

CREATE POLICY leads_select_agency ON leads FOR SELECT
  USING (
    current_user_agency_id() = (
      SELECT counties.agency_id
      FROM counties JOIN properties ON properties.county_id = counties.id
      WHERE properties.id = leads.property_id LIMIT 1
    )
  );

CREATE POLICY leads_update_service ON leads FOR UPDATE
  USING ((SELECT auth.role()) = 'service_role');

CREATE POLICY leads_update_agency ON leads FOR UPDATE
  USING (
    current_user_agency_id() = (
      SELECT counties.agency_id
      FROM counties JOIN properties ON properties.county_id = counties.id
      WHERE properties.id = leads.property_id LIMIT 1
    )
  );

-- ============================================================================
-- PROPERTIES
-- ============================================================================
DROP POLICY IF EXISTS properties_select ON properties;

CREATE POLICY properties_select_service ON properties FOR SELECT
  USING ((SELECT auth.role()) = 'service_role');

CREATE POLICY properties_select_agency ON properties FOR SELECT
  USING (
    current_user_agency_id() = (
      SELECT agency_id FROM counties WHERE counties.id = properties.county_id
    )
  );

-- ============================================================================
-- PERMITS
-- ============================================================================
DROP POLICY IF EXISTS permits_select ON permits;

CREATE POLICY permits_select_service ON permits FOR SELECT
  USING ((SELECT auth.role()) = 'service_role');

CREATE POLICY permits_select_agency ON permits FOR SELECT
  USING (
    current_user_agency_id() = (
      SELECT agency_id FROM counties WHERE counties.id = permits.county_id
    )
  );
