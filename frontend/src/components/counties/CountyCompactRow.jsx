import { CheckCircle, AlertCircle, ChevronRight, HelpCircle } from 'lucide-react';

export default function CountyCompactRow({ county, onClick, isSelected }) {
  const getHealthStatus = () => {
    if (!county.oauth_authorized) return { color: 'yellow', text: 'Setup', icon: AlertCircle };

    const hasLeads = (county.lead_count || 0) > 0;
    const lastPullFailed = county.last_pull_status === 'failed';

    if (lastPullFailed) return { color: 'red', text: 'Error', icon: AlertCircle };
    if (hasLeads) return { color: 'green', text: 'Healthy', icon: CheckCircle };
    return { color: 'yellow', text: 'Setup', icon: AlertCircle };
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
      <div className="flex items-center space-x-4 flex-1 min-w-0">
        {/* Auth indicator */}
        <div className="flex-shrink-0">
          {county.oauth_authorized ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <AlertCircle className="h-5 w-5 text-yellow-600" />
          )}
        </div>

        {/* County name */}
        <span className="font-medium text-gray-900 truncate flex-shrink min-w-[150px]">
          {county.name}
        </span>

        {/* Platform badge */}
        <span className={`px-2 py-1 rounded text-xs font-medium flex-shrink-0 ${getPlatformBadge()}`}>
          {county.platform === 'Unknown' && (
            <HelpCircle className="h-3 w-3 inline mr-1" />
          )}
          {county.platform || 'Unknown'}
        </span>

        {/* Lead count */}
        <span className="text-sm text-gray-600 flex-shrink-0 min-w-[80px]">
          {(county.lead_count || 0).toLocaleString()} leads
        </span>

        {/* Health status */}
        <span className={`
          flex items-center text-sm font-medium flex-shrink-0
          ${health.color === 'green' ? 'text-green-700' : ''}
          ${health.color === 'yellow' ? 'text-yellow-700' : ''}
          ${health.color === 'red' ? 'text-red-700' : ''}
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
