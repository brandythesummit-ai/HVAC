import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { AlertCircle, UserCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { useLeads, useDeleteLead } from '../hooks/useLeads';
import { useCounties } from '../hooks/useCounties';
import LeadsTable from '../components/leads/LeadsTable';
import FilterPanel from '../components/leads/FilterPanel';
import PaginationControls from '../components/leads/PaginationControls';

const LeadReviewPage = () => {
  const location = useLocation();

  // Lead Review: Show ONLY unsynced leads (pending or null sync status)
  const [filters, setFilters] = useState({
    // Fixed filters
    sync_status: 'pending', // FIXED: Only show pending leads for review

    // Basic filters
    county_id: location.state?.filterByCounty || '',
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

    // Pagination
    limit: 50,
    offset: 0,
  });

  const { data: leadsData, isLoading, error } = useLeads(filters);
  const { data: counties } = useCounties();
  const deleteLead = useDeleteLead();

  const leads = leadsData?.leads || [];
  const total = leadsData?.total || 0;

  const handleDelete = async (leadId) => {
    try {
      await deleteLead.mutateAsync(leadId);
      toast.success('Lead deleted successfully');
    } catch (error) {
      console.error('Failed to delete lead:', error);
      toast.error(`Failed to delete lead: ${error.message || 'Unknown error'}`);
      throw error; // Re-throw to let LeadRow know deletion failed
    }
  };

  const handleFilterChange = (e) => {
    if (e.type === 'reset') {
      setFilters(e.resetFilters);
    } else {
      setFilters({ ...filters, [e.target.name]: e.target.value, offset: 0 });
    }
  };

  const handleLimitChange = (newLimit) => {
    setFilters({ ...filters, limit: newLimit, offset: 0 });
  };

  const handlePageChange = (newOffset) => {
    setFilters({ ...filters, offset: newOffset });
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
      <FilterPanel
        filters={filters}
        onFilterChange={handleFilterChange}
        counties={counties}
        fixedFilters={['sync_status']}
      />

      {/* Leads Table */}
      <LeadsTable leads={leads} isLoading={isLoading} onDelete={handleDelete} />

      {/* Pagination Controls */}
      <PaginationControls
        total={total}
        limit={filters.limit}
        offset={filters.offset}
        onLimitChange={handleLimitChange}
        onPageChange={handlePageChange}
      />
    </div>
  );
};

export default LeadReviewPage;
