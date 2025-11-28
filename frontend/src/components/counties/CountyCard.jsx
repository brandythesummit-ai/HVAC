import { useState } from 'react';
import { MapPin, Download, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import PullPermitsModal from './PullPermitsModal';

const CountyCard = ({ county }) => {
  const [showPullModal, setShowPullModal] = useState(false);

  const getStatusIcon = () => {
    switch (county.status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'token_expired':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-red-500" />;
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

  const getStatusColor = () => {
    switch (county.status) {
      case 'connected':
        return 'text-green-700 bg-green-50';
      case 'token_expired':
        return 'text-yellow-700 bg-yellow-50';
      default:
        return 'text-red-700 bg-red-50';
    }
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <div className="p-2 bg-primary-50 rounded-lg">
              <MapPin className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{county.name}</h3>
              <p className="text-sm text-gray-500 mt-1">
                {county.accela_environment || 'Production'}
              </p>
            </div>
          </div>
          {getStatusIcon()}
        </div>

        <div className="mt-4 space-y-2">
          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </div>

          {county.last_pull_at && (
            <div className="flex items-center text-sm text-gray-500">
              <Clock className="h-4 w-4 mr-1" />
              Last pull: {formatRelativeTime(county.last_pull_at)}
            </div>
          )}
        </div>

        <div className="mt-6">
          <button
            onClick={() => setShowPullModal(true)}
            disabled={!county.is_active}
            className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
