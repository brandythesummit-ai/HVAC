import { useState } from 'react';
import { Filter, AlertCircle, GitBranch, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { useLeads } from '../hooks/useLeads';
import { useCounties } from '../hooks/useCounties';
import LeadsTable from '../components/leads/LeadsTable';

const PipelinePage = () => {
  // Pipeline: Show ONLY synced or failed leads
  const [filters, setFilters] = useState({
    county_id: '',
    sync_status: 'synced', // Default to synced leads
    lead_tier: '',
    min_score: '',
    is_qualified: '',
  });

  const { data: leads, isLoading, error } = useLeads(filters);
  const { data: counties } = useCounties();

  const handleFilterChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  // Calculate stats
  const syncedCount = leads?.filter(l => l.summit_sync_status === 'synced').length || 0;
  const failedCount = leads?.filter(l => l.summit_sync_status === 'failed').length || 0;

  if (error) {
    return (
      <div className="card bg-red-50 border-red-200 animate-fade-in">
        <div className="card-body">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-red-800">Error loading pipeline</h3>
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
              <GitBranch className="h-6 w-6 text-green-600 mr-3" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Summit.ai Pipeline</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Monitor leads that have been synced to Summit.ai
                </p>
              </div>
            </div>
            <div className="flex gap-6">
              <div className="text-right">
                <div className="flex items-center text-sm font-medium text-gray-700">
                  <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                  Synced
                </div>
                <p className="text-2xl font-bold text-green-600">{syncedCount}</p>
              </div>
              <div className="text-right">
                <div className="flex items-center text-sm font-medium text-gray-700">
                  <XCircle className="h-4 w-4 text-red-600 mr-1" />
                  Failed
                </div>
                <p className="text-2xl font-bold text-red-600">{failedCount}</p>
              </div>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label htmlFor="sync_status" className="block text-sm font-medium text-gray-700 mb-1">
                Sync Status
              </label>
              <select
                id="sync_status"
                name="sync_status"
                value={filters.sync_status}
                onChange={handleFilterChange}
                className="input-field"
              >
                <option value="synced">✅ Synced</option>
                <option value="failed">❌ Failed</option>
              </select>
            </div>

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
      <LeadsTable leads={leads || []} isLoading={isLoading} showSyncActions={true} />
    </div>
  );
};

export default PipelinePage;
