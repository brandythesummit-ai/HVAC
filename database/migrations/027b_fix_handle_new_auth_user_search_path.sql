-- Migration 027b: Fix search_path in handle_new_auth_user trigger.
--
-- Migration 027 created the trigger but without an explicit search_path.
-- When the trigger fires from the auth schema context (which it does —
-- it's `AFTER INSERT ON auth.users`), unqualified `profiles` references
-- resolve against the auth schema first, and `auth.profiles` doesn't
-- exist — so every new user signup fails with
--   "relation profiles does not exist (SQLSTATE 42P01)"
-- and the Supabase Auth API returns
--   "500: Database error saving new user"
--
-- Fix (belt + suspenders):
--   1. Fully-qualify the INSERT target as `public.profiles`
--   2. Declare SET search_path = public, auth on the function so any
--      future unqualified references still resolve correctly.

CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
   SECURITY DEFINER
   SET search_path = public, auth;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
