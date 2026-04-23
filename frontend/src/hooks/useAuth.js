/**
 * Auth hook — exposes {session, user, loading, signOut}.
 *
 * Subscribes to Supabase's onAuthStateChange so the UI reacts
 * immediately when the user completes the magic-link flow.
 */
import { useEffect, useState } from 'react';
import { supabase } from '../api/supabase';

export function useAuth() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (mounted) {
        setSession(data.session);
        setLoading(false);
      }
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      if (mounted) {
        setSession(newSession);
      }
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return {
    session,
    user: session?.user ?? null,
    loading,
    signOut,
  };
}
