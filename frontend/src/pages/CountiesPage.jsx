/**
 * CountiesPage — HCFL Accela connection management.
 *
 * V1 is single-county (HCFL), so this page simply renders the
 * CountyDetailPanel directly — no list, no accordion. The panel
 * exposes both password-grant and OAuth-popup auth methods, which
 * is the familiar setup-with-login UI the user has used in the past.
 *
 * Milestone 15 deleted the earlier multi-county CountiesPage; this
 * file restores a minimal single-county variant so Accela can be
 * re-authenticated without leaving the app.
 */
import { useCounties } from '../hooks/useCounties';
import CountyDetailPanel from '../components/counties/CountyDetailPanel';
import ViewToggle from '../components/shared/ViewToggle';

export default function CountiesPage() {
  const { data: counties, isLoading, error } = useCounties();

  const hcfl = Array.isArray(counties)
    ? counties.find((c) => c.county_code === 'HCFL') || counties[0]
    : null;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <ViewToggle />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto py-6 px-4">
          <h1 className="text-2xl font-semibold text-gray-900 mb-1">
            County connection
          </h1>
          <p className="text-sm text-gray-600 mb-6">
            Manage the Accela login and pull status for Hillsborough County.
          </p>
          {isLoading && <div className="text-gray-500">Loading…</div>}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              Failed to load county: {error.message}
            </div>
          )}
          {hcfl && (
            <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
              <CountyDetailPanel county={hcfl} onClose={() => { /* page view, not modal */ }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
