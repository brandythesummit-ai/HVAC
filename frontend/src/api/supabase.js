/**
 * Supabase client for frontend auth + data queries.
 *
 * Auth flow: magic-link email sign-in via Supabase Auth.
 * Session persists in localStorage, auto-refreshed by the SDK.
 *
 * Required env vars (set in Vercel + local .env):
 *   VITE_SUPABASE_URL
 *   VITE_SUPABASE_ANON_KEY
 *
 * Session length: configure in Supabase Dashboard → Auth → Settings
 * → JWT expiry. Design doc §6 calls for 30 days.
 */
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  // Not throwing — during dev a missing env means no auth, not a crash.
  console.warn(
    '[auth] VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY not set. ' +
    'Auth will be unavailable. Add them to .env (local) or Vercel env.',
  );
}

export const supabase = createClient(
  SUPABASE_URL || 'http://localhost:54321',
  SUPABASE_ANON_KEY || 'public-anon-key-placeholder',
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
    },
  },
);
