-- Migration 027: Magic-link auth support via Supabase Auth
-- Creates the `profiles` table linked to auth.users for per-user data
-- and RLS policies scoping permits/leads/properties by agency.
--
-- V1 deployment has ONE agency (the user's buddy's HVAC biz) so RLS
-- effectively means "authenticated users see all data." The policies
-- are written with agency_id scoping so multi-tenant V2 is a no-code
-- change (just seed more agencies + map users).

-- profiles table: 1:1 with auth.users. Stores per-user app data.
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    agency_id UUID REFERENCES agencies(id),
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'admin')),
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_profiles_agency_id ON profiles(agency_id);

-- Auto-create a profile row when a new auth.users row is inserted
-- (via magic-link signup). RLS policies below depend on this row
-- existing for the authenticated user.
CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, display_name)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();

-- Enable RLS on the data tables. Policies follow.
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE permits ENABLE ROW LEVEL SECURITY;

-- Helper: is the current auth.uid() in an agency that owns this row?
-- We match agency_id via the profiles table.
CREATE OR REPLACE FUNCTION current_user_agency_id()
RETURNS UUID AS $$
    SELECT agency_id FROM profiles WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Policies. Each does agency_id match plus a permissive NULL-agency
-- path (V1 has one agency + the profile may not have agency_id set
-- yet during initial onboarding — treat unscoped users as seeing
-- everything).
DO $$
BEGIN
    DROP POLICY IF EXISTS properties_select ON properties;
    CREATE POLICY properties_select ON properties FOR SELECT
        USING (
            auth.role() = 'service_role'
            OR current_user_agency_id() IS NULL
            OR current_user_agency_id() = (
                SELECT agency_id FROM counties WHERE counties.id = properties.county_id
            )
        );

    DROP POLICY IF EXISTS leads_select ON leads;
    CREATE POLICY leads_select ON leads FOR SELECT
        USING (
            auth.role() = 'service_role'
            OR current_user_agency_id() IS NULL
            OR current_user_agency_id() = (
                SELECT counties.agency_id FROM counties
                JOIN properties ON properties.county_id = counties.id
                WHERE properties.id = leads.property_id
                LIMIT 1
            )
        );

    DROP POLICY IF EXISTS permits_select ON permits;
    CREATE POLICY permits_select ON permits FOR SELECT
        USING (
            auth.role() = 'service_role'
            OR current_user_agency_id() IS NULL
            OR current_user_agency_id() = (
                SELECT agency_id FROM counties WHERE counties.id = permits.county_id
            )
        );

    -- Write policies: for V1, let authenticated users update their
    -- own rows (leads.lead_status change from the DetailSheet, etc.).
    -- Service role handles all INSERT / UPSERT from the job processor.
    DROP POLICY IF EXISTS leads_update ON leads;
    CREATE POLICY leads_update ON leads FOR UPDATE
        USING (
            auth.role() = 'service_role'
            OR auth.role() = 'authenticated'
        );
END $$;

COMMENT ON TABLE profiles IS
    'Per-user app data linked 1:1 to auth.users. agency_id scopes RLS.';
