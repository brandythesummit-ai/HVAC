import { useState } from 'react';
import { MapPin, Download, AlertCircle, CheckCircle, Clock, ExternalLink, BarChart3, Send } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import { useCountyMetrics, useGetOAuthUrl } from '../../hooks/useCounties';
import PullPermitsModal from './PullPermitsModal';

const CountyCard = ({ county }) => {
  const [showPullModal, setShowPullModal] = useState(false);
  const { data: metrics, isLoading: metricsLoading } = useCountyMetrics(county.id);
  const getOAuthUrl = useGetOAuthUrl();

  const handleAuthorize = async () => {
    try {
      const { authorization_url } = await getOAuthUrl.mutateAsync(county.id);
      window.open(authorization_url, '_blank', 'width=600,height=700');
    } catch (error) {
      console.error('Failed to get OAuth URL:', error);
    }
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
                <h3 className="text-lg font-semibold text-gray-900">{county.name}</h3>
                <p className="text-sm text-gray-500 mt-0.5 font-mono">
                  {county.county_code}
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
                  {metricsLoading ? '-' : metrics.sent_to_ghl || 0}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">Sent to GHL</p>
              </div>
            </div>
          )}

          {/* Last Pull Time */}
          {county.last_pull_at && (
            <div className="flex items-center text-sm text-gray-500 mb-4">
              <Clock className="h-4 w-4 mr-1.5" />
              Last pull: {formatRelativeTime(county.last_pull_at)}
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2">
            {county.oauth_authorized ? (
              <button
                onClick={() => setShowPullModal(true)}
                disabled={!county.is_active}
                className="btn-primary w-full"
              >
                <Download className="h-4 w-4 mr-2" />
                Pull Permits
              </button>
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

      {showPullModal && (
        <PullPermitsModal
          county={county}
          onClose={() => setShowPullModal(false)}
        />
      )}
    </>
  );
};

export default CountyCard;
