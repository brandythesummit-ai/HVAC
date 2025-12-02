import { useState } from 'react';
import { MapPin, Download, AlertCircle, CheckCircle, Clock, ExternalLink, BarChart3, Send, Trash2, Database, RefreshCw, Calendar, HelpCircle, Shield } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import { useCountyMetrics, useGetOAuthUrl, useDeleteCounty, useCountyPullStatus, useUpdateCountyPlatform } from '../../hooks/useCounties';

const CountyCard = ({ county }) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showPlatformSelect, setShowPlatformSelect] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const { data: metrics, isLoading: metricsLoading } = useCountyMetrics(county.id);
  const { data: pullStatus } = useCountyPullStatus(county.id);
  const getOAuthUrl = useGetOAuthUrl();
  const deleteCounty = useDeleteCounty();
  const updatePlatform = useUpdateCountyPlatform();

  const platformOptions = [
    { value: 'Accela', label: 'Accela', color: 'text-blue-700 bg-blue-100' },
    { value: 'EnerGov', label: 'EnerGov (Tyler)', color: 'text-purple-700 bg-purple-100' },
    { value: 'eTRAKiT', label: 'eTRAKiT (Central Square)', color: 'text-orange-700 bg-orange-100' },
    { value: 'Tyler', label: 'Tyler Technologies', color: 'text-indigo-700 bg-indigo-100' },
    { value: 'OpenGov', label: 'OpenGov', color: 'text-green-700 bg-green-100' },
    { value: 'Custom', label: 'Custom System', color: 'text-gray-700 bg-gray-100' },
  ];

  const handleAuthorize = async () => {
    try {
      const { authorization_url } = await getOAuthUrl.mutateAsync(county.id);
      window.open(authorization_url, '_blank', 'width=600,height=700');
    } catch {
      // OAuth authorization failed - error handled by mutation
    }
  };

  const handleDelete = async () => {
    try {
      await deleteCounty.mutateAsync(county.id);
      setShowDeleteConfirm(false);
    } catch {
      // County deletion failed - error handled by mutation
    }
  };

  const handlePlatformUpdate = async () => {
    if (!selectedPlatform) return;

    try {
      await updatePlatform.mutateAsync({
        countyId: county.id,
        platform: selectedPlatform,
        platform_confidence: 'Confirmed',
        platform_detection_notes: 'Manually set by user'
      });
      setShowPlatformSelect(false);
      setSelectedPlatform('');
    } catch {
      // Platform update failed - error handled by mutation
    }
  };

  const getPlatformBadgeClass = () => {
    const platform = county.platform || 'Unknown';
    const colors = {
      'Accela': 'badge-success',
      'EnerGov': 'text-purple-700 bg-purple-100',
      'eTRAKiT': 'text-orange-700 bg-orange-100',
      'Tyler': 'text-indigo-700 bg-indigo-100',
      'OpenGov': 'text-green-700 bg-green-100',
      'Custom': 'text-gray-700 bg-gray-100',
      'Unknown': 'badge-secondary'
    };
    return `badge ${colors[platform] || 'badge-secondary'}`;
  };

  const getStatusBadgeClass = () => {
    if (county.oauth_authorized) {
      return 'badge badge-success';
    }
    return 'badge badge-warning';
  };

  const getStatusText = () => {
    if (county.oauth_authorized) {
      return 'Authorized';
    }
    return 'Not Authorized';
  };

  const getStatusIcon = () => {
    if (county.oauth_authorized) {
      return <CheckCircle className="h-4 w-4" />;
    }
    return <AlertCircle className="h-4 w-4" />;
  };

  return (
    <>
      <div className="card hover:shadow-md transition-shadow animate-fade-in">
        <div className="card-header">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
                <MapPin className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-lg font-semibold text-gray-900">{county.name}</h3>
                  {/* Platform Badge */}
                  <div className={getPlatformBadgeClass()}>
                    {county.platform_confidence === 'Confirmed' && county.platform !== 'Unknown' && (
                      <CheckCircle className="h-3 w-3 mr-1" />
                    )}
                    {county.platform === 'Unknown' && (
                      <HelpCircle className="h-3 w-3 mr-1" />
                    )}
                    <span className="text-xs">{county.platform || 'Unknown'}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-500 font-mono">
                  {county.county_code || 'No code set'}
                </p>
              </div>
            </div>
            <div className={getStatusBadgeClass()}>
              {getStatusIcon()}
              <span className="ml-1">{getStatusText()}</span>
            </div>
          </div>
        </div>

        <div className="card-body">
          {/* Platform Selection for Unknown Platforms */}
          {county.platform === 'Unknown' && !showPlatformSelect && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start">
                <HelpCircle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div className="ml-3 flex-1">
                  <h4 className="text-sm font-semibold text-yellow-800">Platform Unknown</h4>
                  <p className="text-xs text-yellow-700 mt-1">
                    We couldn't automatically detect which permit platform this county uses.
                  </p>
                  <button
                    onClick={() => setShowPlatformSelect(true)}
                    className="mt-2 text-xs font-medium text-yellow-800 hover:text-yellow-900 underline"
                  >
                    Set platform manually
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Manual Platform Selection UI */}
          {showPlatformSelect && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="text-sm font-semibold text-blue-900 mb-3">Select Permit Platform</h4>
              <div className="space-y-2 mb-3">
                {platformOptions.map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center p-2 rounded-lg border border-gray-200 hover:bg-white cursor-pointer transition-colors"
                  >
                    <input
                      type="radio"
                      name="platform"
                      value={option.value}
                      checked={selectedPlatform === option.value}
                      onChange={(e) => setSelectedPlatform(e.target.value)}
                      className="mr-3"
                    />
                    <span className={`px-2 py-1 rounded text-xs font-medium ${option.color}`}>
                      {option.label}
                    </span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handlePlatformUpdate}
                  disabled={!selectedPlatform || updatePlatform.isPending}
                  className="btn-primary text-sm flex-1"
                >
                  {updatePlatform.isPending ? 'Saving...' : 'Save Platform'}
                </button>
                <button
                  onClick={() => {
                    setShowPlatformSelect(false);
                    setSelectedPlatform('');
                  }}
                  disabled={updatePlatform.isPending}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Metrics Section */}
          {county.oauth_authorized && metrics && (
            <div className="grid grid-cols-3 gap-4 mb-4">
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
          )}

          {/* Pull Status Section */}
          {county.oauth_authorized && pullStatus && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
              {/* Initial Pull Progress */}
              {pullStatus.initial_pull_progress !== null && !pullStatus.initial_pull_completed && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center text-sm font-medium text-blue-700">
                      <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      30-Year Historical Pull
                    </div>
                    {/* Show year progress instead of just percentage */}
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
                  {/* Show year range below progress bar */}
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

                  {/* Last pull status indicator */}
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
            <div className="flex items-center text-sm text-gray-500 mb-4">
              <Clock className="h-4 w-4 mr-1.5" />
              Last pull: {formatRelativeTime(county.last_pull_at)}
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2">
            {county.oauth_authorized ? (
              <>
                {/* Delete Button */}
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="btn-secondary w-full text-red-600 hover:bg-red-50 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete County
                </button>
              </>
            ) : (
              <button
                onClick={handleAuthorize}
                disabled={getOAuthUrl.isPending}
                className="btn-primary w-full"
              >
                {getOAuthUrl.isPending ? (
                  <>Loading...</>
                ) : (
                  <>
                    Authorize with Accela
                    <ExternalLink className="h-4 w-4 ml-2" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900 bg-opacity-50">
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
};

export default CountyCard;
