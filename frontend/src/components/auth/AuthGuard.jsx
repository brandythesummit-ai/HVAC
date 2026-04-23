/**
 * AuthGuard — wraps authed routes. Shows a loading splash while the
 * session hydrates, the magic-link login form when not signed in,
 * and the child content once authenticated.
 */
import MagicLinkLogin from './MagicLinkLogin';
import { useAuth } from '../../hooks/useAuth';

export default function AuthGuard({ children }) {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-slate-500">Loading…</div>
      </div>
    );
  }

  if (!session) {
    return <MagicLinkLogin />;
  }

  return children;
}
