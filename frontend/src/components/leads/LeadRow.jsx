import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';
import SyncStatusBadge from './SyncStatusBadge';
import LeadDetailView from './LeadDetailView';

const LeadRow = ({ lead, isSelected, onToggle }) => {
  const [expanded, setExpanded] = useState(false);

  // Extract permit data from nested structure
  const permit = lead.permits || {};

  // Clean up address - remove dict string representation from state
  const cleanAddress = (address) => {
    if (!address) return '-';
    // Remove patterns like "{'value': 'FL', 'text': 'FL'}" and replace with just the value
    return address.replace(/\s*\{'value':\s*'([^']+)',\s*'text':\s*'[^']+'\}/g, ' $1').trim();
  };

  return (
    <>
      <tr className="hover:bg-gray-50 transition-colors duration-150">
        <td className="px-6 py-4 whitespace-nowrap">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggle}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
            />
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title={expanded ? "Hide details" : "Show all data"}
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          </div>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <div className="text-sm font-medium text-gray-900">{permit.owner_name || '-'}</div>
          <div className="text-sm text-gray-500">{permit.owner_phone || '-'}</div>
        </td>
        <td className="px-6 py-4">
          <div className="text-sm text-gray-900">{cleanAddress(permit.property_address)}</div>
          <div className="text-sm text-gray-500">{permit.neighborhood || permit.county_name || '-'}</div>
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          {formatDate(permit.opened_date)}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          {permit.lot_size_sqft ? `${permit.lot_size_sqft.toLocaleString()} sqft` : '-'}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
          {formatCurrency(permit.total_property_value)}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
          {formatCurrency(permit.job_value)}
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <SyncStatusBadge status={lead.summit_sync_status} />
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan="8" className="p-0">
            <LeadDetailView lead={lead} />
          </td>
        </tr>
      )}
    </>
  );
};

export default LeadRow;
