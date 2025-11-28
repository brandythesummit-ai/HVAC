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
      <div className="rounded-md bg-red-50 p-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading leads</h3>
            <p className="mt-2 text-sm text-red-700">{error.message}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review and manage your HVAC leads from permit data
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center mb-3">
          <Filter className="h-5 w-5 text-gray-400 mr-2" />
          <h2 className="text-sm font-medium text-gray-900">Filters</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="county_id" className="block text-sm font-medium text-gray-700">
              County
            </label>
            <select
              id="county_id"
              name="county_id"
              value={filters.county_id}
              onChange={handleFilterChange}
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md"
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
            <label htmlFor="sync_status" className="block text-sm font-medium text-gray-700">
              Sync Status
            </label>
            <select
              id="sync_status"
              name="sync_status"
              value={filters.sync_status}
              onChange={handleFilterChange}
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="synced">Synced</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <LeadsTable leads={leads || []} isLoading={isLoading} />
    </div>
  );
};

export default LeadsPage;
