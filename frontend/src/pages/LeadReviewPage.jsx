import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Filter, AlertCircle, UserCheck } from 'lucide-react';
import { useLeads } from '../hooks/useLeads';
import { useCounties } from '../hooks/useCounties';
import LeadsTable from '../components/leads/LeadsTable';

const LeadReviewPage = () => {
  const location = useLocation();

  // Lead Review: Show ONLY unsynced leads (pending or null sync status)
  const [filters, setFilters] = useState({
    county_id: location.state?.filterByCounty || '',
    sync_status: 'pending', // FIXED: Only show pending leads for review
    lead_tier: '',
    min_score: '',
    is_qualified: '',
  });

  const { data: leadsData, isLoading, error } = useLeads(filters);
  const { data: counties } = useCounties();

  const leads = leadsData?.leads || [];
  const total = leadsData?.total || 0;

  const handleFilterChange = (e) => {
    // Don't allow changing sync_status on Lead Review page
    if (e.target.name === 'sync_status') return;
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  if (error) {
    return (
      <div className="card bg-red-50 border-red-200 animate-fade-in">
        <div className="card-body">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-red-800">Error loading leads</h3>
              <p className="mt-2 text-sm text-red-700">{error.message}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="card animate-fade-in">
        <div className="card-body">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <UserCheck className="h-6 w-6 text-blue-600 mr-3" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Lead Review</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Review and manage unsynced leads before sending to Summit.ai
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700">Unsynced Leads</p>
              <p className="text-2xl font-bold text-blue-600">{total}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card animate-fade-in">
        <div className="card-header">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label htmlFor="county_id" className="block text-sm font-medium text-gray-700 mb-1">
                County
              </label>
              <select
                id="county_id"
                name="county_id"
                value={filters.county_id}
                onChange={handleFilterChange}
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

            <div>
              <label htmlFor="lead_tier" className="block text-sm font-medium text-gray-700 mb-1">
                Lead Tier
              </label>
              <select
                id="lead_tier"
                name="lead_tier"
                value={filters.lead_tier}
                onChange={handleFilterChange}
                className="input-field"
              >
                <option value="">All Tiers</option>
                <option value="HOT">🔥 HOT (15+ years)</option>
                <option value="WARM">🌡️ WARM (10-15 years)</option>
                <option value="COOL">❄️ COOL (5-10 years)</option>
                <option value="COLD">🧊 COLD (&lt;5 years)</option>
              </select>
            </div>

            <div>
              <label htmlFor="min_score" className="block text-sm font-medium text-gray-700 mb-1">
                Min Score
              </label>
              <input
                type="number"
                id="min_score"
                name="min_score"
                value={filters.min_score}
                onChange={handleFilterChange}
                min="0"
                max="100"
                placeholder="0-100"
                className="input-field"
              />
            </div>

            <div>
              <label htmlFor="is_qualified" className="block text-sm font-medium text-gray-700 mb-1">
                Qualified Status
              </label>
              <select
                id="is_qualified"
                name="is_qualified"
                value={filters.is_qualified}
                onChange={handleFilterChange}
                className="input-field"
              >
                <option value="">All Leads</option>
                <option value="true">Qualified Only (5+ yrs)</option>
                <option value="false">Not Qualified</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <LeadsTable leads={leads} isLoading={isLoading} />
    </div>
  );
};

export default LeadReviewPage;
