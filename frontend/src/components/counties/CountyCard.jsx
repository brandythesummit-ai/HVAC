import { useState } from 'react';
import { MapPin, Download, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import PullPermitsModal from './PullPermitsModal';

const CountyCard = ({ county }) => {
  const [showPullModal, setShowPullModal] = useState(false);

  const getStatusBadgeClass = () => {
    switch (county.status) {
      case 'connected':
        return 'badge badge-success';
      case 'token_expired':
        return 'badge badge-warning';
      default:
        return 'badge badge-error';
    }
  };

  const getStatusText = () => {
    switch (county.status) {
      case 'connected':
        return 'Connected';
      case 'token_expired':
        return 'Token Expired';
      default:
        return 'Error';
    }
  };

  const getStatusIcon = () => {
    switch (county.status) {
      case 'connected':
        return <CheckCircle className="h-4 w-4" />;
      case 'token_expired':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
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
                <p className="text-sm text-gray-500 mt-0.5">
                  {county.accela_environment || 'Production'}
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
          {county.last_pull_at && (
            <div className="flex items-center text-sm text-gray-500 mb-4">
              <Clock className="h-4 w-4 mr-1.5" />
              Last pull: {formatRelativeTime(county.last_pull_at)}
            </div>
          )}

          <button
            onClick={() => setShowPullModal(true)}
            disabled={!county.is_active}
            className="btn-primary w-full"
          >
            <Download className="h-4 w-4 mr-2" />
            Pull Permits
          </button>
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
