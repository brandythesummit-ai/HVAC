-- 055_default_agency_on_signup.sql
--
-- Patches `handle_new_auth_user()` so new signups auto-link to the single V1
-- agency. Without this, the post-054 RLS lockdown would lock out every new
-- user (their profile would have agency_id = NULL → current_user_agency_id()
-- returns NULL → policies deny). The original Hillsborough user got an UPDATE
-- to set agency_id immediately after migration 054 was applied; this trigger
-- ensures future signups don't repeat the trip.
--
-- Single-tenant V1 only. When V2 multi-tenancy ships, the assignment source
-- must change (email-domain matching, invite token, JWT claim, etc.).

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'auth'
AS $$
DECLARE
    default_agency uuid;
BEGIN
    SELECT id INTO default_agency
    FROM agencies
    WHERE (SELECT COUNT(*) FROM agencies) = 1
    LIMIT 1;

    INSERT INTO public.profiles (id, display_name, agency_id)
    VALUES (NEW.id, NEW.email, default_agency)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;
