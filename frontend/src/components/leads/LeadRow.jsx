import { useState } from 'react';
import { ChevronDown, ChevronRight, Target } from 'lucide-react';
import { formatDate, formatCurrency } from '../../utils/formatters';
import SyncStatusBadge from './SyncStatusBadge';
import LeadDetailView from './LeadDetailView';
import LeadTierBadge from './LeadTierBadge';

const LeadRow = ({ lead, isSelected, onToggle, visibleColumns }) => {
  const [expanded, setExpanded] = useState(false);

  // Extract property and permit data from nested structure
  const property = lead.properties || {};
  const permit = lead.permits || {};

  // Prioritize property data over permit data
  const displayData = {
    owner_name: property.owner_name || permit.owner_name,
    owner_phone: property.owner_phone || permit.owner_phone,
    owner_email: property.owner_email || permit.owner_email,
    address: property.normalized_address || permit.property_address,
    neighborhood: permit.neighborhood || permit.county_name,
    hvac_age_years: property.hvac_age_years,
    most_recent_hvac_date: property.most_recent_hvac_date,
    lot_size_sqft: property.lot_size_sqft || permit.lot_size_sqft,
    total_property_value: property.total_property_value || permit.total_property_value,
    year_built: property.year_built,
    lead_score: lead.lead_score,
    lead_tier: lead.lead_tier,
    recommended_pipeline: property.recommended_pipeline,
    pipeline_confidence: property.pipeline_confidence,
    contact_completeness: property.contact_completeness,
    affluence_tier: property.affluence_tier,
  };

  // Clean up address - remove dict string representation from state
  const cleanAddress = (address) => {
    if (!address) return '-';
    return address.replace(/\s*\{'value':\s*'([^']+)',\s*'text':\s*'[^']+'\}/g, ' $1').trim();
  };

  // Helper functions for display
  const getPipelineBadge = (pipeline, confidence) => {
    if (!pipeline) return <span className="text-gray-400 text-sm">—</span>;

    const badges = {
      'hot_call': { color: 'red', label: 'Hot Call' },
      'premium_mailer': { color: 'orange', label: 'Premium Mailer' },
      'nurture_drip': { color: 'blue', label: 'Nurture Drip' },
      'retargeting_ads': { color: 'purple', label: 'Retargeting' },
      'cold_storage': { color: 'gray', label: 'Cold Storage' },
    };

    const badge = badges[pipeline] || { color: 'gray', label: pipeline };
    const colorClasses = {
      red: 'bg-red-100 text-red-800 border-red-300',
      orange: 'bg-orange-100 text-orange-800 border-orange-300',
      blue: 'bg-blue-100 text-blue-800 border-blue-300',
      purple: 'bg-purple-100 text-purple-800 border-purple-300',
      gray: 'bg-gray-100 text-gray-800 border-gray-300',
    };

    return (
      <div className="flex flex-col gap-1">
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${colorClasses[badge.color]}`}>
          <Target className="h-3 w-3" />
          {badge.label}
        </span>
        {confidence && (
          <span className="text-xs text-gray-500">{confidence}% confidence</span>
        )}
      </div>
    );
  };

  const getContactCompletenessBadge = (completeness) => {
    if (!completeness) return <span className="text-gray-400 text-sm">—</span>;

    const badges = {
      'complete': { emoji: '✅', label: 'Complete', color: 'bg-green-100 text-green-800 border-green-300' },
      'partial': { emoji: '⚠️', label: 'Partial', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
      'minimal': { emoji: '❌', label: 'Minimal', color: 'bg-red-100 text-red-800 border-red-300' },
    };

    const badge = badges[completeness] || { emoji: '', label: completeness, color: 'bg-gray-100 text-gray-800 border-gray-300' };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${badge.color}`}>
        {badge.emoji} {badge.label}
      </span>
    );
  };

  const getAffluenceBadge = (tier) => {
    if (!tier) return <span className="text-gray-400 text-sm">—</span>;

    const badges = {
      'ultra_high': { emoji: '💎', label: 'Ultra High', color: 'bg-purple-100 text-purple-800 border-purple-300' },
      'high': { emoji: '🏆', label: 'High', color: 'bg-blue-100 text-blue-800 border-blue-300' },
      'medium': { emoji: '⭐', label: 'Medium', color: 'bg-green-100 text-green-800 border-green-300' },
      'standard': { emoji: '📊', label: 'Standard', color: 'bg-gray-100 text-gray-800 border-gray-300' },
    };

    const badge = badges[tier] || { emoji: '', label: tier, color: 'bg-gray-100 text-gray-800 border-gray-300' };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${badge.color}`}>
        {badge.emoji} {badge.label}
      </span>
    );
  };

  // Render individual columns based on visibility
  const renderColumn = (columnId) => {
    switch (columnId) {
      case 'select':
        return (
          <td key="select" className="px-6 py-4 whitespace-nowrap">
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
        );

      case 'contact':
        return (
          <td key="contact" className="px-6 py-4 whitespace-nowrap">
            <div className="text-sm font-medium text-gray-900">{displayData.owner_name || '-'}</div>
            <div className="text-sm text-gray-500">{displayData.owner_phone || '-'}</div>
          </td>
        );

      case 'address':
        return (
          <td key="address" className="px-6 py-4">
            <div className="text-sm text-gray-900">{cleanAddress(displayData.address)}</div>
            <div className="text-sm text-gray-500">{displayData.neighborhood || '-'}</div>
          </td>
        );

      case 'pipeline':
        return (
          <td key="pipeline" className="px-6 py-4 whitespace-nowrap">
            {getPipelineBadge(displayData.recommended_pipeline, displayData.pipeline_confidence)}
          </td>
        );

      case 'hvac_age':
        return (
          <td key="hvac_age" className="px-6 py-4 whitespace-nowrap">
            {displayData.hvac_age_years !== null && displayData.hvac_age_years !== undefined ? (
              <div>
                <div className="text-sm font-semibold text-gray-900">{displayData.hvac_age_years} years</div>
                <div className="text-xs text-gray-500">{formatDate(displayData.most_recent_hvac_date)}</div>
              </div>
            ) : (
              <span className="text-sm text-gray-400">—</span>
            )}
          </td>
        );

      case 'score_tier':
        return (
          <td key="score_tier" className="px-6 py-4 whitespace-nowrap">
            <LeadTierBadge tier={displayData.lead_tier} score={displayData.lead_score} />
          </td>
        );

      case 'contact_info':
        return (
          <td key="contact_info" className="px-6 py-4 whitespace-nowrap">
            {getContactCompletenessBadge(displayData.contact_completeness)}
          </td>
        );

      case 'affluence':
        return (
          <td key="affluence" className="px-6 py-4 whitespace-nowrap">
            {getAffluenceBadge(displayData.affluence_tier)}
          </td>
        );

      case 'lot_size':
        return (
          <td key="lot_size" className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            {displayData.lot_size_sqft ? `${displayData.lot_size_sqft.toLocaleString()} sqft` : '-'}
          </td>
        );

      case 'property_value':
        return (
          <td key="property_value" className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
            {formatCurrency(displayData.total_property_value)}
          </td>
        );

      case 'year_built':
        return (
          <td key="year_built" className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            {displayData.year_built || '-'}
          </td>
        );

      case 'status':
        return (
          <td key="status" className="px-6 py-4 whitespace-nowrap">
            <SyncStatusBadge
              status={lead.summit_sync_status}
              errorMessage={lead.sync_error_message}
            />
          </td>
        );

      default:
        return null;
    }
  };

  return (
    <>
      <tr className="hover:bg-gray-50 transition-colors duration-150">
        {visibleColumns.map(columnId => renderColumn(columnId))}
      </tr>
      {expanded && (
        <tr>
          <td colSpan={visibleColumns.length} className="p-0">
            <LeadDetailView lead={lead} />
          </td>
        </tr>
      )}
    </>
  );
};

export default LeadRow;
