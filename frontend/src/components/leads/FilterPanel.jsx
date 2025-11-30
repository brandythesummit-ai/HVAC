import { useState } from 'react';
import { Filter, ChevronDown, ChevronRight, ChevronUp, RotateCcw } from 'lucide-react';

/**
 * Comprehensive FilterPanel for leads
 * Supports all 20+ filter parameters from the backend API
 */
const FilterPanel = ({ filters, onFilterChange, counties, fixedFilters = [] }) => {
  // Panel-level collapse state (persisted in localStorage)
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(() =>
    localStorage.getItem('filterPanelCollapsed') === 'true'
  );

  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    pipeline: false,
    property: false,
    contact: false,
    advanced: false,
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const togglePanelCollapse = () => {
    const newState = !isPanelCollapsed;
    setIsPanelCollapsed(newState);
    localStorage.setItem('filterPanelCollapsed', newState.toString());
  };

  const handleChange = (e) => {
    const { name, value } = e.target;

    // Don't allow changing fixed filters
    if (fixedFilters.includes(name)) return;

    onFilterChange(e);
  };

  const handleReset = () => {
    // Define proper default values
    const resetFilters = {
      limit: 50,
      offset: 0,
      county_id: '',
      lead_tier: '',
      min_score: '',
      max_score: '',
      is_qualified: '',
      recommended_pipeline: '',
      min_pipeline_confidence: '',
      contact_completeness: '',
      affluence_tier: '',
      min_hvac_age: '',
      max_hvac_age: '',
      min_property_value: '',
      max_property_value: '',
      year_built_min: '',
      year_built_max: '',
      has_phone: '',
      has_email: '',
      city: '',
      state: '',
    };

    // Preserve fixed filters (like sync_status)
    fixedFilters.forEach(key => {
      if (filters[key] !== undefined) {
        resetFilters[key] = filters[key];
      }
    });

    // Fire single event with reset type
    onFilterChange({
      type: 'reset',
      resetFilters
    });
  };

  const Section = ({ title, sectionKey, children }) => {
    const isExpanded = expandedSections[sectionKey];

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <span className="font-semibold text-gray-900">{title}</span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-600" />
          )}
        </button>

        {isExpanded && (
          <div className="px-4 py-3 bg-white">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {children}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="card animate-fade-in">
      {/* Header */}
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={togglePanelCollapse}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title={isPanelCollapsed ? "Expand filters" : "Collapse filters"}
          >
            {isPanelCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </button>
          <Filter className="h-5 w-5 text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-900">Advanced Filters</h2>
        </div>
        {!isPanelCollapsed && (
          <button
            onClick={handleReset}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <RotateCcw className="h-3 w-3" />
            Reset All
          </button>
        )}
      </div>

      {/* Filter Sections */}
      {!isPanelCollapsed && (
        <div className="card-body space-y-3">
        {/* Basic Filters */}
        <Section title="Basic Filters" sectionKey="basic">
          {/* County */}
          <div>
            <label htmlFor="county_id" className="block text-sm font-medium text-gray-700 mb-1">
              County
            </label>
            <select
              id="county_id"
              name="county_id"
              value={filters.county_id || ''}
              onChange={handleChange}
              disabled={fixedFilters.includes('county_id')}
              className="input-field"
            >
              <option value="">All Counties</option>
              {counties?.map((county) => (
                <option key={county.id} value={county.id}>
                  {county.name}
                </option>
              ))}
            </select>
          </div>

          {/* Lead Tier */}
          <div>
            <label htmlFor="lead_tier" className="block text-sm font-medium text-gray-700 mb-1">
              Lead Tier
            </label>
            <select
              id="lead_tier"
              name="lead_tier"
              value={filters.lead_tier || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Tiers</option>
              <option value="HOT">🔥 HOT (15+ years)</option>
              <option value="WARM">🌡️ WARM (10-15 years)</option>
              <option value="COOL">❄️ COOL (5-10 years)</option>
              <option value="COLD">🧊 COLD (&lt;5 years)</option>
            </select>
          </div>

          {/* Min Score */}
          <div>
            <label htmlFor="min_score" className="block text-sm font-medium text-gray-700 mb-1">
              Min Lead Score
            </label>
            <input
              type="number"
              id="min_score"
              name="min_score"
              value={filters.min_score || ''}
              onChange={handleChange}
              min="0"
              max="100"
              placeholder="0-100"
              className="input-field"
            />
          </div>

          {/* Max Score */}
          <div>
            <label htmlFor="max_score" className="block text-sm font-medium text-gray-700 mb-1">
              Max Lead Score
            </label>
            <input
              type="number"
              id="max_score"
              name="max_score"
              value={filters.max_score || ''}
              onChange={handleChange}
              min="0"
              max="100"
              placeholder="0-100"
              className="input-field"
            />
          </div>

          {/* Qualified Status */}
          <div>
            <label htmlFor="is_qualified" className="block text-sm font-medium text-gray-700 mb-1">
              Qualified Status
            </label>
            <select
              id="is_qualified"
              name="is_qualified"
              value={filters.is_qualified || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Leads</option>
              <option value="true">Qualified Only (5+ yrs)</option>
              <option value="false">Not Qualified</option>
            </select>
          </div>
        </Section>

        {/* Pipeline Intelligence */}
        <Section title="Pipeline Intelligence" sectionKey="pipeline">
          {/* Recommended Pipeline */}
          <div>
            <label htmlFor="recommended_pipeline" className="block text-sm font-medium text-gray-700 mb-1">
              Recommended Pipeline
            </label>
            <select
              id="recommended_pipeline"
              name="recommended_pipeline"
              value={filters.recommended_pipeline || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Pipelines</option>
              <option value="hot_call">🔥 Hot Call</option>
              <option value="premium_mailer">📧 Premium Mailer</option>
              <option value="nurture_drip">💧 Nurture Drip</option>
              <option value="retargeting_ads">🎯 Retargeting Ads</option>
              <option value="cold_storage">❄️ Cold Storage</option>
            </select>
          </div>

          {/* Pipeline Confidence */}
          <div>
            <label htmlFor="min_pipeline_confidence" className="block text-sm font-medium text-gray-700 mb-1">
              Min Pipeline Confidence
            </label>
            <input
              type="number"
              id="min_pipeline_confidence"
              name="min_pipeline_confidence"
              value={filters.min_pipeline_confidence || ''}
              onChange={handleChange}
              min="0"
              max="100"
              placeholder="0-100"
              className="input-field"
            />
          </div>

          {/* Contact Completeness */}
          <div>
            <label htmlFor="contact_completeness" className="block text-sm font-medium text-gray-700 mb-1">
              Contact Completeness
            </label>
            <select
              id="contact_completeness"
              name="contact_completeness"
              value={filters.contact_completeness || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Levels</option>
              <option value="complete">✅ Complete</option>
              <option value="partial">⚠️ Partial</option>
              <option value="minimal">❌ Minimal</option>
            </select>
          </div>

          {/* Affluence Tier */}
          <div>
            <label htmlFor="affluence_tier" className="block text-sm font-medium text-gray-700 mb-1">
              Affluence Tier
            </label>
            <select
              id="affluence_tier"
              name="affluence_tier"
              value={filters.affluence_tier || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All Tiers</option>
              <option value="ultra_high">💎 Ultra High ($500K+)</option>
              <option value="high">🏆 High ($350K+)</option>
              <option value="medium">⭐ Medium ($200K+)</option>
              <option value="standard">📊 Standard</option>
            </select>
          </div>
        </Section>

        {/* Property Details */}
        <Section title="Property Details" sectionKey="property">
          {/* HVAC Age Range */}
          <div>
            <label htmlFor="min_hvac_age" className="block text-sm font-medium text-gray-700 mb-1">
              Min HVAC Age (years)
            </label>
            <input
              type="number"
              id="min_hvac_age"
              name="min_hvac_age"
              value={filters.min_hvac_age || ''}
              onChange={handleChange}
              min="0"
              placeholder="e.g., 10"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="max_hvac_age" className="block text-sm font-medium text-gray-700 mb-1">
              Max HVAC Age (years)
            </label>
            <input
              type="number"
              id="max_hvac_age"
              name="max_hvac_age"
              value={filters.max_hvac_age || ''}
              onChange={handleChange}
              min="0"
              placeholder="e.g., 20"
              className="input-field"
            />
          </div>

          {/* Property Value Range */}
          <div>
            <label htmlFor="min_property_value" className="block text-sm font-medium text-gray-700 mb-1">
              Min Property Value
            </label>
            <input
              type="number"
              id="min_property_value"
              name="min_property_value"
              value={filters.min_property_value || ''}
              onChange={handleChange}
              min="0"
              placeholder="e.g., 200000"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="max_property_value" className="block text-sm font-medium text-gray-700 mb-1">
              Max Property Value
            </label>
            <input
              type="number"
              id="max_property_value"
              name="max_property_value"
              value={filters.max_property_value || ''}
              onChange={handleChange}
              min="0"
              placeholder="e.g., 500000"
              className="input-field"
            />
          </div>

          {/* Year Built Range */}
          <div>
            <label htmlFor="year_built_min" className="block text-sm font-medium text-gray-700 mb-1">
              Year Built (Min)
            </label>
            <input
              type="number"
              id="year_built_min"
              name="year_built_min"
              value={filters.year_built_min || ''}
              onChange={handleChange}
              min="1800"
              max={new Date().getFullYear()}
              placeholder="e.g., 2000"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="year_built_max" className="block text-sm font-medium text-gray-700 mb-1">
              Year Built (Max)
            </label>
            <input
              type="number"
              id="year_built_max"
              name="year_built_max"
              value={filters.year_built_max || ''}
              onChange={handleChange}
              min="1800"
              max={new Date().getFullYear()}
              placeholder="e.g., 2020"
              className="input-field"
            />
          </div>
        </Section>

        {/* Contact Information */}
        <Section title="Contact Information" sectionKey="contact">
          {/* Has Phone */}
          <div>
            <label htmlFor="has_phone" className="block text-sm font-medium text-gray-700 mb-1">
              Phone Available
            </label>
            <select
              id="has_phone"
              name="has_phone"
              value={filters.has_phone || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>

          {/* Has Email */}
          <div>
            <label htmlFor="has_email" className="block text-sm font-medium text-gray-700 mb-1">
              Email Available
            </label>
            <select
              id="has_email"
              name="has_email"
              value={filters.has_email || ''}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">All</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </Section>

        {/* Advanced Filters */}
        <Section title="Advanced" sectionKey="advanced">
          {/* City */}
          <div>
            <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-1">
              City
            </label>
            <input
              type="text"
              id="city"
              name="city"
              value={filters.city || ''}
              onChange={handleChange}
              placeholder="e.g., Tampa"
              className="input-field"
            />
          </div>

          {/* State */}
          <div>
            <label htmlFor="state" className="block text-sm font-medium text-gray-700 mb-1">
              State
            </label>
            <input
              type="text"
              id="state"
              name="state"
              value={filters.state || ''}
              onChange={handleChange}
              placeholder="e.g., FL"
              maxLength="2"
              className="input-field"
            />
          </div>
        </Section>
        </div>
      )}
    </div>
  );
};

export default FilterPanel;
