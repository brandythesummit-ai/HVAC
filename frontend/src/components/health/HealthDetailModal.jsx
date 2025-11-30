import { X, CheckCircle2, AlertTriangle, XCircle, HelpCircle, Clock } from 'lucide-react';
import { format } from 'date-fns';

/**
 * Health detail modal component.
 *
 * Shows detailed health information for all system components:
 * - Grouped by priority (Critical, High, Medium, Low)
 * - Component status icons
 * - Response times
 * - Last checked timestamps
 * - Overall status summary
 *
 * Modal closes on ESC key or click outside.
 */
const HealthDetailModal = ({ health, loading, lastChecked, onClose }) => {
  // Handle ESC key
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  // Handle click outside
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Component status icon and color
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-100' };
      case 'degraded':
        return { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-100' };
      case 'down':
        return { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100' };
      case 'unknown':
        return { icon: HelpCircle, color: 'text-gray-600', bg: 'bg-gray-100' };
      default:
        return { icon: HelpCircle, color: 'text-gray-600', bg: 'bg-gray-100' };
    }
  };

  // Format component name for display
  const formatComponentName = (name) => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Group components by priority
  const groupByPriority = (components) => {
    const groups = {
      critical: [],
      high: [],
      medium: [],
      low: [],
    };

    Object.entries(components || {}).forEach(([name, component]) => {
      const priority = component.priority || 'medium';
      if (groups[priority]) {
        groups[priority].push({ name, ...component });
      }
    });

    return groups;
  };

  const componentGroups = health ? groupByPriority(health.components) : {};

  // Render component row
  const ComponentRow = ({ name, status, message, response_time_ms, last_checked }) => {
    const { icon: Icon, color, bg } = getStatusIcon(status);

    return (
      <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0">
        <div className="flex items-center space-x-3 flex-1">
          <div className={`flex items-center justify-center w-8 h-8 ${bg} rounded-lg`}>
            <Icon className={`w-4 h-4 ${color}`} />
          </div>
          <div className="flex-1">
            <div className="font-medium text-gray-900">{formatComponentName(name)}</div>
            <div className="text-sm text-gray-500">{message}</div>
          </div>
        </div>
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          {response_time_ms !== null && response_time_ms !== undefined && (
            <div className="text-right">
              <Clock className="inline w-3 h-3 mr-1" />
              {response_time_ms.toFixed(0)}ms
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">System Health</h2>
            <p className="text-sm text-gray-500">
              {lastChecked && `Last updated ${format(lastChecked, 'p')}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-8 h-8 text-gray-400 rounded-lg hover:bg-gray-200 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-8rem)]">
          {loading && !health ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
                <p className="mt-4 text-gray-600">Loading health status...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Overall Status */}
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-500">Overall Status</div>
                    <div className="flex items-center mt-1 space-x-2">
                      {health?.status === 'healthy' && (
                        <>
                          <div className="w-3 h-3 bg-green-500 rounded-full" />
                          <span className="text-lg font-semibold text-green-700">Healthy</span>
                        </>
                      )}
                      {health?.status === 'degraded' && (
                        <>
                          <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                          <span className="text-lg font-semibold text-yellow-700">Degraded</span>
                        </>
                      )}
                      {health?.status === 'down' && (
                        <>
                          <div className="w-3 h-3 bg-red-500 rounded-full" />
                          <span className="text-lg font-semibold text-red-600">System Down</span>
                        </>
                      )}
                    </div>
                  </div>
                  {health?.summary && (
                    <div className="flex space-x-4 text-sm">
                      {health.summary.healthy > 0 && (
                        <div className="text-green-600">
                          {health.summary.healthy} healthy
                        </div>
                      )}
                      {health.summary.degraded > 0 && (
                        <div className="text-yellow-600">
                          {health.summary.degraded} degraded
                        </div>
                      )}
                      {health.summary.down > 0 && (
                        <div className="text-red-600">{health.summary.down} down</div>
                      )}
                      {health.summary.unknown > 0 && (
                        <div className="text-gray-600">{health.summary.unknown} unknown</div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Critical Components */}
              {componentGroups.critical && componentGroups.critical.length > 0 && (
                <div className="px-6 py-4">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Critical Components
                  </h3>
                  {componentGroups.critical.map((component) => (
                    <ComponentRow key={component.name} {...component} />
                  ))}
                </div>
              )}

              {/* High Priority */}
              {componentGroups.high && componentGroups.high.length > 0 && (
                <div className="px-6 py-4 border-t border-gray-200">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    High Priority
                  </h3>
                  {componentGroups.high.map((component) => (
                    <ComponentRow key={component.name} {...component} />
                  ))}
                </div>
              )}

              {/* Medium Priority */}
              {componentGroups.medium && componentGroups.medium.length > 0 && (
                <div className="px-6 py-4 border-t border-gray-200">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    External Services
                  </h3>
                  {componentGroups.medium.map((component) => (
                    <ComponentRow key={component.name} {...component} />
                  ))}
                </div>
              )}

              {/* Low Priority */}
              {componentGroups.low && componentGroups.low.length > 0 && (
                <div className="px-6 py-4 border-t border-gray-200">
                  <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Internal Services
                  </h3>
                  {componentGroups.low.map((component) => (
                    <ComponentRow key={component.name} {...component} />
                  ))}
                </div>
              )}

              {/* Uptime */}
              {health?.uptime_seconds && (
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                  <div className="text-sm text-gray-600">
                    Uptime: {Math.floor(health.uptime_seconds / 3600)}h{' '}
                    {Math.floor((health.uptime_seconds % 3600) / 60)}m
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default HealthDetailModal;
