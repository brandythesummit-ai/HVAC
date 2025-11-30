import { Clock, CheckCircle, XCircle } from 'lucide-react';
import { useState } from 'react';

const SyncStatusBadge = ({ status, errorMessage }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  const configs = {
    pending: {
      icon: Clock,
      text: 'Pending',
      className: 'badge badge-warning',
      iconColor: 'text-yellow-600',
    },
    synced: {
      icon: CheckCircle,
      text: 'Synced',
      className: 'badge badge-success',
      iconColor: 'text-green-600',
    },
    failed: {
      icon: XCircle,
      text: 'Failed',
      className: 'badge badge-error',
      iconColor: 'text-red-600',
    },
  };

  const config = configs[status] || configs.pending;
  const Icon = config.icon;
  const hasTooltip = status === 'failed' && errorMessage;

  return (
    <div className="relative inline-block">
      <span
        className={config.className}
        onMouseEnter={() => hasTooltip && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        style={{ cursor: hasTooltip ? 'help' : 'default' }}
      >
        <Icon className={`h-3 w-3 mr-1 ${config.iconColor}`} />
        {config.text}
      </span>

      {showTooltip && errorMessage && (
        <div className="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg max-w-xs whitespace-normal">
          <div className="font-semibold mb-1">Error Details:</div>
          <div className="text-xs">{errorMessage}</div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
      )}
    </div>
  );
};

export default SyncStatusBadge;
