import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';
import SyncStatusBadge from './SyncStatusBadge';
import LeadDetailView from './LeadDetailView';
import LeadTierBadge from './LeadTierBadge';

const LeadRow = ({ lead, isSelected, onToggle }) => {
  const [expanded, setExpanded] = useState(false);

  // Extract property and permit data from nested structure
  const property = lead.properties || {};
  const permit = lead.permits || {};

  // Prioritize property data over permit data (property is aggregated from most recent permit)
  const displayData = {
    owner_name: property.owner_name || permit.owner_name,
    owner_phone: property.owner_phone || permit.owner_phone,
    address: property.normalized_address || permit.property_address,
    neighborhood: permit.neighborhood || permit.county_name,
    hvac_age_years: property.hvac_age_years,
    most_recent_hvac_date: property.most_recent_hvac_date,
    lot_size_sqft: property.lot_size_sqft || permit.lot_size_sqft,
    total_property_value: property.total_property_value || permit.total_property_value,
    lead_score: lead.lead_score,
    lead_tier: lead.lead_tier,
  };

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
          <div className="text-sm font-medium text-gray-900">{displayData.owner_name || '-'}</div>
          <div className="text-sm text-gray-500">{displayData.owner_phone || '-'}</div>
        </td>
        <td className="px-6 py-4">
          <div className="text-sm text-gray-900">{cleanAddress(displayData.address)}</div>
          <div className="text-sm text-gray-500">{displayData.neighborhood || '-'}</div>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          {displayData.hvac_age_years !== null && displayData.hvac_age_years !== undefined ? (
            <div>
              <div className="text-sm font-semibold text-gray-900">{displayData.hvac_age_years} years</div>
              <div className="text-xs text-gray-500">{formatDate(displayData.most_recent_hvac_date)}</div>
            </div>
          ) : (
            <span className="text-sm text-gray-400">—</span>
          )}
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <LeadTierBadge tier={displayData.lead_tier} score={displayData.lead_score} />
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          {displayData.lot_size_sqft ? `${displayData.lot_size_sqft.toLocaleString()} sqft` : '-'}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
          {formatCurrency(displayData.total_property_value)}
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <SyncStatusBadge status={lead.summit_sync_status} />
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan="7" className="p-0">
            <LeadDetailView lead={lead} />
          </td>
        </tr>
      )}
    </>
  );
};

export default LeadRow;
