import React from 'react';
import { ChevronDown, ChevronRight, MapPin, CheckCircle } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import CountiesVirtualList from './CountiesVirtualList';

const StateSection = React.memo(({
  state,
  counties,
  metrics,
  isExpanded,
  onToggle,
  onCountySelect,
  selectedCountyId
}) => {
  return (
    <div className="border-b border-gray-200">
      {/* State header - always visible */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-500" />
          )}
          <MapPin className="h-5 w-5 text-blue-600" />
          <div className="text-left">
            <h3 className="text-lg font-semibold text-gray-900">
              {state} ({metrics.total} counties)
            </h3>
            <div className="flex items-center space-x-4 text-sm text-gray-600 mt-1">
              <span className="flex items-center">
                <CheckCircle className="h-4 w-4 mr-1 text-green-600" />
                {metrics.authorized} authorized
              </span>
              <span>•</span>
              <span>{metrics.totalLeads.toLocaleString()} total leads</span>
              {metrics.lastPull && (
                <>
                  <span>•</span>
                  <span>Last pull: {formatRelativeTime(metrics.lastPull)}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Counties list - only when expanded */}
      {isExpanded && (
        <CountiesVirtualList
          counties={counties}
          onCountySelect={onCountySelect}
          selectedCountyId={selectedCountyId}
        />
      )}
    </div>
  );
});

StateSection.displayName = 'StateSection';

export default StateSection;
