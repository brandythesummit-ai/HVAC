/**
 * Magic-link login screen.
 *
 * Mobile-first single-column layout. User enters email → Supabase
 * sends a magic link → tap link → session established → redirected
 * to the Map view.
 *
 * No password field by design (per grill-session §6):
 *   "I am good with magic links for now but will want google sso or
 *    similar in the future"
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { supabase } from '../../api/supabase';

export default function MagicLinkLogin() {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      toast.error('Enter your email');
      return;
    }
    setSubmitting(true);
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email: trimmed,
        options: {
          emailRedirectTo: `${window.location.origin}/map`,
        },
      });
      if (error) throw error;
      setSent(true);
      toast.success('Magic link sent — check your email');
    } catch (err) {
      console.error('Magic link error', err);
      toast.error(err.message || 'Failed to send magic link');
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50">
        <div className="max-w-md w-full bg-white rounded-xl shadow p-8 text-center">
          <h1 className="text-2xl font-bold mb-2">Check your email</h1>
          <p className="text-slate-600 mb-4">
            We sent a magic link to <strong>{email}</strong>. Tap it on
            this device to sign in.
          </p>
          <button
            onClick={() => { setSent(false); setEmail(''); }}
            className="text-blue-600 underline"
          >
            Use a different email
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50">
      <div className="max-w-md w-full bg-white rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-2">HVAC Lead Gen</h1>
        <p className="text-slate-600 mb-6">Sign in with your email.</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            autoComplete="email"
            required
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none"
          />
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
          >
            {submitting ? 'Sending…' : 'Send magic link'}
          </button>
        </form>
      </div>
    </div>
  );
}
