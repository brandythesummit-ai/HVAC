import { X, CheckCircle, AlertCircle, Clock, RefreshCw, Calendar, BarChart3, Send, HelpCircle, Trash2, Key, ExternalLink, Loader2 } from 'lucide-react';
import { useCountyMetrics, useCountyPullStatus, useDeleteCounty, useSetupCountyWithPassword, useGetOAuthUrl, useUpdateCounty } from '../../hooks/useCounties';
import { formatRelativeTime } from '../../utils/formatters';
import { useState } from 'react';

export default function CountyDetailPanel({ county, onClose }) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showCredentialForm, setShowCredentialForm] = useState(false);
  const [authMethod, setAuthMethod] = useState('password');
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [countyCode, setCountyCode] = useState(county.county_code || '');

  const { data: metrics, isLoading: metricsLoading } = useCountyMetrics(county.id);
  const { data: pullStatus } = useCountyPullStatus(county.id);
  const deleteCounty = useDeleteCounty();
  const setupWithPassword = useSetupCountyWithPassword();
  const getOAuthUrl = useGetOAuthUrl();
  const updateCounty = useUpdateCounty();

  const getPlatformBadgeClass = () => {
    const platform = county.platform || 'Unknown';
    const colors = {
      'Accela': 'badge-success',
      'EnerGov': 'text-purple-700 bg-purple-100',
      'eTRAKiT': 'text-orange-700 bg-orange-100',
      'Tyler': 'text-indigo-700 bg-indigo-100',
      'OpenGov': 'text-green-700 bg-green-100',
      'Custom': 'text-gray-700 bg-gray-100',
      'Unknown': 'badge badge-secondary'
    };
    return `badge ${colors[platform] || 'badge-secondary'}`;
  };

  const handleDelete = async () => {
    try {
      await deleteCounty.mutateAsync(county.id);
      setShowDeleteConfirm(false);
      onClose(); // Close panel after deleting
    } catch {
      // Deletion failed - error handled by mutation
    }
  };

  const handleCredentialChange = (e) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
  };

  const handlePasswordSetup = async (e) => {
    e.preventDefault();

    try {
      // Update county_code if provided and different
      if (countyCode && countyCode !== county.county_code) {
        await updateCounty.mutateAsync({
          id: county.id,
          data: { county_code: countyCode }
        });
      }

      // Setup OAuth with password grant
      await setupWithPassword.mutateAsync({
        id: county.id,
        credentials: {
          username: credentials.username,
          password: credentials.password,
          scope: 'records'
        }
      });

      // Reset form on success - panel will auto-update via React Query invalidation
      setShowCredentialForm(false);
      setCredentials({ username: '', password: '' });
    } catch {
      // Error handled by mutation
    }
  };

  const handleOAuthPopup = async () => {
    try {
      // Update county_code first if needed
      if (countyCode && countyCode !== county.county_code) {
        await updateCounty.mutateAsync({
          id: county.id,
          data: { county_code: countyCode }
        });
      }

      const result = await getOAuthUrl.mutateAsync(county.id);
      const authUrl = result.authorization_url || result.data?.authorization_url;
      if (authUrl) {
        window.open(authUrl, '_blank', 'width=600,height=700');
      }
    } catch {
      // Error handled by mutation
    }
  };

  // Check if OAuth setup is in progress
  const isSettingUp = setupWithPassword.isPending || getOAuthUrl.isPending || updateCounty.isPending;
  const setupError = setupWithPassword.error || getOAuthUrl.error || updateCounty.error;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-25 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-50 overflow-y-auto animate-slide-in-right">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-gray-900 truncate">{county.name}</h2>
            <p className="text-sm text-gray-500 mt-1">
              {county.state} • {county.county_code || 'No code'} • {county.platform || 'Unknown'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 ml-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Content - reusing CountyCard sections */}
        <div className="p-6 space-y-6">
          {/* Platform badge */}
          {county.platform && (
            <div className="flex items-center space-x-2">
              <span className={getPlatformBadgeClass()}>
                {county.platform_confidence === 'Confirmed' && county.platform !== 'Unknown' && (
                  <CheckCircle className="h-3 w-3 mr-1 inline" />
                )}
                {county.platform === 'Unknown' && (
                  <HelpCircle className="h-3 w-3 mr-1 inline" />
                )}
                {county.platform}
              </span>
              {county.platform_confidence && county.platform !== 'Unknown' && (
                <span className="text-xs text-gray-500">({county.platform_confidence})</span>
              )}
            </div>
          )}

          {/* Metrics Section (reused from CountyCard lines 199-229) */}
          {county.oauth_authorized && metrics && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">📊 Metrics</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="flex items-center justify-center mb-1">
                    <BarChart3 className="h-4 w-4 text-blue-600" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">
                    {metricsLoading ? '-' : metrics.total_permits || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Total Permits</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center mb-1">
                    <AlertCircle className="h-4 w-4 text-yellow-600" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">
                    {metricsLoading ? '-' : metrics.new_leads || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">New Leads</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center mb-1">
                    <Send className="h-4 w-4 text-green-600" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900">
                    {metricsLoading ? '-' : metrics.sent_to_summit || 0}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Sent to Summit.AI</p>
                </div>
              </div>
            </div>
          )}

          {/* Pull Status Section (reused from CountyCard lines 232-323) */}
          {county.oauth_authorized && pullStatus && (
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              {/* Initial Pull Progress */}
              {pullStatus.initial_pull_progress !== null && !pullStatus.initial_pull_completed && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center text-sm font-medium text-blue-700">
                      <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      30-Year Historical Pull
                    </div>
                    {pullStatus.years_info ? (
                      <div className="text-sm font-semibold text-blue-700">
                        <div className="text-right">
                          {pullStatus.years_info.current_year && (
                            <div>Processing {pullStatus.years_info.current_year}</div>
                          )}
                          <div className="text-xs">
                            {pullStatus.years_info.years_completed} of {pullStatus.years_info.total_years} years
                          </div>
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm font-semibold text-blue-700">
                        {pullStatus.initial_pull_progress}%
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${pullStatus.initial_pull_progress}%` }}
                    ></div>
                  </div>
                  {pullStatus.years_info && (
                    <div className="text-xs text-gray-500 mt-1">
                      {pullStatus.years_info.start_year}–{pullStatus.years_info.end_year}
                    </div>
                  )}
                </div>
              )}

              {/* Initial Pull Complete */}
              {pullStatus.initial_pull_completed && (
                <div className="flex items-center text-sm text-green-700 mb-2">
                  <CheckCircle className="h-4 w-4 mr-1.5" />
                  Historical pull complete
                </div>
              )}

              {/* Next Pull Schedule with Status */}
              {pullStatus.auto_pull_enabled && pullStatus.next_pull_at && (
                <div>
                  <div className="flex items-center text-sm text-gray-600">
                    <Calendar className="h-3.5 w-3.5 mr-1.5" />
                    Next auto-pull: {formatRelativeTime(pullStatus.next_pull_at)}
                  </div>

                  {pullStatus.last_pull_status && (
                    <div className="flex items-center text-xs mt-1">
                      {pullStatus.last_pull_status === 'success' && (
                        <span className="flex items-center text-green-600">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Last pull successful
                        </span>
                      )}
                      {pullStatus.last_pull_status === 'failed' && (
                        <span className="flex items-center text-red-600">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          Last pull failed
                        </span>
                      )}
                      {pullStatus.last_pull_status === 'pending' && (
                        <span className="flex items-center text-yellow-600">
                          <Clock className="h-3 w-3 mr-1" />
                          Pull pending
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Last Pull Stats */}
              {pullStatus.last_pull_at && pullStatus.last_pull_permits > 0 && (
                <div className="flex items-center text-xs text-gray-500 mt-1.5">
                  Last pull: {pullStatus.last_pull_permits} permits • {formatRelativeTime(pullStatus.last_pull_at)}
                </div>
              )}
            </div>
          )}

          {/* Legacy Last Pull Time */}
          {county.last_pull_at && !pullStatus && (
            <div className="flex items-center text-sm text-gray-500">
              <Clock className="h-4 w-4 mr-1.5" />
              Last pull: {formatRelativeTime(county.last_pull_at)}
            </div>
          )}

          {/* Authorization Section */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">🔌 Authorization</h3>
            {county.oauth_authorized ? (
              <div className="space-y-2">
                <div className="flex items-center text-sm text-green-700">
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Authorized with Accela
                </div>
                {county.last_pull_at && (
                  <p className="text-sm text-gray-600">
                    Connected: {formatRelativeTime(county.last_pull_at)}
                  </p>
                )}
              </div>
            ) : (
              // Not authorized - show configuration form or button
              <div className="space-y-4">
                {/* Check if this platform supports Accela */}
                {county.platform === 'Accela' || county.platform === 'Unknown' ? (
                  <>
                    {!showCredentialForm ? (
                      // Initial state: Show "Connect to Accela" button
                      <button
                        onClick={() => setShowCredentialForm(true)}
                        className="btn-primary w-full flex items-center justify-center"
                      >
                        <Key className="h-4 w-4 mr-2" />
                        Connect to Accela
                      </button>
                    ) : (
                      // Expanded state: Show credential configuration form
                      <div className="space-y-4">
                        {/* County Code field (if not already set) */}
                        {!county.county_code && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                              Accela Agency Code
                            </label>
                            <input
                              type="text"
                              value={countyCode}
                              onChange={(e) => setCountyCode(e.target.value.toUpperCase())}
                              placeholder="e.g., HCFL"
                              className="input-field"
                            />
                            <p className="mt-1 text-xs text-gray-500">
                              The Accela agency code for this county (all caps)
                            </p>
                          </div>
                        )}

                        {/* Auth method toggle */}
                        <div className="flex gap-2 p-1 bg-gray-100 rounded-lg">
                          <button
                            type="button"
                            onClick={() => setAuthMethod('password')}
                            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                              authMethod === 'password'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-600 hover:text-gray-900'
                            }`}
                          >
                            <Key className="h-4 w-4 inline mr-1.5" />
                            Password
                          </button>
                          <button
                            type="button"
                            onClick={() => setAuthMethod('oauth')}
                            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                              authMethod === 'oauth'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-600 hover:text-gray-900'
                            }`}
                          >
                            <ExternalLink className="h-4 w-4 inline mr-1.5" />
                            OAuth Popup
                          </button>
                        </div>

                        {/* Password Method Form */}
                        {authMethod === 'password' && (
                          <form onSubmit={handlePasswordSetup} className="space-y-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                Accela Username/Email
                              </label>
                              <input
                                type="email"
                                name="username"
                                value={credentials.username}
                                onChange={handleCredentialChange}
                                placeholder="user@example.com"
                                className="input-field"
                                required
                                disabled={isSettingUp}
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                Accela Password
                              </label>
                              <input
                                type="password"
                                name="password"
                                value={credentials.password}
                                onChange={handleCredentialChange}
                                placeholder="••••••••"
                                className="input-field"
                                required
                                disabled={isSettingUp}
                              />
                              <p className="mt-1 text-xs text-gray-500">
                                Your password is sent directly to Accela and never stored
                              </p>
                            </div>

                            {/* Error Message */}
                            {setupError && (
                              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <div className="flex items-start">
                                  <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                                  <p className="text-sm text-red-800">
                                    {setupError.response?.data?.error || setupError.message || 'Failed to connect'}
                                  </p>
                                </div>
                              </div>
                            )}

                            {/* Action Buttons */}
                            <div className="flex gap-2 pt-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setShowCredentialForm(false);
                                  setCredentials({ username: '', password: '' });
                                }}
                                className="btn-secondary flex-1"
                                disabled={isSettingUp}
                              >
                                Cancel
                              </button>
                              <button
                                type="submit"
                                disabled={isSettingUp || (!county.county_code && !countyCode)}
                                className="btn-primary flex-1"
                              >
                                {isSettingUp ? (
                                  <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Connecting...
                                  </>
                                ) : (
                                  'Connect County'
                                )}
                              </button>
                            </div>
                          </form>
                        )}

                        {/* OAuth Popup Method */}
                        {authMethod === 'oauth' && (
                          <div className="space-y-3">
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                              <p className="text-sm text-blue-800">
                                You'll be taken to Accela's login page in a new window.
                              </p>
                            </div>

                            {/* Error Message */}
                            {setupError && (
                              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <div className="flex items-start">
                                  <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                                  <p className="text-sm text-red-800">
                                    {setupError.response?.data?.error || setupError.message || 'Failed to get authorization URL'}
                                  </p>
                                </div>
                              </div>
                            )}

                            {/* Action Buttons */}
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setShowCredentialForm(false);
                                }}
                                className="btn-secondary flex-1"
                                disabled={isSettingUp}
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={handleOAuthPopup}
                                disabled={isSettingUp || (!county.county_code && !countyCode)}
                                className="btn-primary flex-1"
                              >
                                {isSettingUp ? (
                                  <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Loading...
                                  </>
                                ) : (
                                  <>
                                    Authorize with Accela
                                    <ExternalLink className="h-4 w-4 ml-2" />
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  // Non-Accela platform - show different message
                  <div className="text-sm text-gray-600 space-y-2">
                    <p>This county uses <strong>{county.platform}</strong>.</p>
                    <p className="text-gray-500">Accela integration is not available for this platform.</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Platform Details */}
          {county.county_code && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">🌐 Platform Details</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">Agency Code:</span>{' '}
                  <span className="font-mono text-gray-900">{county.county_code}</span>
                </div>
                {county.permit_portal_url && (
                  <div className="break-all">
                    <span className="text-gray-600">Portal:</span>{' '}
                    <a
                      href={county.permit_portal_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {county.permit_portal_url}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Actions */}
          {county.oauth_authorized && (
            <div className="pt-4 border-t border-gray-200">
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="btn-secondary w-full text-red-600 hover:bg-red-50 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete County
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-gray-900 bg-opacity-50">
          <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl animate-slide-in">
            <div className="px-6 py-6">
              <div className="flex items-start mb-4">
                <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-full mr-4">
                  <Trash2 className="h-6 w-6 text-red-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    Delete {county.name}?
                  </h3>
                  <p className="text-sm text-gray-600">
                    This will permanently delete this county connection.
                    All permits and leads will be preserved in the system.
                  </p>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-yellow-800">
                  <strong>Warning:</strong> This action cannot be undone.
                </p>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="btn-secondary"
                  disabled={deleteCounty.isPending}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteCounty.isPending}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-sm"
                >
                  {deleteCounty.isPending ? 'Deleting...' : 'Delete County'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
