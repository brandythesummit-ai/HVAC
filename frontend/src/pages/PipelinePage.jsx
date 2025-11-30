import { useState } from 'react';
import { AlertCircle, GitBranch, CheckCircle, XCircle } from 'lucide-react';
import { useLeads } from '../hooks/useLeads';
import { useCounties } from '../hooks/useCounties';
import LeadsTable from '../components/leads/LeadsTable';
import FilterPanel from '../components/leads/FilterPanel';

const PipelinePage = () => {
  // Pipeline: Show ONLY synced or failed leads
  const [filters, setFilters] = useState({
    // Sync status filter (toggleable on this page)
    sync_status: 'synced', // Default to synced leads

    // Basic filters
    county_id: '',
    lead_tier: '',
    min_score: '',
    max_score: '',
    is_qualified: '',

    // Pipeline intelligence filters
    recommended_pipeline: '',
    min_pipeline_confidence: '',
    contact_completeness: '',
    affluence_tier: '',

    // Property details
    min_hvac_age: '',
    max_hvac_age: '',
    min_property_value: '',
    max_property_value: '',
    year_built_min: '',
    year_built_max: '',

    // Contact information
    has_phone: '',
    has_email: '',

    // Advanced
    city: '',
    state: '',
  });

  const { data: leadsData, isLoading, error } = useLeads(filters);
  const { data: counties } = useCounties();

  const leads = leadsData?.leads || [];
  const total = leadsData?.total || 0;

  const handleFilterChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  // Calculate stats
  const syncedCount = filters.sync_status === 'synced' ? total : 0;
  const failedCount = filters.sync_status === 'failed' ? total : 0;

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
            <div className="flex gap-3">
              <button
                onClick={() => setFilters({ ...filters, sync_status: 'synced' })}
                className={`flex flex-col items-center px-4 py-2 rounded-lg transition-all ${
                  filters.sync_status === 'synced'
                    ? 'bg-green-50 border-2 border-green-600'
                    : 'bg-gray-50 border-2 border-gray-200 hover:border-green-400'
                }`}
              >
                <div className="flex items-center text-sm font-medium text-gray-700 mb-1">
                  <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                  Synced
                </div>
                <p className={`text-2xl font-bold ${
                  filters.sync_status === 'synced' ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {syncedCount}
                </p>
              </button>
              <button
                onClick={() => setFilters({ ...filters, sync_status: 'failed' })}
                className={`flex flex-col items-center px-4 py-2 rounded-lg transition-all ${
                  filters.sync_status === 'failed'
                    ? 'bg-red-50 border-2 border-red-600'
                    : 'bg-gray-50 border-2 border-gray-200 hover:border-red-400'
                }`}
              >
                <div className="flex items-center text-sm font-medium text-gray-700 mb-1">
                  <XCircle className="h-4 w-4 text-red-600 mr-1" />
                  Failed
                </div>
                <p className={`text-2xl font-bold ${
                  filters.sync_status === 'failed' ? 'text-red-600' : 'text-gray-400'
                }`}>
                  {failedCount}
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <FilterPanel
        filters={filters}
        onFilterChange={handleFilterChange}
        counties={counties}
        fixedFilters={[]}
      />

      {/* Leads Table */}
      <LeadsTable leads={leads} isLoading={isLoading} />
    </div>
  );
};

export default PipelinePage;
