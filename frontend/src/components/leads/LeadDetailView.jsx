import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, MapPin, User, Home } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';

/**
 * Displays ALL raw data from Accela for a permit/lead
 * This component ensures complete data visibility as required
 */
const LeadDetailView = ({ lead }) => {
  const [expandedSections, setExpandedSections] = useState({
    permit: true,
    addresses: false,
    owners: false,
    parcels: false,
  });

  const permit = lead.permits || {};
  const rawData = permit.raw_data || {};

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Render any value (handle objects, arrays, primitives)
  const renderValue = (value, depth = 0) => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className="text-blue-600 font-medium">{value.toString()}</span>;
    }

    if (typeof value === 'number') {
      return <span className="text-green-600 font-medium">{value}</span>;
    }

    if (typeof value === 'string') {
      // Format dates if they look like ISO dates
      if (value.match(/^\d{4}-\d{2}-\d{2}/) && value.length <= 10) {
        return <span className="text-gray-900">{formatDate(value)}</span>;
      }
      if (value.match(/^\d{4}-\d{2}-\d{2}T/)) {
        return <span className="text-gray-900">{new Date(value).toLocaleString()}</span>;
      }
      return <span className="text-gray-900">{value}</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400 italic">[]</span>;
      }
      return (
        <div className={`ml-${depth * 4} space-y-2`}>
          {value.map((item, idx) => (
            <div key={idx} className="border-l-2 border-gray-200 pl-3">
              <div className="text-xs text-gray-500 mb-1">Item {idx + 1}</div>
              {renderValue(item, depth + 1)}
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value);
      if (entries.length === 0) {
        return <span className="text-gray-400 italic">{'{}'}</span>;
      }
      return (
        <div className={`ml-${depth * 2} space-y-1`}>
          {entries.map(([key, val]) => (
            <div key={key} className="flex gap-2 text-sm">
              <span className="text-gray-600 font-medium min-w-[150px]">{key}:</span>
              <span className="flex-1">{renderValue(val, depth + 1)}</span>
            </div>
          ))}
        </div>
      );
    }

    return <span className="text-gray-900">{String(value)}</span>;
  };

  const Section = ({ title, icon: Icon, data, sectionKey }) => {
    const isExpanded = expandedSections[sectionKey];
    const hasData = data && (Array.isArray(data) ? data.length > 0 : Object.keys(data).length > 0);

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-gray-600" />
            <span className="font-semibold text-gray-900">{title}</span>
            {hasData && (
              <span className="text-xs text-gray-500">
                {Array.isArray(data) ? `(${data.length} items)` : `(${Object.keys(data).length} fields)`}
              </span>
            )}
          </div>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-600" />
          )}
        </button>

        {isExpanded && (
          <div className="px-4 py-3 bg-white">
            {!hasData ? (
              <p className="text-gray-400 italic text-sm">No data available</p>
            ) : (
              <div className="space-y-2">
                {renderValue(data)}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-gray-50 border-t border-gray-200">
      <div className="px-6 py-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">Complete Permit Data</h3>
          <p className="text-sm text-gray-600">
            All data retrieved from Accela for permit: {permit.custom_id || permit.accela_record_id || 'N/A'}
          </p>
        </div>

        <div className="space-y-3">
          {/* Permit Data Section */}
          <Section
            title="Permit Information"
            icon={FileText}
            data={rawData.permit}
            sectionKey="permit"
          />

          {/* Addresses Section */}
          <Section
            title="Addresses"
            icon={MapPin}
            data={rawData.addresses}
            sectionKey="addresses"
          />

          {/* Owners Section */}
          <Section
            title="Property Owners"
            icon={User}
            data={rawData.owners}
            sectionKey="owners"
          />

          {/* Parcels Section */}
          <Section
            title="Parcel Information"
            icon={Home}
            data={rawData.parcels}
            sectionKey="parcels"
          />
        </div>

        {/* Raw JSON View (for debugging/advanced users) */}
        <div className="mt-4 border-t pt-4">
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900 flex items-center gap-2">
              <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
              View Raw JSON
            </summary>
            <div className="mt-2 bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs font-mono">
              <pre>{JSON.stringify(rawData, null, 2)}</pre>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default LeadDetailView;
