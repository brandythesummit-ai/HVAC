import { useState } from 'react';
import { Filter, AlertCircle } from 'lucide-react';
import { useLeads } from '../hooks/useLeads';
import { useCounties } from '../hooks/useCounties';
import LeadsTable from '../components/leads/LeadsTable';

const LeadsPage = () => {
  const [filters, setFilters] = useState({
    county_id: '',
    sync_status: '',
  });

  const { data: leads, isLoading, error } = useLeads(filters);
  const { data: counties } = useCounties();

  const handleFilterChange = (e) => {
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
      {/* Filters */}
      <div className="card animate-fade-in">
        <div className="card-header">
          <div className="flex items-center">
            <Filter className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
          </div>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="synced">Synced</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <LeadsTable leads={leads || []} isLoading={isLoading} />
    </div>
  );
};

export default LeadsPage;
