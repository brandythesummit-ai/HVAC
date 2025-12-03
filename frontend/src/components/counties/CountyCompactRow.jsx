import { CheckCircle, AlertCircle, ChevronRight, HelpCircle, RefreshCw } from 'lucide-react';

export default function CountyCompactRow({ county, onClick, isSelected }) {
  const getHealthStatus = () => {
    if (!county.oauth_authorized) return { color: 'yellow', text: 'Setup', icon: AlertCircle };

    // Check if pull is in progress (authorized but initial pull not completed)
    if (!county.initial_pull_completed) {
      return { color: 'blue', text: 'Pulling', icon: RefreshCw };
    }

    const hasLeads = (county.lead_count || 0) > 0;
    const lastPullFailed = county.last_pull_status === 'failed';

    if (lastPullFailed) return { color: 'red', text: 'Error', icon: AlertCircle };
    if (hasLeads) return { color: 'green', text: 'Healthy', icon: CheckCircle };
    return { color: 'green', text: 'Active', icon: CheckCircle };
  };

  const health = getHealthStatus();
  const HealthIcon = health.icon;

  const getPlatformBadge = () => {
    const platform = county.platform || 'Unknown';
    const colors = {
      'Accela': 'text-blue-700 bg-blue-100',
      'EnerGov': 'text-purple-700 bg-purple-100',
      'eTRAKiT': 'text-orange-700 bg-orange-100',
      'Tyler': 'text-indigo-700 bg-indigo-100',
      'OpenGov': 'text-green-700 bg-green-100',
      'Custom': 'text-gray-700 bg-gray-100',
      'Unknown': 'text-gray-500 bg-gray-100'
    };
    return colors[platform] || 'text-gray-500 bg-gray-100';
  };

  return (
    <button
      onClick={onClick}
      className={`
        w-full h-[60px] px-6 flex items-center justify-between
        border-b border-gray-200 hover:bg-white transition-colors
        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''}
      `}
    >
      <div className="flex items-center gap-4">
        {/* Auth indicator - fixed width */}
        <div className="w-6 flex-shrink-0">
          {county.oauth_authorized ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <AlertCircle className="h-5 w-5 text-yellow-600" />
          )}
        </div>

        {/* County name - fixed width for alignment */}
        <span className="font-medium text-gray-900 truncate w-44 flex-shrink-0">
          {county.name}
        </span>

        {/* Platform badge - fixed width */}
        <span className={`w-20 flex-shrink-0 px-2 py-1 rounded text-xs font-medium ${getPlatformBadge()}`}>
          {county.platform === 'Unknown' && (
            <HelpCircle className="h-3 w-3 inline mr-1" />
          )}
          {county.platform || 'Unknown'}
        </span>

        {/* Lead count - fixed width */}
        <span className="w-16 flex-shrink-0 text-sm text-gray-600">
          {(county.lead_count || 0).toLocaleString()} leads
        </span>

        {/* Health status - fixed width */}
        <span className={`
          w-20 flex-shrink-0 flex items-center text-sm font-medium
          ${health.color === 'green' ? 'text-green-700' : ''}
          ${health.color === 'yellow' ? 'text-yellow-700' : ''}
          ${health.color === 'red' ? 'text-red-700' : ''}
          ${health.color === 'blue' ? 'text-blue-700' : ''}
        `}>
          <HealthIcon className="h-4 w-4 mr-1" />
          {health.text}
        </span>
      </div>

      {/* Expand arrow */}
      <ChevronRight className="h-5 w-5 text-gray-400 flex-shrink-0 ml-2" />
    </button>
  );
}
