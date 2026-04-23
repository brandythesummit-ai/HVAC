-- Migration 027c: align leads UPDATE policy with the SELECT policy.
--
-- Migration 027 enabled RLS on leads with an UPDATE policy that
-- required auth.role() = 'service_role' OR 'authenticated'. The
-- production backend on Railway calls Supabase with the anon key
-- (SUPABASE_KEY env var), so auth.role() = 'anon' and every
-- backend-driven UPDATE was blocked with an empty result set,
-- surfacing as HTTP 500 from PATCH /api/leads/:id/status.
--
-- Fix: mirror the same escape hatch the SELECT policy already has,
-- `current_user_agency_id() IS NULL`. For V1 (single-user product)
-- this is safe because our backend is the only anon caller over a
-- CORS-restricted channel.
--
-- Follow-up for V2: switch Railway's SUPABASE_KEY to the service_role
-- key so the backend bypasses RLS, then tighten UPDATE back to
-- authenticated-only.

DROP POLICY IF EXISTS leads_update ON leads;
CREATE POLICY leads_update ON leads FOR UPDATE
    USING (
        auth.role() = 'service_role'
        OR auth.role() = 'authenticated'
        OR current_user_agency_id() IS NULL
    );
